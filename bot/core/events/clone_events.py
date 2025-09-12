
from typing import Dict, Any
from .base import Event

class CloneCreatedEvent(Event):
    """Event fired when a clone is created"""
    
    def __init__(self, clone_id: str, owner_id: int, **kwargs):
        super().__init__(
            event_type="clone.created",
            data={
                "clone_id": clone_id,
                "owner_id": owner_id,
                **kwargs
            },
            source="clone_manager"
        )

class CloneStartedEvent(Event):
    """Event fired when a clone starts successfully"""
    
    def __init__(self, clone_id: str, username: str = None, **kwargs):
        super().__init__(
            event_type="clone.started",
            data={
                "clone_id": clone_id,
                "username": username,
                **kwargs
            },
            source="clone_manager"
        )

class CloneStoppedEvent(Event):
    """Event fired when a clone stops"""
    
    def __init__(self, clone_id: str, reason: str = "manual", **kwargs):
        super().__init__(
            event_type="clone.stopped",
            data={
                "clone_id": clone_id,
                "reason": reason,
                **kwargs
            },
            source="clone_manager"
        )

class CloneErrorEvent(Event):
    """Event fired when a clone encounters an error"""
    
    def __init__(self, clone_id: str, error: str, error_type: str = "runtime", **kwargs):
        super().__init__(
            event_type="clone.error",
            data={
                "clone_id": clone_id,
                "error": error,
                "error_type": error_type,
                **kwargs
            },
            source="clone_manager"
        )

class SubscriptionExpiredEvent(Event):
    """Event fired when a subscription expires"""
    
    def __init__(self, clone_id: str, owner_id: int, **kwargs):
        super().__init__(
            event_type="subscription.expired",
            data={
                "clone_id": clone_id,
                "owner_id": owner_id,
                **kwargs
            },
            source="subscription_manager"
        )
