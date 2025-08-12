
import asyncio
from datetime import datetime
from bot.database.subscription_db import check_expired_subscriptions, get_subscription
from bot.database.clone_db import deactivate_clone
from clone_manager import clone_manager

class SubscriptionChecker:
    """Check and manage subscription status"""
    
    def __init__(self):
        self.check_interval = 3600  # Check every hour
    
    async def start_monitoring(self):
        """Start subscription monitoring"""
        while True:
            try:
                await self.check_subscriptions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in subscription monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_subscriptions(self):
        """Check for expired subscriptions"""
        print("🔍 Checking subscription status...")
        
        expired_clones = await check_expired_subscriptions()
        
        for clone_id in expired_clones:
            await self.handle_expired_subscription(clone_id)
            print(f"⚠️ Deactivated expired clone: {clone_id}")
    
    async def handle_expired_subscription(self, clone_id: str):
        """Handle an expired subscription"""
        # Deactivate clone in database
        await deactivate_clone(clone_id)
        
        # Stop clone if running
        try:
            await clone_manager.stop_clone(clone_id)
        except Exception as e:
            print(f"Error stopping clone {clone_id}: {e}")
    
    async def is_subscription_active(self, bot_token: str):
        """Check if subscription is active for a bot"""
        bot_id = bot_token.split(':')[0]
        
        subscription = await get_subscription(bot_id)
        
        if not subscription:
            return True  # Mother bot or no subscription required
        
        return (
            subscription['status'] == 'active' and 
            subscription['expiry_date'] > datetime.now()
        )

# Global instance
subscription_checker = SubscriptionChecker()
