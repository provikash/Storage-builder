
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

# Mother Bot Commands
@Client.on_message(filters.command("createclone") & filters.private)
async def create_clone_command(client: Client, message: Message):
    """Create a new clone bot"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot admins can create clones.")
    
    if len(message.command) < 4:
        return await message.reply_text(
            "❌ **Invalid format!**\n\n"
            "Usage: `/createclone <bot_token> <admin_id> <db_url> [tier]`"
        )
    
    bot_token = message.command[1]
    try:
        admin_id = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ Admin ID must be a valid number!")
    
    db_url = message.command[3]
    tier = message.command[4] if len(message.command) > 4 else "monthly"
    
    processing_msg = await message.reply_text("🔄 Creating clone bot... Please wait.")
    
    try:
        success, result = await clone_manager.create_clone(bot_token, admin_id, db_url, tier)
        
        if success:
            await processing_msg.edit_text(
                f"🎉 **Clone Created Successfully!**\n\n"
                f"🤖 **Bot Username:** @{result['username']}\n"
                f"🆔 **Bot ID:** {result['bot_id']}\n"
                f"👤 **Admin ID:** {result['admin_id']}\n"
                f"💰 **Tier:** {tier}\n"
                f"📊 **Status:** Pending Payment"
            )
        else:
            await processing_msg.edit_text(f"❌ **Failed to create clone:**\n{result}")
            
    except Exception as e:
        await processing_msg.edit_text(f"❌ **Error creating clone:**\n{str(e)}")

@Client.on_message(filters.command("setglobalchannels") & filters.private)
async def set_global_channels(client: Client, message: Message):
    """Set global force channels"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setglobalchannels channel1 channel2 ...`\n\n"
            "Example: `/setglobalchannels @channel1 @channel2 -1001234567890`"
        )
    
    channels = message.command[1:]
    await set_global_force_channels(channels)
    
    await message.reply_text(
        f"✅ **Global force channels updated!**\n\n"
        f"**Channels set:**\n" + 
        "\n".join(f"• {channel}" for channel in channels)
    )

@Client.on_message(filters.command("setglobalabout") & filters.private)
async def set_global_about(client: Client, message: Message):
    """Set global about page"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: /setglobalabout <about_text>")
    
    about_text = " ".join(message.command[1:])
    from bot.database.clone_db import set_global_setting
    await set_global_setting("global_about", about_text)
    
    await message.reply_text(f"✅ **Global about page updated!**\n\nPreview:\n{about_text[:200]}{'...' if len(about_text) > 200 else ''}")

@Client.on_message(filters.command("disableclone") & filters.private)
async def disable_clone_command(client: Client, message: Message):
    """Disable a clone bot"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: /disableclone <bot_id>")
    
    bot_id = message.command[1]
    
    try:
        await deactivate_clone(bot_id)
        await clone_manager.stop_clone(bot_id)
        await message.reply_text(f"✅ Clone {bot_id} has been disabled and stopped.")
    except Exception as e:
        await message.reply_text(f"❌ Error disabling clone: {str(e)}")

# Clone Bot Commands
@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel(client: Client, message: Message):
    """Add local force channel"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addforce <channel_id_or_username>`")
    
    channel = message.command[1]
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    
    channels = current_config.get('channels', {})
    local_force = channels.get('force_channels', [])
    
    if channel not in local_force:
        local_force.append(channel)
        channels['force_channels'] = local_force
        
        await update_clone_config(bot_id, {'channels': channels})
        clone_config_loader.clear_cache(bot_token)
        
        await message.reply_text(f"✅ Added force channel: {channel}")
    else:
        await message.reply_text("❌ Channel already in force list.")

@Client.on_message(filters.command("removeforce") & filters.private)
async def remove_force_channel(client: Client, message: Message):
    """Remove local force channel"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/removeforce <channel_id_or_username>`")
    
    channel = message.command[1]
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    
    channels = current_config.get('channels', {})
    local_force = channels.get('force_channels', [])
    
    if channel in local_force:
        local_force.remove(channel)
        channels['force_channels'] = local_force
        
        await update_clone_config(bot_id, {'channels': channels})
        clone_config_loader.clear_cache(bot_token)
        
        await message.reply_text(f"✅ Removed force channel: {channel}")
    else:
        await message.reply_text("❌ Channel not found in force list.")

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_mode(client: Client, message: Message):
    """Set token verification mode"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/settokenmode <mode>`\n\n"
            "Available modes:\n"
            "• `one_time` - Single use tokens\n"
            "• `command_limit` - Limited uses per token"
        )
    
    mode = message.command[1].lower()
    if mode not in ['one_time', 'command_limit']:
        return await message.reply_text("❌ Invalid mode. Use 'one_time' or 'command_limit'")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['mode'] = mode
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    await message.reply_text(f"✅ Token mode set to: {mode.replace('_', ' ').title()}")

@Client.on_message(filters.command("setcommandlimit") & filters.private)
async def set_command_limit(client: Client, message: Message):
    """Set command limit for tokens"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/setcommandlimit <number>`")
    
    try:
        limit = int(message.command[1])
        if limit < 1:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Please provide a valid positive number.")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['command_limit'] = limit
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    await message.reply_text(f"✅ Command limit set to: {limit}")

