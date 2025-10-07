
"""
Callback safety utilities
Import from unified error_handler
"""
import functools
from pyrogram import Client
from pyrogram.types import CallbackQuery
from bot.logging import LOGGER

logger = LOGGER(__name__)

from bot.utils.error_handler import safe_callback_handler

# Re-export for backward compatibility
__all__ = ['safe_callback_handler']

def _safe_callback_handler(func):
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
    """Comprehensive handler removal error suppression"""
    
    # Patch Client.remove_handler
    original_remove_handler = Client.remove_handler
    
    def safe_remove_handler(self, handler, group: int = 0):
        try:
            # Check if handler exists before removing
            if hasattr(self, 'dispatcher') and hasattr(self.dispatcher, 'groups'):
                if group in self.dispatcher.groups:
                    if handler not in self.dispatcher.groups[group]:
                        logger.debug(f"Handler not in group {group}, skipping removal")
                        return
            
            return original_remove_handler(self, handler, group)
        except ValueError as e:
            if "list.remove(x): x not in list" in str(e):
                logger.debug(f"Handler removal suppressed: {e}")
                return  # Silently ignore
            raise  # Re-raise other ValueErrors
        except Exception as e:
            logger.debug(f"Unexpected error in remove_handler: {e}")
            return  # Ignore all removal errors
    
    Client.remove_handler = safe_remove_handler
    
    # Patch dispatcher's remove_handler method if it exists
    try:
        from pyrogram.dispatcher import Dispatcher
        if hasattr(Dispatcher, 'remove_handler'):
            original_dispatcher_remove = Dispatcher.remove_handler
            
            def safe_dispatcher_remove(self, handler, group: int = 0):
                try:
                    # Check if group and handler exist
                    if group not in self.groups:
                        logger.debug(f"Group {group} not found in dispatcher")
                        return
                    
                    if handler not in self.groups[group]:
                        logger.debug(f"Handler not found in group {group}")
                        return
                    
                    return original_dispatcher_remove(self, handler, group)
                except ValueError as e:
                    if "list.remove(x): x not in list" in str(e):
                        logger.debug(f"Dispatcher handler removal suppressed: {e}")
                        return
                    raise
                except Exception as e:
                    logger.debug(f"Dispatcher removal error suppressed: {e}")
                    return
            
            Dispatcher.remove_handler = safe_dispatcher_remove
            logger.debug("✅ Dispatcher remove_handler patched")
    except ImportError:
        logger.debug("Dispatcher patching skipped - not available")
    
    logger.info("✅ Handler removal error suppression enabled")

# Initialize suppression when module is imported
suppress_handler_removal_errors()
