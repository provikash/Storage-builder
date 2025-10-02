
import logging
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Store bulk indexing tasks
bulk_indexing_tasks = {}
bulk_progress = {}

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.command(['bulkindex', 'batchindex']) & filters.private)
async def bulk_index_command(client: Client, message: Message):
    """Bulk indexing command for multiple channels"""
    try:
        # Verify admin access
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await message.reply_text("❌ This command is only available in clone bots.")
            return
        
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != message.from_user.id:
            await message.reply_text("❌ Only clone admin can use bulk indexing.")
            return
        
        clone_id = get_clone_id_from_client(client)
        
        if len(message.command) < 2:
            help_text = (
                "📚 **Bulk Indexing System**\n\n"
                "**Usage:**\n"
                "`/bulkindex <channel1> <channel2> <channel3>...`\n\n"
                
                "**Supported Formats:**\n"
                "• Channel usernames: `@channel1 @channel2`\n"
                "• Channel IDs: `-1001234 -1005678`\n"
                "• Mixed format: `@channel1 -1001234`\n\n"
                
                "**Example:**\n"
                "`/bulkindex @movies @series @documentaries`\n\n"
                
                "**Features:**\n"
                "✅ Parallel processing\n"
                "✅ Individual channel progress\n"
                "✅ Error recovery per channel\n"
                "✅ Batch completion summary\n\n"
                
                "⚠️ **Note**: Large batch operations may take considerable time."
            )
            await message.reply_text(help_text)
            return
        
        # Parse channel list
        channels = message.command[1:]
        await process_bulk_index_request(client, message, channels, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error in bulk index command: {e}")
        await message.reply_text("❌ Error processing bulk index request.")

async def process_bulk_index_request(client: Client, message: Message, channels: list, clone_id: str, clone_data: dict):
    """Process bulk indexing request"""
    try:
        # Validate channels
        channel_info = []
        invalid_channels = []
        
        for channel in channels:
            try:
                if channel.startswith('@'):
                    username = channel[1:]
                    chat = await client.get_chat(username)
                    channel_id = chat.id
                elif channel.lstrip('-').isdigit():
                    channel_id = int(channel)
                    chat = await client.get_chat(channel_id)
                else:
                    invalid_channels.append(channel)
                    continue
                
                # Get latest message ID
                async for latest_msg in client.iter_messages(channel_id, limit=1):
                    last_msg_id = latest_msg.id
                    break
                else:
                    invalid_channels.append(f"{channel} (empty)")
                    continue
                
                channel_info.append({
                    "id": channel_id,
                    "title": chat.title,
                    "username": f"@{chat.username}" if chat.username else "Private",
                    "last_msg_id": last_msg_id,
                    "input": channel
                })
                
            except Exception as e:
                invalid_channels.append(f"{channel} ({str(e)[:20]})")
        
        if not channel_info:
            await message.reply_text("❌ **No valid channels found**\n\nPlease check your channel list and try again.")
            return
        
        # Show confirmation
        confirmation_text = f"📋 **Bulk Indexing Confirmation**\n\n"
        confirmation_text += f"**Valid Channels ({len(channel_info)}):**\n"
        
        total_messages = 0
        for i, ch in enumerate(channel_info[:10], 1):  # Show first 10
            confirmation_text += f"{i}. {ch['title']} ({ch['username']})\n"
            confirmation_text += f"   📊 ~{ch['last_msg_id']:,} messages\n"
            total_messages += ch['last_msg_id']
        
        if len(channel_info) > 10:
            confirmation_text += f"   ... and {len(channel_info) - 10} more channels\n"
        
        confirmation_text += f"\n**Total Estimated Messages:** {total_messages:,}\n"
        confirmation_text += f"**Clone Database:** `{clone_data.get('db_name')}`\n"
        
        if invalid_channels:
            confirmation_text += f"\n**Invalid Channels ({len(invalid_channels)}):**\n"
            for inv in invalid_channels[:5]:
                confirmation_text += f"• {inv}\n"
            if len(invalid_channels) > 5:
                confirmation_text += f"   ... and {len(invalid_channels) - 5} more\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Start Bulk Indexing", 
                                   callback_data=f"start_bulk:{clone_id}"),
                InlineKeyboardButton("📊 Quick Analysis", 
                                   callback_data=f"bulk_analysis:{clone_id}")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", 
                                   callback_data=f"bulk_settings:{clone_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="close")
            ]
        ])
        
        # Store channel info for callback
        bulk_progress[clone_id] = {
            "channels": channel_info,
            "status": "pending",
            "completed": 0,
            "total_channels": len(channel_info),
            "start_time": None,
            "parallel_limit": 3,
            "current_batch": []
        }
        
        await message.reply_text(confirmation_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error processing bulk request: {e}")
        await message.reply_text("❌ Error processing request.")

@Client.on_callback_query(filters.regex("^start_bulk:"))
async def handle_start_bulk_index(client: Client, query: CallbackQuery):
    """Start bulk indexing process"""
    try:
        await query.answer("Starting bulk indexing...", show_alert=False)
        
        clone_id = query.data.split(":")[1]
        
        # Verify admin access
        bot_token = getattr(client, 'bot_token')
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != query.from_user.id:
            await query.edit_message_text("❌ Access denied.")
            return
        
        if clone_id not in bulk_progress:
            await query.edit_message_text("❌ Bulk indexing session expired. Please start again.")
            return
        
        # Initialize bulk progress
        progress = bulk_progress[clone_id]
        progress["status"] = "running"
        progress["start_time"] = datetime.now()
        progress["completed"] = 0
        progress["failed"] = 0
        progress["results"] = []
        
        # Show initial progress
        progress_text = (
            f"🔄 **Bulk Indexing Started**\n\n"
            f"📊 **Channels**: {progress['total_channels']}\n"
            f"📈 **Parallel Limit**: {progress['parallel_limit']}\n"
            f"🗄️ **Database**: {clone_data.get('db_name')}\n"
            f"⏱️ **Started**: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"**Status**: Initializing parallel tasks..."
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Progress", callback_data=f"bulk_progress:{clone_id}"),
                InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_bulk:{clone_id}")
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data=f"stop_bulk:{clone_id}")
            ]
        ])
        
        await query.edit_message_text(progress_text, reply_markup=buttons)
        
        # Start bulk indexing task
        task = asyncio.create_task(run_bulk_indexing(client, query.message, clone_id, clone_data))
        bulk_indexing_tasks[clone_id] = task
        
    except Exception as e:
        logger.error(f"Error starting bulk indexing: {e}")
        await query.answer("❌ Error starting bulk indexing.", show_alert=True)

