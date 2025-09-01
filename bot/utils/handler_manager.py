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
                logger.debug(f"No handlers tracked for client {client_id}")
                return False

            if handler not in self.registered_handlers[client_id]:
                logger.debug(f"Handler not tracked, skipping removal")
                return False

            # Check if handler exists in dispatcher groups
            if not hasattr(client, 'dispatcher') or not hasattr(client.dispatcher, 'groups'):
                logger.debug(f"Client dispatcher not available")
                return False

            if group not in client.dispatcher.groups:
                logger.debug(f"Group {group} not found in dispatcher")
                return False

            if handler not in client.dispatcher.groups[group]:
                logger.debug(f"Handler not found in group {group}")
                # Remove from our tracking anyway
                self.registered_handlers[client_id].discard(handler)
                if client_id in self.client_handlers and group in self.client_handlers[client_id]:
                    if handler in self.client_handlers[client_id][group]:
                        self.client_handlers[client_id][group].remove(handler)
                return False

            # Safe removal
            client.remove_handler(handler, group)

            # Update tracking
            self.registered_handlers[client_id].discard(handler)
            if client_id in self.client_handlers and group in self.client_handlers[client_id]:
                if handler in self.client_handlers[client_id][group]:
                    self.client_handlers[client_id][group].remove(handler)

            logger.debug(f"✅ Handler removed safely from group {group}")
            return True

        except (ValueError, KeyError, AttributeError) as e:
            logger.debug(f"Handler removal failed (expected): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error removing handler: {e}")
            return False

    async def cleanup_all_handlers(self, client: Client):
        """Cleanup all handlers for a client"""
        try:
            client_id = str(id(client))

            if client_id not in self.registered_handlers:
                logger.debug(f"No handlers to cleanup for client {client_id}")
                return

            handlers_to_remove = list(self.registered_handlers[client_id])
            removed_count = 0

            for handler in handlers_to_remove:
                # Try to find which group this handler is in
                for group in range(10):  # Check groups 0-9
                    if await self.safe_remove_handler(client, handler, group):
                        removed_count += 1
                        break

            # Clear tracking
            if client_id in self.registered_handlers:
                self.registered_handlers[client_id].clear()
            if client_id in self.client_handlers:
                self.client_handlers[client_id].clear()

            logger.info(f"✅ Cleaned up {removed_count} handlers for client")

        except Exception as e:
            logger.error(f"❌ Error cleaning up handlers: {e}")

    def get_handler_count(self, client: Client) -> int:
        """Get number of registered handlers for a client"""
        client_id = str(id(client))
        if client_id in self.registered_handlers:
            return len(self.registered_handlers[client_id])
        return 0

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