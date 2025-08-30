import uvloop
import asyncio
import logging
import signal
import sys
from pathlib import Path
from bot import Bot
from clone_manager import clone_manager
import pymongo
from pyrogram.client import Client
from info import Config

# Setup logging first
from bot.logging import LOGGER

logger = LOGGER(__name__)

uvloop.install()

class GracefulShutdown:
    """Handle graceful shutdown of the application"""

    def __init__(self):
        self.shutdown = False
        self.tasks = set()

    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}. Initiating graceful shutdown...")
        self.shutdown = True

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

async def check_requirements():
    """Check if all requirements are met before starting"""
    logger.info("🔍 Checking requirements...")
    print("🔍 DEBUG MAIN: Checking requirements...")

    # Check if .env file exists (optional in Replit environment)
    if not Path(".env").exists():
        logger.info("ℹ️ No .env file found - using environment variables directly (Replit mode)")
    else:
        logger.info("✅ .env file found")

    # Check logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.info("✅ Requirements check passed")
    print("✅ DEBUG MAIN: Requirements check passed")
    return True

async def initialize_databases():
    """Initialize all database components"""
    try:
        logger.info("🗄️ Initializing databases...")

        from bot.database.subscription_db import init_pricing_tiers
        from bot.database.clone_db import set_global_force_channels, get_global_about, set_global_about

        await init_pricing_tiers()
        logger.info("✅ Pricing tiers initialized")

        # Set default global settings if not exist
        global_about = await get_global_about()
        if not global_about:
            default_about = (
                "🤖 **About This Bot**\n\n"
                "This bot is powered by the Mother Bot System - "
                "an advanced file-sharing platform with clone creation capabilities.\n\n"
                "✨ **Features:**\n"
                "• Fast & reliable file sharing\n"
                "• Advanced search capabilities\n"
                "• Token verification system\n"
                "• Premium subscriptions\n"
                "• Clone bot creation\n\n"
                "🌟 **Want your own bot?**\n"
                "Contact the admin to create your personalized clone!\n\n"
                "🤖 **Made by Mother Bot System**\n"
                "Professional bot hosting & management solutions."
            )
            await set_global_about(default_about)
            logger.info("✅ Default global about page set")

        logger.info("✅ Database initialization completed")
        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

async def cleanup_session_files():
    """Clean up locked session files"""
    try:
        import os
        import glob
        
        # Remove journal files that cause locks
        journal_files = glob.glob("*.session-journal")
        for journal_file in journal_files:
            try:
                os.remove(journal_file)
                logger.info(f"✅ Removed journal file: {journal_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {journal_file}: {e}")
        
        # Remove WAL files
        wal_files = glob.glob("*.session-wal")
        for wal_file in wal_files:
            try:
                os.remove(wal_file)
                logger.info(f"✅ Removed WAL file: {wal_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {wal_file}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error cleaning session files: {e}")

