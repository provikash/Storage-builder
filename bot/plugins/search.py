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

# -----------------------
# Random command - /rand
# -----------------------
@Client.on_message(filters.command("rand") & filters.private)
async def random_command(client: Client, message: Message):
    """Handle /rand command (clone bots only)."""
    try:
        logger.debug(f"/rand command from {message.from_user.id}")
        if not _is_clone_client(client):
            await message.reply_text(
                "🤖 **File Features Not Available Here**\n\n"
                "The `/rand` command is only available in **clone bots**, not in the mother bot.\n\n"
                "🔧 **How to access file features:**\n"
                "1. Create your personal clone bot with `/createclone`\n"
                "2. Use your clone bot to access random files"
            )
            return

        if await handle_force_sub(client, message):
            return

        if not await check_feature_enabled(client, "random"):
            await message.reply_text("❌ Random files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id
        needs_verification, remaining = await check_command_limit(user_id, client)
        if needs_verification:
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get("verification_mode", "command_limit")
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            if verification_mode == "token_required":
                message_text = (
                    "🔐 **Access Token Required!**\n\n"
                    "This bot requires token verification to use commands."
                )
            else:
                command_limit = token_settings.get("command_limit", 3)
                message_text = (
                    "⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands. Get a token or upgrade to Premium!"
                )
            await message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(buttons))
            return

        # Try to use one command
        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text(
                "🔐 **Command Limit Reached!**\n"
                "You've used your free commands. Verify or upgrade to continue.",
                reply_markup=buttons
            )
            return

        # Show random files
        await handle_random_files(client, message, is_callback=False, skip_command_check=True)
    except Exception as e:
        logger.exception(f"/rand handler failed: {e}")
        try:
            await message.reply_text(f"❌ Command failed: {e}")
        except Exception:
            pass

