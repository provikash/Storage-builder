import asyncio
import os
from datetime import datetime
from typing import Optional, Tuple
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

    async def start_clone(self, bot_id: str) -> Tuple[bool, str]:
        """Start a specific clone bot with enhanced error handling"""
        from bot.logging import LOGGER
        from bot.utils.security import security_manager
        import asyncio

        logger = LOGGER(__name__)

        # Input validation
        if not bot_id or not isinstance(bot_id, str):
            return False, "Invalid bot ID provided"

        if not bot_id.isdigit() or len(bot_id) < 8:
            return False, "Bot ID must be a valid numeric string"

        # Enhanced execution tracking with timeout
        class SimpleTracker:
            def __init__(self, name):
                self.name = name
                self.steps = []
                self.start_time = asyncio.get_event_loop().time()

            def add_step(self, step, data=None):
                self.steps.append(step)
                elapsed = asyncio.get_event_loop().time() - self.start_time
                logger.info(f"Step: {step} (elapsed: {elapsed:.2f}s)")

            def complete(self, success=False, error=None):
                elapsed = asyncio.get_event_loop().time() - self.start_time
                if success:
                    logger.info(f"Completed: {self.name} in {elapsed:.2f}s")
                else:
                    logger.error(f"Failed: {self.name} in {elapsed:.2f}s - {error}")

        tracker = SimpleTracker(f"start_clone_{bot_id}")

        # Prevent multiple simultaneous starts with proper locking
        if not hasattr(self, '_starting_clones'):
            self._starting_clones = set()
            self._clone_locks = {}

        if bot_id in self._starting_clones:
            logger.warning(f"Attempted to start clone {bot_id} while startup is already in progress.")
            return False, "Clone startup already in progress"

        # Create lock for this specific clone
        if bot_id not in self._clone_locks:
            self._clone_locks[bot_id] = asyncio.Lock()

        async with self._clone_locks[bot_id]:
            if bot_id in self._starting_clones:
                logger.warning(f"Attempted to start clone {bot_id} while startup is already in progress (inside lock).")
                return False, "Clone startup already in progress"

            self._starting_clones.add(bot_id)

        try:
            logger.info(f"📊 Starting clone: {bot_id}")
            print(f"📊 DEBUG: Starting clone: {bot_id}")

            # Check if clone is already running
            if bot_id in self.active_clones:
                logger.warning(f"⚠️ Clone {bot_id} is already running")
                return True, f"Clone {bot_id} is already running"

            tracker.add_step("fetching_clone_data")
            logger.debug(f"Fetching clone data for {bot_id}")

            clone = await get_clone(bot_id)
            if not clone:
                error_msg = "Clone not found in database"
                logger.error(f"❌ {error_msg} for bot {bot_id}")
                tracker.complete(success=False, error=error_msg)
                return False, error_msg

            tracker.add_step("clone_data_retrieved", {"clone_exists": True})
            logger.debug(f"Clone data retrieved for {bot_id}")

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
                    logger.debug(f"Clone {bot_id} already verified as running.")
                    return True, "Clone already running"
                else:
                    # Clean up stale entry
                    logger.warning(f"Stale entry found for clone {bot_id}, cleaning up.")
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
            logger.debug(f"Creating Pyrogram client for clone {bot_id}")
            clone_bot = await self._create_clone_client(bot_id, bot_token)
            if not clone_bot:
                error_msg = "Failed to create clone client"
                logger.error(f"❌ {error_msg} for bot {bot_id}")
                tracker.complete(success=False, error=error_msg)
                return False, error_msg
            tracker.add_step("client_created")
            logger.debug(f"Pyrogram client created for {bot_id}")

            # Start the bot with timeout and retry
            logger.debug(f"Attempting to start clone client {bot_id}")
            start_success = await self._start_clone_client(clone_bot, bot_id)
            if not start_success:
                error_msg = "Failed to start clone client"
                logger.error(f"❌ {error_msg} for bot {bot_id}")
                tracker.complete(success=False, error=error_msg)
                return False, error_msg
            tracker.add_step("client_started")
            logger.debug(f"Clone client started for {bot_id}")

            # Verify bot is working
            try:
                logger.debug(f"Verifying clone bot {bot_id} status via get_me")
                bot_info = await asyncio.wait_for(clone_bot.get_me(), timeout=10.0)
                logger.info(f"Clone bot started successfully: @{bot_info.username} (ID: {bot_id})")
                tracker.add_step("bot_verified", {"username": bot_info.username})
            except asyncio.TimeoutError:
                logger.error(f"❌ Bot startup verification timeout for clone {bot_id}")
                await self._safe_stop_client(clone_bot)
                error_msg = "Bot startup verification timeout"
                tracker.complete(success=False, error=error_msg)
                return False, error_msg
            except Exception as e:
                logger.error(f"❌ Bot verification failed for clone {bot_id}: {str(e)}")
                await self._safe_stop_client(clone_bot)
                error_msg = f"Bot verification failed: {str(e)}"
                tracker.complete(success=False, error=error_msg)
                return False, error_msg

            # Store in active clones with enhanced metadata
            self.active_clones[bot_id] = {
                'client': clone_bot,
                'data': clone,
                'status': 'running',
                'started_at': datetime.now(),
                'last_health_check': datetime.now(),
                'restart_count': clone.get('metadata', {}).get('restart_count', 0), # Access safely
                'username': bot_info.username if 'bot_info' in locals() else 'unknown'
            }
            logger.debug(f"Clone {bot_id} added to active_clones.")

            # Update database status
            await start_clone_in_db(bot_id)
            logger.debug(f"Database status updated for clone {bot_id} to 'active'.")

            # Create enhanced monitoring task
            task = asyncio.create_task(self._monitor_clone(bot_id))
            self.clone_tasks[bot_id] = task
            logger.debug(f"Monitoring task created for clone {bot_id}.")

            logger.info(f"✅ Clone {bot_id} started successfully")
            tracker.complete(success=True)
            return True, f"Clone @{bot_info.username} started successfully"

        except AuthKeyUnregistered:
            logger.error(f"❌ AuthKeyUnregistered for clone {bot_id}. Deactivating.")
            tracker.complete(success=False, error="AuthKeyUnregistered")
            await self._handle_clone_auth_error(bot_id, "auth_key_unregistered")
            return False, "Authentication key unregistered"
        except AccessTokenExpired:
            logger.error(f"❌ AccessTokenExpired for clone {bot_id}. Deactivating.")
            tracker.complete(success=False, error="AccessTokenExpired")
            await self._handle_clone_auth_error(bot_id, "access_token_expired")
            return False, "Access token expired"
        except AccessTokenInvalid:
            logger.error(f"❌ AccessTokenInvalid for clone {bot_id}. Deactivating.")
            tracker.complete(success=False, error="AccessTokenInvalid")
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
            logger.debug(f"Removed {bot_id} from _starting_clones set.")

    async def _validate_subscription(self, subscription: dict, bot_id: str) -> Tuple[bool, str]:
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
                logger.info(f"Clone {bot_id} client started successfully on attempt {attempt + 1}.")
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Clone {bot_id} start timeout (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                error_msg = str(e)
                if "Client is already connected" in error_msg:
                    logger.info(f"Clone {bot_id} already connected (attempt {attempt + 1})")
                    return True
                elif "invalid syntax" in error_msg.lower() or "syntax error" in error_msg.lower() or "unexpected indent" in error_msg.lower():
                    logger.error(f"Clone {bot_id} syntax error - stopping retries: {e}")
                    return False
                else:
                    logger.error(f"Clone {bot_id} start error (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff

        logger.error(f"Failed to start clone client {bot_id} after {max_retries} attempts.")
        return False

    async def _verify_clone_health(self, bot_id: str) -> bool:
        """Verify clone is actually healthy"""
        if bot_id not in self.active_clones:
            logger.debug(f"Health check: Clone {bot_id} not in active_clones.")
            return False

        try:
            clone_info = self.active_clones[bot_id]
            client = clone_info['client']

            if not client.is_connected:
                logger.debug(f"Health check: Client for {bot_id} is not connected.")
                return False

            # Try to get bot info with timeout
            await asyncio.wait_for(client.get_me(), timeout=5.0)
            logger.debug(f"Health check: Clone {bot_id} is healthy.")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Health check: Timeout verifying clone {bot_id}.")
            return False
        except Exception as e:
            logger.error(f"Health check: Exception verifying clone {bot_id}: {e}")
            return False

    async def _cleanup_stale_clone(self, bot_id: str):
        """Clean up stale clone entry"""
        logger.debug(f"Cleaning up stale clone entry for {bot_id}")
        try:
            if bot_id in self.active_clones:
                clone_info = self.active_clones[bot_id]
                client = clone_info.get('client')
                if client:
                    await self._safe_stop_client(client)
                del self.active_clones[bot_id]
                logger.debug(f"Removed {bot_id} from active_clones.")

            if bot_id in self.clone_tasks:
                self.clone_tasks[bot_id].cancel()
                del self.clone_tasks[bot_id]
                logger.debug(f"Cancelled and removed monitoring task for {bot_id}.")

        except Exception as e:
            logger.error(f"Error cleaning up stale clone {bot_id}: {e}")

    async def _safe_stop_client(self, client: Client):
        """Safely stop a client"""
        try:
            if client.is_connected:
                logger.debug("Attempting to stop client gracefully.")
                await asyncio.wait_for(client.stop(), timeout=10.0)
                logger.debug("Client stopped gracefully.")
        except asyncio.TimeoutError:
            logger.warning("Client stop timed out, attempting to disconnect forcefully.")
            try:
                if hasattr(client, 'disconnect'):
                    await client.disconnect()
                    logger.debug("Client disconnected forcefully.")
            except Exception as disconnect_err:
                logger.error(f"Error during forceful disconnect: {disconnect_err}")
        except Exception as e:
            logger.error(f"Error during safe stop: {e}")
        pass  # Ignore errors during shutdown

    async def _handle_clone_auth_error(self, bot_id: str, error_type: str):
        """Handle authentication errors for clones"""
        logger.info(f"Handling authentication error ({error_type}) for clone {bot_id}")
        try:
            # Deactivate clone
            await deactivate_clone(bot_id)
            logger.debug(f"Clone {bot_id} deactivated in database.")

            # Update clone status with error info
            await update_clone_data(bot_id, {
                'status': 'auth_error',
                'error_type': error_type,
                'error_time': datetime.now()
            })
            logger.debug(f"Updated clone {bot_id} status to 'auth_error' in database.")

            # Clean up active clone
            if bot_id in self.active_clones:
                await self._cleanup_stale_clone(bot_id)
                logger.debug(f"Cleaned up active clone entry for {bot_id}.")

        except Exception as e:
            logger.error(f"Error handling auth error for clone {bot_id}: {e}")

    async def start_all_clones(self):
        """Start all active clones"""
        logger.info("Attempting to start all clones from the database.")
        try:
            # Get list of all clones first
            from bot.database.clone_db import get_all_clones
            all_clones = await get_all_clones()

            if not all_clones:
                logger.warning("⚠️ No clones found in database to start.")
                print("⚠️ DEBUG CLONE: No clones found in database")
                return 0, 0

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

            # Start all clones individually
            started_count = 0
            total_count = len(all_clones)

            for clone in all_clones:
                bot_id = clone.get('_id')
                if bot_id:
                    try:
                        logger.info(f"Attempting to start clone {bot_id}...")
                        success, message = await self.start_clone(bot_id)
                        if success:
                            started_count += 1
                            logger.info(f"Result for clone {bot_id}: Success - {message}")
                        else:
                            logger.error(f"Result for clone {bot_id}: Failure - {message}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while trying to start clone {bot_id}: {e}", exc_info=True)

            logger.info(f"📊 Finished attempting to start all clones. Successfully started: {started_count}/{total_count}")
            return started_count, total_count

        except Exception as e:
            logger.error(f"Error in start_all_clones: {e}", exc_info=True)
            print(f"❌ DEBUG CLONE: Error in start_all_clones: {e}")
            return 0, 0

    async def _monitor_clone(self, bot_id: str):
        """Enhanced clone monitoring with health checks"""
        logger.info(f"Starting monitoring task for clone {bot_id}")
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
                            clone_info['status'] = 'running' # Update status on successful reconnect
                        else:
                            logger.error(f"❌ Failed to reconnect clone {bot_id}. Stopping monitoring.")
                            break
                    else:
                        # Verify connection with ping
                        await asyncio.wait_for(client.get_me(), timeout=10.0)
                        logger.debug(f"Clone {bot_id} is connected and healthy.")

                    # Update health check time
                    clone_info['last_health_check'] = datetime.now()

                except asyncio.TimeoutError:
                    logger.warning(f"Health check timeout for clone {bot_id}")
                except Exception as e:
                    logger.error(f"Health check failed for clone {bot_id}: {e}", exc_info=True)
                    break

                # Update last seen in DB
                try:
                    await update_clone_last_seen(bot_id)
                except Exception as db_err:
                    logger.error(f"Failed to update last_seen for clone {bot_id}: {db_err}")

                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute

        except asyncio.CancelledError:
            logger.info(f"🛑 Monitoring task for clone {bot_id} cancelled")
        except Exception as e:
            logger.error(f"❌ Error in monitoring task for clone {bot_id}: {e}", exc_info=True)
        finally:
            # Clean up on exit if the clone is still thought to be active by this task
            if bot_id in self.active_clones:
                logger.info(f"Monitoring task for {bot_id} exiting, initiating cleanup.")
                await self._cleanup_stale_clone(bot_id)

    async def _reconnect_clone(self, client: Client, bot_id: str, max_attempts: int = 3) -> bool:
        """Attempt to reconnect a clone"""
        logger.info(f"Attempting to reconnect clone {bot_id}...")
        for attempt in range(max_attempts):
            try:
                await asyncio.wait_for(client.start(), timeout=20.0)
                logger.info(f"Successfully reconnected clone {bot_id} on attempt {attempt + 1}.")
                return True
            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt + 1} failed for clone {bot_id}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(min(2 ** attempt, 30)) # Exponential backoff
        logger.error(f"Failed to reconnect clone {bot_id} after {max_attempts} attempts.")
        return False

    async def stop_clone(self, bot_id: str):
        """Stop a clone bot"""
        logger.info(f"Stopping clone {bot_id}")
        try:
            if bot_id not in self.active_clones:
                logger.warning(f"Attempted to stop clone {bot_id}, but it is not currently running.")
                return False, "Clone not running"

            # Cancel background task
            if bot_id in self.clone_tasks:
                logger.debug(f"Cancelling monitoring task for clone {bot_id}")
                self.clone_tasks[bot_id].cancel()
                try:
                    await self.clone_tasks[bot_id] # Wait for cancellation
                except asyncio.CancelledError:
                    pass
                del self.clone_tasks[bot_id]
                logger.debug(f"Monitoring task for clone {bot_id} cancelled.")

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
                    logger.error(f"❌ Error cleaning handlers for {bot_id}: {cleanup_error}")

                # Stop the clone client with timeout
                if clone_bot.is_connected:
                    logger.debug(f"Clone {bot_id} client is connected, stopping...")
                    await self._safe_stop_client(clone_bot)
                    logger.info(f"✅ Clone {bot_id} stopped gracefully")
                else:
                    logger.info(f"✅ Clone {bot_id} was already disconnected")
            except Exception as e:
                logger.error(f"❌ Error stopping clone client {bot_id}: {e}", exc_info=True)
            finally:
                # Remove from active clones regardless of stop success
                if bot_id in self.active_clones:
                    del self.active_clones[bot_id]
                    logger.debug(f"Removed {bot_id} from active_clones.")


            # Update database status
            await stop_clone_in_db(bot_id)
            logger.debug(f"Updated database status for clone {bot_id} to 'stopped'.")

            logger.info(f"🛑 Clone {bot_id} stopped successfully")
            return True, "Clone stopped successfully"

        except Exception as e:
            logger.error(f"❌ Error stopping clone {bot_id}: {e}", exc_info=True)
            # Ensure it's removed from active clones if an error occurred during stop
            if bot_id in self.active_clones:
                del self.active_clones[bot_id]
                logger.debug(f"Removed {bot_id} from active_clones after error.")
            return False, str(e)

    async def _keep_clone_running(self, bot_id: str):
        """Keep clone running in background - This function seems redundant with _monitor_clone and might be removed or refactored"""
        logger.info(f"Starting background 'keep running' task for clone {bot_id}")
        try:
            while bot_id in self.active_clones:
                clone_info = self.active_clones[bot_id]
                clone_bot = clone_info['client']

                # Check if bot is still connected
                if not clone_bot.is_connected:
                    logger.warning(f"⚠️ Background task: Clone {bot_id} disconnected, attempting restart...")
                    try:
                        await clone_bot.start()
                        logger.info(f"✅ Background task: Clone {bot_id} reconnected")
                    except Exception as e:
                        logger.error(f"❌ Background task: Failed to reconnect clone {bot_id}: {e}")
                        break # Exit loop if reconnect fails

                # Update last seen
                try:
                    await update_clone_last_seen(bot_id)
                except Exception as db_err:
                    logger.error(f"Background task: Failed to update last_seen for clone {bot_id}: {db_err}")

                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info(f"🛑 Background task for clone {bot_id} cancelled")
        except Exception as e:
            logger.error(f"❌ Error in background task for clone {bot_id}: {e}", exc_info=True)
        finally:
            # This task might need to trigger cleanup if it's the primary monitor
            if bot_id in self.active_clones:
                logger.info(f"Background task for {bot_id} exiting, initiating cleanup.")
                await self._cleanup_stale_clone(bot_id)

    async def restart_clone(self, bot_id: str):
        """Restart a clone bot"""
        logger.info(f"Restarting clone {bot_id}")
        try:
            # Stop first
            success_stop, msg_stop = await self.stop_clone(bot_id)
            if not success_stop:
                logger.warning(f"Clone {bot_id} was not running or failed to stop: {msg_stop}. Proceeding with start attempt.")

            await asyncio.sleep(2)  # Wait a bit for resources to release

            # Start again
            logger.info(f"Attempting to start clone {bot_id} after stop.")
            success_start, msg_start = await self.start_clone(bot_id)
            if success_start:
                logger.info(f"Clone {bot_id} restarted successfully.")
            else:
                logger.error(f"Clone {bot_id} failed to start after restart: {msg_start}")
            return success_start, msg_start
        except Exception as e:
            logger.error(f"❌ Error restarting clone {bot_id}: {e}", exc_info=True)
            return False, str(e)

    async def get_clone_status(self, bot_id: str):
        """Get clone status"""
        logger.debug(f"Getting status for clone {bot_id}")
        if bot_id in self.active_clones:
            clone_info = self.active_clones[bot_id]
            try:
                client = clone_info['client']
                connected = client.is_connected
                # Optionally perform a quick health check
                is_healthy = await self._verify_clone_health(bot_id)
                status = 'running' if is_healthy else 'unhealthy'
            except Exception:
                status = 'error_checking_status'
                connected = False

            return {
                'status': status,
                'started_at': clone_info['started_at'],
                'connected': connected,
                'username': clone_info.get('username', 'unknown')
            }
        else:
            # Check DB for status if not active
            try:
                clone_data = await get_clone(bot_id)
                if clone_data:
                    return {'status': clone_data.get('status', 'stopped'), 'connected': False, 'username': clone_data.get('username', 'unknown')}
                else:
                    return {'status': 'not_found', 'connected': False, 'username': 'unknown'}
            except Exception:
                return {'status': 'db_error', 'connected': False, 'username': 'unknown'}

    async def start_all_active_clones(self):
        """Alias for start_all_clones for backward compatibility"""
        logger.info("Calling start_all_clones via start_all_active_clones alias.")
        return await self.start_all_clones()

    def get_running_clones(self):
        """Get list of currently running clone IDs"""
        running_ids = list(self.active_clones.keys())
        logger.debug(f"Currently running clones: {running_ids}")
        return running_ids

    async def check_subscriptions(self):
        """Check subscription status for all clones and manage lifecycle"""
        logger.info("Initiating subscription checks and lifecycle management.")
        try:
            await self.cleanup_inactive_clones()
            await self.check_pending_clones()
            logger.info("✅ Subscription check and lifecycle management completed.")
        except Exception as e:
            logger.error(f"❌ Error during subscription check and lifecycle management: {e}", exc_info=True)

    async def _retry_pending_clone(self, bot_id: str, delay: int = 300):
        """Retry starting a clone with pending subscription after delay"""
        max_retries = 12  # 12 retries = 1 hour of checking (5 min intervals)
        retry_count = 0
        logger.info(f"Starting retry mechanism for pending clone {bot_id}. Max retries: {max_retries}, initial delay: {delay}s")

        try:
            while retry_count < max_retries:
                await asyncio.sleep(delay)
                retry_count += 1
                logger.debug(f"Retry attempt {retry_count}/{max_retries} for pending clone {bot_id}")

                # Check if subscription is now active
                subscription = await get_subscription(bot_id)
                if subscription and subscription['status'] == 'active':
                    logger.info(f"🔄 Retrying clone {bot_id} - subscription now active (attempt {retry_count})")
                    success, message = await self.start_clone(bot_id)
                    if success:
                        logger.info(f"✅ Successfully started pending clone {bot_id} on retry.")
                        return # Stop retrying if successful
                    else:
                        logger.warning(f"⚠️ Still failed to start clone {bot_id} after subscription became active: {message}. Continuing retries.")
                        # If it fails to start even with active subscription, continue retrying until max retries
                elif subscription and subscription['status'] in ['expired', 'cancelled']:
                    logger.warning(f"🛑 Stopping retry for clone {bot_id} - subscription status is {subscription['status']}. Deactivating.")
                    await deactivate_clone(bot_id)
                    await update_clone_data(bot_id, {'status': 'subscription_inactive'})
                    return # Stop retrying
                else:
                    logger.info(f"⏳ Clone {bot_id} subscription still not active or status unknown (attempt {retry_count}/{max_retries}). Status: {subscription.get('status', 'N/A') if subscription else 'Not Found'}")

            # If loop finishes without success
            logger.error(f"⚠️ Max retries ({max_retries}) reached for clone {bot_id} - subscription never became active or start failed repeatedly. Marking as failed.")
            await clones_collection.update_one(
                {"_id": bot_id},
                {"$set": {"status": "pending_timeout", "last_check": datetime.now()}}
            )
            logger.debug(f"Updated clone {bot_id} status to 'pending_timeout'.")

        except Exception as e:
            logger.error(f"❌ Error in retry mechanism for pending clone {bot_id}: {e}", exc_info=True)

    async def cleanup_inactive_clones(self):
        """Cleanup inactive or expired clones"""
        logger.info("Running cleanup for inactive or expired clones.")
        try:
            # Find expired subscriptions
            from bot.database.subscription_db import subscriptions_collection
            expired_subscriptions = await subscriptions_collection.find({
                "expires_at": {"$lt": datetime.now()},
                "status": "active"
            }).to_list(None)

            logger.debug(f"Found {len(expired_subscriptions)} subscriptions that have expired.")

            for subscription in expired_subscriptions:
                bot_id = subscription.get('bot_id')
                if not bot_id:
                    logger.warning("Found expired subscription with no bot_id. Skipping.")
                    continue

                logger.info(f"Deactivating expired clone {bot_id} (subscription expired at {subscription.get('expires_at')})")

                # Stop the clone if it's running
                if bot_id in self.active_clones:
                    logger.debug(f"Clone {bot_id} is running, stopping it first.")
                    await self.stop_clone(bot_id)

                # Deactivate in database
                await deactivate_clone(bot_id)
                logger.debug(f"Deactivated clone {bot_id} in database.")

                # Update subscription status
                await subscriptions_collection.update_one(
                    {"_id": bot_id},
                    {"$set": {"status": "expired", "expires_at": subscription.get('expires_at')}}
                )
                logger.debug(f"Updated subscription status for {bot_id} to 'expired'.")

            logger.info(f"Finished cleanup for {len(expired_subscriptions)} expired clones.")

        except Exception as e:
            logger.error(f"❌ Error during inactive clone cleanup: {e}", exc_info=True)

    async def check_pending_clones(self):
        """Check and attempt to start pending clones"""
        logger.info("Checking for clones with pending subscriptions.")
        try:
            from bot.database.subscription_db import subscriptions_collection

            # Find clones that are marked as pending_subscription in the clones collection
            # This assumes the status 'pending_subscription' is set in the clones_collection
            pending_clones_in_db = await clones_collection.find({
                "status": "pending_subscription"
            }).to_list(None)

            logger.debug(f"Found {len(pending_clones_in_db)} clones with status 'pending_subscription'.")

            for clone in pending_clones_in_db:
                bot_id = clone.get('_id')
                if not bot_id:
                    logger.warning("Found pending clone with no _id. Skipping.")
                    continue

                logger.info(f"Checking subscription status for pending clone {bot_id}.")

                # Check if subscription is now active
                subscription = await get_subscription(bot_id)
                if subscription and subscription['status'] == 'active':
                    logger.info(f"🔄 Subscription is active for pending clone {bot_id}. Attempting to start.")
                    success, message = await self.start_clone(bot_id)
                    if success:
                        logger.info(f"✅ Successfully started previously pending clone {bot_id}.")
                    else:
                        logger.warning(f"⚠️ Failed to start clone {bot_id} even with active subscription: {message}. Will retry later if needed.")
                        # Optionally, trigger the retry mechanism here if start fails
                        # asyncio.create_task(self._retry_pending_clone(bot_id))
                elif subscription and subscription['status'] in ['expired', 'cancelled']:
                    logger.warning(f"🛑 Subscription for pending clone {bot_id} is now {subscription['status']}. Deactivating clone.")
                    await deactivate_clone(bot_id)
                    await update_clone_data(bot_id, {'status': 'subscription_inactive'})
                else:
                    logger.debug(f"Subscription for pending clone {bot_id} is still pending or not found. Status: {subscription.get('status', 'N/A') if subscription else 'Not Found'}")
                    # If no subscription or status is still pending, consider starting the retry mechanism
                    # asyncio.create_task(self._retry_pending_clone(bot_id))

            logger.info("Finished checking pending clones.")

        except Exception as e:
            logger.error(f"❌ Error checking pending clones: {e}", exc_info=True)

    async def delete_all_clones(self):
        """Delete all clones and clean up resources"""
        logger.warning("Initiating deletion of ALL clones and associated data.")
        try:
            # Stop all running clones first
            running_clones = list(self.active_clones.keys())
            logger.info(f"Stopping {len(running_clones)} currently running clones before deletion.")
            for bot_id in running_clones:
                await self.stop_clone(bot_id)
                logger.info(f"🛑 Stopped clone {bot_id} in preparation for deletion.")

            # Get all clones from database
            all_clones = await get_all_clones()
            logger.info(f"Found {len(all_clones)} clones in the database to delete.")
            deleted_count = 0

            for clone in all_clones:
                bot_id = clone.get('_id')
                if not bot_id:
                    logger.warning("Found clone entry without _id during mass deletion. Skipping.")
                    continue

                logger.info(f"Deleting clone {bot_id}...")
                try:
                    # Delete from database collections
                    from bot.database.clone_db import delete_clone, delete_clone_config
                    from bot.database.subscription_db import delete_subscription

                    await delete_clone(bot_id)
                    await delete_clone_config(bot_id)
                    await delete_subscription(bot_id)

                    deleted_count += 1
                    logger.info(f"🗑️ Successfully deleted clone {bot_id} and related data.")

                except Exception as e:
                    logger.error(f"❌ Error deleting clone {bot_id}: {e}", exc_info=True)

            # Clear internal tracking
            self.active_clones.clear()
            self.clone_tasks.clear()
            logger.info("Cleared internal tracking of active clones and tasks.")

            logger.warning(f"🗑️ Mass deletion completed: {deleted_count}/{len(all_clones)} clones successfully deleted.")
            return deleted_count, len(all_clones)

        except Exception as e:
            logger.error(f"❌ Fatal error during mass clone deletion process: {e}", exc_info=True)
            return 0, 0

    async def force_start_clone(self, clone_id: str):
        """Force start a specific clone (bypass all validations)"""
        logger.info(f"🔧 Force starting clone {clone_id}...")
        try:
            # Get clone data
            clone = await get_clone(clone_id)
            if not clone:
                logger.error(f"Force start failed: Clone {clone_id} not found in database.")
                return False, f"Clone {clone_id} not found"

            # Activate clone first if it's not already active
            current_status = clone.get('status', 'stopped')
            if current_status != 'active':
                await activate_clone(clone_id)
                logger.debug(f"Activated clone {clone_id} in database before force start.")
            else:
                logger.debug(f"Clone {clone_id} is already active in database.")

            # Try to start, bypassing normal validations within start_clone if possible
            # Note: start_clone itself has some inherent checks that might not be fully bypassable here.
            # This function primarily ensures it's marked 'active' and then calls start_clone.
            success, message = await self.start_clone(clone_id)

            if success:
                logger.info(f"✅ Force start successful for clone {clone_id}")
                return True, f"Clone {clone_id} force started successfully"
            else:
                logger.error(f"❌ Force start failed for clone {clone_id}: {message}")
                return False, f"Force start failed: {message}"

        except Exception as e:
            logger.error(f"❌ Exception during force start for clone {clone_id}: {e}", exc_info=True)
            return False, f"Force start error: {str(e)}"

# Create global instance
clone_manager = CloneManager()

# ==================== CLI FUNCTIONS ====================

async def start_all_clones_cli():
    """Start all clones in database (CLI wrapper)"""
    logger.info("CLI: Request received to start all clones.")
    try:
        logger.info("🚀 CLI: Starting all clones...")
        all_clones = await get_all_clones()

        if not all_clones:
            logger.warning("CLI: No clones found in database to start.")
            print("No clones found in the database.")
            return 0, 0

        logger.info(f"CLI: Found {len(all_clones)} clones in the database.")
        started_count = 0
        total_clones = len(all_clones)

        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'Unknown')

            if not bot_id:
                logger.warning(f"CLI: Skipping clone entry with no _id during start-all.")
                continue

            try:
                logger.info(f"CLI: Activating and starting clone {username} ({bot_id})...")
                await activate_clone(bot_id)
                await update_clone_data(bot_id, {"status": "active"}) # Ensure status is 'active'

                success, message = await clone_manager.start_clone(bot_id)
                if success:
                    started_count += 1
                    logger.info(f"CLI: Successfully started {username} ({bot_id}): {message}")
                else:
                    logger.error(f"CLI: Failed to start {username} ({bot_id}): {message}")
            except Exception as e:
                logger.error(f"CLI: An unexpected error occurred while starting {username} ({bot_id}): {e}", exc_info=True)

        logger.info(f"CLI: Finished starting all clones. Result: {started_count}/{total_clones} started successfully.")
        print(f"\nCLI Result: Started {started_count}/{total_clones} clones.")
        return started_count, total_clones

    except Exception as e:
        logger.error(f"CLI: Fatal error during start_all_clones_cli: {e}", exc_info=True)
        print(f"CLI Error: A fatal error occurred. Check logs for details.")
        return 0, 0

