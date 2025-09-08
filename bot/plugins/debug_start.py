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

# Debug utilities for tracking unhandled commands
# Remove the duplicate start handler to prevent conflicts
# The main start handler is in start_handler.py

@Client.on_message(filters.private & filters.text, group=99)
async def debug_unhandled_commands(client: Client, message: Message):
    """Debug handler for potentially unhandled commands - reduced priority"""
    try:
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0]
            # Only log if it's not a known command
            known_commands = ['/start', '/help', '/search', '/balance', '/clonestatus', '/users']
            if command not in known_commands:
                logger.debug(f"Potentially unhandled command: {command} from user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in debug handler: {e}")