async def start_mother_bot():
    """Start the mother bot"""
    try:
        logger.info("📡 Initializing Mother Bot...")
        print("📡 DEBUG BOT: Initializing Mother Bot...")

        # Clean up session files first
        await cleanup_session_files()
        
        # Wait a moment for file system to sync
        await asyncio.sleep(1)

        # Initialize and start Mother Bot with full plugin access
        mother_bot_plugins = {
            "root": "bot.plugins",
            "include": [
                "start_handler",
                "missing_commands",
                "step_clone_creation",
                "clone_management",
                "mother_admin",
                "admin_commands",
                "admin_panel",
                "balance_management",
                "search",
                "genlink",
                "channel",
                "callback_handlers",
                "callback_fix",
                "missing_callbacks",
                "premium",
                "token",
                "stats",
                "broadcast",
                "clone_admin_settings",
                "water_about"
            ]
        }

        app = Client(
            "mother_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=mother_bot_plugins,
            workdir="temp_sessions"  # Use separate directory for sessions
        )

        # Start with retry logic for rate limiting and connection state checking
        max_start_retries = 3
        for attempt in range(max_start_retries):
            try:
                # Check if client is already connected
                if not app.is_connected:
                    await app.start()
                    logger.info(f"✅ Mother Bot client started successfully!")
                    print(f"✅ DEBUG BOT: Mother Bot client started successfully!")
                else:
                    logger.info(f"✅ Mother Bot client already connected!")
                    print(f"✅ DEBUG BOT: Mother Bot client already connected!")
                return app
            except Exception as start_error:
                if "Client is already connected" in str(start_error):
                    logger.info(f"✅ Mother Bot client already connected (attempt {attempt + 1})")
                    print(f"✅ DEBUG BOT: Mother Bot client already connected (attempt {attempt + 1})")
                    return app
                elif "FLOOD_WAIT" in str(start_error):
                    import re
                    wait_time = int(re.search(r'(\d+)', str(start_error)).group(1)) if re.search(r'(\d+)', str(start_error)) else 15
                    logger.warning(f"FloodWait during start, waiting {wait_time} seconds (attempt {attempt + 1}/{max_start_retries})")
                    await asyncio.sleep(wait_time + 2)
                else:
                    logger.error(f"Start attempt {attempt + 1} failed: {start_error}")
                    if attempt == max_start_retries - 1:
                        raise
                    await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"❌ Failed to start Mother Bot: {e}")
        print(f"❌ DEBUG BOT: Failed to start Mother Bot: {e}")
        raise

async def start_clone_system():
    """Start the clone management system"""
    try:
        logger.info("🔄 Starting Clone Manager...")
        print("🔄 DEBUG CLONE: Starting Clone Manager...")
        await clone_manager.start_all_clones()
        logger.info("✅ Clone manager initialized")
        print("✅ DEBUG CLONE: Clone manager initialized")

        # Start subscription monitoring in background
        logger.info("⏱️ Starting subscription monitoring...")
        print("⏱️ DEBUG CLONE: Starting subscription monitoring...")
        task = asyncio.create_task(clone_manager.check_subscriptions())
        logger.info("✅ Subscription monitoring started")
        print("✅ DEBUG CLONE: Subscription monitoring started")
        return task

    except Exception as e:
        logger.error(f"❌ Clone manager initialization failed: {e}")
        print(f"❌ DEBUG CLONE: Clone manager initialization failed: {e}")
        return None

async def start_subscription_monitoring():
    """Start subscription monitoring for mother bot"""
    try:
        from bot.utils.subscription_checker import subscription_checker
        task = asyncio.create_task(subscription_checker.start_monitoring())
        logger.info("✅ Mother Bot subscription monitoring started")
        print("✅ DEBUG SUBSCRIPTION: Mother Bot subscription monitoring started")
        return task
    except Exception as e:
        logger.error(f"❌ Mother Bot subscription monitoring failed: {e}")
        print(f"❌ DEBUG SUBSCRIPTION: Mother Bot subscription monitoring failed: {e}")
        return None

