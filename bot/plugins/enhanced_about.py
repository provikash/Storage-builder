
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.clone_db import get_global_about, get_global_force_channels
from bot.utils.clone_config_loader import clone_config_loader

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """Enhanced about page with clone system info"""
    
    # Get global about content
    global_about = await get_global_about()
    global_force_channels = await get_global_force_channels()
    
    # Check if this is a clone or mother bot
    bot_token = getattr(client, 'bot_token', None)
    bot_id = bot_token.split(':')[0] if bot_token else str(client.me.id)
    
    # Build about message
    about_text = "ℹ️ **About This Bot**\n\n"
    
    if global_about:
        about_text += f"{global_about}\n\n"
    else:
        about_text += (
            "🤖 This is an advanced file sharing bot with clone system support!\n\n"
            "**Features:**\n"
            "✅ Fast file sharing\n"
            "✅ Batch link generation\n"
            "✅ Advanced search\n"
            "✅ Token verification\n"
            "✅ Premium features\n\n"
        )
    
    about_text += "🌟 **Made by Mother Bot System**\n\n"
    
    # Show global force channels
    if global_force_channels:
        about_text += "📢 **Global Force Channels:**\n"
        for i, channel_id in enumerate(global_force_channels, 1):
            about_text += f"{i}. Channel ID: {channel_id}\n"
        about_text += "\n"
    
    # Get clone admin contact (if this is a clone)
    config = await clone_config_loader.get_bot_config(bot_token or "")
    clone_admin_id = None
    
    if bot_token:  # This is a clone
        from bot.database.clone_db import get_clone
        clone_data = await get_clone(bot_id)
        if clone_data:
            clone_admin_id = clone_data['admin_id']
    
    # Create buttons
    buttons = []
    
    # Create clone button (only for mother bot)
    if not bot_token or bot_id == str(Config.OWNER_ID):
        buttons.append([
            InlineKeyboardButton(
                "🤖 Create Your Clone", 
                url=f"https://t.me/{client.username}?start=create_clone"
            )
        ])
    
    # Clone admin contact
    if clone_admin_id:
        try:
            admin_user = await client.get_users(clone_admin_id)
            if admin_user.username:
                buttons.append([
                    InlineKeyboardButton(
                        "👤 Contact Clone Admin", 
                        url=f"https://t.me/{admin_user.username}"
                    )
                ])
        except:
            pass
    
    # Mother bot contact
    buttons.append([
        InlineKeyboardButton(
            "🏠 Mother Bot", 
            url=f"https://t.me/{Config.BOT_USERNAME}"
        )
    ])
    
    # Help button
    buttons.append([
        InlineKeyboardButton("❓ Help", callback_data="show_help")
    ])
    
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    await message.reply_text(
        about_text,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@Client.on_message(filters.command("setabout") & filters.private)
async def set_about_command(client: Client, message: Message):
    """Set global about page content (Mother Bot admin only)"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied. Only Mother Bot admins can set global about page.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setabout <content>`\n\n"
            "Example: `/setabout Welcome to our amazing bot network!`"
        )
    
    # Get content (everything after /setabout)
    content = message.text.split(' ', 1)[1]
    
    from bot.database.clone_db import set_global_about
    await set_global_about(content)
    
    await message.reply_text(
        f"✅ **Global About Page Updated!**\n\n"
        f"📝 **Content:** {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
        "This content will appear in all clone bots."
    )
