import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, AccessTokenExpired, AccessTokenInvalid
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import get_subscription, subscriptions_collection
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneManager:
    def __init__(self):
        self.instances = {}  # Changed from active_clones to instances for consistency
        self.active_clones = {}
        self.clone_tasks = {}

    async def start_clone(self, bot_id: str):
        """Start a specific clone bot"""
        try:
            clone = await get_clone(bot_id)
            if not clone:
                return False, "Clone not found"

            # Check subscription - be more flexible with status check
            subscription = await get_subscription(bot_id)
            if not subscription:
                return False, "No subscription found"

            # Allow active subscriptions or payment verified subscriptions
            is_active_status = subscription['status'] == 'active'
            is_payment_verified = subscription.get('payment_verified', False)

            if not is_active_status and not is_payment_verified:
                # Only fail if both conditions are false
                if subscription['status'] in ['expired', 'cancelled']:
                    return False, f"Subscription {subscription['status']}"
                # For pending status, allow if payment is verified
                if subscription['status'] == 'pending' and not is_payment_verified:
                    logger.info(f"⏳ Clone {bot_id} subscription pending - will retry later")
                    # Schedule retry after 5 minutes
                    asyncio.create_task(self._retry_pending_clone(bot_id, 300))
                    # Update database to reflect pending status
                    from bot.database.clone_db import clones_collection
                    await clones_collection.update_one(
                        {"_id": bot_id},
                        {"$set": {"status": "pending_subscription", "last_check": datetime.now()}}
                    )
                    return True, f"Clone {bot_id} subscription pending - retry scheduled"



            if bot_id in self.active_clones:
                return True, "Clone already running"

            # Create bot instance with simple file sharing plugins
            bot_token = clone.get('bot_token') or clone.get('token')

            # Define plugin list for clone bots (exclude clone management)
            clone_plugins = {
                "root": "bot/plugins",
                "include": [
                    "simple_file_sharing",
                    "search",
                    "genlink",
                    "channel",
                    "callback_handlers"
                ],
                "exclude": [
                    "clone_management",
                    "step_clone_creation",
                    "mother_admin",
                    "admin_commands",
                    "balance_management"
                ]
            }

            clone_bot = Client(
                f"clone_{bot_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=bot_token,
                plugins=clone_plugins
            )

            # Start the bot
            await clone_bot.start()

            # Store in active clones
            self.active_clones[bot_id] = {
                'client': clone_bot,
                'data': clone,
                'status': 'running',
                'started_at': datetime.now()
            }

            # Update database status
            await start_clone_in_db(bot_id)

            # Create background task to keep it running
            task = asyncio.create_task(self._keep_clone_running(bot_id))
            self.clone_tasks[bot_id] = task

            logger.info(f"✅ Clone {bot_id} started successfully")
            return True, f"Clone @{clone_bot.me.username} started successfully"

        except Exception as e:
            logger.error(f"❌ Error starting clone {bot_id}: {e}")
            return False, str(e)

    async def stop_clone(self, bot_id: str):
        """Stop a clone bot"""
        try:
            if bot_id not in self.active_clones:
                return False, "Clone not running"

            # Cancel background task
            if bot_id in self.clone_tasks:
                self.clone_tasks[bot_id].cancel()
                del self.clone_tasks[bot_id]

            # Stop the bot
            clone_info = self.active_clones[bot_id]
            clone_bot = clone_info['client']

            if clone_bot.is_connected:
                await clone_bot.stop()

            # Remove from active clones
            del self.active_clones[bot_id]

            # Update database status
            await stop_clone_in_db(bot_id)

            logger.info(f"🛑 Clone {bot_id} stopped successfully")
            return True, "Clone stopped successfully"

        except Exception as e:
            logger.error(f"❌ Error stopping clone {bot_id}: {e}")
            return False, str(e)

    async def _keep_clone_running(self, bot_id: str):
        """Keep clone running in background"""
        try:
            while bot_id in self.active_clones:
                clone_info = self.active_clones[bot_id]
                clone_bot = clone_info['client']

                # Check if bot is still connected
                if not clone_bot.is_connected:
                    logger.warning(f"⚠️ Clone {bot_id} disconnected, attempting restart...")
                    try:
                        await clone_bot.start()
                        logger.info(f"✅ Clone {bot_id} reconnected")
                    except Exception as e:
                        logger.error(f"❌ Failed to reconnect clone {bot_id}: {e}")
                        break

                # Update last seen
                await update_clone_last_seen(bot_id)

                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info(f"🛑 Background task for clone {bot_id} cancelled")
        except Exception as e:
            logger.error(f"❌ Error in background task for clone {bot_id}: {e}")

    async def restart_clone(self, bot_id: str):
        """Restart a clone bot"""
        try:
            # Stop first
            await self.stop_clone(bot_id)
            await asyncio.sleep(2)  # Wait a bit

            # Start again
            return await self.start_clone(bot_id)
        except Exception as e:
            logger.error(f"❌ Error restarting clone {bot_id}: {e}")
            return False, str(e)

    async def get_clone_status(self, bot_id: str):
        """Get clone status"""
        if bot_id in self.active_clones:
            clone_info = self.active_clones[bot_id]
            return {
                'status': 'running',
                'started_at': clone_info['started_at'],
                'connected': clone_info['client'].is_connected
            }
        else:
            return {'status': 'stopped'}

    async def start_all_clones(self):
        """Start all active clones from database"""
        try:
            from bot.database.clone_db import get_all_clones
            active_clones_data = await get_all_clones()
            active_clones = [clone for clone in active_clones_data if clone.get('status') == 'active']
            started_count = 0

            for clone_data in active_clones:
                bot_id = clone_data['_id']
                success, message = await self.start_clone(bot_id)
                if success:
                    started_count += 1
                    logger.info(f"✅ Started clone {bot_id}")
                else:
                    logger.error(f"❌ Failed to start clone {bot_id}: {message}")

            logger.info(f"🚀 Started {started_count}/{len(active_clones)} clones")
            return started_count, len(active_clones)

        except Exception as e:
            logger.error(f"❌ Error starting all clones: {e}")
            return 0, 0

    async def start_all_active_clones(self):
        """Alias for start_all_clones for backward compatibility"""
        return await self.start_all_clones()

    def get_running_clones(self):
        """Get list of currently running clones"""
        return list(self.active_clones.keys())

    async def check_subscriptions(self):
        """Check subscription status for all clones"""
        try:
            await self.cleanup_inactive_clones()
            logger.info("✅ Subscription check completed")
        except Exception as e:
            logger.error(f"❌ Error checking subscriptions: {e}")

    async def _retry_pending_clone(self, bot_id: str, delay: int = 300):
        """Retry starting a clone with pending subscription after delay"""
        max_retries = 12  # 12 retries = 1 hour of checking (5 min intervals)
        retry_count = 0

        try:
            while retry_count < max_retries:
                await asyncio.sleep(delay)
                retry_count += 1

                # Check if subscription is now active
                subscription = await get_subscription(bot_id)
                if subscription and subscription['status'] == 'active':
                    logger.info(f"🔄 Retrying clone {bot_id} - subscription now active (attempt {retry_count})")
                    success, message = await self.start_clone(bot_id)
                    if success:
                        logger.info(f"✅ Successfully started pending clone {bot_id}")
                        return
                    else:
                        logger.warning(f"⚠️ Still failed to start clone {bot_id}: {message}")
                        # If it fails to start even with active subscription, stop retrying
                        break
                elif subscription and subscription['status'] in ['expired', 'cancelled']:
                    logger.info(f"🛑 Stopping retry for clone {bot_id} - subscription {subscription['status']}")
                    await deactivate_clone(bot_id)
                    break
                else:
                    logger.info(f"⏳ Clone {bot_id} subscription still pending (attempt {retry_count}/{max_retries})")

            if retry_count >= max_retries:
                logger.warning(f"⚠️ Max retries reached for clone {bot_id} - marking as failed")
                await clones_collection.update_one(
                    {"_id": bot_id},
                    {"$set": {"status": "pending_timeout", "last_check": datetime.now()}}
                )

        except Exception as e:
            logger.error(f"❌ Error retrying pending clone {bot_id}: {e}")

    async def cleanup_inactive_clones(self):
        """Cleanup inactive or expired clones"""
        try:
            # Find expired clones
            from bot.database.subscription_db import subscriptions_collection
            expired_subscriptions = await subscriptions_collection.find({
                "expires_at": {"$lt": datetime.now()},
                "status": "active"
            }).to_list(None)

            for subscription in expired_subscriptions:
                bot_id = subscription['bot_id']

                # Stop the clone
                await self.stop_clone(bot_id)

                # Deactivate in database
                await deactivate_clone(bot_id)
                await subscriptions_collection.update_one(
                    {"_id": bot_id},
                    {"$set": {"status": "expired"}}
                )

                logger.info(f"🔄 Deactivated expired clone {bot_id}")

        except Exception as e:
            logger.error(f"❌ Error cleaning up clones: {e}")

    async def check_pending_clones(self):
        """Check and attempt to start pending clones"""
        try:
            from bot.database.subscription_db import subscriptions_collection

            # Find clones with pending_subscription status
            pending_clones = await clones_collection.find({
                "status": "pending_subscription"
            }).to_list(None)

            for clone in pending_clones:
                bot_id = clone['_id']

                # Check if subscription is now active
                subscription = await get_subscription(bot_id)
                if subscription and subscription['status'] == 'active':
                    logger.info(f"🔄 Attempting to start previously pending clone {bot_id}")
                    success, message = await self.start_clone(bot_id)
                    if success:
                        logger.info(f"✅ Successfully started pending clone {bot_id}")
                    else:
                        logger.warning(f"⚠️ Failed to start clone {bot_id}: {message}")

        except Exception as e:
            logger.error(f"❌ Error checking pending clones: {e}")

    async def delete_all_clones(self):
        """Delete all clones and clean up resources"""
        try:
            # Stop all running clones first
            running_clones = list(self.active_clones.keys())
            for bot_id in running_clones:
                await self.stop_clone(bot_id)
                logger.info(f"🛑 Stopped clone {bot_id}")

            # Get all clones from database
            all_clones = await get_all_clones()
            deleted_count = 0

            for clone in all_clones:
                bot_id = clone['_id']
                try:
                    # Delete from database
                    from bot.database.clone_db import delete_clone, delete_clone_config
                    from bot.database.subscription_db import delete_subscription

                    await delete_clone(bot_id)
                    await delete_clone_config(bot_id)
                    await delete_subscription(bot_id)

                    deleted_count += 1
                    logger.info(f"🗑️ Deleted clone {bot_id}")

                except Exception as e:
                    logger.error(f"❌ Error deleting clone {bot_id}: {e}")

            # Clear internal tracking
            self.active_clones.clear()
            self.clone_tasks.clear()

            logger.info(f"🗑️ Mass deletion completed: {deleted_count} clones deleted")
            return deleted_count, len(all_clones)

        except Exception as e:
            logger.error(f"❌ Error in mass clone deletion: {e}")
            return 0, 0

# Create global instance
clone_manager = CloneManager()