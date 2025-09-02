import asyncio
from typing import Dict, Set, Optional, Any
from pyrogram import Client
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot.logging import LOGGER

logger = LOGGER(__name__)

class HandlerManager:
    """Centralized handler management to prevent removal errors"""

    def __init__(self):
        self.registered_handlers: Dict[str, Set[Any]] = {}
        self.client_handlers: Dict[str, Dict[int, list]] = {}

    def register_handler(self, client: Client, handler: Any, group: int = 0):
        """Register a handler for tracking"""
        client_id = str(id(client))

        if client_id not in self.registered_handlers:
            self.registered_handlers[client_id] = set()

        if client_id not in self.client_handlers:
            self.client_handlers[client_id] = {}

        if group not in self.client_handlers[client_id]:
            self.client_handlers[client_id][group] = []

        self.registered_handlers[client_id].add(handler)
        self.client_handlers[client_id][group].append(handler)

        # Add to client
        try:
            client.add_handler(handler, group)
            logger.debug(f"✅ Handler registered in group {group}")
        except Exception as e:
            logger.error(f"❌ Error registering handler: {e}")

    async def safe_remove_handler(self, client: Client, handler: Any, group: int = 0) -> bool:
        """Safely remove handler without errors"""
        try:
            client_id = str(id(client))

            # Check if we're tracking this handler
            if client_id not in self.registered_handlers:
                logger.debug(f"Client {client_id} not in registered handlers")
                return False

            if handler not in self.registered_handlers[client_id]:
                logger.debug(f"Handler not in registered handlers for client {client_id}")
                return False

            # Check if client has dispatcher
            if not hasattr(client, 'dispatcher'):
                logger.debug(f"Client has no dispatcher, cleaning up tracking")
                self._cleanup_handler_tracking(client_id, handler, group)
                return False

            # Check if dispatcher has groups
            if not hasattr(client.dispatcher, 'groups'):
                logger.debug(f"Dispatcher has no groups, cleaning up tracking")
                self._cleanup_handler_tracking(client_id, handler, group)
                return False

            # Check if group exists
            if group not in client.dispatcher.groups:
                logger.debug(f"Group {group} not in dispatcher groups, cleaning up tracking")
                self._cleanup_handler_tracking(client_id, handler, group)
                return False

            # Check if handler exists in group
            if handler not in client.dispatcher.groups[group]:
                logger.debug(f"Handler not in group {group}, cleaning up tracking")
                self._cleanup_handler_tracking(client_id, handler, group)
                return False

            # Perform the removal with comprehensive error handling
            try:
                # The callback_safety.py patches should handle the actual ValueError
                client.remove_handler(handler, group)
                self._cleanup_handler_tracking(client_id, handler, group)
                logger.debug(f"✅ Successfully removed handler from group {group}")
                return True
            except ValueError as ve:
                if "list.remove(x): x not in list" in str(ve):
                    logger.debug(f"Handler already removed from group {group}")
                    self._cleanup_handler_tracking(client_id, handler, group)
                    return False
                else:
                    logger.debug(f"Unexpected ValueError removing handler: {ve}")
                    self._cleanup_handler_tracking(client_id, handler, group)
                    return False
            except Exception as e:
                logger.debug(f"Unexpected error removing handler: {e}")
                self._cleanup_handler_tracking(client_id, handler, group)
                return False

        except Exception as e:
            logger.debug(f"Error in safe_remove_handler: {e}")
            # Clean up tracking on any failure
            try:
                client_id = str(id(client))
                self._cleanup_handler_tracking(client_id, handler, group)
            except:
                pass
            return False

    def _cleanup_handler_tracking(self, client_id: str, handler: Any, group: int):
        """Helper method to clean up handler tracking"""
        try:
            if client_id in self.registered_handlers:
                self.registered_handlers[client_id].discard(handler)
            if client_id in self.client_handlers and group in self.client_handlers[client_id]:
                if handler in self.client_handlers[client_id][group]:
                    self.client_handlers[client_id][group].remove(handler)
        except Exception:
            pass  # Ignore cleanup errors

    async def cleanup_all_handlers(self, client: Client):
        """Cleanup all handlers for a client"""
        try:
            client_id = str(id(client))

            if client_id not in self.registered_handlers:
                logger.debug(f"No handlers to cleanup for client {client_id}")
                return

            # Get current dispatcher state to avoid removal errors
            if not hasattr(client, 'dispatcher') or not hasattr(client.dispatcher, 'groups'):
                logger.debug(f"Client dispatcher not available, clearing tracking only")
                # Just clear our tracking
                if client_id in self.registered_handlers:
                    self.registered_handlers[client_id].clear()
                if client_id in self.client_handlers:
                    self.client_handlers[client_id].clear()
                return

            removed_count = 0
            
            # Check each group and remove only handlers that actually exist
            for group, group_handlers in client.dispatcher.groups.items():
                if client_id in self.client_handlers and group in self.client_handlers[client_id]:
                    handlers_in_group = list(self.client_handlers[client_id][group])
                    
                    for handler in handlers_in_group:
                        if handler in group_handlers:  # Only remove if actually present
                            try:
                                client.remove_handler(handler, group)
                                removed_count += 1
                                logger.debug(f"✅ Removed handler from group {group}")
                            except ValueError:
                                # Handler was already removed
                                logger.debug(f"Handler already removed from group {group}")
                            except Exception as e:
                                logger.debug(f"Error removing handler from group {group}: {e}")

            # Clear all tracking after cleanup
            if client_id in self.registered_handlers:
                self.registered_handlers[client_id].clear()
            if client_id in self.client_handlers:
                self.client_handlers[client_id].clear()

            logger.info(f"✅ Cleaned up {removed_count} handlers for client")

        except Exception as e:
            logger.error(f"❌ Error cleaning up handlers: {e}")
            # Force clear tracking even on error
            try:
                client_id = str(id(client))
                if client_id in self.registered_handlers:
                    self.registered_handlers[client_id].clear()
                if client_id in self.client_handlers:
                    self.client_handlers[client_id].clear()
            except:
                pass

    def get_handler_count(self, client: Client) -> int:
        """Get number of registered handlers for a client"""
        client_id = str(id(client))
        if client_id in self.registered_handlers:
            return len(self.registered_handlers[client_id])
        return 0

    def handler_exists(self, client: Client, handler: Any, group: int = 0) -> bool:
        """Check if a handler exists in the client's dispatcher"""
        try:
            if not hasattr(client, 'dispatcher') or not hasattr(client.dispatcher, 'groups'):
                return False
            
            if group not in client.dispatcher.groups:
                return False
            
            return handler in client.dispatcher.groups[group]
        except Exception:
            return False

    def safe_remove_if_exists(self, client: Client, handler: Any, group: int = 0) -> bool:
        """Remove handler only if it exists, without any errors"""
        try:
            if not self.handler_exists(client, handler, group):
                return False
            
            # Use the existing safe removal method
            return asyncio.run(self.safe_remove_handler(client, handler, group))
        except Exception:
            return False

# Global instance
handler_manager = HandlerManager()

async def register_handlers(app):
    """Register all handlers with the app"""
    try:
        logger.info("🔄 Starting handler registration...")

        # Don't clear handlers - let Pyrogram manage them
        # Just import plugins to register their handlers

        # Import core handlers first
        from bot.plugins import callback_fix  # Emergency handlers first
        from bot.plugins import start_handler
        from bot.plugins import callback_handlers
        from bot.plugins import search
        from bot.plugins import clone_admin_settings

        # Import other plugin handlers
        from bot.plugins import (
            admin_commands,
            mother_admin,
            step_clone_creation,
            premium,
            balance_management,
            referral_program,
            token,
            index,
            genlink,
            stats,
            broadcast,
            callback
        )

        logger.info("✅ All handlers registered successfully")

    except Exception as e:
        logger.error(f"❌ Error registering handlers: {e}")
        raise