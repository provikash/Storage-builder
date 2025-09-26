
#!/usr/bin/env python3
import asyncio
import sys
from clone_manager import clone_manager
from bot.database.clone_db import activate_clone, get_clone
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def restart_specific_clone(bot_id: str):
    """Restart a specific clone by bot ID"""
    try:
        logger.info(f"🔄 Attempting to restart clone {bot_id}")
        
        # Get clone info
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found in database")
            return False
            
        username = clone.get('username', 'Unknown')
        logger.info(f"📋 Found clone: {username} ({bot_id})")
        
        # Stop if running
        if bot_id in clone_manager.active_clones:
            logger.info(f"🛑 Stopping running clone {username}")
            await clone_manager.stop_clone(bot_id)
            await asyncio.sleep(2)
        
        # Activate in database
        await activate_clone(bot_id)
        logger.info(f"✅ Activated clone {username} in database")
        
        # Start the clone
        success, message = await clone_manager.start_clone(bot_id)
        if success:
            logger.info(f"🎉 Successfully started clone {username}: {message}")
            return True
        else:
            logger.error(f"❌ Failed to start clone {username}: {message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error restarting clone {bot_id}: {e}")
        return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python restart_specific_clone.py <bot_id>")
        print("Example: python restart_specific_clone.py 6739244490")
        return
    
    bot_id = sys.argv[1]
    success = await restart_specific_clone(bot_id)
    
    if success:
        print(f"✅ Clone {bot_id} restarted successfully")
    else:
        print(f"❌ Failed to restart clone {bot_id}")

if __name__ == "__main__":
    asyncio.run(main())
