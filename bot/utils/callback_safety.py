
import asyncio
import functools
from pyrogram import Client
from pyrogram.types import CallbackQuery
from bot.logging import LOGGER

logger = LOGGER(__name__)

def safe_callback_handler(func):
    """Decorator to safely handle callbacks and prevent task exceptions"""
    @functools.wraps(func)
    async def wrapper(client: Client, query: CallbackQuery):
        try:
            # Ensure query is answered to prevent timeout
            try:
                await query.answer()
            except Exception:
                pass  # Query might already be answered
            
            # Execute the actual handler
            return await func(client, query)
            
        except Exception as e:
            logger.error(f"❌ Error in callback handler {func.__name__}: {e}")
            
            # Try to notify user of error
            try:
                if not query.message:
                    return
                    
                error_text = "❌ Button temporarily unresponsive. Please try again or use /start"
                
                try:
                    await query.edit_message_text(error_text)
                except Exception:
                    # If edit fails, try answering with alert
                    try:
                        await query.answer(error_text, show_alert=True)
                    except Exception:
                        pass  # Give up gracefully
                        
            except Exception as notify_error:
                logger.error(f"Failed to notify user of callback error: {notify_error}")
    
    return wrapper

def suppress_handler_removal_errors():
    """Suppress handler removal errors by patching the remove_handler method"""
    original_remove_handler = Client.remove_handler
    
    def safe_remove_handler(self, handler, group: int = 0):
        try:
            return original_remove_handler(self, handler, group)
        except ValueError as e:
            if "list.remove(x): x not in list" in str(e):
                logger.debug(f"Handler removal suppressed: {e}")
                return  # Silently ignore
            raise  # Re-raise other ValueErrors
        except Exception as e:
            logger.error(f"Unexpected error in remove_handler: {e}")
            raise
    
    # Monkey patch the method
    Client.remove_handler = safe_remove_handler
    logger.info("✅ Handler removal error suppression enabled")

# Initialize suppression when module is imported
suppress_handler_removal_errors()