async def restart_all_clones_cli():
    """Restart all clone bots (CLI wrapper)"""
    logger.info("CLI: Request received to restart all clones.")
    try:
        logger.info("🔄 CLI: Restarting all clones...")
        all_clones = await get_all_clones()

        if not all_clones:
            logger.warning("CLI: No clones found in database to restart.")
            print("No clones found in the database.")
            return 0, 0

        logger.info(f"CLI: Found {len(all_clones)} clones.")

        # First, stop all running clones
        stopping_tasks = []
        for clone in all_clones:
            bot_id = clone.get('_id')
            if bot_id in clone_manager.active_clones:
                logger.info(f"CLI: Stopping clone {clone.get('username', bot_id)}...")
                stopping_tasks.append(clone_manager.stop_clone(bot_id))
        if stopping_tasks:
            await asyncio.gather(*stopping_tasks)
            logger.info("CLI: All running clones have been signaled to stop.")

        await asyncio.sleep(3) # Give a moment for processes to shut down

        # Then, start them again
        started_count = 0
        total_clones = len(all_clones)
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'unknown')

            if not bot_id:
                logger.warning(f"CLI: Skipping clone entry with no _id during restart-all.")
                continue

            try:
                logger.info(f"CLI: Activating and starting clone {username} ({bot_id}) after restart.")
                await activate_clone(bot_id)
                await update_clone_data(bot_id, {"status": "active"})

                success, message = await clone_manager.start_clone(bot_id)
                if success:
                    started_count += 1
                    logger.info(f"CLI: Successfully restarted {username} ({bot_id}): {message}")
                else:
                    logger.error(f"CLI: Failed to restart {username} ({bot_id}): {message}")
            except Exception as e:
                logger.error(f"CLI: An unexpected error occurred during restart of {username} ({bot_id}): {e}", exc_info=True)

        logger.info(f"CLI: Finished restarting all clones. Result: {started_count}/{total_clones} started successfully.")
        print(f"\nCLI Result: Restarted {started_count}/{total_clones} clones.")
        return started_count, total_clones

    except Exception as e:
        logger.error(f"CLI: Fatal error during restart_all_clones_cli: {e}", exc_info=True)
        print(f"CLI Error: A fatal error occurred during restart. Check logs for details.")
        return 0, 0

