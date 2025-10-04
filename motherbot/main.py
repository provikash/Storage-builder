
"""
Mother Bot Main Module
Handles mother bot startup and plugin loading
"""
import asyncio
from pyrogram import Client, idle
from info import Config
from shared.database.mongo_db import database
from logger import LOGGER

logger = LOGGER(__name__)

async def start_mother_bot():
    """Initialize and start the mother bot"""
    logger.info("🤖 Initializing Mother Bot...")
    
    # Create bot instance
    bot = Client(
        "mother_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="motherbot.plugins"),
        sleep_threshold=60
    )
    
    # Start database
    await database.connect()
    logger.info("✅ Database connected")
    
    # Start bot
    await bot.start()
    logger.info(f"✅ Mother Bot started: @{bot.me.username}")
    
    # Keep running
    await idle()
    
    # Cleanup
    await bot.stop()
    await database.disconnect()
    logger.info("👋 Mother Bot stopped")

def run_mother_bot():
    """Run the mother bot"""
    asyncio.run(start_mother_bot())