async def run_bulk_indexing(client: Client, msg: Message, clone_id: str, clone_data: dict):
    """Run bulk indexing with parallel processing"""
    try:
        progress = bulk_progress[clone_id]
        channels = progress["channels"]
        parallel_limit = progress["parallel_limit"]
        
        # Process channels in batches
        for i in range(0, len(channels), parallel_limit):
            if progress.get("stop_requested"):
                break
            
            # Get current batch
            batch = channels[i:i + parallel_limit]
            progress["current_batch"] = [ch["title"] for ch in batch]
            
            # Create tasks for parallel processing
            tasks = []
            for channel in batch:
                task = asyncio.create_task(
                    index_single_channel_bulk(client, channel, clone_id, clone_data)
                )
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                channel = batch[j]
                if isinstance(result, Exception):
                    progress["failed"] += 1
                    progress["results"].append({
                        "channel": channel["title"],
                        "status": "failed",
                        "error": str(result),
                        "indexed": 0
                    })
                else:
                    progress["completed"] += 1
                    progress["results"].append({
                        "channel": channel["title"],
                        "status": "completed",
                        "indexed": result.get("indexed", 0),
                        "duplicates": result.get("duplicates", 0),
                        "errors": result.get("errors", 0)
                    })
            
            # Update progress
            await update_bulk_progress(msg, clone_id)
            
            # Small delay between batches
            if i + parallel_limit < len(channels):
                await asyncio.sleep(2)
        
        # Finalize
        progress["status"] = "completed"
        progress["end_time"] = datetime.now()
        await finalize_bulk_indexing(msg, clone_id)
        
    except Exception as e:
        logger.error(f"Error in bulk indexing: {e}")
        progress["status"] = "failed"
        progress["error"] = str(e)
    finally:
        # Cleanup
        if clone_id in bulk_indexing_tasks:
            del bulk_indexing_tasks[clone_id]

