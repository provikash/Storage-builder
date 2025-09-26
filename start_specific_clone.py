
#!/usr/bin/env python3
"""
Script to start a specific clone manually
"""
import asyncio
import sys
from clone_manager import clone_manager
from bot.database.clone_db import activate_clone, get_clone, update_clone_data
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def start_specific_clone_by_id(bot_id: str = "6739244490"):
    """Start a specific clone by bot ID"""
    try:
        logger.info(f"🔄 Attempting to start clone {bot_id}")
        
        # Get clone info
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found in database")
            return False
            
        username = clone.get('username', 'Unknown')
        logger.info(f"📋 Found clone: {username} ({bot_id})")
        
        # Force activate in database
        await activate_clone(bot_id)
        logger.info(f"✅ Activated clone {username} in database")
        
        # Update status to active
        await update_clone_data(bot_id, {"status": "active"})
        logger.info(f"✅ Updated clone status to active")
        
        # Start the clone
        success, message = await clone_manager.start_clone(bot_id)
        if success:
            logger.info(f"🎉 Successfully started clone {username}: {message}")
            return True
        else:
            logger.error(f"❌ Failed to start clone {username}: {message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error starting clone {bot_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    bot_id = sys.argv[1] if len(sys.argv) > 1 else "6739244490"
    asyncio.run(start_specific_clone_by_id(bot_id))
