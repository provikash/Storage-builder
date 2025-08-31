
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config
from bot.database.clone_db import get_clone_by_bot_token, update_clone_token_verification, update_clone_shortener_settings
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_mode_command(client: Client, message: Message):
    """Set token verification mode via command"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/settokenmode <mode>`\n\n"
            "**Available modes:**\n"
            "• `command_limit` - Limited commands per token\n"
            "• `time_based` - Time-based token validity\n"
            "• `disabled` - Disable token verification"
        )
    
    mode = message.command[1].lower()
    valid_modes = ['command_limit', 'time_based', 'disabled']
    
    if mode not in valid_modes:
        return await message.reply_text(f"❌ Invalid mode. Use: {', '.join(valid_modes)}")
    
    bot_id = str(clone_data.get('bot_id'))
    
    if mode == 'disabled':
        await update_clone_token_verification(bot_id, enabled=False)
        await message.reply_text("✅ Token verification disabled.")
    else:
        await update_clone_token_verification(bot_id, verification_mode=mode, enabled=True)
        await message.reply_text(f"✅ Token mode set to: {mode.replace('_', ' ').title()}")

@Client.on_message(filters.command("setcommandlimit") & filters.private)
async def set_command_limit_command(client: Client, message: Message):
    """Set command limit for token verification"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/setcommandlimit <number>`\n\nSet the number of commands per token (1-100).")
    
    try:
        limit = int(message.command[1])
        if not 1 <= limit <= 100:
            return await message.reply_text("❌ Command limit must be between 1-100.")
        
        bot_id = str(clone_data.get('bot_id'))
        await update_clone_token_verification(bot_id, command_limit=limit)
        await message.reply_text(f"✅ Command limit set to {limit}.")
        
    except ValueError:
        await message.reply_text("❌ Please provide a valid number.")

@Client.on_message(filters.command("settimeduration") & filters.private)
async def set_time_duration_command(client: Client, message: Message):
    """Set time duration for token verification"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/settimeduration <hours>`\n\nSet token validity duration in hours (1-168).")
    
    try:
        hours = int(message.command[1])
        if not 1 <= hours <= 168:
            return await message.reply_text("❌ Duration must be between 1-168 hours.")
        
        bot_id = str(clone_data.get('bot_id'))
        await update_clone_token_verification(bot_id, time_duration=hours)
        await message.reply_text(f"✅ Token duration set to {hours} hours.")
        
    except ValueError:
        await message.reply_text("❌ Please provide a valid number.")

@Client.on_message(filters.command("setshortenerurl") & filters.private)
async def set_shortener_url_command(client: Client, message: Message):
    """Set URL shortener API URL"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/setshortenerurl <api_url>`\n\nExample: `/setshortenerurl https://teraboxlinks.com/`")
    
    url = " ".join(message.command[1:])
    bot_id = str(clone_data.get('bot_id'))
    
    await update_clone_shortener_settings(bot_id, api_url=url)
    await message.reply_text(f"✅ Shortener URL updated to: {url}")

@Client.on_message(filters.command("setshortenerkey") & filters.private)
async def set_shortener_key_command(client: Client, message: Message):
    """Set URL shortener API key"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/setshortenerkey <api_key>`")
    
    key = " ".join(message.command[1:])
    bot_id = str(clone_data.get('bot_id'))
    
    await update_clone_shortener_settings(bot_id, api_key=key)
    await message.reply_text("✅ API key updated successfully.")

@Client.on_message(filters.command("toggleshortener") & filters.private)
async def toggle_shortener_command(client: Client, message: Message):
    """Toggle URL shortener on/off"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    from bot.database.clone_db import get_clone_config
    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    
    current_enabled = config.get('shortener_settings', {}).get('enabled', True) if config else True
    new_state = not current_enabled
    
    await update_clone_shortener_settings(bot_id, enabled=new_state)
    await message.reply_text(f"✅ URL Shortener {'enabled' if new_state else 'disabled'}.")

@Client.on_message(filters.command("toggletoken") & filters.private)
async def toggle_token_command(client: Client, message: Message):
    """Toggle token verification system on/off"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can use this command.")
    
    from bot.database.clone_db import get_clone_config
    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    
    current_enabled = config.get('token_settings', {}).get('enabled', True) if config else True
    new_state = not current_enabled
    
    await update_clone_token_verification(bot_id, enabled=new_state)
    await message.reply_text(f"✅ Token verification {'enabled' if new_state else 'disabled'}.")
