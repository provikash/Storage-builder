
"""
Clone bot management and lifecycle
"""
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from bot.utils.permissions import require_mother_admin
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("myclones") & filters.private)
async def my_clones_command(client: Client, message: Message):
    """Handle my clones command"""
    user_id = message.from_user.id
    
    try:
        from bot.database.clone_db import get_user_clones
        user_clones = await get_user_clones(user_id)
        
        if not user_clones:
            await message.reply_text("🤖 You don't have any clone bots yet.\n\nUse /createclone to create your first clone!")
            return
            
        text = "🤖 **Your Clone Bots:**\n\n"
        for clone in user_clones:
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'Unknown')
            text += f"• @{username} - {status}\n"
            
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error in myclones command: {e}")
        await message.reply_text("❌ Error loading your clones. Please try again.")

# Move all clone management related handlers here
