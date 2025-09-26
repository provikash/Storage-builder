
<file_path>bot/plugins/clone_auto_index.py</file_path>
<change_summary>Auto-index forwarded media messages</change_summary>

```python
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

@Client.on_message(filters.media & filters.forwarded & filters.private)
async def auto_index_forwarded_media(client: Client, message: Message):
    """Automatically index forwarded media messages in clone bots"""
    try:
        # Check if this is a clone bot
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return  # Not a clone bot
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            return
        
        # Check if user is admin of this clone
        if message.from_user.id != clone_data['admin_id']:
            return  # Only admin forwards are auto-indexed
        
        # Check if auto-indexing is enabled (you can add this setting later)
        auto_index_enabled = clone_data.get('auto_index_forwarded', True)
        if not auto_index_enabled:
            return
        
        # Import the auto-index function
        from bot.plugins.clone_index import auto_index_forwarded_message
        
        # Try to auto-index the message
        success = await auto_index_forwarded_message(client, message, clone_id)
        
        if success:
            # Send a subtle confirmation
            try:
                await message.reply_text(
                    "✅ **Auto-indexed**\n\n"
                    f"📁 **File**: `{message.document.file_name if message.document else message.photo or message.video or message.audio}`\n"
                    f"💾 **Size**: `{message.document.file_size if message.document else 'N/A'}`\n"
                    f"🔍 File is now searchable in your clone bot!",
                    quote=True
                )
            except:
                pass  # If reply fails, it's okay
        
    except Exception as e:
        logger.error(f"Error in auto-index forwarded media: {e}")

@Client.on_message(filters.command(['autoindex']) & filters.private)
async def toggle_auto_index_command(client: Client, message: Message):
    """Toggle auto-indexing for forwarded messages"""
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
        
        # Toggle auto-index setting
        current_setting = clone_data.get('auto_index_forwarded', True)
        new_setting = not current_setting
        
        # Update in database
        from bot.database.clone_db import clones_collection
        await clones_collection.update_one(
            {"bot_id": clone_data['bot_id']},
            {"$set": {"auto_index_forwarded": new_setting}}
        )
        
        status = "enabled" if new_setting else "disabled"
        emoji = "✅" if new_setting else "❌"
        
        await message.reply_text(
            f"{emoji} **Auto-indexing {status.title()}**\n\n"
            f"📝 **Status**: Auto-indexing is now **{status}**\n\n"
            f"💡 **How it works**: When you forward media files to this bot, "
            f"they will {'automatically be indexed' if new_setting else 'not be auto-indexed'} "
            f"to your clone's database.\n\n"
            f"🔧 Use `/autoindex` again to toggle this setting."
        )
        
    except Exception as e:
        logger.error(f"Error in toggle auto-index command: {e}")
        await message.reply_text("❌ Error toggling auto-index setting.")

@Client.on_message(filters.command(['batchindex']) & filters.private)
async def batch_index_command(client: Client, message: Message):
    """Start batch indexing from a channel"""
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
                "📚 **Batch Indexing**\n\n"
                "**Usage:** `/batchindex <channel_username_or_id>`\n\n"
                "**Examples:**\n"
                "• `/batchindex @mychannel`\n"
                "• `/batchindex -1001234567890`\n\n"
                "**Note:** Bot must be admin in the channel or channel must be public.\n"
                "This will index all media files from the channel to your clone's database."
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
                
            # Import and use the indexing function
            from bot.plugins.clone_index import process_clone_index_request
            
            # Create a fake link format for the existing function
            fake_link = f"https://t.me/c/{str(chat.id).replace('-100', '')}/{last_msg_id}"
            
            await process_clone_index_request(client, message, fake_link, clone_id)
            
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
        logger.error(f"Error in batch index command: {e}")
        await message.reply_text("❌ Error processing batch index request.")
```