async def main():
    """Main function for Mother Bot + Clone System"""
    shutdown_handler = GracefulShutdown()
    shutdown_handler.setup_signal_handlers()

    app = None
    monitoring_tasks = []

    try:
        logger.info("🚀 Starting Mother Bot + Clone System...")
        print("🚀 DEBUG MAIN: Starting Mother Bot + Clone System...")

        # Check requirements
        if not await check_requirements():
            sys.exit(1)

        # Initialize databases
        if not await initialize_databases():
            sys.exit(1)

        # Add startup delay to prevent immediate rate limiting
        await asyncio.sleep(2)

        # Start mother bot
        app = await start_mother_bot()

        # Get bot info with retry logic for FloodWait
        me = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ensure client is connected before getting info
                if not app.is_connected:
                    await app.connect()
                me = await app.get_me()
                break
            except Exception as e:
                if "FLOOD_WAIT" in str(e):
                    import re
                    wait_time = int(re.search(r'(\d+)', str(e)).group(1)) if re.search(r'(\d+)', str(e)) else 15
                    logger.warning(f"FloodWait detected, waiting {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time + 2)  # Add 2 extra seconds as buffer
                elif "Client is already connected" in str(e):
                    logger.warning(f"Client connection issue, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to get bot info: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(5)

        # Start clone system
        clone_task = await start_clone_system()
        if clone_task:
            monitoring_tasks.append(clone_task)

        # Start subscription monitoring
        subscription_task = await start_subscription_monitoring()
        if subscription_task:
            monitoring_tasks.append(subscription_task)

        # Add periodic pending clone check (every 10 minutes)
        async def periodic_pending_check():
            while True:
                try:
                    await asyncio.sleep(600)  # 10 minutes
                    await clone_manager.check_pending_clones()
                except Exception as e:
                    logger.error(f"❌ Error in periodic pending check: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error

        pending_monitor = asyncio.create_task(periodic_pending_check())
        monitoring_tasks.append(pending_monitor)

        # Start session cleanup task if session manager exists
        try:
            if hasattr(clone_manager, 'session_manager'):
                asyncio.create_task(clone_manager.session_manager.start_cleanup_task())
        except AttributeError:
            logger.warning("⚠️ Session manager not available, skipping cleanup task")

        # Clone request feature removed - users create clones directly

        # Start system monitoring
        try:
            from bot.utils.system_monitor import system_monitor
            monitoring_task = asyncio.create_task(system_monitor.start_monitoring())
            monitoring_tasks.append(monitoring_task)
            logger.info("✅ System monitoring started")
        except ImportError:
            logger.warning("⚠️ psutil not available, skipping system monitoring")
        except Exception as e:
            logger.error(f"❌ System monitoring failed: {e}")

        # Start health monitoring
        try:
            from bot.utils.health_check import health_checker
            health_task = asyncio.create_task(health_checker.start_monitoring())
            monitoring_tasks.append(health_task)
            logger.info("✅ Health monitoring started")
        except Exception as e:
            logger.error(f"❌ Health monitoring failed: {e}")

        # Start web server for monitoring dashboard
        try:
            from web.server import start_webserver
            web_thread = start_webserver()
            logger.info("✅ Web monitoring dashboard started (port 5000 or 8080)")
            logger.info("🌐 Dashboard URL: Available on web server port")
        except Exception as e:
            logger.error(f"❌ Web server failed: {e}")

        # Print startup summary
        logger.info("\n" + "="*60)
        logger.info("🎉 MOTHER BOT + CLONE SYSTEM READY!")
        logger.info("="*60)
        logger.info(f"🤖 Mother Bot: @{me.username}")
        logger.info(f"📊 Running Clones: {len(clone_manager.get_running_clones())}")
        logger.info(f"🎛️ Admin Panel: /motheradmin")
        logger.info(f"🆕 Create Clone: /createclone")
        logger.info("="*60)

        # Keep the application running using pyrogram's idle
        from pyrogram.sync import idle
        await idle()

    except KeyboardInterrupt:
        logger.info("⚠️ Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise
    finally:
        # Graceful shutdown
        logger.info("🛑 Initiating graceful shutdown...")

        # Cancel monitoring tasks
        for task in monitoring_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop all clones
        try:
            for bot_id in list(clone_manager.instances.keys()):
                await clone_manager.stop_clone(bot_id)
            logger.info("✅ All clones stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping clones: {e}")

        # Stop mother bot
        if app:
            try:
                if app.is_connected:
                    await app.stop()
                    logger.info("✅ Mother Bot stopped")
                else:
                    logger.info("✅ Mother Bot already disconnected")
            except Exception as e:
                logger.error(f"❌ Error stopping Mother Bot: {e}")

        logger.info("✅ Graceful shutdown completed")

if __name__ == "__main__":
    # Test MongoDB connection first
    try:
        from bot.database.mongo_db import MongoDB
        mongo = MongoDB()
        asyncio.run(mongo.test_connection())
        logger.info("✅ MongoDB connection test successful")
        mongo.close()
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred during MongoDB connection test: {e}")
        sys.exit(1)

    # Run the main application
    asyncio.run(main())