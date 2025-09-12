
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from bot.logging import LOGGER

logger = LOGGER(__name__)

@dataclass
class Event:
    """Base event class"""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    
class EventHandler(ABC):
    """Abstract event handler"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle the event"""
        pass
    
    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        """Event types this handler can process"""
        pass

class EventBus:
    """Simple event bus for pub/sub messaging"""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._async_handlers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
    
    def subscribe(self, handler: EventHandler):
        """Subscribe an event handler"""
        for event_type in handler.event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def subscribe_async(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Subscribe an async function handler"""
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """Publish an event to all subscribers"""
        logger.debug(f"Publishing event: {event.event_type}")
        
        # Handle class-based handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__class__.__name__}: {e}")
        
        # Handle function-based handlers
        async_handlers = self._async_handlers.get(event.event_type, [])
        for handler in async_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in async event handler: {e}")
    
    def publish_sync(self, event: Event):
        """Publish event without waiting (fire and forget)"""
        asyncio.create_task(self.publish(event))

# Global event bus instance
event_bus = EventBus()
