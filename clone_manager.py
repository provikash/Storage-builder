
#!/usr/bin/env python3
"""
Advanced Clone Manager for Mother Bot + Clone Bot Architecture
This script manages multiple bot instances with configuration-driven behavior
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, ApiIdInvalid, FloodWait
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from bot.logging import LOGGER

logger = LOGGER(__name__)

class BotInstance:
    """Individual bot instance with configuration-driven behavior"""
    
    def __init__(self, bot_token: str, clone_config: dict):
        self.bot_token = bot_token
        self.bot_id = bot_token.split(':')[0]
        self.config = clone_config
        self.client = None
        self.running = False
        
    async def start(self):
        """Start the bot instance"""
        try:
            self.client = Client(
                name=f"clone_{self.bot_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=self.bot_token,
                plugins=dict(root="bot/plugins")
            )
            
            # Set bot configuration for dynamic behavior
            self.client.clone_config = self.config
            self.client.is_clone = True
            self.client.bot_token = self.bot_token
            
            await self.client.start()
            me = await self.client.get_me()
            
            self.running = True
            logger.info(f"✅ Clone bot @{me.username} ({self.bot_id}) started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting clone {self.bot_id}: {e}")
            return False
            
    async def stop(self):
        """Stop the bot instance"""
        try:
            if self.client and self.running:
                await self.client.stop()
                self.running = False
                logger.info(f"✅ Clone bot {self.bot_id} stopped successfully")
                
        except Exception as e:
            logger.error(f"❌ Error stopping clone {self.bot_id}: {e}")

class CloneManager:
    """Advanced clone manager with subscription and configuration support"""
    
    def __init__(self):
        self.instances = {}  # bot_id -> BotInstance
        self.subscription_check_interval = 3600  # 1 hour
        
    async def create_clone(self, bot_token: str, admin_id: int, db_url: str, tier: str = "monthly"):
        """Create a new clone with subscription"""
        try:
            # Validate bot token
            test_client = Client(
                name=f"test_{bot_token[:10]}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=bot_token
            )
            
            await test_client.start()
            me = await test_client.get_me()
            bot_id = str(me.id)
            
            # Store in database
            success, clone_data = await create_clone(bot_token, admin_id, db_url)
            if not success:
                await test_client.stop()
                return False, clone_data
                
            # Create subscription
            await create_subscription(bot_id, admin_id, tier, payment_verified=False)
            
            await test_client.stop()
            
            logger.info(f"✅ Clone created: @{me.username} ({bot_id})")
            return True, {
                'bot_id': bot_id,
                'username': me.username,
                'first_name': me.first_name,
                'admin_id': admin_id,
                'tier': tier
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating clone: {e}")
            return False, str(e)
            
    async def start_clone(self, bot_id: str):
        """Start a specific clone"""
        try:
            # Check if already running
            if bot_id in self.instances and self.instances[bot_id].running:
                return False, "Clone is already running"
            
            # Check subscription status
            subscription = await get_subscription(bot_id)
            if not subscription or subscription['status'] != 'active':
                logger.warning(f"⚠️ Cannot start clone {bot_id}: subscription not active")
                return False, "Clone subscription is not active"
                
            # Check if subscription has expired
            if subscription['expiry_date'] < datetime.now():
                logger.warning(f"⚠️ Cannot start clone {bot_id}: subscription expired")
                await subscriptions.update_one(
                    {"_id": bot_id},
                    {"$set": {"status": "expired"}}
                )
                return False, "Clone subscription has expired"
                
            # Get clone data
            clone_data = await get_clone(bot_id)
            if not clone_data:
                logger.error(f"❌ Clone data not found for {bot_id}")
                return False, "Clone not found"
                
            # Get configuration
            config = await clone_config_loader.get_bot_config(clone_data['token'])
            
            # Create and start instance
            instance = BotInstance(clone_data['token'], config)
            success = await instance.start()
            
            if success:
                self.instances[bot_id] = instance
                logger.info(f"✅ Clone {bot_id} started successfully")
                return True, f"Clone {bot_id} started successfully"
            else:
                logger.error(f"❌ Failed to start clone instance {bot_id}")
                return False, "Failed to start clone"
                
        except FloodWait as e:
            logger.error(f"❌ Telegram flood wait for clone {bot_id}: {e.value}s")
            return False, f"Telegram rate limit: wait {e.value}s"
        except Exception as e:
            logger.error(f"❌ Error starting clone {bot_id}: {e}")
            return False, str(e)
            
    async def stop_clone(self, bot_id: str):
        """Stop a specific clone"""
        try:
            if bot_id in self.instances:
                await self.instances[bot_id].stop()
                del self.instances[bot_id]
                return True, f"Clone {bot_id} stopped successfully"
            else:
                return False, "Clone not running"
                
        except Exception as e:
            logger.error(f"❌ Error stopping clone {bot_id}: {e}")
            return False, str(e)
            
    async def start_all_clones(self):
        """Start all active clones with valid subscriptions"""
        logger.info("🚀 Starting all active clones...")
        
        # Get all active clones
        clones = await get_all_clones()
        started = 0
        
        for clone in clones:
            if clone['status'] == 'active':
                # Check subscription
                subscription = await get_subscription(clone['_id'])
                if subscription and subscription['status'] == 'active':
                    success, message = await self.start_clone(clone['_id'])
                    if success:
                        started += 1
                    else:
                        logger.warning(f"Failed to start clone {clone['_id']}: {message}")
                        
        logger.info(f"✅ Started {started} clones")
        
    async def check_subscriptions(self):
        """Check and handle expired subscriptions"""
        while True:
            try:
                logger.info("🔍 Checking subscription status...")
                
                # Get expired subscriptions
                expired_clones = await check_expired_subscriptions()
                
                for clone_id in expired_clones:
                    # Stop the clone
                    if clone_id in self.instances:
                        await self.stop_clone(clone_id)
                        logger.info(f"⏰ Stopped expired clone: {clone_id}")
                        
                    # Deactivate in database
                    await deactivate_clone(clone_id)
                    
                await asyncio.sleep(self.subscription_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error checking subscriptions: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    def get_running_clones(self):
        """Get list of currently running clones"""
        return {
            bot_id: {
                'running': instance.running,
                'config': instance.config
            }
            for bot_id, instance in self.instances.items()
        }

# Global clone manager instance
clone_manager = CloneManager()

async def main():
    """Main function for standalone clone manager"""
    await clone_manager.start_all_clones()
    
    # Start subscription monitoring
    asyncio.create_task(clone_manager.check_subscriptions())
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down clone manager...")
        for bot_id in list(clone_manager.instances.keys()):
            await clone_manager.stop_clone(bot_id)
        logger.info("✅ All clones stopped.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
