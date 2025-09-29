
import logging
import asyncio
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from info import Config
from bot.database.mongo_db import add_file_to_clone_index
from bot.database.clone_db import get_clone_by_bot_token
import re

logger = logging.getLogger(__name__)

# Temporary storage for clone indexing state
clone_index_temp = {}

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.command(['index', 'cloneindex', 'batchindex']) & filters.private)
async def clone_index_command(client: Client, message: Message):
    """Handle indexing command for clone bots - ADMIN ONLY"""
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
        
        # Strict admin check - only clone admin can use indexing commands
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text(
                "❌ **Access Denied**\n\n"
                "Only the clone administrator can use indexing commands.\n"
                "Contact your clone admin for file indexing requests."
            )
            return
        
        if len(message.command) < 2:
            await message.reply_text(
                "📚 **Clone Indexing Commands**\n\n"
                "**Basic Usage:**\n"
                "• `/index <channel_link>` - Index from channel link\n"
                "• `/index <start_id> <end_id>` - Index message range\n"
                "• `/index <channel_id> <start_id> <end_id>` - Index specific range\n\n"
                "**Examples:**\n"
                "• `/index https://t.me/channel/123`\n"
                "• `/index 100 500` - Messages 100-500 from forwarded channel\n"
                "• `/index -1001234567890 1 1000` - Channel with range\n\n"
                "**Advanced:**\n"
                "• `/batchindex` - Batch index multiple channels\n"
                "• `/skipdup` - Skip duplicate files during indexing\n\n"
                "**Note:** Files will be indexed to your clone's database."
            )
            return
        
        # Parse arguments
        args = message.command[1:]
        
        # Handle different argument patterns
        if len(args) == 1:
            # Single argument - could be channel link or channel ID
            arg = args[0]
            if arg.startswith('http'):
                await process_clone_index_link(client, message, arg, clone_id)
            else:
                await message.reply_text("❌ Invalid format. Use channel link or provide message range.")
        elif len(args) == 2:
            # Two arguments - start and end message IDs (need forwarded message context)
            try:
                start_id = int(args[0])
                end_id = int(args[1])
                await process_clone_index_range(client, message, None, start_id, end_id, clone_id)
            except ValueError:
                await message.reply_text("❌ Invalid message IDs. Use numbers only.")
        elif len(args) == 3:
            # Three arguments - channel_id, start_id, end_id
            try:
                channel_id = int(args[0]) if args[0].lstrip('-').isdigit() else args[0]
                start_id = int(args[1])
                end_id = int(args[2])
                await process_clone_index_range(client, message, channel_id, start_id, end_id, clone_id)
            except ValueError:
                await message.reply_text("❌ Invalid arguments. Check format and try again.")
        else:
            await message.reply_text("❌ Too many arguments. Check command format.")
        
    except Exception as e:
        logger.error(f"Error in clone index command: {e}")
        await message.reply_text("❌ Error processing index request.")

