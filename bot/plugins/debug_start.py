
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("debug") & filters.private)
async def debug_command(client: Client, message: Message):
    """Debug command to test bot responsiveness"""
    try:
        await message.reply_text("🔧 **Debug Response**\n\n✅ Bot is responsive and working!")
        logger.info(f"Debug command successful for user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Debug command failed: {e}")

@Client.on_message(filters.text & filters.private, group=99)
async def catch_all_handler(client: Client, message: Message):
    """Catch-all handler to log unhandled messages"""
    if message.text and message.text.startswith('/'):
        logger.warning(f"Unhandled command: {message.text} from user {message.from_user.id}")
        await message.reply_text("❌ **Unknown Command**\n\nUse /start to see available options.")