async def start_clone_cli(bot_id: str):
    """Start a specific clone by bot ID (CLI wrapper)"""
    logger.info(f"CLI: Request received to start clone {bot_id}")
    try:
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"CLI: Clone {bot_id} not found in database.")
            print(f"Error: Clone with ID {bot_id} not found.")
            return False

        username = clone.get('username', 'Unknown')
        logger.info(f"CLI: Found clone {username} ({bot_id}).")

        logger.info(f"CLI: Activating and starting clone {username} ({bot_id})...")
        await activate_clone(bot_id)
        await update_clone_data(bot_id, {"status": "active"}) # Ensure status is 'active'

        success, message = await clone_manager.start_clone(bot_id)
        if success:
            logger.info(f"CLI: Successfully started {username} ({bot_id}): {message}")
            print(f"Successfully started clone {username}.")
            return True
        else:
            logger.error(f"CLI: Failed to start {username} ({bot_id}): {message}")
            print(f"Failed to start clone {username}: {message}")
            return False

    except Exception as e:
        logger.error(f"CLI: Error starting clone {bot_id}: {e}", exc_info=True)
        print(f"CLI Error: An unexpected error occurred while starting clone {bot_id}. Check logs.")
        return False

async def restart_clone_cli(bot_id: str):
    """Restart a specific clone by bot ID (CLI wrapper)"""
    logger.info(f"CLI: Request received to restart clone {bot_id}")
    try:
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"CLI: Clone {bot_id} not found in database.")
            print(f"Error: Clone with ID {bot_id} not found.")
            return False

        username = clone.get('username', 'Unknown')
        logger.info(f"CLI: Found clone {username} ({bot_id}).")

        logger.info(f"CLI: Attempting to restart clone {username} ({bot_id})...")
        # The restart_clone method handles stop and start internally
        success, message = await clone_manager.restart_clone(bot_id)

        if success:
            logger.info(f"CLI: Successfully restarted {username} ({bot_id}): {message}")
            print(f"Successfully restarted clone {username}.")
            return True
        else:
            logger.error(f"CLI: Failed to restart {username} ({bot_id}): {message}")
            print(f"Failed to restart clone {username}: {message}")
            return False

    except Exception as e:
        logger.error(f"CLI: Error restarting clone {bot_id}: {e}", exc_info=True)
        print(f"CLI Error: An unexpected error occurred while restarting clone {bot_id}. Check logs.")
        return False

