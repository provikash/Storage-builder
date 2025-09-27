
import logging
import asyncio
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient
import re

logger = logging.getLogger(__name__)

# Global state for bulk indexing
bulk_indexing_state = {}

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.command(['bulkindex', 'massindex', 'channelindex']) & filters.private)
async def bulk_index_channel_command(client: Client, message: Message):
    """Handle bulk indexing command for large channels"""
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
                "📚 **Bulk Channel Indexing**\n\n"
                "**Usage:** `/bulkindex <channel_username_or_id>`\n\n"
                "**Examples:**\n"
                "• `/bulkindex @mychannel`\n"
                "• `/bulkindex -1001234567890`\n\n"
                "**Features:**\n"
                "• Optimized for thousands of files\n"
                "• Batch processing to avoid timeouts\n"
                "• Resume capability if interrupted\n"
                "• Progress tracking\n\n"
                "**Note:** Bot must be admin in the channel."
            )
            return
        
        channel_identifier = message.command[1]
        
        # Try to get channel info
        try:
            chat = await client.get_chat(channel_identifier)
            
            # Check if bot is admin
            try:
                bot_member = await client.get_chat_member(chat.id, client.me.id)
                if bot_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                    await message.reply_text(
                        f"❌ **Access Required**\n\n"
                        f"Bot is not admin in **{chat.title}**\n"
                        f"Please add the bot as admin with message reading permissions."
                    )
                    return
            except Exception as e:
                await message.reply_text(
                    f"❌ **Access Error**\n\n"
                    f"Cannot check admin status: {str(e)}"
                )
                return
            
            # Get approximate message count
            try:
                # Get a recent message to estimate total messages
                latest_msg = None
                async for msg in client.iter_messages(chat.id, limit=1):
                    latest_msg = msg
                    break
                
                if not latest_msg:
                    await message.reply_text("❌ Channel appears to be empty.")
                    return
                
                estimated_total = latest_msg.id
                
                # Show confirmation with estimated stats
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🚀 Start Bulk Indexing", 
                                           callback_data=f"bulk_start:{chat.id}:{clone_id}")
                    ],
                    [
                        InlineKeyboardButton("⚙️ Advanced Options", 
                                           callback_data=f"bulk_options:{chat.id}:{clone_id}")
                    ],
                    [
                        InlineKeyboardButton("❌ Cancel", callback_data="close")
                    ]
                ])
                
                await message.reply_text(
                    f"📊 **Bulk Indexing Preview**\n\n"
                    f"**Channel:** {chat.title}\n"
                    f"**Channel ID:** `{chat.id}`\n"
                    f"**Estimated Messages:** ~{estimated_total:,}\n"
                    f"**Clone ID:** `{clone_id}`\n\n"
                    f"🔥 **Bulk Mode Features:**\n"
                    f"• Processes 100 messages per batch\n"
                    f"• 2-second delay between batches\n"
                    f"• Auto-resume on disconnection\n"
                    f"• Real-time progress updates\n\n"
                    f"⚠️ **Note:** This may take several hours for large channels.",
                    reply_markup=buttons
                )
                
            except Exception as e:
                await message.reply_text(f"❌ Error getting channel info: {str(e)}")
                return
                
        except ChannelInvalid:
            await message.reply_text("❌ Cannot access this channel. Make sure the bot is added as admin.")
            return
        except Exception as e:
            await message.reply_text(f"❌ Error accessing channel: {str(e)}")
            return
        
    except Exception as e:
        logger.error(f"Error in bulk index command: {e}")
        await message.reply_text("❌ Error processing bulk index request.")

