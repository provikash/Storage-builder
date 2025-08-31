
<file_path>bot/utils/handler_manager.py</file_path>
<line_number>1</line_number>
import asyncio
from typing import Dict, Set
from pyrogram import Client
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot.logging import LOGGER
from bot.utils.error_handler import safe_remove_handler

logger = LOGGER(__name__)

class HandlerManager:
    """Manage handler registration and removal safely"""
    
    def __init__(self):
        self.registered_handlers = {}
    
    async def add_handler(self, client: Client, handler, group: int = 0):
        """Safely add handler"""
        try:
            client.add_handler(handler, group)
            handler_id = id(handler)
            self.registered_handlers[handler_id] = (handler, group)
            logger.debug(f"Added handler {handler_id} to group {group}")
        except Exception as e:
            logger.error(f"Error adding handler: {e}")
    
    async def remove_handler(self, client: Client, handler, group: int = 0):
        """Safely remove handler"""
        await safe_remove_handler(client, handler, group)
        handler_id = id(handler)
        if handler_id in self.registered_handlers:
            del self.registered_handlers[handler_id]
    
    async def cleanup_all_handlers(self, client: Client):
        """Remove all registered handlers safely"""
        for handler_id, (handler, group) in list(self.registered_handlers.items()):
            await self.remove_handler(client, handler, group)
        self.registered_handlers.clear()

# Global handler manager instance
handler_manager = HandlerManager()

class HandlerManager:
    """Manage handlers to prevent duplicate registration/removal errors"""
    
    def __init__(self):
        self.registered_handlers: Dict[str, Set] = {}
    
    async def safe_add_handler(self, client: Client, handler, group: int = 0):
        """Safely add handler without duplicates"""
        try:
            client_id = str(id(client))
            if client_id not in self.registered_handlers:
                self.registered_handlers[client_id] = set()
            
            handler_id = f"{type(handler).__name__}_{group}_{hash(str(handler.callback))}"
            
            if handler_id not in self.registered_handlers[client_id]:
                client.add_handler(handler, group)
                self.registered_handlers[client_id].add(handler_id)
                logger.debug(f"✅ Added handler: {handler_id}")
            else:
                logger.debug(f"⚠️ Handler already exists: {handler_id}")
                
        except Exception as e:
            logger.error(f"❌ Error adding handler: {e}")
    
    async def safe_remove_handler(self, client: Client, handler, group: int = 0):
        """Safely remove handler"""
        try:
            client_id = str(id(client))
            handler_id = f"{type(handler).__name__}_{group}_{hash(str(handler.callback))}"
            
            if (client_id in self.registered_handlers and 
                handler_id in self.registered_handlers[client_id]):
                
                client.remove_handler(handler, group)
                self.registered_handlers[client_id].discard(handler_id)
                logger.debug(f"✅ Removed handler: {handler_id}")
            else:
                logger.debug(f"⚠️ Handler not found for removal: {handler_id}")
                
        except ValueError as e:
            logger.warning(f"⚠️ Handler removal error (expected): {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error removing handler: {e}")
    
    def clear_client_handlers(self, client: Client):
        """Clear all tracked handlers for a client"""
        client_id = str(id(client))
        if client_id in self.registered_handlers:
            del self.registered_handlers[client_id]
            logger.debug(f"✅ Cleared handlers for client {client_id}")

# Global instance
handler_manager = HandlerManager()