@Client.on_message(filters.command(['batchindex']) & filters.private)
async def batch_index_command(client: Client, message: Message):
    """Handle batch indexing for multiple channels - ADMIN ONLY"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This command is only available in clone bots.")
            return
        
        # Verify admin access
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can use batch indexing.")
            return
        
        # Store batch indexing session
        clone_index_temp[f"batch_{clone_id}"] = {
            "channels": [],
            "status": "collecting",
            "user_id": message.from_user.id
        }
        
        await message.reply_text(
            "📚 **Batch Indexing Mode**\n\n"
            "Send channel links or channel IDs one by one.\n"
            "When done, send `/startbatch` to begin indexing.\n"
            "Send `/cancelbatch` to cancel.\n\n"
            "**Supported formats:**\n"
            "• https://t.me/channel/123\n"
            "• @channelname\n"
            "• -1001234567890"
        )
        
    except Exception as e:
        logger.error(f"Error in batch index command: {e}")

@Client.on_message(filters.command(['startbatch']) & filters.private)
async def start_batch_indexing(client: Client, message: Message):
    """Start batch indexing process"""
    try:
        clone_id = get_clone_id_from_client(client)
        batch_key = f"batch_{clone_id}"
        
        if batch_key not in clone_index_temp:
            await message.reply_text("❌ No batch indexing session found. Use `/batchindex` first.")
            return
        
        batch_data = clone_index_temp[batch_key]
        if not batch_data["channels"]:
            await message.reply_text("❌ No channels added. Add channels first.")
            return
        
        # Verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can start batch indexing.")
            return
        
        channels = batch_data["channels"]
        total_channels = len(channels)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Batch Indexing", 
                               callback_data=f"start_batch_index:{clone_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        channel_list = "\n".join([f"• {ch}" for ch in channels[:10]])
        if len(channels) > 10:
            channel_list += f"\n... and {len(channels) - 10} more"
        
        await message.reply_text(
            f"📚 **Batch Indexing Ready**\n\n"
            f"**Channels to index:** {total_channels}\n\n"
            f"{channel_list}\n\n"
            f"**Clone:** {clone_id}\n"
            f"Ready to start batch indexing?",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error starting batch indexing: {e}")

@Client.on_message(filters.command(['skipdup']) & filters.private)
async def toggle_skip_duplicates(client: Client, message: Message):
    """Toggle skip duplicates setting for indexing"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        # Verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can change indexing settings.")
            return
        
        # Toggle setting in clone configuration
        current_setting = clone_data.get('skip_duplicates', True)
        new_setting = not current_setting
        
        from bot.database.clone_db import update_clone_config
        await update_clone_config(clone_id, {"skip_duplicates": new_setting})
        
        status = "enabled" if new_setting else "disabled"
        await message.reply_text(f"✅ Skip duplicates {status} for indexing.")
        
    except Exception as e:
        logger.error(f"Error toggling skip duplicates: {e}")

