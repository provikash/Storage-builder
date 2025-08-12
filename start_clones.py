
#!/usr/bin/env python3
"""
Start all configured clones
Usage: python3 start_clones.py
"""

import asyncio
from clone_manager import clone_manager

async def main():
    print("🚀 Starting Mother Bot Clone System...")
    
    # List existing clones
    clone_manager.list_clones()
    
    # Start all clones
    await clone_manager.start_all_clones()
    
    print("✅ All clones started! Press Ctrl+C to stop.")
    
    try:
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all clones...")
        
        # Stop all clones
        for bot_id in list(clone_manager.clones.keys()):
            await clone_manager.stop_clone(bot_id)
        
        print("✅ All clones stopped.")

if __name__ == "__main__":
    asyncio.run(main())
