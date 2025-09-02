import logging
import traceback
import asyncio
from typing import Optional, Dict, Any
from pyrogram.errors import (
    FloodWait, UserIsBlocked, ChatWriteForbidden,
    MessageNotModified, ButtonDataInvalid, QueryIdInvalid,
    MessageIdInvalid, UserNotParticipant, ChannelPrivate
)

logger = logging.getLogger(__name__)

class ProductionErrorHandler:
    """Production-ready error handler with comprehensive logging and recovery"""

    def __init__(self):
        self.error_counts = {}
        self.max_error_count = 10
        self.error_window = 3600  # 1 hour

    async def handle_error(self, error: Exception, context: str, user_id: Optional[int] = None) -> str:
        """Handle errors with appropriate responses and logging"""

        # Log the error
        await self.log_error(error, context, user_id)

        # Track error frequency
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
                await asyncio.sleep(wait_time + 1)
                return None  # Retry after waiting
            else:
                return f"Rate limited. Please try again in {wait_time // 60} minutes."

        elif isinstance(error, UserIsBlocked):
            logger.warning(f"User {user_id} blocked the bot")
            return "Unable to send message - bot is blocked."

        elif isinstance(error, ChatWriteForbidden):
            logger.error(f"Chat write forbidden in {context}")
            return "Cannot send messages to this chat."

        elif isinstance(error, (MessageNotModified, ButtonDataInvalid, QueryIdInvalid)):
            logger.warning(f"Message/Query error in {context}: {error}")
            return None  # Silent handling for UI errors

        elif isinstance(error, MessageIdInvalid):
            logger.warning(f"Invalid message ID in {context}")
            return "Message no longer available."

        elif isinstance(error, (UserNotParticipant, ChannelPrivate)):
            logger.warning(f"Access denied in {context}")
            return "Access denied or channel is private."

        else:
            logger.error(f"Unhandled error in {context}: {error}")
            return "An unexpected error occurred. Please try again."

    async def log_error(self, error: Exception, context: str, user_id: Optional[int] = None):
        """Log error details with full context"""
        error_details = {
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }

        logger.error(f"Error in {context}: {error_details}")

        # Store critical errors for monitoring
        if isinstance(error, (ConnectionError, TimeoutError)):
            logger.critical(f"Critical system error: {error_details}")

    async def safe_execute(self, func, *args, context: str = "unknown", user_id: Optional[int] = None, **kwargs):
        """Safely execute a function with error handling"""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            error_msg = await self.handle_error(e, context, user_id)
            if error_msg:
                logger.warning(f"Error handled in {context}: {error_msg}")
            return None

# Global instance
error_handler = ProductionErrorHandler()