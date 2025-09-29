
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType
from info import Config
from bot.database.clone_db import get_clone_by_bot_token

logger = logging.getLogger(__name__)

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.forwarded & filters.media & filters.private)
async def handle_forwarded_media_indexing(client: Client, message: Message):
    """Auto-index forwarded media from clone admin ONLY"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return  # Not a clone bot
        
        # Get clone data to verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            return
        
        # STRICT ADMIN CHECK - Only clone admin can trigger auto-indexing
  # Exit early for non-admin users
        
        # Check if message is forwarded from a channel
        if not message.forward_from_chat:
            return
        
        forward_chat = message.forward_from_chat
        forward_msg_id = message.forward_from_message_id
        
        # Check if auto-indexing is enabled
        auto_index_enabled = clone_data.get('auto_index_forwarded', True)
        if not auto_index_enabled:
            return
        
        # Get the channel info
        channel_id = forward_chat.id
        channel_title = forward_chat.title or "Unknown Channel"
        
        # Try to get latest message ID from the channel
        try:
            latest_msg = None
            async for msg in client.iter_messages(channel_id, limit=1):
                latest_msg = msg
                break
            
            if not latest_msg:
                await message.reply_text("❌ **Error**: Cannot access channel messages.")
                return
                
            latest_msg_id = latest_msg.id
            
            # Ask admin if they want to index the entire channel
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Index Entire Channel", 
                                       callback_data=f"auto_index_channel:{channel_id}:{latest_msg_id}:{clone_id}")
                ],
                [
                    InlineKeyboardButton("📁 Index This File Only", 
                                       callback_data=f"index_single_file:{clone_id}")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="close")
                ]
            ])
            
            await message.reply_text(
                f"📋 **Auto-Index Detected**\n\n"
                f"**Channel:** {channel_title}\n"
                f"**Total Messages:** ~{latest_msg_id:,}\n"
                f"**Forwarded Message ID:** {forward_msg_id}\n\n"
                f"Would you like to index all media from this channel to your clone's database?",
                reply_markup=buttons
            )
            
        except Exception as e:
            logger.error(f"Error accessing channel {channel_id}: {e}")
            await message.reply_text(
                f"❌ **Channel Access Error**\n\n"
                f"Cannot access channel: {channel_title}\n"
                f"Make sure the bot is added as admin in the channel."
            )
        
    except Exception as e:
        logger.error(f"Error in forwarded media indexing: {e}")

@Client.on_callback_query(filters.regex("^auto_index_channel:"))
async def handle_auto_index_channel(client: Client, query):
    """Handle auto index channel callback"""
    try:
        data_parts = query.data.split(":")
        channel_id = int(data_parts[1])
        latest_msg_id = int(data_parts[2])
        clone_id = data_parts[3]
        
        await query.answer("Starting channel indexing...", show_alert=True)
        
        # Import the indexing function
        from bot.plugins.clone_index import index_clone_files, clone_index_temp
        
        # Initialize indexing state
        clone_index_temp[clone_id] = {
            "cancel": False,
            "current": 0
        }
        
        await query.edit_message_text(
            "🔄 **Starting Auto Channel Indexing**\n\n"
            "Indexing all media files to your clone's database...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")]
            ])
        )
        
        # Start indexing process
        await index_clone_files(client, query.message, channel_id, latest_msg_id, clone_id)
        
    except Exception as e:
        logger.error(f"Error in auto index channel: {e}")
        await query.answer("❌ Error starting indexing.", show_alert=True)

@Client.on_callback_query(filters.regex("^index_single_file:"))
async def handle_index_single_file(client: Client, query):
    """Handle single file indexing"""
    try:
        clone_id = query.data.split(":")[1]
        
        # Get the original message (should be replied to)
        if not query.message.reply_to_message:
            await query.answer("❌ Cannot find the forwarded file.", show_alert=True)
            return
        
        forwarded_msg = query.message.reply_to_message
        
        # Import the auto-index function
        from bot.plugins.clone_index import auto_index_forwarded_message
        
        success = await auto_index_forwarded_message(client, forwarded_msg, clone_id)
        
        if success:
            await query.edit_message_text(
                "✅ **File Indexed Successfully**\n\n"
                f"📁 **File**: `{forwarded_msg.document.file_name if forwarded_msg.document else 'Media file'}`\n"
                f"🔍 File is now searchable in your clone bot!"
            )
        else:
            await query.edit_message_text(
                "❌ **Indexing Failed**\n\n"
                "File could not be indexed. It may already exist or there was an error."
            )
        
    except Exception as e:
        logger.error(f"Error indexing single file: {e}")
        await query.answer("❌ Error indexing file.", show_alert=True)

@Client.on_message(filters.command(['channelindex']) & filters.private)
async def channel_index_command(client: Client, message: Message):
    """Command to index a channel by username or ID"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This command is only available in clone bots.")
            return
        
        # Get clone data to verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        # Check if user is admin of this clone
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can use this command.")
            return
        
        if len(message.command) < 2:
            await message.reply_text(
                "📚 **Channel Indexing**\n\n"
                "**Usage:** `/channelindex <channel_username_or_id>`\n\n"
                "**Examples:**\n"
                "• `/channelindex @mychannel`\n"
                "• `/channelindex -1001234567890`\n\n"
                "**Note:** Bot must be admin in the channel or channel must be public."
            )
            return
        
        channel_identifier = message.command[1]
        
        # Try to get channel info
        try:
            chat = await client.get_chat(channel_identifier)
            
            # Get latest message ID
            async for latest_msg in client.iter_messages(chat.id, limit=1):
                last_msg_id = latest_msg.id
                break
            else:
                await message.reply_text("❌ Channel appears to be empty.")
                return
            
            # Show confirmation
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Start Indexing", 
                                   callback_data=f"auto_index_channel:{chat.id}:{last_msg_id}:{clone_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="close")]
            ])
            
            await message.reply_text(
                f"📋 **Channel Indexing Request**\n\n"
                f"**Channel:** {chat.title}\n"
                f"**Username:** @{chat.username or 'None'}\n"
                f"**Total Messages:** ~{last_msg_id:,}\n"
                f"**Clone ID:** {clone_id}\n\n"
                f"Files will be indexed to your clone's database.\n"
                f"Proceed with indexing?",
                reply_markup=buttons
            )
                
        except Exception as e:
            if "CHAT_ADMIN_REQUIRED" in str(e):
                await message.reply_text(
                    "❌ **Access Denied**\n\n"
                    "Bot needs admin access to this channel.\n"
                    "Please add the bot as admin in the channel and try again."
                )
            elif "USERNAME_NOT_RESOLVED" in str(e):
                await message.reply_text(
                    "❌ **Channel Not Found**\n\n"
                    "Please check the channel username/ID and try again.\n"
                    "Make sure the channel exists and is accessible."
                )
            else:
                await message.reply_text(f"❌ **Error**: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in channel index command: {e}")
        await message.reply_text("❌ Error processing channel index request.")
