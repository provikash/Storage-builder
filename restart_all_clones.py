
#!/usr/bin/env python3
"""
Script to restart all clone bots
"""
import asyncio
import logging
from clone_manager import clone_manager
from bot.database.clone_db import get_all_clones, activate_clone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def restart_all_clones():
    """Restart all clone bots"""
    try:
        print("🔄 Starting clone restart process...")
        
        # Get all clones
        all_clones = await get_all_clones()
        if not all_clones:
            print("❌ No clones found in database")
            return
        
        print(f"📋 Found {len(all_clones)} clones")
        
        # Stop all running clones first
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'unknown')
            
            if bot_id in clone_manager.active_clones:
                print(f"🛑 Stopping clone {username} ({bot_id})")
                try:
                    await clone_manager.stop_clone(bot_id)
                except Exception as e:
                    print(f"⚠️ Error stopping {username}: {e}")
        
        # Wait a bit
        await asyncio.sleep(3)
        
        # Activate and start all clones
        started_count = 0
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'unknown')
            
            print(f"🔄 Activating and starting clone {username} ({bot_id})")
            
            try:
                # Activate in database
                await activate_clone(bot_id)
                
                # Start the clone
                success, message = await clone_manager.start_clone(bot_id)
                if success:
                    started_count += 1
                    print(f"✅ Started {username}: {message}")
                else:
                    print(f"❌ Failed to start {username}: {message}")
            except Exception as e:
                print(f"❌ Error with {username}: {e}")
        
        print(f"🎉 Restart complete: {started_count}/{len(all_clones)} clones started")
        
    except Exception as e:
        print(f"❌ Fatal error during restart: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(restart_all_clones())
