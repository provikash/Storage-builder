import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable, Union
from pyrogram.errors import (
    FloodWait, UserIsBlocked, ChatWriteForbidden,
    MessageNotModified, ButtonDataInvalid, QueryIdInvalid,
    MessageIdInvalid, UserNotParticipant, ChannelPrivate
)
from functools import wraps

# Assuming bot.logging exists and provides get_context_logger
# If not, a placeholder or direct use of logging.getLogger would be needed.
# For this example, we'll assume it exists and works as expected.
try:
    from bot.logging import get_context_logger
except ImportError:
    # Placeholder if bot.logging is not available in this context
    def get_context_logger(name):
        logger = logging.getLogger(name)
        # Add any default handlers or formatters if needed for the placeholder
        return logger

logger = get_context_logger(__name__)

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

def safe_execute(
    func: Callable,
    *args,
    config: Optional[ErrorRecoveryConfig] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """Safely execute function with enhanced error handling and recovery"""
    config = config or ErrorRecoveryConfig()
    context = context or {}

    func_name = getattr(func, '__name__', str(func))

    for attempt in range(config.max_retries + 1):
        try:
            result = func(*args, **kwargs)

            if attempt > 0:
                logger.info(
                    f"Function succeeded after {attempt} retries",
                    function=func_name,
                    attempt=attempt,
                    **context
                )

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
                    logger.warning(
                        f"Function failed, retrying in {delay}s",
                        retry_delay=delay,
                        **error_context
                    )

                import time
                time.sleep(delay)
            else:
                if config.log_errors:
                    logger.error(
                        "Function failed after all retry attempts",
                        **error_context
                    )

                if config.raise_on_final_failure:
                    raise

                return config.fallback_value

async def safe_execute_async(
    func: Callable,
    *args,
    config: Optional[ErrorRecoveryConfig] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """Safely execute async function with enhanced error handling and recovery"""
    config = config or ErrorRecoveryConfig()
    context = context or {}

    func_name = getattr(func, '__name__', str(func))

    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # This branch might be less common if expecting async funcs,
                # but included for completeness if a sync func is passed.
                result = func(*args, **kwargs)

            if attempt > 0:
                logger.info(
                    f"Function succeeded after {attempt} retries",
                    function=func_name,
                    attempt=attempt,
                    **context
                )

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
                    logger.warning(
                        f"Function failed, retrying in {delay}s",
                        retry_delay=delay,
                        **error_context
                    )

                await asyncio.sleep(delay)
            else:
                if config.log_errors:
                    logger.error(
                        "Function failed after all retry attempts",
                        **error_context
                    )

                if config.raise_on_final_failure:
                    raise

                return config.fallback_value

def resilient(config: Optional[ErrorRecoveryConfig] = None, context: Optional[Dict[str, Any]] = None):
    """Decorator for resilient function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await safe_execute_async(func, *args, config=config, context=context, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return safe_execute(func, *args, config=config, context=context, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

class ProductionErrorHandler:
    """Production-ready error handler with comprehensive logging and recovery"""

    def __init__(self):
        # These attributes are now less central as safe_execute handles retries
        # but can be kept for other potential uses or monitoring.
        self.error_counts = {}
        self.max_error_count = 10
        self.error_window = 3600  # 1 hour

    async def handle_error(self, error: Exception, context: str, user_id: Optional[int] = None) -> str:
        """Handle errors with appropriate responses and logging"""

        # Log the error using the enhanced logging mechanism
        await self.log_error(error, context, user_id)

        # Track error frequency (This logic might be redundant with
        # the retry mechanism in safe_execute, but can serve as a different
        # type of rate limiting or alert mechanism).
        error_key = f"{type(error).__name__}:{context}"
        current_time = asyncio.get_event_loop().time()

        if error_key not in self.error_counts:
            self.error_counts[error_key] = []

        # Clean old errors
        self.error_counts[error_key] = [
            t for t in self.error_counts[error_key]
            if current_time - t < self.error_window
        ]

        self.error_counts[error_key].append(current_time)

        # Check if error is too frequent
        if len(self.error_counts[error_key]) > self.max_error_count:
            logger.critical(f"Too many {error_key} errors in the last hour!")
            return "System temporarily unavailable. Please try again later."

        # Handle specific error types
        if isinstance(error, FloodWait):
            wait_time = error.value
            logger.warning(f"FloodWait: {wait_time} seconds in {context}")
            if wait_time < 60:
                # The retry logic is now handled by safe_execute/resilient decorator.
                # This part is more about informing the user or handling immediate retries.
                # await asyncio.sleep(wait_time + 1) # Moved to safe_execute
                return f"Rate limited. Please try again in {wait_time} seconds." # Informative message
            else:
                return f"Rate limited. Please try again in {wait_time // 60} minutes."

        elif isinstance(error, UserIsBlocked):
            logger.warning(f"User {user_id} blocked the bot", user_id=user_id)
            return "Unable to send message - bot is blocked."

        elif isinstance(error, ChatWriteForbidden):
            logger.error(f"Chat write forbidden in {context}", context=context, user_id=user_id)
            return "Cannot send messages to this chat."

        elif isinstance(error, (MessageNotModified, ButtonDataInvalid, QueryIdInvalid)):
            logger.warning(f"Message/Query error in {context}: {error}", context=context)
            return None  # Silent handling for UI errors

        elif isinstance(error, MessageIdInvalid):
            logger.warning(f"Invalid message ID in {context}", context=context)
            return "Message no longer available."

        elif isinstance(error, (UserNotParticipant, ChannelPrivate)):
            logger.warning(f"Access denied in {context}", context=context, user_id=user_id)
            return "Access denied or channel is private."

        else:
            # For any other unhandled exceptions, log them and return a generic message.
            # The specific traceback is already logged in log_error.
            logger.error(f"Unhandled error in {context}", context=context, error_message=str(error), user_id=user_id)
            return "An unexpected error occurred. Please try again."

    async def log_error(self, error: Exception, context: str, user_id: Optional[int] = None):
        """Log error details with full context using the enhanced logger"""
        error_details = {
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }

        # Using the context logger for structured logging
        logger.error(
            "Error encountered",
            exc_info=True, # Include traceback automatically if needed by logger setup
            context=context,
            user_id=user_id,
            error_type=type(error).__name__,
            error_message=str(error)
            # traceback is already formatted, can be added as a field if logger supports it
        )

        # Store critical errors for monitoring
        if isinstance(error, (ConnectionError, TimeoutError, OSError)): # Added OSError as a common critical system error
            logger.critical(
                "Critical system error detected",
                exc_info=True,
                context=context,
                user_id=user_id,
                error_type=type(error).__name__,
                error_message=str(error)
            )

    # The safe_execute method from the original class is now replaced by the standalone functions.
    # If this class is meant to be instantiated and used, its methods should either call
    # the new global functions or be refactored to use the same underlying logic.
    # For now, we'll assume the standalone functions are the primary mechanism.
    async def safe_execute(self, func, *args, context: str = "unknown", user_id: Optional[int] = None, **kwargs):
        """
        Safely execute a function with error handling.
        This method now acts as a wrapper to the global safe_execute_async or safe_execute.
        It translates the older context string to the new context dictionary if needed.
        """
        # Adapt the single string context to a dictionary for the new functions
        new_context = {"operation": context}
        if user_id:
            new_context["user_id"] = user_id

        # Determine if the function is async
        if asyncio.iscoroutinefunction(func):
            return await safe_execute_async(func, *args, context=new_context, **kwargs)
        else:
            return safe_execute(func, *args, context=new_context, **kwargs)


# Global instance of the error handler
error_handler = ProductionErrorHandler()