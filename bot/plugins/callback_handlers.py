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
    "clone_settings": -5, # Clone settings highest priority
    "admin": 1,          # Admin callbacks
    "search": 4,         # Search related
    "general": 5,        # General callbacks
    "settings": 6,       # Settings handlers
    "catchall": 99       # Catch-all lowest priority
}

# High priority clone settings handler
@Client.on_callback_query(filters.regex("^clone_settings_panel$"), group=CALLBACK_PRIORITIES["clone_settings"])
async def handle_clone_settings_direct(client: Client, query: CallbackQuery):
    """Direct clone settings handler with highest priority"""
    await query.answer()
    user_id = query.from_user.id
    
    logger.info(f"🎛️ DIRECT SETTINGS HANDLER: Clone settings accessed by user {user_id}")
    
    try:
        # Import and call the settings function directly
        from bot.plugins.clone_admin_settings import clone_settings_command
        
        # Create message proxy
        class MessageProxy:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat if query.message else None
                self.message_id = query.message.id if query.message else None

            async def reply_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

            async def edit_message_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

        proxy_message = MessageProxy(query)
        await clone_settings_command(client, proxy_message)
        
    except Exception as e:
        logger.error(f"Error in direct clone settings handler: {e}")
        await query.edit_message_text("❌ Error loading clone settings. Please try again.")

# Alternative patterns for clone settings
@Client.on_callback_query(filters.regex("^(clone_settings|settings)$"), group=CALLBACK_PRIORITIES["clone_settings"])
async def handle_clone_settings_alt(client: Client, query: CallbackQuery):
    """Alternative clone settings handler"""
    await query.answer()
    user_id = query.from_user.id
    
    logger.info(f"🎛️ ALT SETTINGS HANDLER: Settings accessed by user {user_id}")
    
    try:
        from bot.plugins.clone_admin_settings import clone_settings_command
        
        class MessageProxy:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat if query.message else None
                self.message_id = query.message.id if query.message else None

            async def reply_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

            async def edit_message_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

        proxy_message = MessageProxy(query)
        await clone_settings_command(client, proxy_message)
        
    except Exception as e:
        logger.error(f"Error in alt clone settings handler: {e}")
        await query.edit_message_text("❌ Error loading settings. Please try again.")

# Catch-all handler for unhandled callbacks
@Client.on_callback_query(group=CALLBACK_PRIORITIES["catchall"])
@safe_callback_handler
async def catchall_callback_handler(client: Client, query: CallbackQuery):
    """Catch-all handler for unhandled callback queries"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")

    await query.answer("❌ This button is not implemented yet.", show_alert=True)