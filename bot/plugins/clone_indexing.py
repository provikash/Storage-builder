
import logging
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

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

async def verify_clone_admin(client: Client, user_id: int) -> tuple[bool, dict]:
    """Verify if user is clone admin and return clone data"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False, None
        
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return False, None
        
        is_admin = user_id == clone_data.get('admin_id')
        return is_admin, clone_data
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        return False, None

@Client.on_message(filters.command(['index', 'indexing']) & filters.private)
async def clone_index_command(client: Client, message: Message):
    """Handle indexing command for clone bots - ADMIN ONLY"""
    try:
        # Verify this is a clone bot and user is admin
        is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
        if not is_admin:
            await message.reply_text("❌ **Access Denied**\n\nThis command is only available to clone administrators.")
            return
        
        clone_id = get_clone_id_from_client(client)
        
        if len(message.command) < 2:
            help_text = (
                "📚 **Clone Indexing System**\n\n"
                "**Available Commands:**\n"
                "• `/index <channel_link>` - Index from channel link\n"
                "• `/index <username>` - Index from channel username\n"
                "• `/indexstats` - View indexing statistics\n"
                "• `/indexstatus` - Check current indexing status\n\n"
                
                "**Supported Formats:**\n"
                "• `https://t.me/channel/123`\n"
                "• `https://t.me/c/123456/789`\n"
                "• `@channelname`\n"
                "• Channel ID: `-1001234567890`\n\n"
                
                "**Features:**\n"
                "✅ Auto-duplicate detection\n"
                "✅ Progress tracking\n"
                "✅ Pause/Resume support\n"
                "✅ Error recovery\n\n"
                
                f"**Clone Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`"
            )
            await message.reply_text(help_text)
            return
        
        # Parse the input
        input_text = " ".join(message.command[1:]).strip()
        await process_index_request(client, message, input_text, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error in clone index command: {e}")
        await message.reply_text("❌ Error processing indexing request.")

async def process_index_request(client: Client, message: Message, input_text: str, clone_id: str, clone_data: dict):
    """Process indexing request from various input formats"""
    try:
        channel_id = None
        last_msg_id = None
        
        # Parse different input formats
        if input_text.startswith('@'):
            # Username format
            username = input_text[1:]
            try:
                chat = await client.get_chat(username)
                channel_id = chat.id
            except Exception as e:
                await message.reply_text(f"❌ **Error**: Cannot access @{username}\n{str(e)}")
                return
                
        elif input_text.startswith('https://t.me/'):
            # URL format
            if '/c/' in input_text:
                # Private channel format: https://t.me/c/123456/789
                regex = re.compile(r"https://t\.me/c/(\d+)/(\d+)")
                match = regex.match(input_text)
                if match:
                    channel_id = int(f"-100{match.group(1)}")
                    last_msg_id = int(match.group(2))
            else:
                # Public channel format: https://t.me/channel/123
                regex = re.compile(r"https://t\.me/([^/]+)/?(\d+)?")
                match = regex.match(input_text)
                if match:
                    username = match.group(1)
                    msg_id = match.group(2)
                    try:
                        chat = await client.get_chat(username)
                        channel_id = chat.id
                        if msg_id:
                            last_msg_id = int(msg_id)
                    except Exception as e:
                        await message.reply_text(f"❌ **Error**: Cannot access channel\n{str(e)}")
                        return
                        
        elif input_text.startswith('-100') and input_text.lstrip('-').isdigit():
            # Channel ID format
            channel_id = int(input_text)
            
        else:
            await message.reply_text(
                "❌ **Invalid Format**\n\n"
                "Please use one of these formats:\n"
                "• `@channelname`\n"
                "• `https://t.me/channel/123`\n"
                "• `https://t.me/c/123456/789`\n"
                "• `-1001234567890`"
            )
            return
        
        if not channel_id:
            await message.reply_text("❌ **Error**: Could not determine channel ID from input.")
            return
        
        # Verify channel access
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title or "Unknown Channel"
            channel_username = f"@{chat.username}" if chat.username else "Private Channel"
            
            # Get latest message ID if not provided
            if not last_msg_id:
                async for latest_msg in client.iter_messages(channel_id, limit=1):
                    last_msg_id = latest_msg.id
                    break
                
                if not last_msg_id:
                    await message.reply_text("❌ **Error**: Channel appears to be empty.")
                    return
            
        except ChannelInvalid:
            await message.reply_text("❌ **Channel Access Error**\n\nBot is not a member of this channel or channel doesn't exist.")
            return
        except ChatAdminRequired:
            await message.reply_text("❌ **Admin Required**\n\nBot needs admin access to index this channel.")
            return
        except Exception as e:
            await message.reply_text(f"❌ **Error**: {str(e)}")
            return
        
        # Show confirmation dialog
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Start Indexing", 
                                   callback_data=f"start_index:{channel_id}:{last_msg_id}:{clone_id}"),
                InlineKeyboardButton("📊 Quick Scan", 
                                   callback_data=f"quick_scan:{channel_id}:{last_msg_id}:{clone_id}")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", 
                                   callback_data=f"index_settings:{clone_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="close")
            ]
        ])
        
        confirmation_text = (
            f"📋 **Indexing Confirmation**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**Username:** {channel_username}\n"
            f"**Channel ID:** `{channel_id}`\n"
            f"**Messages:** ~{last_msg_id:,}\n"
            f"**Clone Database:** `{clone_data.get('db_name')}`\n\n"
            
            f"**Options:**\n"
            f"• **Start Indexing**: Begin full indexing process\n"
            f"• **Quick Scan**: Preview what will be indexed\n"
            f"• **Settings**: Configure indexing preferences\n\n"
            
            f"⚠️ **Note**: Indexing may take time for large channels."
        )
        
        await message.reply_text(confirmation_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error processing index request: {e}")
        await message.reply_text("❌ Error processing request.")

@Client.on_callback_query(filters.regex("^start_index:"))
async def handle_start_index(client: Client, query: CallbackQuery):
    """Handle start indexing callback"""
    try:
        await query.answer("Starting indexing process...", show_alert=False)
        
        data_parts = query.data.split(":")
        channel_id = int(data_parts[1])
        last_msg_id = int(data_parts[2])
        clone_id = data_parts[3]
        
        # Verify admin access
        is_admin, clone_data = await verify_clone_admin(client, query.from_user.id)
        if not is_admin:
            await query.edit_message_text("❌ Access denied. Only clone admin can start indexing.")
            return
        
        # Check if already indexing
        if clone_id in indexing_tasks and not indexing_tasks[clone_id].done():
            await query.edit_message_text("⚠️ **Already Indexing**\n\nPlease wait for current indexing to complete.")
            return
        
        # Initialize progress tracking
        indexing_progress[clone_id] = {
            "status": "initializing",
            "processed": 0,
            "indexed": 0,
            "duplicates": 0,
            "errors": 0,
            "deleted": 0,
            "non_media": 0,
            "channel_id": channel_id,
            "total_estimate": last_msg_id,
            "start_time": datetime.now(),
            "current_message_id": 0,
            "batch_size": 50,
            "pause_requested": False
        }
        
        # Show initial progress
        progress_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Progress", callback_data=f"show_progress:{clone_id}"),
                InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_index:{clone_id}")
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data=f"stop_index:{clone_id}")
            ]
        ])
        
        await query.edit_message_text(
            f"🔄 **Indexing Started**\n\n"
            f"📊 **Status**: Initializing...\n"
            f"🗄️ **Database**: {clone_data.get('db_name')}\n"
            f"📁 **Channel**: {channel_id}\n"
            f"📈 **Estimated Messages**: {last_msg_id:,}\n\n"
            f"⏱️ **Started**: {datetime.now().strftime('%H:%M:%S')}\n"
            f"📱 Use buttons below to monitor progress.",
            reply_markup=progress_buttons
        )
        
        # Start indexing task
        task = asyncio.create_task(index_channel_messages(client, query.message, channel_id, last_msg_id, clone_id, clone_data))
        indexing_tasks[clone_id] = task
        
    except Exception as e:
        logger.error(f"Error starting indexing: {e}")
        await query.answer("❌ Error starting indexing.", show_alert=True)

async def index_channel_messages(client: Client, msg: Message, channel_id: int, last_msg_id: int, clone_id: str, clone_data: dict):
    """Main indexing function with enhanced features"""
    progress = indexing_progress[clone_id]
    
    try:
        # Connect to clone database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
        files_collection = clone_db['files']
        
        progress["status"] = "running"
        
        # Create index for better performance
        await files_collection.create_index([("file_id", 1), ("message_id", 1)], unique=True)
        
        async for message in client.iter_messages(channel_id, last_msg_id):
            # Check for pause/stop requests
            if progress.get("pause_requested"):
                progress["status"] = "paused"
                while progress.get("pause_requested") and not progress.get("stop_requested"):
                    await asyncio.sleep(1)
                progress["status"] = "running"
            
            if progress.get("stop_requested"):
                progress["status"] = "stopped"
                break
            
            progress["processed"] += 1
            progress["current_message_id"] = message.id
            
            # Update progress every 20 messages
            if progress["processed"] % 20 == 0:
                await update_progress_message(msg, clone_id, progress)
            
            # Handle different message types
            if message.empty:
                progress["deleted"] += 1
                continue
            
            if not message.media:
                progress["non_media"] += 1
                continue
            
            # Only index supported media types
            if message.media not in [
                enums.MessageMediaType.VIDEO,
                enums.MessageMediaType.AUDIO, 
                enums.MessageMediaType.DOCUMENT,
                enums.MessageMediaType.PHOTO
            ]:
                progress["non_media"] += 1
                continue
            
            try:
                # Extract file information
                media = getattr(message, message.media.value, None)
                if not media:
                    progress["non_media"] += 1
                    continue
                
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
                
                # Extract enhanced metadata
                file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
                mime_type = getattr(media, 'mime_type', '')
                duration = getattr(media, 'duration', 0)
                width = getattr(media, 'width', 0)
                height = getattr(media, 'height', 0)
                
                # Quality detection
                quality = 'unknown'
                if file_type == 'video' and height > 0:
                    if height >= 1080:
                        quality = '1080p+'
                    elif height >= 720:
                        quality = '720p'
                    elif height >= 480:
                        quality = '480p'
                    else:
                        quality = 'low'
                elif file_type == 'audio' and file_size > 0:
                    if file_size > 10 * 1024 * 1024:
                        quality = 'high'
                    elif file_size > 5 * 1024 * 1024:
                        quality = 'medium'
                    else:
                        quality = 'low'
                
                # Extract keywords
                keywords = []
                text_content = f"{file_name} {caption}".lower()
                words = re.findall(r'\b\w+\b', text_content)
                keywords = [word for word in words if len(word) > 2]
                
                # Add metadata keywords
                if quality != 'unknown':
                    keywords.append(quality)
                if file_extension:
                    keywords.append(file_extension)
                
                # Prepare file document
                file_doc = {
                    "file_id": file_id,
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
                    "keywords": list(set(keywords)),
                    "caption": caption,
                    "indexed_at": datetime.now(),
                    "clone_id": clone_id,
                    "access_count": 0,
                    "download_count": 0,
                    "last_accessed": None,
                    "is_indexed": True
                }
                
                # Insert with duplicate handling
                try:
                    await files_collection.insert_one(file_doc)
                    progress["indexed"] += 1
                except Exception:
                    # Handle duplicate
                    progress["duplicates"] += 1
                
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")
                progress["errors"] += 1
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        # Finalization
        progress["status"] = "completed"
        progress["end_time"] = datetime.now()
        
        await finalize_indexing(msg, clone_id, progress)
        
        clone_client.close()
        
    except Exception as e:
        logger.error(f"Error in indexing process: {e}")
        progress["status"] = "failed"
        progress["error"] = str(e)
        await msg.edit_text(f"❌ **Indexing Failed**\n\nError: {str(e)}")
    finally:
        # Cleanup
        if clone_id in indexing_progress:
            del indexing_progress[clone_id]
        if clone_id in indexing_tasks:
            del indexing_tasks[clone_id]

async def update_progress_message(msg: Message, clone_id: str, progress: dict):
    """Update progress message with current stats"""
    try:
        elapsed = (datetime.now() - progress["start_time"]).total_seconds()
        rate = progress["processed"] / elapsed if elapsed > 0 else 0
        
        # Calculate ETA
        remaining = progress["total_estimate"] - progress["processed"]
        eta_seconds = remaining / rate if rate > 0 else 0
        eta_text = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 0 else "Calculating..."
        
        progress_text = (
            f"🔄 **Indexing Progress**\n\n"
            f"📊 **Status**: {progress['status'].title()}\n"
            f"🔍 **Processed**: {progress['processed']:,} / {progress['total_estimate']:,}\n"
            f"✅ **Indexed**: {progress['indexed']:,}\n"
            f"🔁 **Duplicates**: {progress['duplicates']:,}\n"
            f"🗑️ **Deleted**: {progress['deleted']:,}\n"
            f"📄 **Non-media**: {progress['non_media']:,}\n"
            f"❌ **Errors**: {progress['errors']:,}\n\n"
            
            f"⏱️ **Elapsed**: {int(elapsed // 60)}m {int(elapsed % 60)}s\n"
            f"🎯 **ETA**: {eta_text}\n"
            f"⚡ **Rate**: {rate:.1f} msg/s\n"
            f"📱 **Current**: #{progress['current_message_id']}\n\n"
            
            f"📈 **Progress**: {(progress['processed'] / progress['total_estimate'] * 100):.1f}%"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"show_progress:{clone_id}"),
                InlineKeyboardButton("⏸️ Pause" if progress['status'] == 'running' else "▶️ Resume", 
                                   callback_data=f"{'pause' if progress['status'] == 'running' else 'resume'}_index:{clone_id}")
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data=f"stop_index:{clone_id}")
            ]
        ])
        
        await msg.edit_text(progress_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error updating progress: {e}")

async def finalize_indexing(msg: Message, clone_id: str, progress: dict):
    """Finalize indexing process and show results"""
    try:
        elapsed = (progress.get("end_time", datetime.now()) - progress["start_time"]).total_seconds()
        
        final_text = (
            f"✅ **Indexing Complete**\n\n"
            f"📊 **Final Statistics:**\n"
            f"🔍 **Processed**: {progress['processed']:,} messages\n"
            f"✅ **Successfully Indexed**: {progress['indexed']:,}\n"
            f"🔁 **Duplicates Skipped**: {progress['duplicates']:,}\n"
            f"🗑️ **Deleted Messages**: {progress['deleted']:,}\n"
            f"📄 **Non-media Messages**: {progress['non_media']:,}\n"
            f"❌ **Errors**: {progress['errors']:,}\n\n"
            
            f"⏱️ **Total Time**: {int(elapsed // 60)}m {int(elapsed % 60)}s\n"
            f"⚡ **Average Rate**: {(progress['processed'] / elapsed):.1f} msg/s\n\n"
            
            f"🎉 **Files are now searchable in your clone bot!**\n"
            f"💡 Use `/search <query>` to find indexed files."
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 View Stats", callback_data=f"clone_stats:{clone_id}"),
                InlineKeyboardButton("🔍 Search Files", callback_data=f"search_files:{clone_id}")
            ]
        ])
        
        await msg.edit_text(final_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in finalization: {e}")

# Additional callback handlers for progress control
@Client.on_callback_query(filters.regex("^pause_index:"))
async def handle_pause_index(client: Client, query: CallbackQuery):
    """Handle pause indexing"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in indexing_progress:
            indexing_progress[clone_id]["pause_requested"] = True
            await query.answer("⏸️ Indexing paused", show_alert=False)
        else:
            await query.answer("❌ No active indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error pausing index: {e}")

