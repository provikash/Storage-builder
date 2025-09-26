
#!/usr/bin/env python3
"""
Debug script for clone startup testing
"""
import asyncio
import sys
from clone_manager import clone_manager
from bot.database.clone_db import get_clone, activate_clone
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def test_clone_startup():
    """Test clone startup with detailed debugging"""
    bot_id = "6739244490"  # Your clone bot ID
    
    try:
        logger.info(f"🔍 Testing clone startup for bot {bot_id}")
        print(f"🔍 DEBUG: Testing clone startup for bot {bot_id}")
        
        # Get clone data
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found in database")
            print(f"❌ DEBUG: Clone {bot_id} not found in database")
            return False
            
        logger.info(f"📋 Clone data: {clone}")
        print(f"📋 DEBUG: Clone data found for {clone.get('username', 'Unknown')}")
        
        # Force activate
        await activate_clone(bot_id)
        logger.info(f"✅ Activated clone {bot_id}")
        print(f"✅ DEBUG: Activated clone {bot_id}")
        
        # Test token
        bot_token = clone.get('bot_token') or clone.get('token')
        if bot_token:
            logger.info(f"🔑 Bot token found: {bot_token[:20]}...")
            print(f"🔑 DEBUG: Bot token found: {bot_token[:20]}...")
        else:
            logger.error(f"❌ No bot token found")
            print(f"❌ DEBUG: No bot token found")
            return False
        
        # Attempt startup
        logger.info(f"🚀 Starting clone {bot_id}")
        print(f"🚀 DEBUG: Starting clone {bot_id}")
        
        success, message = await clone_manager.start_clone(bot_id)
        
        if success:
            logger.info(f"🎉 Clone startup successful: {message}")
            print(f"🎉 DEBUG: Clone startup successful: {message}")
            
            # Check if it's actually running
            if bot_id in clone_manager.active_clones:
                clone_info = clone_manager.active_clones[bot_id]
                logger.info(f"✅ Clone is active: {clone_info.get('status')}")
                print(f"✅ DEBUG: Clone is active: {clone_info.get('status')}")
            else:
                logger.warning(f"⚠️ Clone not found in active_clones")
                print(f"⚠️ DEBUG: Clone not found in active_clones")
                
        else:
            logger.error(f"❌ Clone startup failed: {message}")
            print(f"❌ DEBUG: Clone startup failed: {message}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Exception during clone test: {e}")
        print(f"❌ DEBUG: Exception during clone test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_clone_startup())
