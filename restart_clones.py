#!/usr/bin/env python3
"""
Script to manually restart all active clones
"""
import asyncio
import sys
from bot.database.clone_db import get_all_clones, activate_clone
from clone_manager import clone_manager
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def restart_all_clones():
    """Restart all clones that should be active"""
    try:
        logger.info("🔄 Starting clone restart process...")

        # Get all clones from database
        all_clones = await get_all_clones()

        if not all_clones:
            logger.warning("❌ No clones found in database")
            return

        logger.info(f"📊 Found {len(all_clones)} clones in database")

        active_count = 0
        started_count = 0

        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'inactive')

            logger.info(f"🤖 Processing clone: {username} ({bot_id}) - Status: {status}")

            # Activate clones that should be running (including stopped and deactivated ones)
            if status in ['active', 'pending', 'running', 'deactivated', 'stopped', 'inactive']:
                active_count += 1

                # Ensure it's marked as active
                await activate_clone(bot_id)
                logger.info(f"📝 Activated clone {username} ({bot_id}) in database")

                # Try to start it
                success, message = await clone_manager.start_clone(bot_id)

                if success:
                    started_count += 1
                    logger.info(f"✅ Started clone {username}: {message}")
                else:
                    logger.error(f"❌ Failed to start clone {username}: {message}")
            else:
                logger.info(f"⏭️ Skipping clone {username} with status: {status}")

        logger.info(f"🎉 Clone restart complete: {started_count}/{active_count} clones started")

    except Exception as e:
        logger.error(f"❌ Error during clone restart: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(restart_all_clones())