async def stop_clone_cli(bot_id: str):
    """Stop a specific clone by bot ID (CLI wrapper)"""
    logger.info(f"CLI: Request received to stop clone {bot_id}")
    try:
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"CLI: Clone {bot_id} not found in database.")
            print(f"Error: Clone with ID {bot_id} not found.")
            return False

        username = clone.get('username', 'Unknown')

        if bot_id not in clone_manager.active_clones:
            logger.warning(f"CLI: Clone {username} ({bot_id}) is not currently running.")
            print(f"Clone {username} is not running.")
            return True # Indicate success as it's already stopped

        logger.info(f"CLI: Stopping clone {username} ({bot_id})...")
        success, message = await clone_manager.stop_clone(bot_id)

        if success:
            logger.info(f"CLI: Successfully stopped {username} ({bot_id}).")
            print(f"Successfully stopped clone {username}.")
            return True
        else:
            logger.error(f"CLI: Failed to stop {username} ({bot_id}): {message}")
            print(f"Failed to stop clone {username}: {message}")
            return False

    except Exception as e:
        logger.error(f"CLI: Error stopping clone {bot_id}: {e}", exc_info=True)
        print(f"CLI Error: An unexpected error occurred while stopping clone {bot_id}. Check logs.")
        return False

async def stop_all_clones_cli():
    """Stop all running clones (CLI wrapper)"""
    logger.info("CLI: Request received to stop all running clones.")
    try:
        running_clones_ids = clone_manager.get_running_clones()

        if not running_clones_ids:
            logger.warning("CLI: No running clones found to stop.")
            print("No running clones found.")
            return 0

        logger.info(f"CLI: Found {len(running_clones_ids)} running clones. Initiating stop process...")

        stopping_tasks = []
        for bot_id in running_clones_ids:
            stopping_tasks.append(clone_manager.stop_clone(bot_id))

        results = await asyncio.gather(*stopping_tasks, return_exceptions=True)

        stopped_count = 0
        for i, result in enumerate(results):
            bot_id = running_clones_ids[i]
            if isinstance(result, tuple) and result[0]: # (True, message)
                stopped_count += 1
                logger.info(f"CLI: Successfully stopped clone {bot_id}.")
            else:
                logger.error(f"CLI: Failed to stop clone {bot_id}. Result: {result}")

        logger.info(f"CLI: Finished stopping clones. Stopped {stopped_count}/{len(running_clones_ids)} running clones.")
        print(f"\nCLI Result: Stopped {stopped_count}/{len(running_clones_ids)} running clones.")
        return stopped_count

    except Exception as e:
        logger.error(f"CLI: Fatal error during stop_all_clones_cli: {e}", exc_info=True)
        print(f"CLI Error: A fatal error occurred during stop all. Check logs.")
        return 0

