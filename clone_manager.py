import asyncio
import os
from datetime import datetime
from typing import Optional
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
        """Start a specific clone bot with enhanced error handling"""
        from bot.logging import LOGGER

        logger = LOGGER(__name__)

        # Simple execution tracking
        class SimpleTracker:
            def __init__(self, name):
                self.name = name
                self.steps = []
            def add_step(self, step, data=None):
                self.steps.append(step)
                logger.info(f"Step: {step}")
            def complete(self, success=False, error=None):
                if success:
                    logger.info(f"Completed: {self.name}")
                else:
                    logger.error(f"Failed: {self.name} - {error}")

        tracker = SimpleTracker(f"start_clone_{bot_id}")

        # Prevent multiple simultaneous starts
        if bot_id in getattr(self, '_starting_clones', set()):
            return False, "Clone startup already in progress"

        if not hasattr(self, '_starting_clones'):
            self._starting_clones = set()

        self._starting_clones.add(bot_id)

        try:
            tracker.add_step("fetching_clone_data")
            logger.debug("Starting clone startup process")

            clone = await get_clone(bot_id)
            if not clone:
                error_msg = "Clone not found in database"
                logger.error(error_msg)
                tracker.complete(success=False, error=error_msg)
                return False, error_msg

            tracker.add_step("clone_data_retrieved", {"clone_exists": True})

            # Enhanced subscription validation (TESTING MODE - ALWAYS ALLOW)
            tracker.add_step("checking_subscription")
            subscription = await get_subscription(bot_id)
            logger.info(f"🔍 DEBUG: Subscription for bot {bot_id}: {subscription}")
            print(f"🔍 DEBUG SUBSCRIPTION: For bot {bot_id}: {subscription}")

            # Always allow during development - bypass subscription validation
            subscription_valid, subscription_msg = True, "Development mode: subscription validation bypassed"
            logger.info(f"✅ DEBUG: Subscription validation result: {subscription_valid} - {subscription_msg}")
            print(f"✅ DEBUG SUBSCRIPTION: Result: {subscription_valid} - {subscription_msg}")

            if bot_id in self.active_clones:
                # Check if clone is actually running
                if await self._verify_clone_health(bot_id):
                    return True, "Clone already running"
                else:
                    # Clean up stale entry
                    await self._cleanup_stale_clone(bot_id)

            # Validate bot token
            bot_token = clone.get('bot_token') or clone.get('token')
            logger.info(f"🔍 DEBUG: Bot token for {bot_id}: {bot_token[:20] if bot_token else 'None'}...")
            print(f"🔍 DEBUG TOKEN: For {bot_id}: {bot_token[:20] if bot_token else 'None'}...")

            if not bot_token:
                error_msg = "Missing bot token in clone data"
                logger.error(f"❌ {error_msg} for bot {bot_id}")
                print(f"❌ DEBUG TOKEN: {error_msg} for bot {bot_id}")
                tracker.complete(success=False, error=error_msg)
                return False, error_msg

            token_valid = await self._validate_bot_token(bot_token)
            if not token_valid:
                error_msg = "Invalid bot token format"
                logger.error(f"❌ {error_msg} for bot {bot_id}")
                print(f"❌ DEBUG TOKEN: {error_msg} for bot {bot_id}")
                tracker.complete(success=False, error=error_msg)
                return False, error_msg

            tracker.add_step("bot_token_validated")
            logger.info(f"✅ Bot token validated for {bot_id}")
            print(f"✅ DEBUG TOKEN: Token validated for {bot_id}")

            # Create bot instance with proper error handling
            clone_bot = await self._create_clone_client(bot_id, bot_token)
            if not clone_bot:
                return False, "Failed to create clone client"

            # Start the bot with timeout and retry
            start_success = await self._start_clone_client(clone_bot, bot_id)
            if not start_success:
                return False, "Failed to start clone client"

            # Verify bot is working
            try:
                bot_info = await asyncio.wait_for(clone_bot.get_me(), timeout=10.0)
                logger.info(f"Clone bot started: @{bot_info.username}")
            except asyncio.TimeoutError:
                await self._safe_stop_client(clone_bot)
                return False, "Bot startup verification timeout"
            except Exception as e:
                await self._safe_stop_client(clone_bot)
                return False, f"Bot verification failed: {str(e)}"

            # Store in active clones with enhanced metadata
            self.active_clones[bot_id] = {
                'client': clone_bot,
                'data': clone,
                'status': 'running',
                'started_at': datetime.now(),
                'last_health_check': datetime.now(),
                'restart_count': getattr(clone.get('metadata', {}), 'restart_count', 0),
                'username': bot_info.username if 'bot_info' in locals() else 'unknown'
            }

            # Update database status
            await start_clone_in_db(bot_id)

            # Create enhanced monitoring task
            task = asyncio.create_task(self._monitor_clone(bot_id))
            self.clone_tasks[bot_id] = task

            logger.info(f"✅ Clone {bot_id} started successfully")
            tracker.complete(success=True)
            return True, f"Clone @{bot_info.username} started successfully"

        except AuthKeyUnregistered:
            logger.error(f"❌ AuthKeyUnregistered for clone {bot_id}. Deactivating.")
            await self._handle_clone_auth_error(bot_id, "auth_key_unregistered")
            return False, "Authentication key unregistered"
        except AccessTokenExpired:
            logger.error(f"❌ AccessTokenExpired for clone {bot_id}. Deactivating.")
            await self._handle_clone_auth_error(bot_id, "access_token_expired")
            return False, "Access token expired"
        except AccessTokenInvalid:
            logger.error(f"❌ AccessTokenInvalid for clone {bot_id}. Deactivating.")
            await self._handle_clone_auth_error(bot_id, "access_token_invalid")
            return False, "Access token invalid"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Unexpected error starting clone {bot_id}: {error_msg}", exc_info=True)
            tracker.complete(success=False, error=error_msg)

            # Clean up any partial state
            if bot_id in self.active_clones:
                try:
                    clone_info = self.active_clones[bot_id]
                    client = clone_info.get('client')
                    if client:
                        await self._safe_stop_client(client)
                    del self.active_clones[bot_id]
                    logger.debug(f"Cleaned up partial state for clone {bot_id}")
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup for clone {bot_id}: {cleanup_error}")

            # Return more specific error message based on error type
            if "unexpected indent" in error_msg or "await" in error_msg:
                return False, "Python syntax error detected. Code has syntax issues that need to be fixed."
            elif "connection" in error_msg.lower():
                return False, "Connection error. Please check network and try again."
            elif "invalid token" in error_msg.lower():
                return False, "Invalid bot token. Please check the bot token configuration."
            elif "memory" in error_msg.lower():
                return False, "Memory error. System may be under high load."
            else:
                return False, f"Startup failed: {error_msg}"
        finally:
            self._starting_clones.discard(bot_id)

    async def _validate_subscription(self, subscription: dict, bot_id: str) -> tuple[bool, str]:
        """Completely permissive subscription validation for testing"""
        logger.info(f"🔄 Subscription validation for bot {bot_id} - ALLOWING ALL (TESTING MODE)")
        print(f"🔄 DEBUG SUBSCRIPTION: Validation for bot {bot_id} - ALLOWING ALL (TESTING MODE)")

        # Always return True during development/testing
        return True, "Development mode: All clones allowed to start regardless of subscription status"

    async def _validate_bot_token(self, token: str) -> bool:
        """Validate bot token format"""
        import re
        # Basic bot token format validation
        pattern = r'^\d+:[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, token))

    async def _create_clone_client(self, bot_id: str, bot_token: str) -> Optional[Client]:
        """Create clone client with proper configuration"""
        try:
            clone_plugins = {
                "root": "bot.plugins",
                "include": [
                    "start_handler", "simple_test_commands", "admin", "channel",
                    "clone_admin", "clone_admin_commands", "clone_force_commands",
                    "clone_token_commands", "debug_callbacks", "debug_commands",
                    "enhanced_about", "force_sub_commands", "genlink", "index",
                    "referral_program", "simple_file_sharing",
                    "token", "auto_post", "clone_random_files"
                ],
                "exclude": [
                    "clone_management", "step_clone_creation", "mother_admin",
                    "admin_commands", "balance_management", "admin_panel", "missing_commands", "missing_callbacks"
                ]
            }

            return Client(
                f"clone_{bot_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=bot_token,
                plugins=clone_plugins,
                workdir="temp_sessions"
            )
        except Exception as e:
            logger.error(f"Error creating clone client {bot_id}: {e}")
            return None

    async def _start_clone_client(self, client: Client, bot_id: str, max_retries: int = 3) -> bool:
        """Start clone client with retry logic"""
        for attempt in range(max_retries):
            try:
                # Check if client is already connected before attempting to start
                if client.is_connected:
                    logger.info(f"Clone {bot_id} client already connected (attempt {attempt + 1})")
                    return True

                await asyncio.wait_for(client.start(), timeout=30.0)
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Clone {bot_id} start timeout (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                error_msg = str(e)
                if "Client is already connected" in error_msg:
                    logger.info(f"Clone {bot_id} already connected (attempt {attempt + 1})")
                    return True
                elif "invalid syntax" in error_msg:
                    logger.error(f"Clone {bot_id} syntax error - stopping retries: {e}")
                    return False
                elif "syntax error" in error_msg.lower() or "unexpected indent" in error_msg.lower():
                    logger.error(f"Clone {bot_id} syntax error - stopping retries: {e}")
                    return False
                else:
                    logger.error(f"Clone {bot_id} start error (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff

        return False

    async def _verify_clone_health(self, bot_id: str) -> bool:
        """Verify clone is actually healthy"""
        if bot_id not in self.active_clones:
            return False

        try:
            clone_info = self.active_clones[bot_id]
            client = clone_info['client']

            if not client.is_connected:
                return False

            # Try to get bot info with timeout
            await asyncio.wait_for(client.get_me(), timeout=5.0)
            return True
        except:
            return False

    async def _cleanup_stale_clone(self, bot_id: str):
        """Clean up stale clone entry"""
        try:
            if bot_id in self.active_clones:
                clone_info = self.active_clones[bot_id]
                client = clone_info.get('client')
                if client:
                    await self._safe_stop_client(client)
                del self.active_clones[bot_id]

            if bot_id in self.clone_tasks:
                self.clone_tasks[bot_id].cancel()
                del self.clone_tasks[bot_id]

        except Exception as e:
            logger.error(f"Error cleaning up stale clone {bot_id}: {e}")

    async def _safe_stop_client(self, client: Client):
        """Safely stop a client"""
        try:
            if client.is_connected:
                await asyncio.wait_for(client.stop(), timeout=10.0)
        except:
            pass  # Ignore errors during shutdown

    async def _handle_clone_auth_error(self, bot_id: str, error_type: str):
        """Handle authentication errors for clones"""
        try:
            # Deactivate clone
            await deactivate_clone(bot_id)

            # Update clone status with error info
            await self._update_clone_status(bot_id, "auth_error", {
                'error_type': error_type,
                'error_time': datetime.now()
            })

            # Clean up active clone
            if bot_id in self.active_clones:
                await self._cleanup_stale_clone(bot_id)

        except Exception as e:
            logger.error(f"Error handling auth error for clone {bot_id}: {e}")

    async def start_all_clones(self):
        """Start all active clones"""
        try:
            # Get list of all clones first
            from bot.database.clone_db import get_all_clones
            all_clones = await get_all_clones()

            if not all_clones:
                logger.warning("⚠️ No clones found in database")
                print("⚠️ DEBUG CLONE: No clones found in database")
                return None

            # Show all clones with their statuses and activate stopped ones
            for clone in all_clones:
                status = clone.get('status', 'unknown')
                username = clone.get('username', 'unknown')
                bot_id = clone.get('_id', 'unknown')
                logger.info(f"📋 Clone found: {username} ({bot_id}) - Status: {status}")
                print(f"📋 DEBUG CLONE: Clone found: {username} ({bot_id}) - Status: {status}")

                # Activate stopped clones for testing
                if status == 'stopped':
                    from bot.database.clone_db import activate_clone
                    await activate_clone(bot_id)
                    logger.info(f"🔄 Activated stopped clone: {username} ({bot_id})")
                    print(f"🔄 DEBUG CLONE: Activated stopped clone: {username} ({bot_id})")

            # Start ALL clones regardless of status (testing mode)
            logger.info(f"📊 Attempting to start ALL {len(all_clones)} clones (testing mode)")
            print(f"📊 DEBUG CLONE: Attempting to start ALL {len(all_clones)} clones (testing mode)")

            # Start all clones
            started_count, total_count = await clone_manager.start_all_clones()
            return started_count, total_count

        except Exception as e:
            logger.error(f"Error in start_all_clones: {e}")
            print(f"❌ DEBUG CLONE: Error in start_all_clones: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0

    async def _monitor_clone(self, bot_id: str):
        """Enhanced clone monitoring with health checks"""
        try:
            while bot_id in self.active_clones:
                clone_info = self.active_clones[bot_id]
                client = clone_info['client']

                # Health check with timeout
                try:
                    if not client.is_connected:
                        logger.warning(f"Clone {bot_id} disconnected, attempting reconnect...")
                        if await self._reconnect_clone(client, bot_id):
                            logger.info(f"✅ Clone {bot_id} reconnected")
                        else:
                            logger.error(f"❌ Failed to reconnect clone {bot_id}")
                            break
                    else:
                        # Verify connection with ping
                        await asyncio.wait_for(client.get_me(), timeout=10.0)

                    # Update health check time
                    clone_info['last_health_check'] = datetime.now()

                except asyncio.TimeoutError:
                    logger.warning(f"Health check timeout for clone {bot_id}")
                except Exception as e:
                    logger.error(f"Health check failed for clone {bot_id}: {e}")
                    break

                # Update last seen
                await update_clone_last_seen(bot_id)

                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute

        except asyncio.CancelledError:
            logger.info(f"🛑 Monitoring task for clone {bot_id} cancelled")
        except Exception as e:
            logger.error(f"❌ Error in monitoring task for clone {bot_id}: {e}")
        finally:
            # Clean up on exit
            if bot_id in self.active_clones:
                await self._cleanup_stale_clone(bot_id)

    async def _reconnect_clone(self, client: Client, bot_id: str, max_attempts: int = 3) -> bool:
        """Attempt to reconnect a clone"""
        for attempt in range(max_attempts):
            try:
                await asyncio.wait_for(client.start(), timeout=20.0)
                return True
            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt + 1} failed for clone {bot_id}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(min(2 ** attempt, 30))
        return False

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

            try:
                # Clean up handlers safely before stopping
                try:
                    from bot.utils.handler_manager import handler_manager
                    await handler_manager.cleanup_all_handlers(clone_bot)
                    logger.debug(f"✅ Handlers cleaned up for clone {bot_id}")
                except ImportError:
                    logger.warning(f"⚠️ Handler manager not available for cleanup")
                except Exception as cleanup_error:
                    logger.error(f"❌ Error cleaning handlers: {cleanup_error}")

                # Stop the clone client with timeout
                if clone_bot.is_connected:
                    try:
                        await asyncio.wait_for(clone_bot.stop(), timeout=10.0)
                        logger.info(f"✅ Clone {bot_id} stopped gracefully")
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Clone {bot_id} stop timeout, forcing disconnect")
                        # Force disconnect if graceful stop fails
                        if hasattr(clone_bot, 'disconnect'):
                            await clone_bot.disconnect()
                else:
                    logger.info(f"✅ Clone {bot_id} was already disconnected")
            except Exception as e:
                logger.error(f"❌ Error stopping clone {bot_id}: {e}")
            finally:
                # Remove from active clones
                if bot_id in self.active_clones:
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
        """Start all active clones"""
        try:
            # Get list of all clones first
            from bot.database.clone_db import get_all_clones
            all_clones = await get_all_clones()

            if not all_clones:
                logger.warning("⚠️ No clones found in database")
                print("⚠️ DEBUG CLONE: No clones found in database")
                return None

            # Show all clones with their statuses and activate stopped ones
            for clone in all_clones:
                status = clone.get('status', 'unknown')
                username = clone.get('username', 'unknown')
                bot_id = clone.get('_id', 'unknown')
                logger.info(f"📋 Clone found: {username} ({bot_id}) - Status: {status}")
                print(f"📋 DEBUG CLONE: Clone found: {username} ({bot_id}) - Status: {status}")

                # Activate stopped clones for testing
                if status == 'stopped':
                    from bot.database.clone_db import activate_clone
                    await activate_clone(bot_id)
                    logger.info(f"🔄 Activated stopped clone: {username} ({bot_id})")
                    print(f"🔄 DEBUG CLONE: Activated stopped clone: {username} ({bot_id})")

            # Start ALL clones regardless of status (testing mode)
            logger.info(f"📊 Attempting to start ALL {len(all_clones)} clones (testing mode)")
            print(f"📊 DEBUG CLONE: Attempting to start ALL {len(all_clones)} clones (testing mode)")

            # Start all clones
            started_count, total_count = await clone_manager.start_all_clones()
            return started_count, total_count

        except Exception as e:
            logger.error(f"Error in start_all_clones: {e}")
            print(f"❌ DEBUG CLONE: Error in start_all_clones: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0

    async def start_all_active_clones(self):
        """Alias for start_all_clones for backward compatibility"""
        return await self.start_all_clones()

    def get_running_clones(self):
        """Get list of currently running clone IDs"""
        return list(self.active_clones.keys())

    async def check_subscriptions(self):
        """Check subscription status for all clones"""
        try:
            await self.cleanup_inactive_clones()
            await self.check_pending_clones()
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

                # Stop the clone if it's running
                if bot_id in self.active_clones:
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
                        # If it fails to start even with active subscription, consider marking as failed or deactivated
                        # For now, we'll let the _retry_pending_clone handle further retries if needed

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

    async def force_start_clone(self, clone_id: str):
        """Force start a specific clone (bypass all validations)"""
        try:
            logger.info(f"🔧 Force starting clone {clone_id}...")

            # Get clone data
            clone = await get_clone(clone_id)
            if not clone:
                return False, f"Clone {clone_id} not found"

            # Activate clone first
            await activate_clone(clone_id)

            # Try to start
            success, message = await self.start_clone(clone_id)

            if success:
                logger.info(f"✅ Force start successful for clone {clone_id}")
                return True, f"Clone {clone_id} force started successfully"
            else:
                logger.error(f"❌ Force start failed for clone {clone_id}: {message}")
                return False, f"Force start failed: {message}"

        except Exception as e:
            logger.error(f"❌ Force start error for clone {clone_id}: {e}")
            return False, f"Force start error: {str(e)}"

# Create global instance
clone_manager = CloneManager()