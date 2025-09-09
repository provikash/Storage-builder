
"""
Handler Registry - Centralized handler management to prevent conflicts
"""
import asyncio
from typing import Dict, Set, Any
from bot.logging import LOGGER

logger = LOGGER(__name__)

class HandlerRegistry:
    """Registry to track and prevent handler conflicts"""
    
    def __init__(self):
        self._registered_handlers: Dict[str, Set[str]] = {}
        self._processing_commands: Dict[int, Set[str]] = {}
        self._lock = asyncio.Lock()
    
    async def register_handler(self, handler_type: str, handler_name: str, group: int = 0):
        """Register a handler to prevent conflicts"""
        async with self._lock:
            if handler_type not in self._registered_handlers:
                self._registered_handlers[handler_type] = set()
            
            if handler_name in self._registered_handlers[handler_type]:
                logger.warning(f"Handler {handler_name} of type {handler_type} already registered")
                return False
            
            self._registered_handlers[handler_type].add(handler_name)
            logger.info(f"Registered handler: {handler_type}.{handler_name} (group={group})")
            return True
    
    async def is_processing(self, user_id: int, command: str) -> bool:
        """Check if a command is currently being processed for a user"""
        if user_id not in self._processing_commands:
            return False
        return command in self._processing_commands[user_id]
    
    async def start_processing(self, user_id: int, command: str):
        """Mark a command as being processed for a user"""
        if user_id not in self._processing_commands:
            self._processing_commands[user_id] = set()
        self._processing_commands[user_id].add(command)
    
    async def stop_processing(self, user_id: int, command: str):
        """Mark a command as finished processing for a user"""
        if user_id in self._processing_commands:
            self._processing_commands[user_id].discard(command)
            if not self._processing_commands[user_id]:
                del self._processing_commands[user_id]
    
    def get_registered_handlers(self) -> Dict[str, Set[str]]:
        """Get all registered handlers"""
        return self._registered_handlers.copy()

# Global registry instance
handler_registry = HandlerRegistry()
