
import uvloop
import asyncio
import logging
import signal
import sys
from pathlib import Path
from pyrogram import idle
from bot import Bot
from clone_manager import clone_manager
import pymongo

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

    # Check if .env file exists
    if not Path(".env").exists():
        logger.error("❌ .env file not found. Please create one based on .env.example")
        return False

    # Check logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.info("✅ Requirements check passed")
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

async def start_mother_bot():
    """Start the mother bot"""
    try:
        logger.info("📡 Initializing Mother Bot...")
        app = Bot()
        await app.start()

        me = await app.get_me()
        logger.info(f"✅ Mother Bot @{me.username} started successfully!")
        return app

    except Exception as e:
        logger.error(f"❌ Failed to start Mother Bot: {e}")
        raise

async def start_clone_system():
    """Start the clone management system"""
    try:
        logger.info("🔄 Starting Clone Manager...")
        await clone_manager.start_all_clones()
        logger.info("✅ Clone manager initialized")

        # Start subscription monitoring in background
        logger.info("⏱️ Starting subscription monitoring...")
        task = asyncio.create_task(clone_manager.check_subscriptions())
        logger.info("✅ Subscription monitoring started")
        return task

    except Exception as e:
        logger.error(f"❌ Clone manager initialization failed: {e}")
        return None

async def start_subscription_monitoring():
    """Start subscription monitoring for mother bot"""
    try:
        from bot.utils.subscription_checker import subscription_checker
        task = asyncio.create_task(subscription_checker.start_monitoring())
        logger.info("✅ Mother Bot subscription monitoring started")
        return task
    except Exception as e:
        logger.error(f"❌ Mother Bot subscription monitoring failed: {e}")
        return None

async def main():
    """Main function for Mother Bot + Clone System"""
    shutdown_handler = GracefulShutdown()
    shutdown_handler.setup_signal_handlers()

    app = None
    monitoring_tasks = []

    try:
        logger.info("🚀 Starting Mother Bot + Clone System...")

        # Check requirements
        if not await check_requirements():
            sys.exit(1)

        # Initialize databases
        if not await initialize_databases():
            sys.exit(1)

        # Start mother bot
        app = await start_mother_bot()
        me = await app.get_me()

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
            logger.info("✅ Web monitoring dashboard started on port 5000")
            logger.info("🌐 Dashboard URL: http://0.0.0.0:5000/dashboard")
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
                await app.stop()
                logger.info("✅ Mother Bot stopped")
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
