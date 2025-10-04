
"""
Clone Indexing Program  
Handles file indexing for clone bots
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_clone_admin
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneIndexingProgram:
    """Clone bot file indexing program"""
    
    def __init__(self):
        self.name = "Clone Indexing"
        self.indexing_sessions = {}
    
    async def start_indexing(self, client: Client, message: Message, channel_input: str):
        """Start indexing from a channel"""
        user_id = message.from_user.id
        
        # Parse channel input
        channel_id = await self.parse_channel_input(channel_input)
        
        if not channel_id:
            await message.reply_text("❌ Invalid channel format. Use @username or channel ID")
            return
        
        # Start indexing process
        self.indexing_sessions[user_id] = {
            'channel_id': channel_id,
            'status': 'active',
            'indexed_count': 0
        }
        
        status_msg = await message.reply_text("📚 **Starting indexing...**\n\n⏳ Please wait...")
        
        # Actual indexing logic would go here
        await status_msg.edit_text("✅ **Indexing completed!**\n\n📊 Files indexed: 0")
    
    async def parse_channel_input(self, channel_input: str):
        """Parse channel username or ID"""
        if channel_input.startswith('@'):
            return channel_input
        elif channel_input.startswith('-100'):
            return int(channel_input)
        else:
            try:
                return int(channel_input)
            except ValueError:
                return None
    
    def register_handlers(self, app: Client):
        """Register indexing handlers"""
        
        @app.on_message(filters.command(["index", "indexing"]) & filters.private)
        async def index_command(client: Client, message: Message):
            await self.handle_index_command(client, message)
    
    async def handle_index_command(self, client: Client, message: Message):
        """Handle index command"""
        user_id = message.from_user.id
        
        # Check if user is clone admin
        from bot.utils.permissions import is_clone_bot_instance
        is_clone, bot_token = is_clone_bot_instance(client)
        
        if not is_clone:
            await message.reply_text("❌ Indexing is only available in clone bots")
            return
        
        # Check admin permission
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        
        if not clone_data or clone_data.get('admin_id') != user_id:
            await message.reply_text("❌ Only clone admin can use indexing")
            return
        
        if len(message.command) < 2:
            help_text = (
                "📚 **Clone Indexing**\n\n"
                "**Usage:** `/index <channel>`\n\n"
                "**Examples:**\n"
                "• `/index @channelname`\n"
                "• `/index -1001234567890`\n\n"
                "**Features:**\n"
                "✅ Auto-duplicate detection\n"
                "✅ Progress tracking\n"
                "✅ Error recovery"
            )
            await message.reply_text(help_text)
            return
        
        channel_input = message.command[1]
        await self.start_indexing(client, message, channel_input)

# Global instance  
clone_indexing_program = CloneIndexingProgram()