async def index_single_channel_bulk(client: Client, channel: dict, clone_id: str, clone_data: dict):
    """Index a single channel as part of bulk operation"""
    try:
        channel_id = channel["id"]
        last_msg_id = channel["last_msg_id"]
        
        # Connect to database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
        files_collection = clone_db['files']
        
        result = {
            "indexed": 0,
            "duplicates": 0,
            "errors": 0,
            "processed": 0
        }
        
        # Index messages with simplified logic for bulk
        async for message in client.iter_messages(channel_id, last_msg_id):
            result["processed"] += 1
            
            # Check for media
            if not message.media or message.media not in [
                enums.MessageMediaType.VIDEO,
                enums.MessageMediaType.AUDIO, 
                enums.MessageMediaType.DOCUMENT,
                enums.MessageMediaType.PHOTO
            ]:
                continue
            
            try:
                # Extract basic file info
                media = getattr(message, message.media.value, None)
                if not media:
                    continue
                
                file_id = getattr(media, 'file_id', None)
                if not file_id:
                    continue
                
                file_name = getattr(media, 'file_name', f"File_{message.id}")
                file_size = getattr(media, 'file_size', 0)
                file_type = message.media.value
                
                # Simplified document structure for bulk indexing
                file_doc = {
                    "file_id": file_id,
                    "message_id": message.id,
                    "chat_id": channel_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "caption": message.caption or '',
                    "indexed_at": datetime.now(),
                    "clone_id": clone_id,
                    "bulk_indexed": True
                }
                
                # Insert with duplicate handling
                try:
                    await files_collection.insert_one(file_doc)
                    result["indexed"] += 1
                except:
                    result["duplicates"] += 1
                
            except Exception as e:
                result["errors"] += 1
                logger.error(f"Error indexing message {message.id}: {e}")
            
            # Rate limiting for bulk
            if result["processed"] % 100 == 0:
                await asyncio.sleep(0.5)
        
        clone_client.close()
        return result
        
    except Exception as e:
        logger.error(f"Error indexing channel {channel['title']}: {e}")
        raise e

