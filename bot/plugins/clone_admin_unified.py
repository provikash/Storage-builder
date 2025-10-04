
"""
Unified Clone Admin Module
Consolidates clone_admin.py, clone_admin_commands.py, and clone_admin_settings.py
"""
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import (
    get_clone_config, update_clone_config, get_clone_by_bot_token,
    update_clone_setting, get_clone_user_count, get_clone_file_count,
    update_clone_token_verification, update_clone_shortener_settings
)
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store clone admin sessions
clone_admin_sessions = {}

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

def create_settings_keyboard():
    """Create the clone admin settings keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎲 Random Toggle", callback_data="clone_toggle_random"),
            InlineKeyboardButton("📊 Recent Toggle", callback_data="clone_toggle_recent")
        ],
        [
            InlineKeyboardButton("🔥 Popular Toggle", callback_data="clone_toggle_popular"),
            InlineKeyboardButton("📢 Force Join", callback_data="clone_force_join")
        ],
        [
            InlineKeyboardButton("🔑 Token Mode", callback_data="clone_token_mode"),
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener")
        ],
        [
            InlineKeyboardButton("📈 Clone Stats", callback_data="clone_view_stats"),
            InlineKeyboardButton("ℹ️ About Settings", callback_data="clone_about_settings")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_command(client: Client, message: Message):
    """Clone admin panel command"""
    user_id = message.from_user.id
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ Clone admin panel is only available in clone bots!")

    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data:
        return await message.reply_text("❌ Clone configuration not found!")

    if clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can access this panel!")

    await clone_admin_panel(client, message)

async def clone_admin_panel(client: Client, message):
    """Display clone admin panel"""
    text = f"⚙️ **Clone Bot Admin Panel**\n\n"
    text += f"🤖 **Bot Management:**\n"
    text += f"Manage your clone bot's settings and features.\n\n"
    text += f"🔧 **Available Options:**\n"
    text += f"• Configure bot features\n"
    text += f"• Manage force channels\n" 
    text += f"• Token verification settings\n"
    text += f"• URL shortener configuration\n\n"
    text += f"📊 **Choose an option below:**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎛️ Bot Features", callback_data="clone_bot_features"),
            InlineKeyboardButton("🔐 Force Channels", callback_data="clone_local_force_channels")
        ],
        [
            InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_command_config"),
            InlineKeyboardButton("💰 Token Pricing", callback_data="clone_token_pricing")
        ],
        [
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener"),
            InlineKeyboardButton("📊 Subscription Status", callback_data="clone_subscription_status")
        ],
        [
            InlineKeyboardButton("🔄 Toggle Token System", callback_data="clone_toggle_token_system"),
            InlineKeyboardButton("📋 Request Channels", callback_data="clone_request_channels")
        ]
    ])

    if hasattr(message, 'edit_message_text'):
        await message.edit_message_text(text, reply_markup=buttons)
    else:
        await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("clonesettings") & filters.private)
async def clone_settings_command(client: Client, message):
    """Clone settings command"""
    user_id = message.from_user.id
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    
    if bot_token == Config.BOT_TOKEN:
        error_msg = "❌ Settings panel is only available in clone bots!"
        if hasattr(message, 'edit_message_text'):
            return await message.edit_message_text(error_msg)
        else:
            return await message.reply_text(error_msg)

    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data:
        return await message.reply_text("❌ Clone configuration not found!")

    if user_id != clone_data.get('admin_id'):
        return await message.reply_text("❌ Only clone admin can access settings!")

    await clone_admin_panel(client, message)

# Token commands
@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_verification_mode(client: Client, message: Message):
    """Set token verification mode"""
    user_id = message.from_user.id
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/settokenmode <mode>`\n\n"
            "**Available modes:**\n"
            "• `command_limit` - Token gives specific number of commands\n"
            "• `time_based` - Token valid for specific time period\n\n"
            "**Example:** `/settokenmode time_based`"
        )

    mode = message.command[1].lower()
    if mode not in ['command_limit', 'time_based']:
        return await message.reply_text("❌ Invalid mode. Use `command_limit` or `time_based`")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, verification_mode=mode)
    
    mode_text = "Command Limit" if mode == "command_limit" else "Time-Based (24 hours)"
    await message.reply_text(f"✅ Token verification mode set to: **{mode_text}**")

@Client.on_message(filters.command("togglerandom") & filters.private)
async def toggle_random_button(client: Client, message: Message):
    """Toggle random button"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('random_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {"features.random_button": new_state})
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Random button {status}!")

@Client.on_message(filters.command("togglerecent") & filters.private)
async def toggle_recent_button(client: Client, message: Message):
    """Toggle recent button"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('recent_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {"features.recent_button": new_state})
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Recent button {status}!")