# Handle batch channel collection
@Client.on_message(filters.text & filters.private)
async def collect_batch_channels(client: Client, message: Message):
    """Collect channels for batch indexing"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        batch_key = f"batch_{clone_id}"
        if batch_key not in clone_index_temp:
            return
        
        batch_data = clone_index_temp[batch_key]
        if batch_data["status"] != "collecting" or batch_data["user_id"] != message.from_user.id:
            return
        
        text = message.text.strip()
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Validate channel format
        if any(fmt in text for fmt in ['t.me/', '@', '-100']):
            batch_data["channels"].append(text)
            await message.reply_text(
                f"✅ Added channel: `{text}`\n"
                f"Total channels: {len(batch_data['channels'])}\n\n"
                f"Send more channels or `/startbatch` to begin."
            )
        else:
            await message.reply_text("❌ Invalid channel format. Use channel link, @username, or channel ID.")
        
    except Exception as e:
        logger.error(f"Error collecting batch channels: {e}")

async def process_clone_index_link(client: Client, message: Message, link: str, clone_id: str):
    """Process indexing request for clone using channel link"""
    try:
        # Parse channel link
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(link)
        
        if not match:
            await message.reply_text("❌ Invalid channel link format.")
            return
        
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
        
        await process_clone_index_range(client, message, chat_id, 1, last_msg_id, clone_id)
        
    except Exception as e:
        logger.error(f"Error processing clone index link: {e}")
        await message.reply_text("❌ Error processing channel link.")

async def process_clone_index_range(client: Client, message: Message, channel_id, start_id: int, end_id: int, clone_id: str):
    """Process indexing for a specific message range"""
    try:
        # If no channel_id provided, try to get from forwarded message context
        if channel_id is None:
            if message.reply_to_message and message.reply_to_message.forward_from_chat:
                channel_id = message.reply_to_message.forward_from_chat.id
            else:
                await message.reply_text("❌ No channel specified. Reply to a forwarded message or provide channel ID.")
                return
        
        # Validate channel access
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title or str(channel_id)
        except ChannelInvalid:
            await message.reply_text("❌ Cannot access this channel. Make sure the bot is added as admin.")
            return
        except Exception as e:
            await message.reply_text(f"❌ Error accessing channel: {e}")
            return
        
        # Validate message range
        if start_id > end_id:
            await message.reply_text("❌ Start ID must be less than or equal to End ID.")
            return
        
        if end_id - start_id > 10000:
            await message.reply_text("❌ Range too large. Maximum 10,000 messages per batch.")
            return
        
        # Show confirmation
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Indexing", 
                               callback_data=f"clone_start_range_index:{channel_id}:{start_id}:{end_id}:{clone_id}")],
            [InlineKeyboardButton("⚙️ Advanced Options", 
                               callback_data=f"clone_index_options:{channel_id}:{start_id}:{end_id}:{clone_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        await message.reply_text(
            f"📚 **Clone Range Indexing**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**Range:** {start_id} to {end_id} ({end_id - start_id + 1:,} messages)\n"
            f"**Clone ID:** {clone_id}\n\n"
            f"Files will be indexed to your clone's database.\n"
            f"Proceed with indexing?",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error processing clone index range: {e}")
        await message.reply_text("❌ Error processing range request.")

@Client.on_callback_query(filters.regex("^clone_start_range_index:"))
async def handle_clone_start_range_index(client: Client, query):
    """Handle clone range indexing start"""
    try:
        await query.answer("Starting range indexing...", show_alert=True)
        
        data_parts = query.data.split(":")
        channel_id = int(data_parts[1])
        start_id = int(data_parts[2])
        end_id = int(data_parts[3])
        clone_id = data_parts[4]
        
        # Verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or query.from_user.id != clone_data['admin_id']:
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        # Initialize indexing state
        clone_index_temp[clone_id] = {
            "cancel": False,
            "current": start_id - 1,
            "total": end_id - start_id + 1,
            "start_id": start_id,
            "end_id": end_id,
            "channel_id": channel_id
        }
        
        await query.edit_message_text(
            "🔄 **Starting Clone Range Indexing**\n\n"
            f"Range: {start_id} to {end_id}\n"
            "Indexing files to your clone's database...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")],
                [InlineKeyboardButton("📊 Progress", callback_data=f"clone_show_progress:{clone_id}")]
            ])
        )
        
        # Start indexing process
        await index_clone_files_range(client, query.message, channel_id, start_id, end_id, clone_id)
        
    except Exception as e:
        logger.error(f"Error starting clone range indexing: {e}")
        await query.answer("❌ Error starting indexing.", show_alert=True)

@Client.on_callback_query(filters.regex("^clone_index_options:"))
async def handle_clone_index_options(client: Client, query):
    """Show advanced indexing options"""
    try:
        data_parts = query.data.split(":")
        channel_id = data_parts[1]
        start_id = data_parts[2]
        end_id = data_parts[3]
        clone_id = data_parts[4]
        
        # Get current settings
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        skip_duplicates = clone_data.get('skip_duplicates', True)
        media_only = clone_data.get('index_media_only', True)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔄 Skip Duplicates: {'ON' if skip_duplicates else 'OFF'}", 
                               callback_data=f"toggle_skip_dup:{clone_id}")],
            [InlineKeyboardButton(f"📁 Media Only: {'ON' if media_only else 'OFF'}", 
                               callback_data=f"toggle_media_only:{clone_id}")],
            [InlineKeyboardButton("✅ Start with Current Settings", 
                               callback_data=f"clone_start_range_index:{channel_id}:{start_id}:{end_id}:{clone_id}")],
            [InlineKeyboardButton("🔙 Back", 
                               callback_data=f"clone_start_range_index:{channel_id}:{start_id}:{end_id}:{clone_id}")]
        ])
        
        await query.edit_message_text(
            f"⚙️ **Indexing Options**\n\n"
            f"**Current Settings:**\n"
            f"• Skip Duplicates: {'✅ Enabled' if skip_duplicates else '❌ Disabled'}\n"
            f"• Media Only: {'✅ Enabled' if media_only else '❌ Disabled'}\n\n"
            f"**Range:** {start_id} to {end_id}\n"
            f"**Clone:** {clone_id}",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error showing index options: {e}")

@Client.on_callback_query(filters.regex("^toggle_skip_dup:"))
async def toggle_skip_dup_callback(client: Client, query):
    """Toggle skip duplicates setting"""
    try:
        clone_id = query.data.split(":")[1]
        
        # Verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or query.from_user.id != clone_data['admin_id']:
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        current_setting = clone_data.get('skip_duplicates', True)
        new_setting = not current_setting
        
        from bot.database.clone_db import update_clone_config
        await update_clone_config(clone_id, {"skip_duplicates": new_setting})
        
        await query.answer(f"Skip duplicates {'enabled' if new_setting else 'disabled'}!")
        
    except Exception as e:
        logger.error(f"Error toggling skip duplicates: {e}")

@Client.on_callback_query(filters.regex("^clone_show_progress:"))
async def show_indexing_progress(client: Client, query):
    """Show detailed indexing progress"""
    try:
        clone_id = query.data.split(":")[1]
        
        if clone_id not in clone_index_temp:
            await query.answer("❌ No active indexing process.", show_alert=True)
            return
        
        progress = clone_index_temp[clone_id]
        current = progress.get("current", 0)
        total = progress.get("total", 0)
        
        if total > 0:
            percentage = (current / total) * 100
            progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        else:
            percentage = 0
            progress_bar = "░" * 20
        
        progress_text = (
            f"📊 **Indexing Progress**\n\n"
            f"Progress: {current:,} / {total:,} ({percentage:.1f}%)\n"
            f"{progress_bar}\n\n"
            f"Range: {progress.get('start_id', 0)} to {progress.get('end_id', 0)}\n"
            f"Channel: {progress.get('channel_id', 'N/A')}\n"
            f"Clone: {clone_id}"
        )
        
        await query.edit_message_text(
            progress_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"clone_show_progress:{clone_id}")],
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")]
            ])
        )
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error showing progress: {e}")
        await query.answer("❌ Error loading progress.", show_alert=True)

async def index_clone_files_range(client: Client, msg: Message, channel_id: int, start_id: int, end_id: int, clone_id: str):
    """Index files for a specific clone within a message range"""
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = start_id - 1
    
    try:
        # Get clone settings
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        skip_duplicates = clone_data.get('skip_duplicates', True)
        media_only = clone_data.get('index_media_only', True)
        
        # Update progress
        clone_index_temp[clone_id]["current"] = current
        
        # Index messages in the specified range
        for msg_id in range(start_id, end_id + 1):
            if clone_index_temp.get(clone_id, {}).get("cancel", False):
                await msg.edit_text(
                    f"🛑 **Indexing Cancelled**\n\n"
                    f"✅ Saved: `{total_files}` files\n"
                    f"📋 Duplicates: `{duplicate}`\n"
                    f"🗑️ Deleted: `{deleted}`\n"
                    f"📄 Non-media: `{no_media + unsupported}`\n"
                    f"❌ Errors: `{errors}`"
                )
                break
            
            current = msg_id
            clone_index_temp[clone_id]["current"] = current
            
            if current % 50 == 0:  # Update progress every 50 messages
                try:
                    await msg.edit_text(
                        f"🔄 **Clone Range Indexing Progress**\n\n"
                        f"📊 Range: {start_id} to {end_id}\n"
                        f"📍 Current: `{current}`\n"
                        f"✅ Files indexed: `{total_files}`\n"
                        f"📋 Duplicates: `{duplicate}`\n"
                        f"🗑️ Deleted: `{deleted}`\n"
                        f"📄 Non-media: `{no_media + unsupported}`\n"
                        f"❌ Errors: `{errors}`",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")],
                            [InlineKeyboardButton("📊 Progress", callback_data=f"clone_show_progress:{clone_id}")]
                        ])
                    )
                except:
                    pass  # Ignore edit errors during rapid updates
            
            try:
                # Get specific message
                message = await client.get_messages(channel_id, msg_id)
                
                if not message or message.empty:
                    deleted += 1
                    continue
                
                if not message.media:
                    no_media += 1
                    if not media_only:
                        # Index text messages if media_only is disabled
                        continue
                    else:
                        continue
                
                if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, 
                                       enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
                    unsupported += 1
                    continue
                
                # Process media file
                success = await process_message_for_indexing(message, clone_id, channel_id, skip_duplicates)
                if success:
                    total_files += 1
                else:
                    duplicate += 1
                    
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                errors += 1
                continue
        
        # Clean up temp data
        if clone_id in clone_index_temp:
            del clone_index_temp[clone_id]
        
        await msg.edit_text(
            f"✅ **Clone Range Indexing Complete**\n\n"
            f"📊 **Final Results:**\n"
            f"✅ Files indexed: `{total_files}`\n"
            f"📋 Duplicates skipped: `{duplicate}`\n"
            f"🗑️ Deleted messages: `{deleted}`\n"
            f"📄 Non-media messages: `{no_media + unsupported}`\n"
            f"❌ Errors: `{errors}`\n\n"
            f"🎉 Files are now searchable in your clone bot!\n"
            f"💡 Use `/search <query>` to find files."
        )
        
    except Exception as e:
        logger.error(f"Error indexing clone files range: {e}")
        await msg.edit_text(f"❌ **Indexing Error**\n\nError: {str(e)}")
        
        # Clean up temp data
        if clone_id in clone_index_temp:
            del clone_index_temp[clone_id]

async def process_message_for_indexing(message: Message, clone_id: str, channel_id: int, skip_duplicates: bool = True):
    """Process a single message for indexing"""
    try:
        media = getattr(message, message.media.value, None)
        if not media:
            return False
        
        # Extract file information
        file_name = getattr(media, 'file_name', None)
        if not file_name:
            if message.media == enums.MessageMediaType.PHOTO:
                file_name = f"Photo_{message.id}.jpg"
            else:
                file_name = message.caption.split('\n')[0] if message.caption else f"File_{message.id}"
        
        file_size = getattr(media, 'file_size', 0)
        file_type = message.media.value
        caption = message.caption or ''
        file_id = getattr(media, 'file_id', None)
        
        # Enhanced metadata extraction
        file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
        mime_type = getattr(media, 'mime_type', '')
        duration = getattr(media, 'duration', 0)
        width = getattr(media, 'width', 0)
        height = getattr(media, 'height', 0)
        
        # Extract quality indicators
        quality = 'unknown'
        if file_size > 0:
            if file_type == 'video':
                if height >= 1080:
                    quality = '1080p+'
                elif height >= 720:
                    quality = '720p'
                elif height >= 480:
                    quality = '480p'
                else:
                    quality = 'low'
            elif file_type == 'audio':
                if file_size > 10 * 1024 * 1024:  # 10MB+
                    quality = 'high'
                elif file_size > 5 * 1024 * 1024:  # 5MB+
                    quality = 'medium'
                else:
                    quality = 'low'
        
        # Enhanced keywords extraction
        keywords = []
        text_content = f"{file_name} {caption}".lower()
        
        # Extract keywords from filename and caption
        words = re.findall(r'\b\w+\b', text_content)
        keywords = [word for word in words if len(word) > 2]
        
        # Add metadata-based keywords
        if quality != 'unknown':
            keywords.append(quality)
        if file_extension:
            keywords.append(file_extension)
        if duration > 0:
            if duration > 3600:  # 1 hour+
                keywords.extend(['long', 'movie', 'full'])
            elif duration > 1800:  # 30+ minutes
                keywords.extend(['medium', 'episode'])
            else:
                keywords.extend(['short', 'clip'])

        # Prepare enhanced file data for clone's database
        file_data = {
            "file_id": file_id or str(message.id),
            "message_id": message.id,
            "chat_id": channel_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "file_extension": file_extension,
            "mime_type": mime_type,
            "duration": duration,
            "width": width,
            "height": height,
            "quality": quality,
            "keywords": list(set(keywords)),  # Remove duplicates
            "caption": caption,
            "user_id": message.from_user.id if message.from_user else 0,
            "date": message.date,
            "views": getattr(message, 'views', 0),
            "forwards": getattr(message, 'forwards', 0),
            "indexed_at": datetime.utcnow(),
            "access_count": 0,
            "last_accessed": None,
            "clone_id": clone_id
        }
        
        # Add to clone's database
        success = await add_file_to_clone_index(file_data, clone_id)
        return success
        
    except Exception as e:
        logger.error(f"Error processing message for indexing: {e}")
        return False

# Keep existing callback handlers for compatibility
@Client.on_callback_query(filters.regex("^clone_start_index:"))
async def handle_clone_start_index(client: Client, query):
    """Handle original clone indexing start (backward compatibility)"""
    try:
        await query.answer("Starting indexing...", show_alert=True)
        
        _, chat_id, last_msg_id, clone_id = query.data.split(":")
        chat_id = int(chat_id)
        last_msg_id = int(last_msg_id)
        
        # Verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or query.from_user.id != clone_data['admin_id']:
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        # Initialize indexing state
        clone_index_temp[clone_id] = {
            "cancel": False,
            "current": 0,
            "total": last_msg_id,
            "start_id": 1,
            "end_id": last_msg_id,
            "channel_id": chat_id
        }
        
        await query.edit_message_text(
            "🔄 **Starting Clone Indexing**\n\n"
            "Indexing files to your clone's database...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")],
                [InlineKeyboardButton("📊 Progress", callback_data=f"clone_show_progress:{clone_id}")]
            ])
        )
        
        # Start indexing process
        await index_clone_files_range(client, query.message, chat_id, 1, last_msg_id, clone_id)
        
    except Exception as e:
        logger.error(f"Error starting clone indexing: {e}")
        await query.answer("❌ Error starting indexing.", show_alert=True)

@Client.on_callback_query(filters.regex("^clone_cancel_index:"))
async def handle_clone_cancel_index(client: Client, query):
    """Handle clone indexing cancellation"""
    try:
        clone_id = query.data.split(":")[1]
        
        if clone_id in clone_index_temp:
            clone_index_temp[clone_id]["cancel"] = True
        
        await query.answer("Cancelling indexing...", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error cancelling clone indexing: {e}")

# Function for auto-indexing forwarded messages (enhanced)
async def auto_index_forwarded_message(client: Client, message: Message, clone_id: str):
    """Automatically index a forwarded message - ADMIN ONLY"""
    try:
        # Verify admin access first
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        clone_data = await get_clone_by_bot_token(bot_token)
        
        if not clone_data or message.from_user.id != clone_data.get('admin_id'):
            logger.warning(f"Auto-indexing blocked: User {message.from_user.id} is not clone admin")
            return False
        
        if not message.media:
            return False
        
        if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, 
                               enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
            return False
        
        # Get channel info from forward header
        channel_id = None
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
        
        # Process message for indexing
        skip_duplicates = clone_data.get('skip_duplicates', True)
        success = await process_message_for_indexing(message, clone_id, channel_id, skip_duplicates)
        
        return success
        
    except Exception as e:
        logger.error(f"Error in auto-index forwarded message: {e}")
        return False
