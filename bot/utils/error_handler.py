
import logging
import traceback
from functools import wraps
from typing import Callable, Any
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import (
    FloodWait, UserIsBlocked, ChatAdminRequired,
    MessageNotModified, QueryIdInvalid, UserNotParticipant,
    ChatWriteForbidden, MessageIdInvalid
)
import asyncio

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling system"""
    
    @staticmethod
    async def handle_pyrogram_error(error: Exception, context: str = "Unknown") -> str:
        """Handle Pyrogram-specific errors"""
        
        if isinstance(error, FloodWait):
            wait_time = error.value
            logger.warning(f"FloodWait: {wait_time}s in {context}")
            await asyncio.sleep(wait_time)
            return f"Rate limited. Please wait {wait_time} seconds."
        
        elif isinstance(error, UserIsBlocked):
            logger.warning(f"User blocked bot in {context}")
            return "Unable to send message - user has blocked the bot."
        
        elif isinstance(error, ChatAdminRequired):
            logger.error(f"Admin rights required in {context}")
            return "Bot needs admin rights to perform this action."
        
        elif isinstance(error, MessageNotModified):
            logger.debug(f"Message not modified in {context}")
            return "Message content is already up to date."
        
        elif isinstance(error, QueryIdInvalid):
            logger.warning(f"Invalid query ID in {context}")
            return "This button has expired. Please try again."
        
        elif isinstance(error, UserNotParticipant):
            logger.info(f"User not participant in {context}")
            return "You need to join the required channel first."
        
        elif isinstance(error, ChatWriteForbidden):
            logger.error(f"Write forbidden in {context}")
            return "Bot cannot send messages to this chat."
        
        elif isinstance(error, MessageIdInvalid):
            logger.warning(f"Invalid message ID in {context}")
            return "Message not found or has been deleted."
        
        else:
            logger.error(f"Unhandled Pyrogram error in {context}: {error}")
            return "An unexpected error occurred. Please try again later."

    @staticmethod
    async def log_error(error: Exception, context: str, user_id: int = None):
        """Log detailed error information"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }
        
        logger.error(f"Error in {context}: {error_info}")

def error_handler(context: str = "Unknown"):
    """Decorator for handling errors in bot functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Try to extract user_id and client from args
                user_id = None
                client = None
                message = None
                
                for arg in args:
                    if isinstance(arg, Client):
                        client = arg
                    elif isinstance(arg, (Message, CallbackQuery)):
                        message = arg
                        user_id = arg.from_user.id if arg.from_user else None
                
                # Log the error
                await ErrorHandler.log_error(e, context, user_id)
                
                # Handle Pyrogram errors
                error_message = await ErrorHandler.handle_pyrogram_error(e, context)
                
                # Try to send error message to user
                if message and client:
                    try:
                        if isinstance(message, CallbackQuery):
                            await message.answer(error_message, show_alert=True)
                        else:
                            await message.reply_text(f"❌ {error_message}")
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
                
                return None
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, **kwargs):
    """Safely execute a function with error handling"""
    try:
        if asyncio.iscoroutinefunction(func):
            return asyncio.create_task(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in safe_execute: {e}")
        return None
