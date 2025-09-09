
"""
Search and file browsing handlers
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.text & filters.private)
async def handle_search_query(client: Client, message: Message):
    """Handle search queries"""
    user_id = message.from_user.id
    query = message.text.strip()
    
    is_clone, _ = is_clone_bot_instance(client)
    
    if is_clone and len(query) > 2:
        # Handle search in clone bot
        await message.reply_text(f"🔍 Searching for: `{query}`")
