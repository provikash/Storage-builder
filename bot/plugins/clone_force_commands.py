
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config
from bot.database.clone_db import get_clone_by_bot_token, update_clone_setting
from bot.logging import LOGGER

logger = LOGGER(__name__)

def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    if not hasattr(client, 'clone_config') or not client.clone_config:
        return False
    return user_id == client.clone_config.get('admin_id')

@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel_clone(client: Client, message: Message):
    """Add force subscription channel for clone bot"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    if not hasattr(client, 'is_clone') or not client.is_clone:
        await message.reply_text("❌ This command is only available in clone bots.")
        return

    if not is_clone_admin(client, user_id):
        await message.reply_text("❌ Only the clone admin can manage force channels.")
        return

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/addforce <channel_id_or_username>`\nExample: `/addforce -1001234567890` or `/addforce @mychannel`")

    try:
        channel_input = message.command[1]
        
        # Handle username input
        if channel_input.startswith('@'):
            channel_input = channel_input[1:]  # Remove @ symbol
        
        # Test if bot can access the channel
        try:
            chat = await client.get_chat(channel_input)
            channel_id = chat.id
            channel_title = chat.title or f"Channel {channel_id}"
        except Exception as e:
            return await message.reply_text(f"❌ Cannot access channel {channel_input}. Make sure the bot is added to the channel and the channel ID/username is correct.\nError: {str(e)}")

        # Get current clone data
        clone_data = await get_clone_by_bot_token(client.bot_token)
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found.")

        # Get current force channels
        current_channels = clone_data.get('force_channels', [])
        
        if channel_id in current_channels:
            return await message.reply_text(f"❌ Channel **{channel_title}** is already in the force subscription list.")

        # Add new channel
        current_channels.append(channel_id)
        
        # Update in database
        bot_id = clone_data.get('bot_id') or clone_data.get('_id')
        await update_clone_setting(bot_id, 'force_channels', current_channels)

        await message.reply_text(f"✅ Added force subscription channel: **{channel_title}** (`{channel_id}`)")

    except Exception as e:
        await message.reply_text(f"❌ Error adding channel: {str(e)}")
        logger.error(f"Error in addforce command: {e}")

@Client.on_message(filters.command("removeforce") & filters.private)
async def remove_force_channel_clone(client: Client, message: Message):
    """Remove force subscription channel for clone bot"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    if not hasattr(client, 'is_clone') or not client.is_clone:
        await message.reply_text("❌ This command is only available in clone bots.")
        return

    if not is_clone_admin(client, user_id):
        await message.reply_text("❌ Only the clone admin can manage force channels.")
        return

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/removeforce <channel_id>`")

    try:
        channel_id = int(message.command[1])

        # Get current clone data
        clone_data = await get_clone_by_bot_token(client.bot_token)
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found.")

        # Get current force channels
        current_channels = clone_data.get('force_channels', [])
        
        if channel_id not in current_channels:
            return await message.reply_text(f"❌ Channel {channel_id} is not in force subscription list.")

        # Remove channel
        current_channels.remove(channel_id)
        
        # Update in database
        bot_id = clone_data.get('bot_id') or clone_data.get('_id')
        await update_clone_setting(bot_id, 'force_channels', current_channels)

        await message.reply_text(f"✅ Removed force subscription channel: `{channel_id}`")

    except ValueError:
        await message.reply_text("❌ Invalid channel ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error removing channel: {str(e)}")
        logger.error(f"Error in removeforce command: {e}")

@Client.on_message(filters.command("listforce") & filters.private)
async def list_force_channels_clone(client: Client, message: Message):
    """List all force subscription channels for clone bot"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    if not hasattr(client, 'is_clone') or not client.is_clone:
        await message.reply_text("❌ This command is only available in clone bots.")
        return

    if not is_clone_admin(client, user_id):
        await message.reply_text("❌ Only the clone admin can view force channels.")
        return

    try:
        # Get current clone data
        clone_data = await get_clone_by_bot_token(client.bot_token)
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found.")

        force_channels = clone_data.get('force_channels', [])
        
        if not force_channels:
            return await message.reply_text("📋 No force subscription channels configured.")

        text = "📢 **Force Subscription Channels:**\n\n"
        valid_channels = []
        
        for i, channel_id in enumerate(force_channels, 1):
            try:
                chat = await client.get_chat(channel_id)
                title = chat.title or f"Channel {channel_id}"
                text += f"{i}. **{title}**\n   ID: `{channel_id}`\n\n"
                valid_channels.append(channel_id)
            except Exception as e:
                text += f"{i}. **Invalid Channel**\n   ID: `{channel_id}` ❌\n   Error: {str(e)[:50]}...\n\n"

        # Update with only valid channels if needed
        if len(valid_channels) != len(force_channels):
            bot_id = clone_data.get('bot_id') or clone_data.get('_id')
            await update_clone_setting(bot_id, 'force_channels', valid_channels)
            text += f"\n🔧 **Auto-cleaned invalid channels. Valid channels: {len(valid_channels)}**"

        await message.reply_text(text)

    except Exception as e:
        await message.reply_text(f"❌ Error listing channels: {str(e)}")
        logger.error(f"Error in listforce command: {e}")