async def list_clones_cli():
    """List all clones with their status (CLI function)"""
    logger.info("CLI: Request received to list all clones.")
    try:
        all_clones_data = await get_all_clones()

        if not all_clones_data:
            print("No clones found in the database.")
            return

        print("\n--- Clone Status ---")
        print(f"{'Bot ID':<15} {'Username':<25} {'DB Status':<15} {'Running':<10}")
        print("-" * 70)

        running_clone_ids = clone_manager.get_running_clones()

        for clone in all_clones_data:
            bot_id = str(clone.get('_id', 'Unknown'))
            username = clone.get('username', 'Unknown')
            db_status = clone.get('status', 'unknown')
            is_running = bot_id in running_clone_ids
            running_indicator = "Yes" if is_running else "No"

            print(f"{bot_id:<15} {username:<25} {db_status:<15} {running_indicator:<10}")

        print("-" * 70)
        print(f"Total clones in DB: {len(all_clones_data)}")
        print(f"Currently running clones: {len(running_clone_ids)}")
        print("--------------------")

    except Exception as e:
        logger.error(f"CLI: Error listing clones: {e}", exc_info=True)
        print(f"CLI Error: An error occurred while listing clones. Check logs.")

async def cli_main():
    """CLI main entry point"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Unified Clone Management CLI')
    parser.add_argument('action', choices=['start', 'restart', 'stop', 'list', 'start-all', 'restart-all', 'stop-all'],
                       help='Action to perform: start, restart, stop, list, start-all, restart-all, stop-all')
    parser.add_argument('--bot-id', type=str, help='Bot ID for single clone operations (start, restart, stop)')

    # Parse arguments. If no args provided, print help and exit.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.action == 'start-all':
        await start_all_clones_cli()
    elif args.action == 'restart-all':
        await restart_all_clones_cli()
    elif args.action == 'stop-all':
        await stop_all_clones_cli()
    elif args.action == 'list':
        await list_clones_cli()
    elif args.action in ['start', 'restart', 'stop']:
        if not args.bot_id:
            print(f"Error: --bot-id is required for the '{args.action}' action.")
            sys.exit(1)
        
        if args.action == 'start':
            success = await start_clone_cli(args.bot_id)
        elif args.action == 'restart':
            success = await restart_clone_cli(args.bot_id)
        else: # stop
            success = await stop_clone_cli(args.bot_id)

        sys.exit(0 if success else 1)
    else:
        # This case should ideally not be reached due to 'choices' in add_argument
        print(f"Unknown action: {args.action}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)