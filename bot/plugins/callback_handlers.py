"""
Main callback query router - simplified and focused
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Import all the focused handlers
from bot.handlers import emergency, file_browsing, admin

# Define callback priorities to prevent conflicts
CALLBACK_PRIORITIES = {
    "emergency": -10,    # Emergency handlers highest priority
    "admin": 1,          # Admin callbacks
    "search": 4,         # Search related
    "general": 5,        # General callbacks
    "settings": 6,       # Settings handlers
    "catchall": 99       # Catch-all lowest priority
}

# Catch-all handler for unhandled callbacks
@Client.on_callback_query(group=CALLBACK_PRIORITIES["catchall"])
@safe_callback_handler
async def catchall_callback_handler(client: Client, query: CallbackQuery):
    """Catch-all handler for unhandled callback queries"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")

    await query.answer("❌ This button is not implemented yet.", show_alert=True)