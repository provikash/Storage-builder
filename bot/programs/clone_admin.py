
"""
Clone admin functionality and commands
"""
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from bot.utils.permissions import require_clone_admin, is_clone_bot_instance
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_command(client: Client, message: Message):
    """Handle clone admin panel command"""
    user_id = message.from_user.id
    
    is_clone, bot_token = is_clone_bot_instance(client)
    if not is_clone:
        await message.reply_text("❌ This command is only available in clone bots!")
        return
        
    # Get clone data and verify admin
    from bot.database.clone_db import get_clone_by_bot_token
    clone_data = await get_clone_by_bot_token(bot_token)
    
    if not clone_data:
        await message.reply_text("❌ Clone configuration not found!")
        return
        
    if int(user_id) != int(clone_data.get('admin_id')):
        await message.reply_text("❌ Only clone admin can access this panel!")
        return
        
    await message.reply_text("🛠️ **Clone Admin Panel**\n\nManage your clone bot settings and features.")

# Move all clone admin related handlers here from bot/plugins/clone_admin.py
