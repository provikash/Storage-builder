"""
Main callback query router - simplified and focused
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Import all the focused handlers
from bot.handlers import emergency, file_browsing, admin, callback, commands, start, search
from bot.programs import clone_admin, clone_features, clone_indexing, clone_management, clone_random_files

# Define callback priorities to prevent conflicts
CALLBACK_PRIORITIES = {
    "emergency": -10,    # Emergency handlers highest priority
    "clone_settings": -8, # Clone settings high priority
    "admin": 1,          # Admin callbacks
    "search": 4,         # Search related
    "general": 5,        # General callbacks
    "settings": 6,       # Settings handlers
    "catchall": 99       # Catch-all lowest priority
}

# Clone Settings Button Handler
@Client.on_callback_query(filters.regex(r"^clone_settings_panel$"), group=-5)
async def handle_clone_settings(client: Client, query: CallbackQuery):
    """Handle clone settings button"""
    await query.answer()
    user_id = query.from_user.id
    
    logger.info(f"🎛️ CLONE SETTINGS: User {user_id} accessing settings")
    
    try:
        from bot.plugins.clone_admin_settings import clone_settings_command
        
        # Create message proxy
        class MessageProxy:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat if query.message else None
                self.message_id = query.message.id if query.message else None
                self._query = query

            async def reply_text(self, text, reply_markup=None):
                return await self._query.edit_message_text(text, reply_markup=reply_markup)

            async def edit_message_text(self, text, reply_markup=None):
                return await self._query.edit_message_text(text, reply_markup=reply_markup)

        await clone_settings_command(client, MessageProxy(query))
        
    except Exception as e:
        logger.error(f"Error in clone settings: {e}")
        await query.edit_message_text("❌ Error loading settings. Please try again.")

# File Browsing Handlers
@Client.on_callback_query(filters.regex(r"^(random_files|recent_files|popular_files)$"), group=-4)
async def handle_file_browsing(client: Client, query: CallbackQuery):
    """Handle file browsing buttons"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"📁 FILE BROWSING: User {user_id} clicked {callback_data}")
    
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        
        # Check if this is a clone bot
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ File browsing is only available in clone bots.")
            return
            
        # Get clone data and check feature availability
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        
        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found.")
            return
        
        # Check if feature is enabled
        feature_map = {
            'random_files': 'random_mode',
            'recent_files': 'recent_mode', 
            'popular_files': 'popular_mode'
        }
        
        feature_key = feature_map.get(callback_data)
        if feature_key and not clone_data.get(feature_key, False):
            await query.edit_message_text(f"❌ {callback_data.replace('_', ' ').title()} feature is disabled.")
            return
        
        # Route to appropriate handler
        if callback_data == "random_files":
            from bot.plugins.clone_random_files import handle_clone_random_files
            await handle_clone_random_files(client, query)
        elif callback_data == "recent_files":
            from bot.plugins.clone_random_files import handle_clone_recent_files
            await handle_clone_recent_files(client, query)
        elif callback_data == "popular_files":
            from bot.plugins.clone_random_files import handle_clone_popular_files
            await handle_clone_popular_files(client, query)
            
    except Exception as e:
        logger.error(f"Error in file browsing: {e}")
        await query.edit_message_text("❌ Error accessing files. Please try again.")

# Catch-all handler for unhandled callbacks
@Client.on_callback_query(group=99)
@safe_callback_handler
async def catchall_callback_handler(client: Client, query: CallbackQuery):
    """Catch-all handler for unhandled callback queries"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")
    await query.answer("❌ This feature is not yet implemented.", show_alert=True)