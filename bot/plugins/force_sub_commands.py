"""
Force Subscription Management Commands for Mother Bot
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.clone_db import get_global_force_channels, set_global_force_channels, get_global_about, set_global_about
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("addglobalchannel") & filters.private)
async def add_global_channel(client: Client, message: Message):
    """Add a global force subscription channel"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can manage global force channels.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "📢 **Add Global Force Channel**\n\n"
            "**Usage:** `/addglobalchannel <channel_id>`\n"
            "**Example:** `/addglobalchannel -1001234567890`\n\n"
            "**Tips:**\n"
            "• Make sure the bot is admin in the channel\n"
            "• Channel ID should start with -100\n"
            "• You can get channel ID from channel info"
        )
    
    try:
        channel_id = int(message.command[1])
        
        # Verify the channel exists and bot has access
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title
        except Exception as e:
            return await message.reply_text(
                f"❌ **Channel Error!**\n\n"
                f"Cannot access channel `{channel_id}`.\n"
                f"Make sure:\n"
                f"• Channel ID is correct\n"
                f"• Bot is added to the channel\n"
                f"• Bot has admin permissions\n\n"
                f"Error: {str(e)}"
            )
        
        # Get current channels
        current_channels = await get_global_force_channels()
        
        if channel_id in current_channels:
            return await message.reply_text(
                f"⚠️ **Already Added!**\n\n"
                f"Channel **{channel_title}** (`{channel_id}`) is already in the global force channels list."
            )
        
        # Add the new channel
        current_channels.append(channel_id)
        await set_global_force_channels(current_channels)
        
        await message.reply_text(
            f"✅ **Channel Added Successfully!**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**ID:** `{channel_id}`\n\n"
            f"Users will now need to join this channel to access bot content."
        )
        
        logger.info(f"Admin {message.from_user.id} added global force channel: {channel_id}")
        
    except ValueError:
        await message.reply_text(
            "❌ **Invalid Channel ID!**\n\n"
            "Channel ID must be a number.\n"
            "**Example:** `/addglobalchannel -1001234567890`"
        )
    except Exception as e:
        logger.error(f"Error adding global channel: {e}")
        await message.reply_text(f"❌ **Error!** Failed to add channel: {str(e)}")

@Client.on_message(filters.command("removeglobalchannel") & filters.private)
async def remove_global_channel(client: Client, message: Message):
    """Remove a global force subscription channel"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can manage global force channels.")
    
    if len(message.command) < 2:
        current_channels = await get_global_force_channels()
        if not current_channels:
            return await message.reply_text("📢 **No Global Force Channels**\n\nThere are no global force channels to remove.")
        
        channels_text = "📢 **Remove Global Force Channel**\n\n**Current Channels:**\n"
        for i, channel_id in enumerate(current_channels, 1):
            try:
                chat = await client.get_chat(channel_id)
                title = chat.title or f"Channel {channel_id}"
                channels_text += f"{i}. **{title}** (`{channel_id}`)\n"
            except:
                channels_text += f"{i}. `{channel_id}` (Inaccessible)\n"
        
        channels_text += f"\n**Usage:** `/removeglobalchannel <channel_id>`\n"
        channels_text += f"**Example:** `/removeglobalchannel -1001234567890`"
        
        return await message.reply_text(channels_text)
    
    try:
        channel_id = int(message.command[1])
        
        # Get current channels
        current_channels = await get_global_force_channels()
        
        if channel_id not in current_channels:
            return await message.reply_text(
                f"⚠️ **Channel Not Found!**\n\n"
                f"Channel `{channel_id}` is not in the global force channels list."
            )
        
        # Get channel title before removing
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title
        except:
            channel_title = f"Channel {channel_id}"
        
        # Remove the channel
        current_channels.remove(channel_id)
        await set_global_force_channels(current_channels)
        
        await message.reply_text(
            f"✅ **Channel Removed Successfully!**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**ID:** `{channel_id}`\n\n"
            f"Users no longer need to join this channel to access bot content."
        )
        
        logger.info(f"Admin {message.from_user.id} removed global force channel: {channel_id}")
        
    except ValueError:
        await message.reply_text(
            "❌ **Invalid Channel ID!**\n\n"
            "Channel ID must be a number.\n"
            "**Example:** `/removeglobalchannel -1001234567890`"
        )
    except Exception as e:
        logger.error(f"Error removing global channel: {e}")
        await message.reply_text(f"❌ **Error!** Failed to remove channel: {str(e)}")

@Client.on_message(filters.command("clearglobalchannels") & filters.private)
async def clear_global_channels(client: Client, message: Message):
    """Clear all global force subscription channels"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can manage global force channels.")
    
    current_channels = await get_global_force_channels()
    
    if not current_channels:
        return await message.reply_text("📢 **No Channels to Clear**\n\nThere are no global force channels configured.")
    
    # Clear all channels
    await set_global_force_channels([])
    
    await message.reply_text(
        f"✅ **All Global Force Channels Cleared!**\n\n"
        f"Removed {len(current_channels)} channel(s) from the global force subscription list.\n"
        f"Users can now access bot content without joining any channels."
    )
    
    logger.info(f"Admin {message.from_user.id} cleared all global force channels")

