
import asyncio
import sys
sys.path.append('.')

from clone_manager import clone_manager
from bot.database.clone_db import get_all_clones, activate_clone

async def test_clone_manually():
    """Test clone startup manually"""
    print("🔧 Manual Clone Test Starting...")
    
    # Get all clones
    clones = await get_all_clones()
    print(f"📋 Found {len(clones)} clones")
    
    for clone in clones:
        clone_id = clone.get('_id')
        username = clone.get('username', 'Unknown')
        status = clone.get('status', 'unknown')
        
        print(f"🤖 Clone: @{username} (ID: {clone_id}) - Status: {status}")
        
        # Activate the clone
        print(f"🔄 Activating clone {clone_id}...")
        await activate_clone(clone_id)
        
        # Force start the clone
        print(f"🚀 Force starting clone {clone_id}...")
        success, message = await clone_manager.force_start_clone(clone_id)
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_clone_manually())