@Client.on_callback_query(filters.regex("^resume_index:"))
async def handle_resume_index(client: Client, query: CallbackQuery):
    """Handle resume indexing"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in indexing_progress:
            indexing_progress[clone_id]["pause_requested"] = False
            await query.answer("▶️ Indexing resumed", show_alert=False)
        else:
            await query.answer("❌ No paused indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error resuming index: {e}")

@Client.on_callback_query(filters.regex("^stop_index:"))
async def handle_stop_index(client: Client, query: CallbackQuery):
    """Handle stop indexing"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in indexing_progress:
            indexing_progress[clone_id]["stop_requested"] = True
            await query.answer("🛑 Indexing will stop after current batch", show_alert=True)
        else:
            await query.answer("❌ No active indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error stopping index: {e}")

@Client.on_callback_query(filters.regex("^show_progress:"))
async def handle_show_progress(client: Client, query: CallbackQuery):
    """Show current indexing progress"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in indexing_progress:
            await update_progress_message(query.message, clone_id, indexing_progress[clone_id])
            await query.answer()
        else:
            await query.answer("❌ No active indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error showing progress: {e}")

@Client.on_callback_query(filters.regex("^quick_scan:"))
async def handle_quick_scan(client: Client, query: CallbackQuery):
    """Handle quick scan of channel"""
    try:
        await query.answer("Starting quick scan...", show_alert=False)
        
        data_parts = query.data.split(":")
        channel_id = int(data_parts[1])
        last_msg_id = int(data_parts[2])
        clone_id = data_parts[3]
        
        # Verify admin access
        is_admin, clone_data = await verify_clone_admin(client, query.from_user.id)
        if not is_admin:
            await query.edit_message_text("❌ Access denied.")
            return
        
        # Quick scan (sample 100 messages)
        scan_results = {
            "total_scanned": 0,
            "media_files": 0,
            "file_types": {},
            "total_size": 0,
            "sample_files": []
        }
        
        scan_limit = min(100, last_msg_id)
        
        async for message in client.iter_messages(channel_id, limit=scan_limit):
            scan_results["total_scanned"] += 1
            
            if message.media and message.media in [
                enums.MessageMediaType.VIDEO,
                enums.MessageMediaType.AUDIO, 
                enums.MessageMediaType.DOCUMENT,
                enums.MessageMediaType.PHOTO
            ]:
                scan_results["media_files"] += 1
                
                media = getattr(message, message.media.value, None)
                if media:
                    file_type = message.media.value
                    file_size = getattr(media, 'file_size', 0)
                    file_name = getattr(media, 'file_name', f"File_{message.id}")
                    
                    scan_results["file_types"][file_type] = scan_results["file_types"].get(file_type, 0) + 1
                    scan_results["total_size"] += file_size
                    
                    if len(scan_results["sample_files"]) < 5:
                        scan_results["sample_files"].append({
                            "name": file_name,
                            "type": file_type,
                            "size": file_size
                        })
        
        # Format results
        scan_text = (
            f"📊 **Quick Scan Results**\n\n"
            f"🔍 **Scanned**: {scan_results['total_scanned']}/{scan_limit} messages\n"
            f"📁 **Media Files**: {scan_results['media_files']}\n"
            f"📊 **Total Size**: {get_readable_size(scan_results['total_size'])}\n\n"
            
            f"**File Types:**\n"
        )
        
        for file_type, count in scan_results["file_types"].items():
            scan_text += f"• {file_type.title()}: {count}\n"
        
        if scan_results["sample_files"]:
            scan_text += f"\n**Sample Files:**\n"
            for i, file_info in enumerate(scan_results["sample_files"], 1):
                scan_text += f"{i}. {file_info['name'][:30]}{'...' if len(file_info['name']) > 30 else ''}\n"
        
        # Estimate for full channel
        if scan_results["total_scanned"] > 0:
            media_ratio = scan_results["media_files"] / scan_results["total_scanned"]
            estimated_media = int(last_msg_id * media_ratio)
            estimated_size = scan_results["total_size"] * (last_msg_id / scan_results["total_scanned"])
            
            scan_text += (
                f"\n**Full Channel Estimates:**\n"
                f"📁 Estimated Media: ~{estimated_media:,} files\n"
                f"📊 Estimated Size: ~{get_readable_size(estimated_size)}\n"
            )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Proceed with Indexing", 
                                   callback_data=f"start_index:{channel_id}:{last_msg_id}:{clone_id}")
            ],
            [
                InlineKeyboardButton("🔄 New Scan", callback_data=f"quick_scan:{channel_id}:{last_msg_id}:{clone_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="close")
            ]
        ])
        
        await query.edit_message_text(scan_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in quick scan: {e}")
        await query.answer("❌ Error during scan.", show_alert=True)

def get_readable_size(size_bytes: int) -> str:
    """Convert bytes to readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"

