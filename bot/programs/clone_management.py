
"""
Clone Management Program
Handles clone bot lifecycle management
"""
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_mother_admin
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneManagementProgram:
    """Clone bot management program"""
    
    def __init__(self):
        self.name = "Clone Management"
    
    async def list_user_clones(self, user_id: int):
        """List all clones for a user"""
        from bot.database.clone_db import get_user_clones
        clones = await get_user_clones(user_id)
        return clones if clones else []
    
    async def get_clone_status(self, clone_id: str):
        """Get clone bot status"""
        from clone_manager import clone_manager
        running_clones = clone_manager.get_running_clones()
        return "running" if clone_id in running_clones else "stopped"
    
    def register_handlers(self, app: Client):
        """Register clone management handlers"""
        
        @app.on_message(filters.command("myclones") & filters.private)
        async def myclones_command(client: Client, message: Message):
            await self.show_user_clones(client, message)
    
    async def show_user_clones(self, client: Client, message: Message):
        """Show user's clone bots"""
        user_id = message.from_user.id
        
        clones = await self.list_user_clones(user_id)
        
        if not clones:
            text = "🤖 **My Clone Bots**\n\n"
            text += "You don't have any clone bots yet.\n\n"
            text += "Use /createclone to create your first clone!"
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create Clone", callback_data="start_clone_creation")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await message.reply_text(text, reply_markup=buttons)
            return
        
        text = f"🤖 **My Clone Bots** ({len(clones)})\n\n"
        buttons = []
        
        for clone in clones:
            clone_id = clone['_id']
            username = clone.get('username', 'Unknown')
            status = await self.get_clone_status(clone_id)
            status_emoji = "🟢" if status == "running" else "🔴"
            
            text += f"{status_emoji} @{username} - {status}\n"
            buttons.append([
                InlineKeyboardButton(
                    f"⚙️ Manage @{username}", 
                    callback_data=f"manage_clone_{clone_id}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("➕ Create New Clone", callback_data="start_clone_creation")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
        
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Global instance
clone_management_program = CloneManagementProgram()
