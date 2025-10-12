"""
Handler Registry - Prevents duplicate command processing
"""
import asyncio
from typing import Dict, Set

class HandlerRegistry:
    """Registry to track and prevent duplicate handler execution"""
    
    def __init__(self):
        self._processing: Dict[int, Set[str]] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
    
    async def is_processing(self, user_id: int, handler_name: str) -> bool:
        """Check if handler is currently processing for user"""
        return handler_name in self._processing.get(user_id, set())
    
    async def start_processing(self, user_id: int, handler_name: str):
        """Mark handler as processing for user"""
        if user_id not in self._processing:
            self._processing[user_id] = set()
            self._locks[user_id] = asyncio.Lock()
        
        self._processing[user_id].add(handler_name)
    
    async def stop_processing(self, user_id: int, handler_name: str):
        """Mark handler as finished for user"""
        if user_id in self._processing:
            self._processing[user_id].discard(handler_name)
            
            # Cleanup if no more handlers processing
            if not self._processing[user_id]:
                del self._processing[user_id]
                if user_id in self._locks:
                    del self._locks[user_id]
    
    def clear_user(self, user_id: int):
        """Clear all processing handlers for a user"""
        self._processing.pop(user_id, None)
        self._locks.pop(user_id, None)

# Global instance
handler_registry = HandlerRegistry()
