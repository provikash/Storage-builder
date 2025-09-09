
"""
Centralized error handling for callback queries
"""
import traceback
from typing import Optional
from pyrogram import Client
from pyrogram.types import CallbackQuery
from pyrogram.errors import MessageNotModified, QueryIdInvalid, ButtonDataInvalid
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def handle_callback_error(client: Client, query: CallbackQuery, error: Exception, context: str) -> bool:
    """
    Handle callback query errors centrally
    
    Returns:
        bool: True if error was handled gracefully, False if critical
    """
    user_id = query.from_user.id
    callback_data = getattr(query, 'data', 'unknown')
    
    # Log the error with context
    logger.error(f"Callback error in {context}: {error}", 
                user_id=user_id, 
                callback_data=callback_data,
                exc_info=True)
    
    try:
        # Handle specific error types
        if isinstance(error, MessageNotModified):
            # Message content is the same, just acknowledge
            await query.answer()
            return True
            
        elif isinstance(error, (QueryIdInvalid, ButtonDataInvalid)):
            # Query is too old or invalid
            await query.answer("❌ This button has expired. Please try again.", show_alert=True)
            return True
            
        elif isinstance(error, Exception):
            # Generic error handling
            error_msg = f"❌ An error occurred in {context}. Please try again."
            
            try:
                await query.answer(error_msg, show_alert=True)
            except:
                # If we can't even answer the query, just log it
                logger.error(f"Failed to answer query after error in {context}")
                
            return False
            
    except Exception as handler_error:
        logger.error(f"Error in error handler for {context}: {handler_error}")
        return False

def safe_callback_handler(func):
    """Decorator for safe callback handling with centralized error management"""
    async def wrapper(client: Client, query: CallbackQuery):
        try:
            return await func(client, query)
        except Exception as e:
            context = func.__name__.replace('_', ' ').title()
            await handle_callback_error(client, query, e, context)
    
    return wrapper
