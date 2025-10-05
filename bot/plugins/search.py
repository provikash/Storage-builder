# search.py (fixed)
# Source reviewed from user's uploaded file. See original for reference. fileciteturn0file0

from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from bot.database import (
    get_random_files, get_popular_files, get_recent_files,
    get_index_stats, increment_access_count, is_premium_user
)
from bot.utils import encode, get_readable_file_size, handle_force_sub
from bot.utils.command_verification import check_command_limit, use_command
from bot.utils.token_verification import TokenVerificationManager
from info import Config
import asyncio
import traceback
from datetime import datetime, timedelta
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Helper: determine if this client is a clone (uses clone DB)
def _is_clone_client(client: Client) -> bool:
    bot_token = getattr(client, "bot_token", Config.BOT_TOKEN)
    return bot_token != Config.BOT_TOKEN or getattr(client, "is_clone", False) or getattr(client, "clone_config", False) or getattr(client, "clone_data", False)

# Helper: safe send/edit text depending on whether message is a Message or CallbackQuery.message
async def _safe_send_or_edit(target, text, reply_markup=None, replace=False):
    """
    target: either Message or CallbackQuery.message (pyrogram.types.Message)
    If replace=True and target has edit_text, attempt to edit; otherwise reply.
    """
    try:
        if replace and hasattr(target, "edit_text"):
            await target.edit_text(text, reply_markup=reply_markup)
        else:
            await target.reply_text(text, reply_markup=reply_markup)
    except Exception:
        # fallback: try reply
        try:
            await target.reply_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Failed to send/edit message: {e}")

# --- Feature check (clone-aware) ---
async def check_feature_enabled(client: Client, feature_name: str) -> bool:
    """Check clone database for feature flag; mother bot returns False by default."""
    try:
        bot_token = getattr(client, "bot_token", Config.BOT_TOKEN)

        # If not a clone, mother bot disables these features
        if not _is_clone_client(client) and bot_token == Config.BOT_TOKEN:
            return False

        # For clone bots, query clone DB
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            logger.warning(f"Clone data not found for token {bot_token}; defaulting {feature_name} to enabled for clone.")
            return True
        feature_key = f"{feature_name}_mode"
        return clone_data.get(feature_key, True)
    except Exception as e:
        logger.exception(f"Error checking feature '{feature_name}': {e}")
        # fail open for clones
        return True

# NOTE: Random, Popular, and Recent file handlers are now in clone_random_files.py
# This file focuses only on search functionality to avoid duplication

# -----------------------
# Search command (placeholder)
# -----------------------
@Client.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ **Usage:** `/search <query>`\n\nExample: `/search funny videos`")
            return
        query = " ".join(message.command[1:])
        
        # This section is a placeholder for actual search logic.
        # It currently only returns a static message.
        # The actual implementation would involve querying a database or API.
        
        # Mocking search results for demonstration purposes.
        # In a real scenario, 'files' would be populated from a search query.
        files = [] # Placeholder for actual search results
        
        text = f"🔍 **Search Results for** `{query}`\n\n"

        if not files:
            await message.reply_text( # Changed from query.edit_message_text to message.reply_text
                "❌ **No Results Found!**\n\n"
                f"🔍 **Query:** `{query}`\n"
                f"💡 **Tip:** Try different keywords or check spelling\n\n"
                f"🔄 **Search Again:** /search <query>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="start")]
                ])
            )
            return

        # Paginate results
        per_page = 10
        total_pages = (len(files) + per_page - 1) // per_page
        current_page = int(message.text.split('_')[2]) if len(message.text.split('_')) > 2 else 1 # Changed from data to message.text

        start_idx = (current_page - 1) * per_page
        end_idx = start_idx + per_page
        page_files = files[start_idx:end_idx]

        text += f"\n📊 **Page {current_page}/{total_pages}** ({len(files)} total results)\n\n"

        for idx, file in enumerate(page_files, start_idx + 1):
            file_name = file.get('file_name', 'Unknown')
            file_size = get_readable_file_size(file.get('file_size', 0))
            file_type = file.get('file_type', '📄').upper()

            text += f"**{idx}.** `{file_name}`\n"
            text += f"📁 **Size:** {file_size} | 📋 **Type:** {file_type}\n\n"
        
        # If there are results, send the text. This part is reached only if 'files' is not empty.
        # For now, it just sends the static message as search results are mocked.
        await message.reply_text(text) 
        logger.info(f"Search query '{query}' from user {message.from_user.id}")
    except Exception as e:
        logger.exception(f"Error in search command: {e}")
        await message.reply_text("❌ Search error occurred. Please try again.")