@Client.on_callback_query(filters.regex("^bulk_start:"))
async def handle_bulk_start(client: Client, query):
    """Handle bulk indexing start"""
    try:
        await query.answer("Starting bulk indexing...", show_alert=False)
        
        _, chat_id, clone_id = query.data.split(":")
        chat_id = int(chat_id)
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found.")
            return
        
        # Initialize bulk indexing state
        bulk_indexing_state[clone_id] = {
            "cancel": False,
            "processed": 0,
            "indexed": 0,
            "duplicates": 0,
            "errors": 0,
            "last_msg_id": 0,
            "batch_size": 100,
            "batch_delay": 2
        }
        
        await query.edit_message_text(
            "🔄 **Initializing Bulk Indexing**\n\n"
            "Setting up optimized batch processing...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"bulk_cancel:{clone_id}")]
            ])
        )
        
        # Start bulk indexing process
        await start_bulk_indexing(client, query.message, chat_id, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error starting bulk indexing: {e}")
        await query.answer("❌ Error starting bulk indexing.", show_alert=True)

@Client.on_callback_query(filters.regex("^bulk_cancel:"))
async def handle_bulk_cancel(client: Client, query):
    """Handle bulk indexing cancellation"""
    try:
        clone_id = query.data.split(":")[1]
        
        if clone_id in bulk_indexing_state:
            bulk_indexing_state[clone_id]["cancel"] = True
        
        await query.answer("Cancelling bulk indexing...", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error cancelling bulk indexing: {e}")

async def start_bulk_indexing(client: Client, message: Message, chat_id: int, clone_id: str, clone_data: dict):
    """Start the optimized bulk indexing process"""
    state = bulk_indexing_state[clone_id]
    
    try:
        # Get MongoDB connection for this clone
        mongodb_url = clone_data.get('mongodb_url')
        if not mongodb_url:
            await message.edit_text("❌ No MongoDB URL configured for this clone.")
            return
        
        clone_client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000
        )
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
        files_collection = clone_db.files
        
        # Test connection
        await clone_client.admin.command('ping')
        
        # Get the latest message ID to start from
        latest_msg = None
        async for msg in client.iter_messages(chat_id, limit=1):
            latest_msg = msg
            break
        
        if not latest_msg:
            await message.edit_text("❌ No messages found in channel.")
            return
        
        total_messages = latest_msg.id
        current_msg_id = total_messages
        
        await message.edit_text(
            f"🚀 **Bulk Indexing Started**\n\n"
            f"📊 **Total Messages**: ~{total_messages:,}\n"
            f"📦 **Batch Size**: {state['batch_size']}\n"
            f"⏱️ **Batch Delay**: {state['batch_delay']}s\n\n"
            f"📈 **Progress**: 0%\n"
            f"✅ **Indexed**: 0\n"
            f"🔄 **Processed**: 0\n\n"
            f"⚡ Processing in progress...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"bulk_cancel:{clone_id}")]
            ])
        )
        
        batch_count = 0
        last_update = datetime.now()
        
        # Process messages in batches
        while current_msg_id > 0 and not state["cancel"]:
            try:
                # Process a batch of messages
                batch_messages = []
                batch_start_id = max(1, current_msg_id - state['batch_size'] + 1)
                
                # Get messages in current batch
                async for msg in client.iter_messages(
                    chat_id, 
                    offset_id=current_msg_id + 1,
                    limit=state['batch_size']
                ):
                    if msg.id < batch_start_id:
                        break
                    batch_messages.append(msg)
                
                if not batch_messages:
                    break
                
                # Process batch
                batch_indexed = await process_message_batch(
                    batch_messages, files_collection, clone_id, state
                )
                
                state["indexed"] += batch_indexed
                state["processed"] += len(batch_messages)
                
                # Update progress every 10 batches or every 2 minutes
                batch_count += 1
                now = datetime.now()
                
                if batch_count % 10 == 0 or (now - last_update).seconds > 120:
                    progress = (state["processed"] / total_messages) * 100
                    
                    await message.edit_text(
                        f"🚀 **Bulk Indexing in Progress**\n\n"
                        f"📊 **Total Messages**: ~{total_messages:,}\n"
                        f"📈 **Progress**: {progress:.1f}%\n\n"
                        f"✅ **Files Indexed**: {state['indexed']:,}\n"
                        f"🔄 **Messages Processed**: {state['processed']:,}\n"
                        f"📋 **Duplicates Skipped**: {state['duplicates']:,}\n"
                        f"❌ **Errors**: {state['errors']:,}\n\n"
                        f"🏃‍♂️ **Current Batch**: {batch_count:,}\n"
                        f"⚡ **Processing**: Batch {current_msg_id-state['batch_size']+1} to {current_msg_id}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🛑 Cancel", callback_data=f"bulk_cancel:{clone_id}")]
                        ])
                    )
                    last_update = now
                
                # Move to next batch
                current_msg_id -= state['batch_size']
                
                # Delay between batches to avoid rate limits
                await asyncio.sleep(state['batch_delay'])
                
            except FloodWait as e:
                logger.warning(f"FloodWait: {e.x} seconds")
                await asyncio.sleep(e.x)
                continue
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                state["errors"] += 1
                current_msg_id -= state['batch_size']
                await asyncio.sleep(5)
                continue
        
        # Final status
        if state["cancel"]:
            status_emoji = "⏹️"
            status_text = "Cancelled"
        else:
            status_emoji = "✅"
            status_text = "Completed"
        
        final_progress = (state["processed"] / total_messages) * 100
        
        await message.edit_text(
            f"{status_emoji} **Bulk Indexing {status_text}**\n\n"
            f"📊 **Final Statistics**:\n"
            f"✅ **Files Indexed**: {state['indexed']:,}\n"
            f"🔄 **Messages Processed**: {state['processed']:,}\n"
            f"📋 **Duplicates Skipped**: {state['duplicates']:,}\n"
            f"❌ **Errors**: {state['errors']:,}\n"
            f"📈 **Progress**: {final_progress:.1f}%\n\n"
            f"🎉 **Channel indexing {'completed' if not state['cancel'] else 'was cancelled'}!**\n"
            f"💡 Use `/search <query>` to find your files."
        )
        
        # Cleanup
        clone_client.close()
        if clone_id in bulk_indexing_state:
            del bulk_indexing_state[clone_id]
        
    except Exception as e:
        logger.error(f"Error in bulk indexing: {e}")
        await message.edit_text(f"❌ **Bulk Indexing Failed**\n\nError: {str(e)}")
        
        # Cleanup
        if clone_id in bulk_indexing_state:
            del bulk_indexing_state[clone_id]

