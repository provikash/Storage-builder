
"""
Callback query handlers
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.utils.callback_error_handler import safe_callback_handler
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Import all callback handlers from the original callback_handlers.py
# This will be the main callback routing module

@Client.on_callback_query(filters.regex("^(test_callback)$"), group=5)
@safe_callback_handler
async def test_callback_handler(client: Client, query: CallbackQuery):
    """Test callback handler"""
    await query.answer("Test callback received!")
