import asyncio
from datetime import datetime
from bot.database.subscription_db import check_expired_subscriptions, get_subscription
from bot.database.clone_db import deactivate_clone
from clone_manager import clone_manager
from bot.logging import LOGGER

logger = LOGGER(__name__)

class SubscriptionChecker:
    """Check and manage subscription status"""

    def __init__(self):
        self.check_interval = 3600  # Check every hour

    async def start_monitoring(self):
        """Start subscription monitoring"""
        logger.info("🔄 Starting subscription monitoring...")
        while True:
            try:
                await self.check_subscriptions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Error in subscription monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def check_subscriptions(self):
        """Check for expired subscriptions"""
        logger.info("🔍 Checking subscription status...")

        try:
            expired_clones = await check_expired_subscriptions()

            for clone_id in expired_clones:
                await self.handle_expired_subscription(clone_id)
                logger.info(f"⚠️ Deactivated expired clone: {clone_id}")
        except Exception as e:
            logger.error(f"❌ Error checking subscriptions: {e}")

    async def handle_expired_subscription(self, clone_id: str):
        """Handle an expired subscription"""
        try:
            # Deactivate clone in database
            await deactivate_clone(clone_id)

            # Stop clone if running
            await clone_manager.stop_clone(clone_id)
            logger.info(f"✅ Successfully handled expired clone: {clone_id}")
        except Exception as e:
            logger.error(f"❌ Error handling expired clone {clone_id}: {e}")

    async def is_subscription_active(self, bot_token: str):
        """Check if subscription is active for a bot"""
        try:
            bot_id = bot_token.split(":")[0]
            subscription = await get_subscription(bot_id)

            if not subscription:
                return False

            return subscription.get('status') == 'active' and subscription.get('expiry_date', datetime.min) > datetime.now()
        except Exception as e:
            logger.error(f"❌ Error checking subscription for bot {bot_token[:10]}: {e}")
            return False

# Global subscription checker instance
subscription_checker = SubscriptionChecker()