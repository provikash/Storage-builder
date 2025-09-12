
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Clone, Subscription

class CloneRepository(ABC):
    """Abstract repository for clone operations"""
    
    @abstractmethod
    async def create(self, clone: Clone) -> Clone:
        """Create a new clone"""
        pass
    
    @abstractmethod
    async def get_by_id(self, clone_id: str) -> Optional[Clone]:
        """Get clone by ID"""
        pass
    
    @abstractmethod
    async def get_by_owner(self, owner_id: int) -> List[Clone]:
        """Get all clones owned by a user"""
        pass
    
    @abstractmethod
    async def update(self, clone: Clone) -> Clone:
        """Update clone information"""
        pass
    
    @abstractmethod
    async def delete(self, clone_id: str) -> bool:
        """Delete a clone"""
        pass
    
    @abstractmethod
    async def get_active_clones(self) -> List[Clone]:
        """Get all active clones"""
        pass

class SubscriptionRepository(ABC):
    """Abstract repository for subscription operations"""
    
    @abstractmethod
    async def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription"""
        pass
    
    @abstractmethod
    async def get_by_clone_id(self, clone_id: str) -> Optional[Subscription]:
        """Get subscription by clone ID"""
        pass
    
    @abstractmethod
    async def update(self, subscription: Subscription) -> Subscription:
        """Update subscription"""
        pass
    
    @abstractmethod
    async def get_expiring_soon(self, hours: int = 24) -> List[Subscription]:
        """Get subscriptions expiring within specified hours"""
        pass
