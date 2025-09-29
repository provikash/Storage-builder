
# Auto-index forwarded media messages - ADMIN ONLY
import logging
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid, MessageEmpty
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

async def verify_clone_admin(client: Client, user_id: int) -> tuple[bool, dict]:
    """Verify if user is clone admin and return clone data"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False, None  # Not a clone bot
        
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return False, None
        
        is_admin = user_id == clone_data.get('admin_id')
        return is_admin, clone_data
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        return False, None

# Store indexing progress for each clone
indexing_progress = {}
indexing_tasks = {}

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.media & filters.forwarded & filters.private, group=10)
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

        # Check if message is forwarded from a channel
        if not message.forward_from_chat:
            return

        forward_chat = message.forward_from_chat
        if forward_chat.type not in ["channel", "supergroup"]:
            return

        channel_id = forward_chat.id
        channel_title = forward_chat.title or "Unknown Channel"
        
        # Check if auto-indexing is enabled
        auto_index_enabled = clone_data.get('auto_index_forwarded', True)
        if not auto_index_enabled:
            return

        logger.info(f"Auto-index triggered for clone {clone_id} from channel {channel_title}")

        # Try to get channel info and latest message
        try:
            chat_info = await client.get_chat(channel_id)
            
            # Get the latest message ID from the channel
            latest_msg = None
            async for msg in client.iter_messages(channel_id, limit=1):
                latest_msg = msg
                break
            
            if not latest_msg:
                await message.reply_text("❌ **Error**: Cannot access channel messages.")
                return
                
            latest_msg_id = latest_msg.id
            
            # Show indexing options to admin
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Index Full Channel", 
                                       callback_data=f"auto_index_full:{channel_id}:{latest_msg_id}:{clone_id}")
                ],
                [
                    InlineKeyboardButton("📁 Index This Media Only", 
                                       callback_data=f"index_single_media:{clone_id}:{message.id}")
                ],
                [
                    InlineKeyboardButton("⚙️ Index Settings", 
                                       callback_data=f"index_settings:{clone_id}")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="close")
                ]
            ])
            
            await message.reply_text(
                f"🔍 **Auto-Index Detection**\n\n"
                f"**Channel:** {channel_title}\n"
                f"**Total Messages:** ~{latest_msg_id:,}\n"
                f"**Clone Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`\n\n"
                f"**Options:**\n"
                f"• Index all media from this channel\n"
                f"• Index only this forwarded media\n"
                f"• Configure indexing settings\n\n"
                f"Choose your preferred indexing method:",
                reply_markup=buttons
            )
            
        except ChannelInvalid:
            await message.reply_text(
                f"❌ **Channel Access Error**\n\n"
                f"Cannot access channel: {channel_title}\n"
                f"Please ensure the bot is added as admin in the channel."
            )
        except Exception as e:
            logger.error(f"Error in auto-index detection: {e}")
            await message.reply_text(
                f"❌ **Error**: Failed to process channel indexing.\n"
                f"Error: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"Error in auto-index forwarded media: {e}")

@Client.on_callback_query(filters.regex("^auto_index_full:"))
async def handle_auto_index_full(client: Client, query: CallbackQuery):
    """Handle full channel indexing"""
    try:
        data_parts = query.data.split(":")
        channel_id = int(data_parts[1])
        latest_msg_id = int(data_parts[2])
        clone_id = data_parts[3]
        
        await query.answer("Starting full channel indexing...", show_alert=True)
        
        # Check if already indexing
        if clone_id in indexing_tasks and not indexing_tasks[clone_id].done():
            await query.edit_message_text("⚠️ **Already Indexing**\n\nPlease wait for the current indexing process to complete.")
            return
        
        # Initialize progress tracking
        indexing_progress[clone_id] = {
            "status": "starting",
            "processed": 0,
            "indexed": 0,
            "duplicates": 0,
            "errors": 0,
            "channel_id": channel_id,
            "total_estimate": latest_msg_id,
            "start_time": datetime.now()
        }
        
        await query.edit_message_text(
            "🔄 **Starting Full Channel Indexing**\n\n"
            f"📊 Estimated messages: {latest_msg_id:,}\n"
            f"🗄️ Target database: Clone {clone_id}\n\n"
            "Indexing all media files to your clone's database...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"cancel_index:{clone_id}")],
                [InlineKeyboardButton("📊 Progress", callback_data=f"index_progress:{clone_id}")]
            ])
        )
        
        # Start indexing task
        task = asyncio.create_task(index_channel_media(client, query.message, channel_id, latest_msg_id, clone_id))
        indexing_tasks[clone_id] = task
        
    except Exception as e:
        logger.error(f"Error in auto index full: {e}")
        await query.answer("❌ Error starting indexing.", show_alert=True)

@Client.on_callback_query(filters.regex("^index_single_media:"))
async def handle_index_single_media(client: Client, query: CallbackQuery):
    """Handle single media indexing"""
    try:
        data_parts = query.data.split(":")
        clone_id = data_parts[1]
        message_id = int(data_parts[2])
        
        await query.answer("Indexing single media...", show_alert=False)
        
        # Get the forwarded message
        try:
            forwarded_msg = await client.get_messages(query.message.chat.id, message_id)
            
            if not forwarded_msg or not forwarded_msg.media:
                await query.edit_message_text("❌ **Error**: Media message not found.")
                return
            
            # Index the single media
            success = await index_single_media_file(client, forwarded_msg, clone_id)
            
            if success:
                media_name = get_media_name(forwarded_msg)
                await query.edit_message_text(
                    "✅ **Media Indexed Successfully**\n\n"
                    f"📁 **File**: `{media_name}`\n"
                    f"🗄️ **Database**: Clone {clone_id}\n\n"
                    f"🔍 Media is now searchable in your clone bot!"
                )
            else:
                await query.edit_message_text(
                    "❌ **Indexing Failed**\n\n"
                    "Media could not be indexed. It may already exist or there was an error."
                )
                
        except Exception as e:
            logger.error(f"Error indexing single media: {e}")
            await query.edit_message_text(f"❌ **Error**: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in index single media: {e}")
        await query.answer("❌ Error indexing media.", show_alert=True)

@Client.on_callback_query(filters.regex("^index_settings:"))
async def handle_index_settings(client: Client, query: CallbackQuery):
    """Handle indexing settings"""
    try:
        clone_id = query.data.split(":")[1]
        
        # Get current settings
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found.")
            return
        
        auto_index = clone_data.get('auto_index_forwarded', True)
        batch_size = clone_data.get('index_batch_size', 100)
        include_duplicates = clone_data.get('index_include_duplicates', False)
        
        settings_text = (
            f"⚙️ **Indexing Settings - Clone {clone_id}**\n\n"
            f"🔄 **Auto-Index Forwards**: {'✅ Enabled' if auto_index else '❌ Disabled'}\n"
            f"📦 **Batch Size**: {batch_size} messages\n"
            f"🔁 **Include Duplicates**: {'✅ Yes' if include_duplicates else '❌ No'}\n"
            f"🗄️ **Database**: `{clone_data.get('db_name', f'clone_{clone_id}')}`\n\n"
            f"**Modify settings below:**"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🔄 Auto-Index: {'ON' if auto_index else 'OFF'}", 
                                   callback_data=f"toggle_auto_index:{clone_id}"),
            ],
            [
                InlineKeyboardButton("📦 Batch Size", callback_data=f"set_batch_size:{clone_id}"),
                InlineKeyboardButton(f"🔁 Duplicates: {'ON' if include_duplicates else 'OFF'}", 
                                   callback_data=f"toggle_duplicates:{clone_id}")
            ],
            [
                InlineKeyboardButton("🗄️ Database Info", callback_data=f"clone_db_info:{clone_id}"),
                InlineKeyboardButton("📊 Index Stats", callback_data=f"index_stats:{clone_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="close")
            ]
        ])
        
        await query.edit_message_text(settings_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in index settings: {e}")
        await query.answer("❌ Error loading settings.", show_alert=True)

@Client.on_callback_query(filters.regex("^index_progress:"))
async def handle_index_progress(client: Client, query: CallbackQuery):
    """Show indexing progress"""
    try:
        clone_id = query.data.split(":")[1]
        
        if clone_id not in indexing_progress:
            await query.answer("❌ No indexing process found.", show_alert=True)
            return
        
        progress = indexing_progress[clone_id]
        elapsed = (datetime.now() - progress["start_time"]).total_seconds()
        
        # Calculate ETA
        if progress["processed"] > 0 and progress["processed"] < progress["total_estimate"]:
            rate = progress["processed"] / elapsed
            remaining = progress["total_estimate"] - progress["processed"]
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_text = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
        else:
            eta_text = "Calculating..."
        
        progress_text = (
            f"📊 **Indexing Progress - Clone {clone_id}**\n\n"
            f"📈 **Status**: {progress['status'].title()}\n"
            f"🔍 **Processed**: {progress['processed']:,}\n"
            f"✅ **Indexed**: {progress['indexed']:,}\n"
            f"🔁 **Duplicates**: {progress['duplicates']:,}\n"
            f"❌ **Errors**: {progress['errors']:,}\n"
            f"⏱️ **Elapsed**: {int(elapsed // 60)}m {int(elapsed % 60)}s\n"
            f"🎯 **ETA**: {eta_text}\n"
            f"📊 **Progress**: {(progress['processed'] / progress['total_estimate'] * 100):.1f}%"
        )
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"index_progress:{clone_id}")],
            [InlineKeyboardButton("🛑 Cancel", callback_data=f"cancel_index:{clone_id}")]
        ])
        
        await query.edit_message_text(progress_text, reply_markup=buttons)
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error showing progress: {e}")
        await query.answer("❌ Error loading progress.", show_alert=True)

@Client.on_callback_query(filters.regex("^cancel_index:"))
async def handle_cancel_index(client: Client, query: CallbackQuery):
    """Cancel indexing process"""
    try:
        clone_id = query.data.split(":")[1]
        
        # Cancel the task
        if clone_id in indexing_tasks and not indexing_tasks[clone_id].done():
            indexing_tasks[clone_id].cancel()
        
        # Update progress
        if clone_id in indexing_progress:
            indexing_progress[clone_id]["status"] = "cancelled"
        
        await query.edit_message_text(
            "🛑 **Indexing Cancelled**\n\n"
            f"The indexing process for clone {clone_id} has been cancelled.\n"
            f"Any files already indexed remain in the database."
        )
        await query.answer("Indexing cancelled.", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error cancelling index: {e}")
        await query.answer("❌ Error cancelling indexing.", show_alert=True)

async def index_channel_media(client: Client, msg: Message, channel_id: int, last_msg_id: int, clone_id: str):
    """Index all media files from a channel"""
    try:
        # Get clone database connection
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or 'mongodb_url' not in clone_data:
            logger.error(f"No MongoDB URL found for clone {clone_id}")
            return
        
        # Connect to clone's specific database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
        files_collection = clone_db['files']
        
        # Update progress
        indexing_progress[clone_id]["status"] = "indexing"
        
        processed = 0
        indexed = 0
        duplicates = 0
        errors = 0
        
        # Index messages in batches
        batch_size = clone_data.get('index_batch_size', 100)
        
        try:
            async for message in client.iter_messages(channel_id, limit=last_msg_id):
                try:
                    # Check if cancelled
                    if indexing_progress[clone_id]["status"] == "cancelled":
                        break
                    
                    processed += 1
                    
                    # Update progress every 50 messages
                    if processed % 50 == 0:
                        indexing_progress[clone_id].update({
                            "processed": processed,
                            "indexed": indexed,
                            "duplicates": duplicates,
                            "errors": errors
                        })
                        
                        # Update the message every 200 processed
                        if processed % 200 == 0:
                            try:
                                await msg.edit_text(
                                    f"🔄 **Indexing Progress**\n\n"
                                    f"📊 Messages processed: `{processed:,}`\n"
                                    f"✅ Files indexed: `{indexed:,}`\n"
                                    f"🔁 Duplicates: `{duplicates:,}`\n"
                                    f"❌ Errors: `{errors:,}`\n\n"
                                    f"🔍 Processing message ID: `{message.id if message else 'N/A'}`",
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton("🛑 Cancel", callback_data=f"cancel_index:{clone_id}")],
                                        [InlineKeyboardButton("📊 Progress", callback_data=f"index_progress:{clone_id}")]
                                    ])
                                )
                            except:
                                pass  # Ignore edit errors
                    
                    # Skip non-media messages
                    if not message or not message.media:
                        continue
                    
                    # Check for valid media types
                    if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, 
                                           enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO, 
                                           enums.MessageMediaType.ANIMATION]:
                        continue
                    
                    # Index the media file
                    success = await index_media_to_clone_db(message, clone_id, files_collection, channel_id)
                    if success:
                        indexed += 1
                    else:
                        duplicates += 1
                        
                except FloodWait as fw:
                    logger.warning(f"FloodWait {fw.value}s during indexing")
                    await asyncio.sleep(fw.value + 1)
                    continue
                except MessageEmpty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing message {message.id if message else 'N/A'}: {e}")
                    errors += 1
                    continue
            
        except Exception as e:
            logger.error(f"Error during channel iteration: {e}")
            errors += 1
        
        # Final update
        indexing_progress[clone_id].update({
            "status": "completed",
            "processed": processed,
            "indexed": indexed,
            "duplicates": duplicates,
            "errors": errors
        })
        
        # Close database connection
        clone_client.close()
        
        # Final message
        await msg.edit_text(
            f"✅ **Channel Indexing Complete**\n\n"
            f"📊 **Final Results:**\n"
            f"✅ Files indexed: `{indexed:,}`\n"
            f"🔁 Duplicates skipped: `{duplicates:,}`\n"
            f"📊 Messages processed: `{processed:,}`\n"
            f"❌ Errors: `{errors:,}`\n\n"
            f"🎉 All media files are now searchable in your clone bot!\n"
            f"💡 Use search commands to find indexed files."
        )
        
    except Exception as e:
        logger.error(f"Error in index_channel_media: {e}")
        if clone_id in indexing_progress:
            indexing_progress[clone_id]["status"] = "error"
        
        try:
            await msg.edit_text(f"❌ **Indexing Error**\n\nError: {str(e)}")
        except:
            pass

async def index_media_to_clone_db(message: Message, clone_id: str, files_collection, channel_id: int):
    """Index a single media file to clone database"""
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
        file_id = getattr(media, 'file_id', None)
        
        if not file_id:
            return False
        
        # Check for duplicates
        existing = await files_collection.find_one({"file_id": file_id})
        if existing:
            return False  # Already exists
        
        # Prepare file data
        file_data = {
            "_id": f"{channel_id}_{message.id}",
            "file_id": file_id,
            "file_name": file_name,
            "file_type": message.media.value,
            "file_size": file_size,
            "message_id": message.id,
            "chat_id": channel_id,
            "caption": message.caption or "",
            "user_id": message.from_user.id if message.from_user else 0,
            "date": message.date,
            "clone_id": clone_id,
            "indexed_at": datetime.now(),
            "download_count": 0,
            "view_count": 0
        }
        
        # Insert to database
        await files_collection.insert_one(file_data)
        return True
        
    except Exception as e:
        logger.error(f"Error indexing media to clone DB: {e}")
        return False

async def index_single_media_file(client: Client, message: Message, clone_id: str):
    """Index a single media file"""
    try:
        # Get clone database connection
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or 'mongodb_url' not in clone_data:
            return False
        
        # Connect to clone's database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
        files_collection = clone_db['files']
        
        # Index the file
        success = await index_media_to_clone_db(
            message, clone_id, files_collection, 
            message.forward_from_chat.id if message.forward_from_chat else message.chat.id
        )
        
        # Close connection
        clone_client.close()
        
        return success
        
    except Exception as e:
        logger.error(f"Error indexing single media: {e}")
        return False

def get_media_name(message: Message):
    """Get media file name"""
    if not message.media:
        return "Unknown"
    
    media = getattr(message, message.media.value, None)
    if not media:
        return "Unknown"
    
    file_name = getattr(media, 'file_name', None)
    if not file_name:
        if message.media == enums.MessageMediaType.PHOTO:
            return f"Photo_{message.id}.jpg"
        else:
            return message.caption.split('\n')[0] if message.caption else f"File_{message.id}"
    
    return file_name

# Command to manually trigger indexing
@Client.on_message(filters.command(['indexchannel', 'index']) & filters.private)
async def manual_index_command(client: Client, message: Message):
    """Manual indexing command for clone admins"""
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
        
        # Check if user is admin
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can use this command.")
            return
        
        if len(message.command) < 2:
            await message.reply_text(
                "🔍 **Manual Channel Indexing**\n\n"
                "**Usage:**\n"
                "`/index <channel_username_or_id>`\n"
                "`/indexchannel <channel_link>`\n\n"
                "**Examples:**\n"
                "• `/index @mychannel`\n"
                "• `/index -1001234567890`\n"
                "• `/indexchannel https://t.me/channel/123`\n\n"
                "**Note:** Bot must be admin in the channel or channel must be public.\n"
                "Each clone uses its own MongoDB database for indexing."
            )
            return
        
        channel_input = message.command[1]
        
        # Parse channel link if provided
        if channel_input.startswith('https://t.me/'):
            regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/?(\d+)?$")
            match = regex.match(channel_input)
            if match:
                channel_input = match.group(4)
                if channel_input.isnumeric():
                    channel_input = int("-100" + channel_input)
        
        # Try to get channel
        try:
            chat = await client.get_chat(channel_input)
            
            # Get latest message ID
            async for latest_msg in client.iter_messages(chat.id, limit=1):
                last_msg_id = latest_msg.id
                break
            else:
                await message.reply_text("❌ Channel appears to be empty.")
                return
            
            # Show confirmation
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Start Indexing", 
                                   callback_data=f"auto_index_full:{chat.id}:{last_msg_id}:{clone_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="close")]
            ])
            
            await message.reply_text(
                f"🔍 **Manual Channel Indexing**\n\n"
                f"**Channel:** {chat.title}\n"
                f"**Username:** @{chat.username or 'None'}\n"
                f"**Total Messages:** ~{last_msg_id:,}\n"
                f"**Clone Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`\n\n"
                f"Ready to index all media from this channel?\n"
                f"This will add files to your clone's database.",
                reply_markup=buttons
            )
                
        except ChannelInvalid:
            await message.reply_text(
                "❌ **Access Denied**\n\n"
                "Bot needs access to this channel.\n"
                "Please add the bot as admin in the channel and try again."
            )
        except Exception as e:
            await message.reply_text(f"❌ **Error**: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in manual index command: {e}")
        await message.reply_text("❌ Error processing indexing request.")
