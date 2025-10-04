
"""
Clone Bot Main Module
Handles clone bot manager startup and clone coordination
"""
import asyncio
from pyrogram import Client, idle
from info import Config
from shared.database.mongo_db import database
from clonebot.manager.clone_manager import CloneManager
from logger import LOGGER

logger = LOGGER(__name__)

async def start_clone_system():
    """Initialize and start the clone bot system"""
    logger.info("🤖 Initializing Clone Bot System...")
    
    # Start database
    await database.connect()
    logger.info("✅ Database connected")
    
    # Create clone manager
    clone_manager = CloneManager()
    
    # Start all active clones
    await clone_manager.start_all_clones()
    logger.info(f"✅ Clone system started: {clone_manager.active_count} clones active")
    
    # Keep running
    await idle()
    
    # Cleanup
    await clone_manager.stop_all_clones()
    await database.disconnect()
    logger.info("👋 Clone system stopped")

def run_clone_system():
    """Run the clone bot system"""
    asyncio.run(start_clone_system())
