#!/usr/bin/env python3
"""
Unified Clone Management CLI
Consolidates all clone start/restart/stop operations into a single tool
"""
import asyncio
import sys
import argparse
from clone_manager import clone_manager
from bot.database.clone_db import get_all_clones, activate_clone, get_clone, update_clone_data
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def start_all_clones():
    """Start all clones in database"""
    try:
        logger.info("🚀 Starting all clones...")
        all_clones = await get_all_clones()
        
        if not all_clones:
            logger.warning("❌ No clones found in database")
            return 0, 0
        
        logger.info(f"📊 Found {len(all_clones)} clones")
        started_count = 0
        
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'Unknown')
            
            try:
                await activate_clone(bot_id)
                success, message = await clone_manager.start_clone(bot_id)
                if success:
                    started_count += 1
                    logger.info(f"✅ Started {username}: {message}")
                else:
                    logger.error(f"❌ Failed to start {username}: {message}")
            except Exception as e:
                logger.error(f"❌ Error starting {username}: {e}")
        
        logger.info(f"🎉 Started {started_count}/{len(all_clones)} clones")
        return started_count, len(all_clones)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

async def restart_all_clones():
    """Restart all clone bots"""
    try:
        logger.info("🔄 Restarting all clones...")
        all_clones = await get_all_clones()
        
        if not all_clones:
            logger.warning("❌ No clones found in database")
            return 0, 0
        
        logger.info(f"📋 Found {len(all_clones)} clones")
        
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'unknown')
            
            if bot_id in clone_manager.active_clones:
                logger.info(f"🛑 Stopping clone {username}")
                try:
                    await clone_manager.stop_clone(bot_id)
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping {username}: {e}")
        
        await asyncio.sleep(3)
        
        started_count = 0
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'unknown')
            
            try:
                await activate_clone(bot_id)
                success, message = await clone_manager.start_clone(bot_id)
                if success:
                    started_count += 1
                    logger.info(f"✅ Started {username}: {message}")
                else:
                    logger.error(f"❌ Failed to start {username}: {message}")
            except Exception as e:
                logger.error(f"❌ Error with {username}: {e}")
        
        logger.info(f"🎉 Restart complete: {started_count}/{len(all_clones)} clones started")
        return started_count, len(all_clones)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

async def start_clone(bot_id: str):
    """Start a specific clone by bot ID"""
    try:
        logger.info(f"🔄 Starting clone {bot_id}")
        
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found")
            return False
            
        username = clone.get('username', 'Unknown')
        logger.info(f"📋 Found clone: {username}")
        
        await activate_clone(bot_id)
        await update_clone_data(bot_id, {"status": "active"})
        
        success, message = await clone_manager.start_clone(bot_id)
        if success:
            logger.info(f"🎉 Started {username}: {message}")
            return True
        else:
            logger.error(f"❌ Failed to start {username}: {message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error starting clone: {e}")
        import traceback
        traceback.print_exc()
        return False

async def restart_clone(bot_id: str):
    """Restart a specific clone by bot ID"""
    try:
        logger.info(f"🔄 Restarting clone {bot_id}")
        
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found")
            return False
            
        username = clone.get('username', 'Unknown')
        logger.info(f"📋 Found clone: {username}")
        
        if bot_id in clone_manager.active_clones:
            logger.info(f"🛑 Stopping {username}")
            await clone_manager.stop_clone(bot_id)
            await asyncio.sleep(2)
        
        await activate_clone(bot_id)
        success, message = await clone_manager.start_clone(bot_id)
        
        if success:
            logger.info(f"🎉 Restarted {username}: {message}")
            return True
        else:
            logger.error(f"❌ Failed to restart {username}: {message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error restarting clone: {e}")
        return False

async def stop_clone(bot_id: str):
    """Stop a specific clone by bot ID"""
    try:
        logger.info(f"🛑 Stopping clone {bot_id}")
        
        clone = await get_clone(bot_id)
        if not clone:
            logger.error(f"❌ Clone {bot_id} not found")
            return False
            
        username = clone.get('username', 'Unknown')
        
        if bot_id not in clone_manager.active_clones:
            logger.warning(f"⚠️ Clone {username} is not running")
            return True
        
        await clone_manager.stop_clone(bot_id)
        logger.info(f"✅ Stopped {username}")
        return True
            
    except Exception as e:
        logger.error(f"❌ Error stopping clone: {e}")
        return False

async def stop_all_clones():
    """Stop all running clones"""
    try:
        logger.info("🛑 Stopping all clones...")
        running_clones = list(clone_manager.active_clones.keys())
        
        if not running_clones:
            logger.warning("⚠️ No running clones found")
            return 0
        
        stopped_count = 0
        for bot_id in running_clones:
            try:
                await clone_manager.stop_clone(bot_id)
                stopped_count += 1
            except Exception as e:
                logger.error(f"❌ Error stopping clone {bot_id}: {e}")
        
        logger.info(f"✅ Stopped {stopped_count}/{len(running_clones)} clones")
        return stopped_count
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 0

async def list_clones():
    """List all clones with their status"""
    try:
        all_clones = await get_all_clones()
        
        if not all_clones:
            print("No clones found")
            return
        
        print(f"\n{'Bot ID':<15} {'Username':<25} {'Status':<15} {'Running':<10}")
        print("-" * 70)
        
        for clone in all_clones:
            bot_id = str(clone.get('_id', 'Unknown'))
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'unknown')
            running = "Yes" if bot_id in clone_manager.active_clones else "No"
            
            print(f"{bot_id:<15} {username:<25} {status:<15} {running:<10}")
        
        print(f"\nTotal: {len(all_clones)} clones")
        print(f"Running: {len(clone_manager.active_clones)} clones")
        
    except Exception as e:
        logger.error(f"❌ Error listing clones: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Unified Clone Management CLI')
    parser.add_argument('action', choices=['start', 'restart', 'stop', 'list', 'start-all', 'restart-all', 'stop-all'],
                       help='Action to perform')
    parser.add_argument('--bot-id', type=str, help='Bot ID for single clone operations')
    
    args = parser.parse_args()
    
    if args.action == 'start-all':
        await start_all_clones()
    elif args.action == 'restart-all':
        await restart_all_clones()
    elif args.action == 'stop-all':
        await stop_all_clones()
    elif args.action == 'list':
        await list_clones()
    elif args.action in ['start', 'restart', 'stop']:
        if not args.bot_id:
            print(f"Error: --bot-id required for {args.action} action")
            sys.exit(1)
        
        if args.action == 'start':
            success = await start_clone(args.bot_id)
        elif args.action == 'restart':
            success = await restart_clone(args.bot_id)
        else:
            success = await stop_clone(args.bot_id)
        
        sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    asyncio.run(main())
