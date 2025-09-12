
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CloneStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"
    SUSPENDED = "suspended"

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    CANCELLED = "cancelled"

@dataclass
class Clone:
    """Clone entity representing a bot instance"""
    bot_id: str
    owner_id: int
    bot_token: str
    username: Optional[str] = None
    status: CloneStatus = CloneStatus.INACTIVE
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    configuration: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Subscription:
    """Subscription entity for clone access"""
    clone_id: str
    owner_id: int
    status: SubscriptionStatus
    plan_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    payment_verified: bool = False
    features: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}
    
    def is_valid(self) -> bool:
        """Check if subscription is currently valid"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < datetime.now():
            return False
        return True