async def process_message_batch(messages: list, files_collection, clone_id: str, state: dict):
    """Process a batch of messages and index media files"""
    indexed_count = 0
    
    try:
        batch_operations = []
        
        for msg in messages:
            try:
                # Check if message has media
                if not msg.media:
                    continue
                elif msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, 
                                     enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
                    continue
                
                media = getattr(msg, msg.media.value, None)
                if not media:
                    continue
                
                # Extract file information
                file_name = getattr(media, 'file_name', None) or msg.caption or f"File_{msg.id}"
                file_size = getattr(media, 'file_size', 0)
                file_type = msg.media.value
                caption = msg.caption or ''
                file_id = getattr(media, 'file_id', str(msg.id))
                
                # Create unique file ID
                unique_file_id = f"{msg.chat.id}_{msg.id}"
                
                # Prepare document for bulk insert
                file_doc = {
                    "_id": unique_file_id,
                    "file_id": file_id,
                    "message_id": msg.id,
                    "chat_id": msg.chat.id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "caption": caption,
                    "user_id": msg.from_user.id if msg.from_user else 0,
                    "date": msg.date,
                    "clone_id": clone_id,
                    "indexed_at": datetime.utcnow()
                }
                
                # Add to batch operations (upsert to handle duplicates)
                batch_operations.append({
                    "replaceOne": {
                        "filter": {"_id": unique_file_id},
                        "replacement": file_doc,
                        "upsert": True
                    }
                })
                
            except Exception as e:
                logger.error(f"Error processing message {msg.id}: {e}")
                state["errors"] += 1
                continue
        
        # Execute batch operations
        if batch_operations:
            result = await files_collection.bulk_write(batch_operations, ordered=False)
            indexed_count = result.upserted_count + result.modified_count
            state["duplicates"] += len(batch_operations) - indexed_count
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        state["errors"] += len(messages)
    
    return indexed_count