@Client.on_message(filters.command("setglobalabout") & filters.private)
async def set_global_about_command(client: Client, message: Message):
    """Set global about message"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can set global about message.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "📄 **Set Global About Message**\n\n"
            "**Usage:** `/setglobalabout <message>`\n"
            "**Example:** `/setglobalabout Welcome to our file sharing bot!`\n\n"
            "**Tips:**\n"
            "• Supports Markdown formatting\n"
            "• Keep under 4000 characters\n"
            "• Will be shown in all clone bots"
        )
    
    # Get the message content (everything after the command)
    about_message = message.text.split(' ', 1)[1]
    
    if len(about_message) > 4000:
        return await message.reply_text(
            "❌ **Message Too Long!**\n\n"
            f"Your message is {len(about_message)} characters long.\n"
            f"Maximum allowed: 4000 characters.\n"
            f"Please shorten your message."
        )
    
    try:
        # Set the global about message
        from bot.database.clone_db import set_global_about
        await set_global_about(about_message)
        
        await message.reply_text(
            "✅ **Global About Message Set!**\n\n"
            f"**Preview:**\n{about_message[:200]}{'...' if len(about_message) > 200 else ''}\n\n"
            f"This message will now be shown in all clone bots."
        )
        
        logger.info(f"Admin {message.from_user.id} set global about message")
        
    except Exception as e:
        logger.error(f"Error setting global about: {e}")
        await message.reply_text(f"❌ **Error!** Failed to set about message: {str(e)}")

@Client.on_message(filters.command("clearglobalabout") & filters.private)
async def clear_global_about_command(client: Client, message: Message):
    """Clear global about message"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can clear global about message.")
    
    current_about = await get_global_about()
    
    if not current_about:
        return await message.reply_text("📄 **No About Message**\n\nThere is no global about message to clear.")
    
    try:
        # Clear the global about message
        from bot.database.clone_db import set_global_about
        await set_global_about("")
        
        await message.reply_text(
            "✅ **Global About Message Cleared!**\n\n"
            "The global about message has been removed from all clone bots."
        )
        
        logger.info(f"Admin {message.from_user.id} cleared global about message")
        
    except Exception as e:
        logger.error(f"Error clearing global about: {e}")
        await message.reply_text(f"❌ **Error!** Failed to clear about message: {str(e)}")

@Client.on_message(filters.command("globalchannels") & filters.private)
async def list_global_channels(client: Client, message: Message):
    """List all global force channels"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ **Access Denied!** Only admins can view global force channels.")
    
    current_channels = await get_global_force_channels()
    
    if not current_channels:
        return await message.reply_text(
            "📢 **Global Force Channels**\n\n"
            "**No global force channels configured.**\n\n"
            "Use `/addglobalchannel <channel_id>` to add channels."
        )
    
    channels_text = f"📢 **Global Force Channels** ({len(current_channels)})\n\n"
    
    for i, channel_id in enumerate(current_channels, 1):
        try:
            chat = await client.get_chat(channel_id)
            title = chat.title or f"Channel {channel_id}"
            members = chat.members_count if hasattr(chat, 'members_count') else "Unknown"
            channels_text += f"{i}. **{title}**\n"
            channels_text += f"   • ID: `{channel_id}`\n"
            channels_text += f"   • Members: {members}\n\n"
        except Exception as e:
            channels_text += f"{i}. `{channel_id}` ❌\n"
            channels_text += f"   • Status: Inaccessible\n"
            channels_text += f"   • Error: {str(e)[:50]}...\n\n"
    
    channels_text += f"**💡 Management Commands:**\n"
    channels_text += f"• `/addglobalchannel <id>` - Add channel\n"
    channels_text += f"• `/removeglobalchannel <id>` - Remove channel\n"
    channels_text += f"• `/clearglobalchannels` - Clear all"
    
    await message.reply_text(channels_text)