async def update_bulk_progress(msg: Message, clone_id: str):
    """Update bulk indexing progress"""
    try:
        progress = bulk_progress[clone_id]
        
        elapsed = (datetime.now() - progress["start_time"]).total_seconds()
        completion_rate = (progress["completed"] + progress["failed"]) / progress["total_channels"]
        
        progress_text = (
            f"🔄 **Bulk Indexing Progress**\n\n"
            f"📊 **Channels**: {progress['completed'] + progress['failed']} / {progress['total_channels']}\n"
            f"✅ **Completed**: {progress['completed']}\n"
            f"❌ **Failed**: {progress['failed']}\n"
            f"📈 **Progress**: {completion_rate * 100:.1f}%\n\n"
            
            f"⏱️ **Elapsed**: {int(elapsed // 60)}m {int(elapsed % 60)}s\n"
        )
        
        if progress["current_batch"]:
            progress_text += f"🔄 **Current Batch**:\n"
            for ch in progress["current_batch"][:3]:
                progress_text += f"• {ch}\n"
        
        # Show recent results
        if progress["results"]:
            progress_text += f"\n**Recent Results**:\n"
            for result in progress["results"][-3:]:
                status_emoji = "✅" if result["status"] == "completed" else "❌"
                progress_text += f"{status_emoji} {result['channel']}: {result.get('indexed', 0)} files\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"bulk_progress:{clone_id}"),
                InlineKeyboardButton("📋 Full Report", callback_data=f"bulk_report:{clone_id}")
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data=f"stop_bulk:{clone_id}")
            ]
        ])
        
        await msg.edit_text(progress_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error updating bulk progress: {e}")

async def finalize_bulk_indexing(msg: Message, clone_id: str):
    """Finalize bulk indexing and show summary"""
    try:
        progress = bulk_progress[clone_id]
        elapsed = (progress.get("end_time", datetime.now()) - progress["start_time"]).total_seconds()
        
        # Calculate totals
        total_indexed = sum(r.get("indexed", 0) for r in progress["results"])
        total_duplicates = sum(r.get("duplicates", 0) for r in progress["results"])
        total_errors = sum(r.get("errors", 0) for r in progress["results"])
        
        summary_text = (
            f"✅ **Bulk Indexing Complete**\n\n"
            f"📊 **Summary**:\n"
            f"🏆 **Total Channels**: {progress['total_channels']}\n"
            f"✅ **Successful**: {progress['completed']}\n"
            f"❌ **Failed**: {progress['failed']}\n"
            f"⏱️ **Total Time**: {int(elapsed // 60)}m {int(elapsed % 60)}s\n\n"
            
            f"📁 **Files**:\n"
            f"✅ **Indexed**: {total_indexed:,}\n"
            f"🔁 **Duplicates**: {total_duplicates:,}\n"
            f"❌ **Errors**: {total_errors:,}\n\n"
            
            f"🎉 **All indexed files are now searchable!**"
        )
        
        # Show detailed results
        if progress["results"]:
            summary_text += f"\n\n**Channel Results**:\n"
            for result in progress["results"][:10]:
                status_emoji = "✅" if result["status"] == "completed" else "❌"
                summary_text += f"{status_emoji} {result['channel']}: {result.get('indexed', 0)} files\n"
            
            if len(progress["results"]) > 10:
                summary_text += f"... and {len(progress['results']) - 10} more channels\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Full Report", callback_data=f"bulk_report:{clone_id}"),
                InlineKeyboardButton("📊 Stats", callback_data=f"clone_stats:{clone_id}")
            ],
            [
                InlineKeyboardButton("🔍 Search Files", callback_data=f"search_files:{clone_id}")
            ]
        ])
        
        await msg.edit_text(summary_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error finalizing bulk indexing: {e}")

@Client.on_callback_query(filters.regex("^bulk_progress:"))
async def handle_bulk_progress(client: Client, query: CallbackQuery):
    """Show bulk indexing progress"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in bulk_progress:
            await update_bulk_progress(query.message, clone_id)
            await query.answer()
        else:
            await query.answer("❌ No bulk indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error showing bulk progress: {e}")

@Client.on_callback_query(filters.regex("^bulk_report:"))
async def handle_bulk_report(client: Client, query: CallbackQuery):
    """Show detailed bulk indexing report"""
    try:
        clone_id = query.data.split(":")[1]
        
        if clone_id not in bulk_progress:
            await query.answer("❌ Report not available", show_alert=True)
            return
        
        progress = bulk_progress[clone_id]
        
        report_text = f"📋 **Detailed Bulk Indexing Report**\n\n"
        
        # Group results by status
        completed_channels = [r for r in progress["results"] if r["status"] == "completed"]
        failed_channels = [r for r in progress["results"] if r["status"] == "failed"]
        
        if completed_channels:
            report_text += f"✅ **Successful Channels ({len(completed_channels)})**:\n"
            for ch in completed_channels:
                report_text += f"• {ch['channel']}: {ch['indexed']} files"
                if ch.get('duplicates', 0) > 0:
                    report_text += f" ({ch['duplicates']} duplicates)"
                report_text += "\n"
        
        if failed_channels:
            report_text += f"\n❌ **Failed Channels ({len(failed_channels)})**:\n"
            for ch in failed_channels:
                report_text += f"• {ch['channel']}: {ch['error'][:50]}...\n"
        
        # Performance metrics
        if progress.get("start_time") and progress.get("end_time"):
            elapsed = (progress["end_time"] - progress["start_time"]).total_seconds()
            avg_time_per_channel = elapsed / len(progress["results"]) if progress["results"] else 0
            
            report_text += (
                f"\n📊 **Performance Metrics**:\n"
                f"• Average time per channel: {avg_time_per_channel:.1f}s\n"
                f"• Parallel processing limit: {progress.get('parallel_limit', 3)}\n"
            )
        
        await query.edit_message_text(report_text[:4000])  # Telegram message limit
        
    except Exception as e:
        logger.error(f"Error generating bulk report: {e}")
        await query.answer("❌ Error generating report", show_alert=True)

# Additional control callbacks
@Client.on_callback_query(filters.regex("^stop_bulk:"))
async def handle_stop_bulk(client: Client, query: CallbackQuery):
    """Stop bulk indexing"""
    try:
        clone_id = query.data.split(":")[1]
        if clone_id in bulk_progress:
            bulk_progress[clone_id]["stop_requested"] = True
            await query.answer("🛑 Bulk indexing will stop after current batch", show_alert=True)
        else:
            await query.answer("❌ No active bulk indexing found", show_alert=True)
    except Exception as e:
        logger.error(f"Error stopping bulk indexing: {e}")
