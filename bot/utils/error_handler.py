import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable
from pyrogram.errors import (
    FloodWait, UserIsBlocked, ChatWriteForbidden,
    MessageNotModified, ButtonDataInvalid, QueryIdInvalid,
    MessageIdInvalid, UserNotParticipant, ChannelPrivate
)
from functools import wraps
from bot.logging import LOGGER

logger = LOGGER(__name__)

class ErrorRecoveryConfig:
    """Configuration for error recovery strategies"""
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
        fallback_value: Any = None,
        log_errors: bool = True,
        raise_on_final_failure: bool = False
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.fallback_value = fallback_value
        self.log_errors = log_errors
        self.raise_on_final_failure = raise_on_final_failure

async def safe_edit_message(query, text, **kwargs):
    """Safely edit a message, handling common errors"""
    try:
        return await query.edit_message_text(text, **kwargs)
    except MessageNotModified:
        await query.answer()
        return None
    except (QueryIdInvalid, ButtonDataInvalid):
        await query.answer("This button has expired.", show_alert=True)
        return None
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return None

async def handle_callback_error(client, query, error: Exception, context: str) -> bool:
    """Handle callback query errors centrally"""
    user_id = query.from_user.id
    callback_data = getattr(query, 'data', 'unknown')

    logger.error(f"Callback error in {context}: {error}", user_id=user_id, callback_data=callback_data, exc_info=True)

    try:
        if isinstance(error, MessageNotModified):
            await query.answer()
            return True
        elif isinstance(error, (QueryIdInvalid, ButtonDataInvalid)):
            await query.answer("❌ This button has expired. Please try again.", show_alert=True)
            return True
        else:
            error_msg = f"❌ An error occurred in {context}. Please try again."
            try:
                await query.answer(error_msg, show_alert=True)
            except:
                logger.error(f"Failed to answer query after error in {context}")
            return False
    except Exception as handler_error:
        logger.error(f"Error in error handler for {context}: {handler_error}")
        return False

def safe_callback_handler(func):
    """Decorator for safe callback handling"""
    @wraps(func)
    async def wrapper(client, query):
        try:
            try:
                await query.answer()
            except:
                pass
            return await func(client, query)
        except Exception as e:
            logger.error(f"❌ Error in callback handler {func.__name__}: {e}")
            try:
                if query.message:
                    error_text = "❌ Button temporarily unresponsive. Please try again or use /start"
                    try:
                        await query.edit_message_text(error_text)
                    except:
                        try:
                            await query.answer(error_text, show_alert=True)
                        except:
                            pass
            except Exception as notify_error:
                logger.error(f"Failed to notify user of callback error: {notify_error}")
    return wrapper

async def safe_execute_async(func, *args, config: Optional[ErrorRecoveryConfig] = None, context: Optional[Dict[str, Any]] = None, **kwargs):
    """Safely execute async function with error handling and recovery"""
    config = config or ErrorRecoveryConfig()
    context = context or {}
    func_name = getattr(func, '__name__', str(func))

    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            if attempt > 0:
                logger.info(f"Function {func_name} succeeded after {attempt} retries")
            return result

        except Exception as e:
            error_context = {
                "function": func_name,
                "attempt": attempt + 1,
                "max_attempts": config.max_retries + 1,
                "error": str(e),
                "error_type": type(e).__name__,
                **context
            }

            if attempt < config.max_retries:
                delay = config.retry_delay
                if config.exponential_backoff:
                    delay *= (2 ** attempt)

                if config.log_errors:
                    logger.warning(f"Function {func_name} failed, retrying in {delay}s", **error_context)

                await asyncio.sleep(delay)
            else:
                if config.log_errors:
                    logger.error(f"Function {func_name} failed after all retries", **error_context)

                if config.raise_on_final_failure:
                    raise

                return config.fallback_value

class ProductionErrorHandler:
    """Production-ready error handler"""
    def __init__(self):
        self.error_counts = {}
        self.max_error_count = 10
        self.error_window = 3600

    async def handle_error(self, error: Exception, context: str, user_id: Optional[int] = None) -> str:
        """Handle errors with appropriate responses"""
        await self.log_error(error, context, user_id)

        error_key = f"{type(error).__name__}:{context}"
        current_time = asyncio.get_event_loop().time()

        if error_key not in self.error_counts:
            self.error_counts[error_key] = []

        self.error_counts[error_key] = [t for t in self.error_counts[error_key] if current_time - t < self.error_window]
        self.error_counts[error_key].append(current_time)

        if len(self.error_counts[error_key]) > self.max_error_count:
            logger.critical(f"Too many {error_key} errors in the last hour!")
            return "System temporarily unavailable. Please try again later."

        if isinstance(error, FloodWait):
            wait_time = error.value
            logger.warning(f"FloodWait: {wait_time} seconds in {context}")
            return f"Rate limited. Please try again in {wait_time} seconds." if wait_time < 60 else f"Rate limited. Please try again in {wait_time // 60} minutes."
        elif isinstance(error, UserIsBlocked):
            logger.warning(f"User {user_id} blocked the bot", user_id=user_id)
            return "Unable to send message - bot is blocked."
        elif isinstance(error, ChatWriteForbidden):
            logger.error(f"Chat write forbidden in {context}", context=context, user_id=user_id)
            return "Cannot send messages to this chat."
        elif isinstance(error, (MessageNotModified, ButtonDataInvalid, QueryIdInvalid)):
            logger.warning(f"Message/Query error in {context}: {error}", context=context)
            return None
        elif isinstance(error, MessageIdInvalid):
            logger.warning(f"Invalid message ID in {context}", context=context)
            return "Message no longer available."
        elif isinstance(error, (UserNotParticipant, ChannelPrivate)):
            logger.warning(f"Access denied in {context}", context=context, user_id=user_id)
            return "Access denied or channel is private."
        else:
            logger.error(f"Unhandled error in {context}", context=context, error_message=str(error), user_id=user_id)
            return "An unexpected error occurred. Please try again."

    async def log_error(self, error: Exception, context: str, user_id: Optional[int] = None):
        """Log error details"""
        logger.error("Error encountered", exc_info=True, context=context, user_id=user_id, error_type=type(error).__name__, error_message=str(error))

        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            logger.critical("Critical system error detected", exc_info=True, context=context, user_id=user_id, error_type=type(error).__name__, error_message=str(error))

error_handler = ProductionErrorHandler()