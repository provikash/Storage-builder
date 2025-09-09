
"""
Command handlers for mother bot and clone bots
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    user_id = message.from_user.id
    is_clone, _ = is_clone_bot_instance(client)
    
    if is_clone:
        await message.reply_text("🤖 **Clone Bot Help**\n\nThis is a clone bot. Use /start to see available features.")
    else:
        await message.reply_text("🤖 **Mother Bot Help**\n\nUse /start to see all available commands and features.")
