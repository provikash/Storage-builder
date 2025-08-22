
import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, AccessTokenExpired, AccessTokenInvalid
from info import Config
from bot.database.clone_db import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneManager:
    def __init__(self):
        self.active_clones = {}
        self.clone_tasks = {}

    async def start_clone(self, bot_id: str):
        """Start a clone bot"""
        try:
            clone_data = await get_clone(bot_id)
            if not clone_data:
                return False, "Clone not found"

            if bot_id in self.active_clones:
                return True, "Clone already running"

            # Create bot instance
            bot_token = clone_data['token']
            clone_bot = Client(
                f"clone_{bot_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=bot_token,
                plugins=dict(root="bot/plugins")
            )

            # Start the bot
            await clone_bot.start()
            
            # Store in active clones
            self.active_clones[bot_id] = {
                'client': clone_bot,
                'data': clone_data,
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

    async def start_all_active_clones(self):
        """Start all active clones from database"""
        try:
            active_clones = await clones_collection.find({"status": "active"}).to_list(None)
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

# Create global instance
clone_manager = CloneManager()