# Keyboard handlers (examples) - they reuse the same underlying functions
@Client.on_message(filters.private & filters.text & filters.regex(r"^🎲 Random$"))
async def keyboard_random_handler(client: Client, message: Message):
    try:
        if await handle_force_sub(client, message):
            return
        if not await check_feature_enabled(client, "random"):
            await message.reply_text("❌ Random files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id
        needs_verification, remaining = await check_command_limit(user_id, client)
        if needs_verification and remaining <= 0:
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get("verification_mode", "command_limit")
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            if verification_mode == "time_based":
                duration = token_settings.get("time_duration", 24)
                message_text = f"⚠️ Verification required. Get {duration} hours access."
            else:
                cmd_limit = token_settings.get("command_limit", 3)
                message_text = f"⚠️ Command limit reached. Get {cmd_limit} more commands via token."
            await message.reply_text(message_text, reply_markup=buttons)
            return

        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text("🔐 Command limit reached.", reply_markup=buttons)
            return

        await handle_random_files(client, message, is_callback=False)
    except Exception as e:
        logger.exception(f"keyboard_random_handler error: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

# -----------------------
# Core: handle_random_files
# -----------------------
async def handle_random_files(client: Client, message, is_callback: bool = True, skip_command_check: bool = False):
    """
    Present random files for clone bots.
    message may be a pyrogram Message object (normal) or CallbackQuery.message (for edits).
    """
    try:
        # Determine replacement target object (Message)
        target_msg = message
        if isinstance(message, CallbackQuery):
            target_msg = message.message

        bot_token = getattr(client, "bot_token", Config.BOT_TOKEN)
        bot_id = bot_token.split(":", 1)[0] if ":" in bot_token else bot_token
        if not _is_clone_client(client):
            await _safe_send_or_edit(target_msg, "❌ This feature is not available on the mother bot. Create a clone bot to use it.")
            return

        # fetch random files for this clone (pass clone id if DB supports it)
        try:
            files = await get_random_files(limit=5, clone_id=bot_id)
        except TypeError:
            # backward-compat: some implementations expect signature get_random_files(limit=5)
            files = await get_random_files(5)

        if not files:
            await _safe_send_or_edit(target_msg,
                "📂 **No Files Found**

No files are currently available in the database.",
                reply_markup=None, replace=False)
            return

        text_lines = ["🎲 **Random Files**
"]
        buttons = []
        for i, f in enumerate(files, start=1):
            file_name = f.get("file_name") or f.get("filename") or "Unknown File"
            file_size = get_readable_file_size(f.get("file_size", 0))
            display_name = (file_name[:30] + "...") if len(file_name) > 30 else file_name
            text_lines.append(f"{i}. 📁 **{file_name}** — {file_size}")
            # Use DB _id for callback payload but encode to string safely
            file_db_id = f.get("_id", f.get("file_id", f"unknown_{i}"))
            callback_data = f"file_{str(file_db_id)}"
            buttons.append([InlineKeyboardButton(f"📥 {display_name}", callback_data=callback_data)])

        # Add refresh row
        buttons.append([InlineKeyboardButton("🔄 Get More Random Files", callback_data="rand_new")])
        reply_markup = InlineKeyboardMarkup(buttons)
        text = "
".join(text_lines)

        # Send or edit depending on callback state
        if is_callback and hasattr(target_msg, "edit_text"):
            await _safe_send_or_edit(target_msg, text, reply_markup=reply_markup, replace=True)
        else:
            await _safe_send_or_edit(target_msg, text, reply_markup=reply_markup, replace=False)

    except Exception as e:
        logger.exception(f"Error in handle_random_files: {e}")
        try:
            # best-effort send error
            if isinstance(message, CallbackQuery):
                await message.answer("❌ Error fetching random files.", show_alert=True)
            else:
                await message.reply_text("❌ Error fetching random files.")
        except Exception:
            pass

# -----------------------
# Popular & Recent display
# -----------------------
async def _determine_clone_id_from_client(client: Client):
    clone_id = getattr(client, "clone_id", None)
    if clone_id:
        return clone_id
    bot_token = getattr(client, "bot_token", Config.BOT_TOKEN)
    if bot_token != Config.BOT_TOKEN:
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return clone_data.get("id")
    return None

@Client.on_callback_query(filters.regex(r"^rand_"))
async def random_callback(client: Client, callback_query: CallbackQuery):
    """Handle rand_* callbacks (new/popular/recent/stats)"""
    try:
        if await handle_force_sub(client, callback_query.message):
            return

        parts = callback_query.data.split("_", 1)
        if len(parts) < 2:
            await callback_query.answer("❌ Invalid action", show_alert=True)
            return
        action = parts[1]
        if action == "new":
            if not await check_feature_enabled(client, "random"):
                await callback_query.answer("❌ Random feature disabled", show_alert=True)
                return
            await handle_random_files(client, callback_query.message, is_callback=True)
        elif action in ("popular", "pop"):
            if not await check_feature_enabled(client, "popular"):
                await callback_query.answer("❌ Popular feature disabled", show_alert=True)
                return
            await show_popular_files(client, callback_query)
        elif action in ("recent",):
            if not await check_feature_enabled(client, "recent"):
                await callback_query.answer("❌ Recent feature disabled", show_alert=True)
                return
            await show_recent_files(client, callback_query)
        elif action in ("stats",):
            await show_index_stats(client, callback_query)
        else:
            await callback_query.answer("❌ Unknown action", show_alert=True)
        try:
            await callback_query.answer()
        except Exception:
            pass
    except Exception as e:
        logger.exception(f"random_callback failed: {e}")
        try:
            await callback_query.answer(f"❌ Error: {e}", show_alert=True)
        except Exception:
            pass

# Helper: fetch message id from DB _id or string
def _extract_message_id_from_db_id(db_id):
    """
    Accept db_id which might be:
     - int (message id)
     - string like "<channel>_<msgid>" or "ObjectId(...)" or str(ObjectId)
    Returns integer message_id or None.
    """
    try:
        if isinstance(db_id, int):
            return db_id
        s = str(db_id)
        if "_" in s:
            last = s.split("_")[-1]
            return int(last)
        # try direct int conversion if possible
        return int(s)
    except Exception:
        return None

async def show_popular_files(client: Client, callback_query: CallbackQuery):
    try:
        clone_id = await _determine_clone_id_from_client(client)
        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID.")
            return

        try:
            files = await get_popular_files(limit=10, clone_id=clone_id)
        except TypeError:
            files = await get_popular_files(10)

        if not files:
            await callback_query.message.edit_text("📊 No popular files found.")
            return

        text = "🔥 **Popular Files**

"
        buttons = []

        for f in files:
            file_name = f.get("file_name") or f.get("filename") or "Unknown"
            file_type = f.get("file_type", "unknown").upper()
            access_count = f.get("access_count", 0)
            display = file_name if len(file_name) <= 35 else (file_name[:35] + "...")
            file_link = encode(f.get("_id"))
            # open link to bot start to allow direct download
            bot_username = getattr(client, "username", None) or ""
            url = f"https://t.me/{bot_username}?start={file_link}" if bot_username else None
            if url:
                buttons.append([InlineKeyboardButton(f"{file_type} • {display} ({access_count} views)", url=url)])
            else:
                buttons.append([InlineKeyboardButton(f"{file_type} • {display} ({access_count} views)", callback_data=f"file_{str(f.get('_id'))}")])

        buttons.append([InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
                        InlineKeyboardButton("🆕 Recent", callback_data="rand_recent")])
        buttons.append([InlineKeyboardButton("📊 Stats", callback_data="rand_stats")])

        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.exception(f"show_popular_files error: {e}")
        try:
            await callback_query.message.edit_text(f"❌ Error: {e}")
        except Exception:
            pass

async def show_recent_files(client: Client, callback_query: CallbackQuery):
    try:
        clone_id = await _determine_clone_id_from_client(client)
        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID.")
            return

        try:
            files = await get_recent_files(limit=10, clone_id=clone_id)
        except TypeError:
            files = await get_recent_files(10)

        if not files:
            await callback_query.message.edit_text("📊 No recent files found.")
            return

        text = "🆕 **Recent Files**

"
        buttons = []
        for f in files:
            file_name = f.get("file_name") or f.get("filename") or "Unknown"
            display = file_name if len(file_name) <= 40 else (file_name[:40] + "...")
            file_link = encode(f.get("_id"))
            bot_username = getattr(client, "username", None) or ""
            url = f"https://t.me/{bot_username}?start={file_link}" if bot_username else None
            if url:
                buttons.append([InlineKeyboardButton(f"{display}", url=url)])
            else:
                buttons.append([InlineKeyboardButton(f"{display}", callback_data=f"file_{str(f.get('_id'))}")])

        buttons.append([InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
                        InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")])
        buttons.append([InlineKeyboardButton("📊 Stats", callback_data="rand_stats")])

        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.exception(f"show_recent_files error: {e}")
        try:
            await callback_query.message.edit_text(f"❌ Error: {e}")
        except Exception:
            pass

async def show_index_stats(client: Client, callback_query: CallbackQuery):
    try:
        clone_id = await _determine_clone_id_from_client(client)
        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID.")
            return

        stats = await get_index_stats(clone_id=clone_id)
        text = "📊 **Database Statistics**

"
        text += f"**Total Files:** {stats.get('total_files', 0)}

"
        if stats.get("file_types"):
            text += "**File Types:**
"
            for k, v in stats["file_types"].items():
                text += f"• {k.title()}: {v}
"

        buttons = [
            [InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
             InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")],
            [InlineKeyboardButton("🆕 Recent", callback_data="rand_recent")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.exception(f"show_index_stats error: {e}")
        try:
            await callback_query.message.edit_text(f"❌ Error: {e}")
        except Exception:
            pass

# -----------------------
# Direct commands for popular/recent
# -----------------------
@Client.on_message(filters.command("popular") & filters.private)
async def popular_files_command(client: Client, message: Message):
    try:
        if await handle_force_sub(client, message):
            return
        if not await check_feature_enabled(client, "popular"):
            await message.reply_text("❌ Most popular files feature is currently disabled by the admin.")
            return
        user_id = message.from_user.id
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text("⚠️ Command limit reached.", reply_markup=buttons)
            return
        await handle_popular_files_direct(client, message, is_callback=False)
    except Exception as e:
        logger.exception(f"popular_files_command error: {e}")
        await message.reply_text(f"❌ Error: {e}")

async def handle_popular_files_direct(client: Client, message: Message, is_callback: bool = False):
    # This function uses similar structure to handle_recent_files_direct; simplified to call show_popular_files flow
    # For brevity we forward to show_popular_files by creating a mock CallbackQuery-like object
    class _MockCQ:
        def __init__(self, message):
            self.message = message
    await show_popular_files(client, _MockCQ(message))

@Client.on_message(filters.command("recent") & filters.private)
async def recent_files_command(client: Client, message: Message):
    try:
        if await handle_force_sub(client, message):
            return
        if not await check_feature_enabled(client, "recent"):
            await message.reply_text("❌ Recent files feature is currently disabled by the admin.")
            return
        user_id = message.from_user.id
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text("⚠️ Command limit reached.", reply_markup=buttons)
            return
        await handle_recent_files_direct(client, message, is_callback=False)
    except Exception as e:
        logger.exception(f"recent_files_command error: {e}")
        await message.reply_text(f"❌ Error: {e}")

async def handle_recent_files_direct(client: Client, message: Message, is_callback: bool = False):
    # For correctness, use the show_recent_files flow (mocking a callback_query)
    class _MockCQ:
        def __init__(self, message):
            self.message = message
    await show_recent_files(client, _MockCQ(message))

# -----------------------
# Search command (placeholder)
# -----------------------
@Client.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ **Usage:** `/search <query>`

Example: `/search funny videos`")
            return
        query = " ".join(message.command[1:])
        text = f"🔍 **Search Results for:** `{query}`

⚠️ Search functionality is currently under development."
        await message.reply_text(text)
        logger.info(f"Search query '{query}' from user {message.from_user.id}")
    except Exception as e:
        logger.exception(f"Error in search command: {e}")
        await message.reply_text("❌ Search error occurred. Please try again.")
