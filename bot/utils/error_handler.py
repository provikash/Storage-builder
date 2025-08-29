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
            # Don't sleep here in error handler, let the caller handle it
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
            logger.error(f"Chat write forbidden in {context}")
            return "Cannot send messages to this chat."

        else:
            logger.error(f"Unhandled error in {context}: {error}")
            return f"An unexpected error occurred: {str(error)}"

    @staticmethod
    async def log_error(error: Exception, context: str, user_id: int = None):
        """Log error details"""
        error_details = {
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }

        logger.error(f"Error in {context}: {error_details}")

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
import asyncio
import logging
from pyrogram.errors import MessageNotModified, FloodWait
from info import Config

logger = logging.getLogger(__name__)

async def safe_edit_message(query, text, reply_markup=None, parse_mode="Markdown"):
    """Safely edit a message with comprehensive error handling"""
    try:
        # Check if message content is the same to avoid MESSAGE_NOT_MODIFIED error
        if hasattr(query.message, 'text') and query.message.text == text:
            logger.info("Message content unchanged, skipping edit")
            await query.answer()
            return True

        if reply_markup:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        return True
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            # Fallback: Try to answer the callback
            await query.answer("❌ Error updating message. Please try again.", show_alert=True)
        except:
            pass
        return False

async def safe_answer_callback(query, text="", show_alert=False):
    """Safely answer callback query"""
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"Error answering callback: {e}")

def handle_database_lock():
    """Handle SQLite database lock by using in-memory storage"""
    try:
        import os
        session_files = [f for f in os.listdir('.') if f.endswith('.session')]
        for session_file in session_files:
            if os.path.exists(session_file + '-journal'):
                os.remove(session_file + '-journal')
                logger.info(f"Removed journal file: {session_file}-journal")
    except Exception as e:
        logger.error(f"Error handling database lock: {e}")