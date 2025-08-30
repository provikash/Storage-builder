
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.clone_db import get_clone_config, update_clone_token_verification, update_clone_shortener_settings, get_clone_by_bot_token
from info import Config
import logging

logger = logging.getLogger(__name__)

def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of current clone"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        
        # If this is mother bot, return False
        if bot_token == Config.BOT_TOKEN:
            return False
            
        # For clone bots, check admin status via config
        if hasattr(client, 'clone_admin_id'):
            return user_id == client.clone_admin_id
            
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_verification_mode(client: Client, message: Message):
    """Set token verification mode (command_limit or time_based)"""
    user_id = message.from_user.id
    
    # Check if user is clone admin
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
        return await message.reply_text(
            "❌ Invalid mode. Use `command_limit` or `time_based`\n\n"
            "• `command_limit` - Users get specific number of commands per token\n"
            "• `time_based` - Users get unlimited commands for specific time period"
        )

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, verification_mode=mode)
    
    mode_text = "Command Limit" if mode == "command_limit" else "Time-Based (24 hours)"
    await message.reply_text(f"✅ Token verification mode set to: **{mode_text}**")

@Client.on_message(filters.command("setcommandlimit") & filters.private)
async def set_command_limit(client: Client, message: Message):
    """Set command limit for command_limit mode"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/setcommandlimit <number>`\n\n"
            "Set how many commands users get per verification token.\n\n"
            "**Example:** `/setcommandlimit 5`"
        )

    try:
        limit = int(message.command[1])
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
    except ValueError as e:
        return await message.reply_text(f"❌ Invalid number. Please provide a number between 1 and 100.")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, command_limit=limit)
    
    await message.reply_text(f"✅ Command limit set to: **{limit} commands per token**")

@Client.on_message(filters.command("settimeduration") & filters.private)
async def set_time_duration(client: Client, message: Message):
    """Set time duration for time_based mode"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/settimeduration <hours>`\n\n"
            "Set how many hours the time-based token remains valid.\n\n"
            "**Example:** `/settimeduration 48` (2 days)"
        )

    try:
        hours = int(message.command[1])
        if hours < 1 or hours > 168:  # Max 7 days
            raise ValueError("Duration must be between 1 and 168 hours (7 days)")
    except ValueError:
        return await message.reply_text(f"❌ Invalid hours. Please provide a number between 1 and 168 (7 days).")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, time_duration=hours)
    
    await message.reply_text(f"✅ Time duration set to: **{hours} hours** ({hours//24} days, {hours%24} hours)")

@Client.on_message(filters.command("toggletoken") & filters.private)
async def toggle_token_system(client: Client, message: Message):
    """Toggle token verification system"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    current_enabled = config.get('token_settings', {}).get('enabled', True) if config else True
    new_state = not current_enabled

    await update_clone_token_verification(bot_id, enabled=new_state)
    
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Token verification system **{status}**")

@Client.on_message(filters.command("setshortenerurl") & filters.private)
async def set_shortener_url(client: Client, message: Message):
    """Set URL shortener API URL"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/setshortenerurl <api_url>`\n\n"
            "Set the URL shortener API endpoint.\n\n"
            "**Popular APIs:**\n"
            "• `https://teraboxlinks.com/`\n"
            "• `https://short.io/`\n"
            "• `https://tinyurl.com/`\n\n"
            "**Example:** `/setshortenerurl https://short.io/`"
        )

    api_url = message.command[1]
    
    # Basic URL validation
    if not api_url.startswith(('http://', 'https://')):
        return await message.reply_text("❌ URL must start with http:// or https://")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_shortener_settings(bot_id, api_url=api_url)
    
    await message.reply_text(f"✅ Shortener URL updated to: `{api_url}`")

@Client.on_message(filters.command("setshortenerkey") & filters.private)
async def set_shortener_key(client: Client, message: Message):
    """Set URL shortener API key"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/setshortenerkey <api_key>`\n\n"
            "Set the API key for your URL shortener service.\n\n"
            "**Example:** `/setshortenerkey your_api_key_here`\n\n"
            "⚠️ **Security Note:** Your API key will be stored securely."
        )

    api_key = message.command[1]
    
    if len(api_key) < 8:
        return await message.reply_text("❌ API key seems too short. Please provide a valid API key.")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_shortener_settings(bot_id, api_key=api_key)
    
    # Show masked key for security
    masked_key = '*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '*' * len(api_key)
    await message.reply_text(f"✅ Shortener API key updated: `{masked_key}`")

@Client.on_message(filters.command("toggleshortener") & filters.private)
async def toggle_shortener_system(client: Client, message: Message):
    """Toggle URL shortener system"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    current_enabled = config.get('shortener_settings', {}).get('enabled', True) if config else True
    new_state = not current_enabled

    await update_clone_shortener_settings(bot_id, enabled=new_state)
    
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ URL shortener system **{status}**")

@Client.on_message(filters.command("tokenconfig") & filters.private)
async def show_token_config(client: Client, message: Message):
    """Show current token configuration"""
    user_id = message.from_user.id
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can view settings.")

    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    
    if not config:
        return await message.reply_text("❌ Configuration not found.")

    token_settings = config.get('token_settings', {})
    shortener_settings = config.get('shortener_settings', {})
    
    verification_mode = token_settings.get('verification_mode', 'command_limit')
    command_limit = token_settings.get('command_limit', 3)
    time_duration = token_settings.get('time_duration', 24)
    token_enabled = token_settings.get('enabled', True)
    
    shortener_url = shortener_settings.get('api_url', 'https://teraboxlinks.com/')
    shortener_enabled = shortener_settings.get('enabled', True)
    
    text = f"⚙️ **Current Token Configuration**\n\n"
    text += f"**Token Verification:**\n"
    text += f"• Status: {'✅ Enabled' if token_enabled else '❌ Disabled'}\n"
    text += f"• Mode: {verification_mode.replace('_', ' ').title()}\n"
    
    if verification_mode == 'command_limit':
        text += f"• Commands per token: {command_limit}\n"
    elif verification_mode == 'time_based':
        text += f"• Token duration: {time_duration} hours ({time_duration//24} days)\n"
    
    text += f"\n**URL Shortener:**\n"
    text += f"• Status: {'✅ Enabled' if shortener_enabled else '❌ Disabled'}\n"
    text += f"• API URL: `{shortener_url}`\n\n"
    
    text += f"**Available Commands:**\n"
    text += f"• `/settokenmode command_limit|time_based`\n"
    text += f"• `/setcommandlimit <number>`\n"
    text += f"• `/settimeduration <hours>`\n"
    text += f"• `/toggletoken`\n"
    text += f"• `/setshortenerurl <url>`\n"
    text += f"• `/setshortenerkey <key>`\n"
    text += f"• `/toggleshortener`"

    await message.reply_text(text)
