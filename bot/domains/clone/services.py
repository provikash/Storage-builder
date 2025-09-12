
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from .entities import Clone, CloneStatus, Subscription, SubscriptionStatus
from .repositories import CloneRepository, SubscriptionRepository
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneManagementService:
    """Domain service for clone management business logic"""
    
    def __init__(self, clone_repo: CloneRepository, subscription_repo: SubscriptionRepository):
        self.clone_repo = clone_repo
        self.subscription_repo = subscription_repo
    
    async def create_clone(self, owner_id: int, bot_token: str, plan_type: str = "free") -> Tuple[bool, str, Optional[Clone]]:
        """Create a new clone with subscription"""
        try:
            # Extract bot ID from token
            bot_id = bot_token.split(':')[0]
            
            # Check if clone already exists
            existing = await self.clone_repo.get_by_id(bot_id)
            if existing:
                return False, "Clone already exists", None
            
            # Create clone entity
            clone = Clone(
                bot_id=bot_id,
                owner_id=owner_id,
                bot_token=bot_token,
                status=CloneStatus.PENDING,
                created_at=datetime.now()
            )
            
            # Create subscription
            subscription = Subscription(
                clone_id=bot_id,
                owner_id=owner_id,
                status=SubscriptionStatus.PENDING,
                plan_type=plan_type,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30) if plan_type != "lifetime" else None
            )
            
            # Save entities
            created_clone = await self.clone_repo.create(clone)
            await self.subscription_repo.create(subscription)
            
            logger.info(f"Clone {bot_id} created for user {owner_id}")
            return True, "Clone created successfully", created_clone
            
        except Exception as e:
            logger.error(f"Failed to create clone: {e}")
            return False, f"Creation failed: {str(e)}", None
    
    async def validate_clone_access(self, clone_id: str, user_id: int) -> Tuple[bool, str]:
        """Validate if user has access to clone"""
        clone = await self.clone_repo.get_by_id(clone_id)
        if not clone:
            return False, "Clone not found"
        
        if clone.owner_id != user_id:
            return False, "Access denied"
        
        subscription = await self.subscription_repo.get_by_clone_id(clone_id)
        if not subscription or not subscription.is_valid():
            return False, "Invalid or expired subscription"
        
        return True, "Access granted"
    
    async def get_user_clones(self, user_id: int) -> List[Clone]:
        """Get all clones for a user"""
        return await self.clone_repo.get_by_owner(user_id)
    
    async def update_clone_status(self, clone_id: str, status: CloneStatus) -> bool:
        """Update clone status"""
        try:
            clone = await self.clone_repo.get_by_id(clone_id)
            if not clone:
                return False
            
            clone.status = status
            clone.last_seen = datetime.now()
            await self.clone_repo.update(clone)
            return True
        except Exception as e:
            logger.error(f"Failed to update clone status: {e}")
            return False

class SubscriptionService:
    """Service for subscription management"""
    
    def __init__(self, subscription_repo: SubscriptionRepository):
        self.subscription_repo = subscription_repo
    
    async def check_expiring_subscriptions(self) -> List[Subscription]:
        """Get subscriptions expiring soon"""
        return await self.subscription_repo.get_expiring_soon()
    
    async def renew_subscription(self, clone_id: str, days: int = 30) -> bool:
        """Renew a subscription"""
        try:
            subscription = await self.subscription_repo.get_by_clone_id(clone_id)
            if not subscription:
                return False
            
            # Extend expiration date
            if subscription.expires_at:
                subscription.expires_at = max(subscription.expires_at, datetime.now()) + timedelta(days=days)
            else:
                subscription.expires_at = datetime.now() + timedelta(days=days)
            
            subscription.status = SubscriptionStatus.ACTIVE
            await self.subscription_repo.update(subscription)
            return True
        except Exception as e:
            logger.error(f"Failed to renew subscription: {e}")
            return False
