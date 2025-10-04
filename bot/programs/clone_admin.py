
"""
Clone Admin Program
Handles clone bot administration functionality
"""
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_clone_admin, is_clone_bot_instance
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneAdminProgram:
    """Clone administration program handler"""
    
    def __init__(self):
        self.name = "Clone Admin"
        self.handlers = []
        
    async def get_clone_settings(self, client: Client, bot_token: str):
        """Get clone settings for display"""
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        return clone_data
    
    async def show_admin_panel(self, client: Client, message: Message):
        """Show clone admin panel"""
        user_id = message.from_user.id
        
        is_clone, bot_token = is_clone_bot_instance(client)
        if not is_clone:
            await message.reply_text("❌ This command is only available in clone bots!")
            return
            
        clone_data = await self.get_clone_settings(client, bot_token)
        
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found!")
            return
            
        if int(user_id) != int(clone_data.get('admin_id')):
            await message.reply_text("❌ Only clone admin can access this panel!")
            return
        
        text = "⚙️ **Clone Admin Panel**\n\n"
        text += f"🤖 **Bot:** @{clone_data.get('username', 'Unknown')}\n"
        text += f"📊 **Status:** {clone_data.get('status', 'Unknown')}\n\n"
        text += "**Manage your clone bot settings below:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎛️ Features", callback_data="clone_admin_features"),
                InlineKeyboardButton("📊 Stats", callback_data="clone_admin_stats")
            ],
            [
                InlineKeyboardButton("🔐 Force Channels", callback_data="clone_admin_force"),
                InlineKeyboardButton("🔑 Token Settings", callback_data="clone_admin_token")
            ],
            [InlineKeyboardButton("🔙 Close", callback_data="close")]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
    
    def register_handlers(self, app: Client):
        """Register all clone admin handlers"""
        
        @app.on_message(filters.command("cloneadmin") & filters.private)
        async def clone_admin_command(client: Client, message: Message):
            await self.show_admin_panel(client, message)
        
        @app.on_callback_query(filters.regex("^clone_admin_"))
        async def clone_admin_callbacks(client: Client, query: CallbackQuery):
            await self.handle_admin_callback(client, query)
    
    async def handle_admin_callback(self, client: Client, query: CallbackQuery):
        """Handle admin panel callbacks"""
        callback_data = query.data
        
        if callback_data == "clone_admin_features":
            await query.answer("Loading features...")
            # Delegate to features program
        elif callback_data == "clone_admin_stats":
            await query.answer("Loading stats...")
            # Show stats
        elif callback_data == "clone_admin_force":
            await query.answer("Loading force channels...")
            # Show force channels
        elif callback_data == "clone_admin_token":
            await query.answer("Loading token settings...")
            # Show token settings

# Global instance
clone_admin_program = CloneAdminProgram()