@Client.on_message(filters.command("settokenprice") & filters.private)
async def set_token_price(client: Client, message: Message):
    """Set token price"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/settokenprice <price>`")
    
    try:
        price = float(message.command[1])
        if price < 0.10 or price > 10.00:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Price must be between $0.10 and $10.00")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['pricing'] = price
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    await message.reply_text(f"✅ Token price set to: ${price}")

@Client.on_message(filters.command("toggletoken") & filters.private)
async def toggle_token_system(client: Client, message: Message):
    """Toggle token system on/off"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    
    current_status = token_settings.get('enabled', True)
    new_status = not current_status
    token_settings['enabled'] = new_status
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    status_text = "enabled" if new_status else "disabled"
    await message.reply_text(f"✅ Token system {status_text}!")
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from clone_manager import clone_manager

@Client.on_message(filters.command("approveclone") & filters.private)
async def approve_clone_command(client: Client, message: Message):
    """Approve a clone request"""
    user_id = message.from_user.id
    
    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can approve clones.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/approveclone <request_id>`")
    
    request_id = message.command[1]
    
    try:
        from bot.plugins.clone_request import get_pending_request, approve_request
        request = await get_pending_request(request_id)
        
        if not request:
            return await message.reply_text("❌ Request not found or already processed.")
        
        # Approve the request
        success, result = await approve_request(request_id)
        
        if success:
            await message.reply_text(
                f"✅ **Clone Approved Successfully!**\n\n"
                f"🤖 **Bot:** @{result['username']}\n"
                f"👤 **Admin:** {result['admin_id']}\n"
                f"💰 **Plan:** {result['tier']}\n"
                f"📅 **Expires:** {result['expiry'].strftime('%Y-%m-%d')}\n\n"
                f"The user has been notified."
            )
        else:
            await message.reply_text(f"❌ Failed to approve clone: {result}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error approving clone: {str(e)}")

@Client.on_message(filters.command("rejectclone") & filters.private)
async def reject_clone_command(client: Client, message: Message):
    """Reject a clone request"""
    user_id = message.from_user.id
    
    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can reject clones.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/rejectclone <request_id> [reason]`")
    
    request_id = message.command[1]
    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
    
    try:
        from bot.plugins.clone_request import get_pending_request, reject_request
        request = await get_pending_request(request_id)
        
        if not request:
            return await message.reply_text("❌ Request not found or already processed.")
        
        # Reject the request
        success, result = await reject_request(request_id, reason)
        
        if success:
            await message.reply_text(
                f"❌ **Clone Rejected**\n\n"
                f"🆔 **Request ID:** {request_id[:8]}...\n"
                f"👤 **User:** {request['user_id']}\n"
                f"📝 **Reason:** {reason}\n\n"
                f"The user has been notified."
            )
        else:
            await message.reply_text(f"❌ Failed to reject clone: {result}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error rejecting clone: {str(e)}")

@Client.on_message(filters.command("deleteclone") & filters.private)
async def delete_clone_command(client: Client, message: Message):
    """Delete a clone permanently"""
    user_id = message.from_user.id
    
    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can delete clones.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/deleteclone <bot_id>`")
    
    bot_id = message.command[1]
    
    try:
        # Get clone info before deletion
        clone = await get_clone(bot_id)
        if not clone:
            return await message.reply_text("❌ Clone not found.")
        
        # Stop the clone if running
        if bot_id in clone_manager.instances:
            await clone_manager.stop_clone(bot_id)
        
        # Delete from database
        await delete_clone(bot_id)
        await delete_subscription(bot_id)
        await delete_clone_config(bot_id)
        
        await message.reply_text(
            f"🗑️ **Clone Deleted Successfully**\n\n"
            f"🤖 **Bot:** @{clone.get('username', 'Unknown')}\n"
            f"🆔 **ID:** {bot_id}\n\n"
            f"⚠️ **This action is permanent and cannot be undone.**"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error deleting clone: {str(e)}")

@Client.on_message(filters.command("enableclone") & filters.private)
async def enable_clone_command(client: Client, message: Message):
    """Enable a disabled clone"""
    user_id = message.from_user.id
    
    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can enable clones.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/enableclone <bot_id>`")
    
    bot_id = message.command[1]
    
    try:
        # Update status to active
        await update_clone_status(bot_id, 'active')
        
        # Start the clone
        success, result = await clone_manager.start_clone(bot_id)
        
        if success:
            await message.reply_text(
                f"✅ **Clone Enabled & Started**\n\n"
                f"🆔 **Bot ID:** {bot_id}\n"
                f"📊 **Status:** Active & Running"
            )
        else:
            await message.reply_text(f"⚠️ Clone enabled but failed to start: {result}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error enabling clone: {str(e)}")

@Client.on_message(filters.command("disableclone") & filters.private)
async def disable_clone_command(client: Client, message: Message):
    """Disable a clone"""
    user_id = message.from_user.id
    
    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can disable clones.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/disableclone <bot_id>`")
    
    bot_id = message.command[1]
    
    try:
        # Stop the clone if running
        if bot_id in clone_manager.instances:
            await clone_manager.stop_clone(bot_id)
        
        # Update status to inactive
        await update_clone_status(bot_id, 'inactive')
        
        await message.reply_text(
            f"🛑 **Clone Disabled**\n\n"
            f"🆔 **Bot ID:** {bot_id}\n"
            f"📊 **Status:** Inactive & Stopped"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error disabling clone: {str(e)}")
