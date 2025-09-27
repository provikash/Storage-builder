# Auto-index forwarded media messages
import logging
import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient

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

        # Try to auto-index the message
        success = await auto_index_forwarded_message(client, message, clone_id, clone_data)

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

@Client.on_message(filters.command(['autoindex', 'toggleautoindex']) & filters.private)
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

            # Start indexing process
            await start_channel_indexing(client, message, chat.id, last_msg_id, clone_id, clone_data)

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

# Indexing functionality implementation
class IndexTemp:
    """Temporary storage for indexing state per clone"""
    def __init__(self):
        self.states = {}  # clone_id -> {"current": 0, "cancel": False}

    def get_state(self, clone_id):
        if clone_id not in self.states:
            self.states[clone_id] = {"current": 0, "cancel": False}
        return self.states[clone_id]

    def set_cancel(self, clone_id, value=True):
        state = self.get_state(clone_id)
        state["cancel"] = value

    def set_current(self, clone_id, value):
        state = self.get_state(clone_id)
        state["current"] = value

# Global indexing state manager
temp = IndexTemp()

async def auto_index_forwarded_message(client: Client, message: Message, clone_id: str, clone_data: dict):
    """Auto-index a single forwarded message"""
    try:
        # Check if message has media
        if not message.media:
            return False
        elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
            return False

        media = getattr(message, message.media.value, None)
        if not media:
            return False

        # Extract file information
        file_name = getattr(media, 'file_name', None) or message.caption or f"File_{message.id}"
        file_size = getattr(media, 'file_size', 0)
        file_type = message.media.value
        caption = message.caption or ''

        # Create a unique file ID using message ID
        unique_file_id = f"auto_{message.id}"

        # Add to clone's specific database
        success = await add_to_clone_index(
            clone_data=clone_data,
            file_id=unique_file_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            caption=caption,
            user_id=message.from_user.id if message.from_user else 0
        )

        return success
    except Exception as e:
        logger.error(f"Error auto-indexing forwarded message: {e}")
        return False

async def start_channel_indexing(client: Client, message: Message, chat_id: int, last_msg_id: int, clone_id: str, clone_data: dict):
    """Start indexing a channel from the latest message backwards"""
    try:
        # Reset indexing state for this clone
        temp.set_cancel(clone_id, False)
        temp.set_current(clone_id, 0)

        # Show initial status message
        status_msg = await message.reply_text(
            "🔄 **Starting Channel Indexing...**\n\n"
            f"📺 **Channel**: `{chat_id}`\n"
            f"📝 **Latest Message ID**: `{last_msg_id}`\n\n"
            "This may take some time. Please wait...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('❌ Cancel', callback_data=f'cancel_index_{clone_id}')]
            ])
        )

        # Start the indexing process
        await index_channel_files_to_db(last_msg_id, chat_id, status_msg, client, clone_id, clone_data)

    except Exception as e:
        logger.error(f"Error starting channel indexing: {e}")
        await message.reply_text(f"❌ Error starting indexing: {str(e)}")