@Client.on_message(filters.command(['indexstats']) & filters.private)
async def clone_index_stats_command(client: Client, message: Message):
    """Show indexing statistics"""
    try:
        is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
        if not is_admin:
            await message.reply_text("❌ Access denied.")
            return
        
        clone_id = get_clone_id_from_client(client)
        
        # Get statistics from database
        try:
            clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
            clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
            files_collection = clone_db['files']
            
            # Get comprehensive stats
            total_files = await files_collection.count_documents({})
            
            if total_files == 0:
                await message.reply_text("📊 **No indexed files found**\n\nUse `/index` command to start indexing.")
                return
            
            # Get file type distribution
            pipeline = [
                {"$group": {"_id": "$file_type", "count": {"$sum": 1}, "total_size": {"$sum": "$file_size"}}},
                {"$sort": {"count": -1}}
            ]
            
            file_types = await files_collection.aggregate(pipeline).to_list(length=None)
            
            # Get size statistics
            size_stats = await files_collection.aggregate([
                {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}, "avg_size": {"$avg": "$file_size"}}}
            ]).to_list(length=1)
            
            total_size = size_stats[0]["total_size"] if size_stats else 0
            avg_size = size_stats[0]["avg_size"] if size_stats else 0
            
            stats_text = (
                f"📊 **Clone Indexing Statistics**\n\n"
                f"🗄️ **Database**: `{clone_data.get('db_name')}`\n"
                f"🔢 **Total Files**: {total_files:,}\n"
                f"📊 **Total Size**: {get_readable_size(total_size)}\n"
                f"📈 **Average Size**: {get_readable_size(avg_size)}\n\n"
                
                f"**File Types Distribution:**\n"
            )
            
            for file_type in file_types:
                percentage = (file_type["count"] / total_files * 100) if total_files > 0 else 0
                stats_text += f"• {file_type['_id'].title()}: {file_type['count']} ({percentage:.1f}%)\n"
            
            clone_client.close()
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_stats:{clone_id}"),
                    InlineKeyboardButton("🔍 Search", callback_data=f"search_files:{clone_id}")
                ]
            ])
            
            await message.reply_text(stats_text, reply_markup=buttons)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.reply_text("❌ Error retrieving statistics.")
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error processing command.")

@Client.on_message(filters.command(['indexstatus']) & filters.private)
async def clone_index_status_command(client: Client, message: Message):
    """Show current indexing status"""
    try:
        is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
        if not is_admin:
            await message.reply_text("❌ Access denied.")
            return
        
        clone_id = get_clone_id_from_client(client)
        
        # Check if currently indexing
        if clone_id in indexing_progress:
            progress = indexing_progress[clone_id]
            await update_progress_message(message, clone_id, progress)
        else:
            status_text = (
                f"📊 **Indexing Status**\n\n"
                f"🔢 **Clone ID**: {clone_id}\n"
                f"📊 **Status**: No active indexing\n"
                f"🗄️ **Database**: `{clone_data.get('db_name')}`\n\n"
                
                f"**Commands:**\n"
                f"• `/index <channel>` - Start indexing\n"
                f"• `/indexstats` - View statistics\n"
                f"• `/search <query>` - Search files"
            )
            
            await message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await message.reply_text("❌ Error processing command.")
