
import asyncio
from clone_manager import clone_manager
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def startup_clones():
    """Start all active clones on startup"""
    try:
        logger.info("🚀 Starting clone manager...")
        started, total = await clone_manager.start_all_active_clones()
        logger.info(f"✅ Clone manager started: {started}/{total} clones running")
        
        # Schedule periodic cleanup
        asyncio.create_task(periodic_cleanup())
        
    except Exception as e:
        logger.error(f"❌ Error starting clone manager: {e}")

async def periodic_cleanup():
    """Periodic cleanup of inactive clones"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await clone_manager.cleanup_inactive_clones()
            logger.info("🔄 Periodic clone cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error in periodic cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(startup_clones())