async def index_channel_files_to_db(last_msg_id: int, chat_id: int, status_msg: Message, client: Client, clone_id: str, clone_data: dict):
    """Index all files in a channel to the clone's database"""
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    state = temp.get_state(clone_id)
    current = state["current"]

    try:
        # Start from the latest message and work backwards
        while not state["cancel"]:
            try:
                # Calculate the message ID to fetch
                fetch_msg_id = last_msg_id - current

                if fetch_msg_id <= 0:
                    break

                # Try to get the message
                try:
                    msg = await client.get_messages(chat_id, fetch_msg_id)
                except:
                    current += 1
                    temp.set_current(clone_id, current)
                    deleted += 1
                    continue

                if not msg or msg.empty:
                    current += 1
                    temp.set_current(clone_id, current)
                    deleted += 1
                    continue

                current += 1
                temp.set_current(clone_id, current)

                # Update status every 20 messages
                if current % 20 == 0:
                    try:
                        await status_msg.edit_text(
                            f"🔄 **Indexing in Progress...**\n\n"
                            f"📺 **Channel**: `{chat_id}`\n"
                            f"📊 **Messages Processed**: `{current}`\n"
                            f"✅ **Files Indexed**: `{total_files}`\n"
                            f"🔄 **Duplicates Skipped**: `{duplicate}`\n"
                            f"❌ **Deleted Messages**: `{deleted}`\n"
                            f"📄 **Non-Media Skipped**: `{no_media + unsupported}`\n"
                            f"⚠️ **Errors**: `{errors}`",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton('❌ Cancel', callback_data=f'cancel_index_{clone_id}')]
                            ])
                        )
                    except:
                        pass  # If edit fails, continue indexing

                # Check if message has media
                if not msg.media:
                    no_media += 1
                    continue
                elif msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue

                media = getattr(msg, msg.media.value, None)
                if not media:
                    unsupported += 1
                    continue

                # Extract file information
                file_name = getattr(media, 'file_name', None) or msg.caption or f"File_{msg.id}"
                file_size = getattr(media, 'file_size', 0)
                file_type = msg.media.value
                caption = msg.caption or ''

                try:
                    # Create a unique file ID using chat and message ID
                    unique_file_id = f"{chat_id}_{msg.id}"

                    # Add to clone's specific database
                    success = await add_to_clone_index(
                        clone_data=clone_data,
                        file_id=unique_file_id,
                        file_name=file_name,
                        file_type=file_type,
                        file_size=file_size,
                        caption=caption,
                        user_id=msg.from_user.id if msg.from_user else 0
                    )

                    if success:
                        total_files += 1
                    else:
                        duplicate += 1

                except Exception as e:
                    logger.exception(f"Error indexing file {msg.id}: {e}")
                    errors += 1

            except FloodWait as e:
                await asyncio.sleep(e.x)
                continue
            except Exception as e:
                logger.exception(f"Error processing message: {e}")
                errors += 1
                continue

    except Exception as e:
        logger.exception(f"Fatal error in indexing: {e}")
        await status_msg.edit_text(f'❌ **Indexing Failed**\n\nError: {e}')
        return

    # Final status update
    if state["cancel"]:
        await status_msg.edit_text(
            f"⏹️ **Indexing Cancelled**\n\n"
            f"📊 **Final Results**:\n"
            f"✅ **Files Indexed**: `{total_files}`\n"
            f"📄 **Messages Processed**: `{current}`\n"
            f"🔄 **Duplicates Skipped**: `{duplicate}`\n"
            f"❌ **Deleted Messages**: `{deleted}`\n"
            f"📄 **Non-Media Skipped**: `{no_media + unsupported}`\n"
            f"⚠️ **Errors**: `{errors}`"
        )
    else:
        await status_msg.edit_text(
            f"✅ **Indexing Completed Successfully!**\n\n"
            f"📊 **Final Results**:\n"
            f"✅ **Files Indexed**: `{total_files}`\n"
            f"📄 **Messages Processed**: `{current}`\n"
            f"🔄 **Duplicates Skipped**: `{duplicate}`\n"
            f"❌ **Deleted Messages**: `{deleted}`\n"
            f"📄 **Non-Media Skipped**: `{no_media + unsupported}`\n"
            f"⚠️ **Errors**: `{errors}`\n\n"
            f"🎉 All files from the channel have been indexed to your clone's database!"
        )

async def add_to_clone_index(clone_data: dict, file_id: str, file_name: str, file_type: str, file_size: int, caption: str, user_id: int):
    """Add file to clone's specific MongoDB database"""
    try:
        # Get MongoDB URL for this clone
        mongodb_url = clone_data.get('mongodb_url')
        if not mongodb_url:
            logger.error(f"No MongoDB URL found for clone {clone_data.get('_id')}")
            return False

        # Connect to clone's specific database with better settings
        clone_client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db.files

        # Create file document
        file_doc = {
            "_id": file_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "caption": caption,
            "user_id": user_id,
            "indexed_at": asyncio.get_event_loop().time(),
            "clone_id": clone_data.get('_id')
        }

        # Insert file (will skip if duplicate due to _id)
        await files_collection.update_one(
            {"_id": file_id},
            {"$set": file_doc},
            upsert=True
        )

        # Close the connection
        clone_client.close()
        return True

    except Exception as e:
        logger.error(f"Error adding file to clone index: {e}")
        return False

# Add callback handler for canceling indexing
@Client.on_callback_query(filters.regex(r'^cancel_index_'))
async def handle_cancel_indexing(client: Client, query):
    """Handle canceling indexing operation"""
    try:
        # Extract clone ID from callback data
        clone_id = query.data.split('_')[-1]

        # Get clone data to verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            return await query.answer("❌ Clone configuration not found.", show_alert=True)

        # Check if user is admin of this clone
        if query.from_user.id != clone_data['admin_id']:
            return await query.answer("❌ Only clone admin can cancel indexing.", show_alert=True)

        # Set cancel flag
        temp.set_cancel(clone_id, True)

        await query.answer("⏹️ Indexing cancellation requested...", show_alert=True)
        await query.edit_message_text(
            "⏹️ **Cancelling Indexing...**\n\n"
            "Please wait while the current batch finishes processing."
        )

    except Exception as e:
        logger.error(f"Error cancelling indexing: {e}")
        await query.answer("❌ Error cancelling indexing.", show_alert=True)