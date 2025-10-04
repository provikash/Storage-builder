
"""
Clone Random Files Program
Handles random file browsing for clone bots
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.callback_error_handler import safe_callback_handler
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneRandomFilesProgram:
    """Clone bot random files program"""
    
    def __init__(self):
        self.name = "Clone Random Files"
        self.file_types = {
            "random": {"name": "Random Files", "emoji": "🎲"},
            "recent": {"name": "Recent Files", "emoji": "🆕"},
            "popular": {"name": "Popular Files", "emoji": "🔥"}
        }
    
    async def get_random_files(self, clone_id: str, limit: int = 10):
        """Get random files from clone database"""
        from bot.database.mongo_db import get_random_files
        files = await get_random_files(limit=limit, clone_id=clone_id)
        return files if files else []
    
    async def get_recent_files(self, clone_id: str, limit: int = 10):
        """Get recent files from clone database"""
        from bot.database.mongo_db import get_recent_files
        files = await get_recent_files(limit=limit, clone_id=clone_id)
        return files if files else []
    
    async def get_popular_files(self, clone_id: str, limit: int = 10):
        """Get popular files from clone database"""
        from bot.database.mongo_db import get_popular_files
        files = await get_popular_files(limit=limit, clone_id=clone_id)
        return files if files else []
    
    def register_handlers(self, app: Client):
        """Register random files handlers"""
        
        @app.on_callback_query(filters.regex("^browse_"))
        @safe_callback_handler
        async def handle_file_browsing(client: Client, query: CallbackQuery):
            await self.handle_browse_callback(client, query)
    
    async def handle_browse_callback(self, client: Client, query: CallbackQuery):
        """Handle file browsing callbacks"""
        file_type = query.data.replace("browse_", "")
        
        is_clone, bot_token = is_clone_bot_instance(client)
        
        if not is_clone:
            await query.answer("❌ Only available in clone bots", show_alert=True)
            return
        
        clone_id = bot_token.split(':')[0]
        
        if file_type == "random":
            files = await self.get_random_files(clone_id)
        elif file_type == "recent":
            files = await self.get_recent_files(clone_id)
        elif file_type == "popular":
            files = await self.get_popular_files(clone_id)
        else:
            await query.answer("❌ Invalid file type", show_alert=True)
            return
        
        if not files:
            await query.answer("No files found", show_alert=True)
            return
        
        # Display files
        type_info = self.file_types.get(file_type, {})
        text = f"{type_info.get('emoji', '📁')} **{type_info.get('name', 'Files')}**\n\n"
        text += f"Found {len(files)} files\n\n"
        
        buttons = []
        for idx, file in enumerate(files[:5], 1):
            file_name = file.get('file_name', 'Unknown')
            buttons.append([
                InlineKeyboardButton(
                    f"{idx}. {file_name[:30]}...", 
                    callback_data=f"get_file_{file.get('_id')}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Global instance
clone_random_files_program = CloneRandomFilesProgram()
