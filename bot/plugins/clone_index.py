
import logging
import asyncio
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

@Client.on_message(filters.command(['index', 'cloneindex']) & filters.private)
async def clone_index_command(client: Client, message: Message):
    """Handle indexing command for clone bots"""
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
                "📚 **Clone Indexing**\n\n"
                "**Usage:** `/index <channel_link_or_forward_message>`\n\n"
                "**Examples:**\n"
                "• `/index https://t.me/channel/123`\n"
                "• Forward a message and use `/index`\n\n"
                "**Note:** Files will be indexed to your clone's database."
            )
            return
        
        # Handle channel link
        link = message.command[1]
        await process_clone_index_request(client, message, link, clone_id)
        
    except Exception as e:
        logger.error(f"Error in clone index command: {e}")
        await message.reply_text("❌ Error processing index request.")

async def process_clone_index_request(client: Client, message: Message, link: str, clone_id: str):
    """Process indexing request for clone"""
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
        
        try:
            await client.get_chat(chat_id)
        except ChannelInvalid:
            await message.reply_text("❌ Cannot access this channel. Make sure the bot is added as admin.")
            return
        except Exception as e:
            await message.reply_text(f"❌ Error accessing channel: {e}")
            return
        
        # Start indexing
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Indexing", callback_data=f"clone_start_index:{chat_id}:{last_msg_id}:{clone_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        await message.reply_text(
            f"📚 **Clone Indexing Request**\n\n"
            f"**Channel:** `{chat_id}`\n"
            f"**Last Message ID:** `{last_msg_id}`\n"
            f"**Clone ID:** `{clone_id}`\n\n"
            f"Files will be indexed to your clone's database.\n"
            f"Proceed with indexing?",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error processing clone index request: {e}")
        await message.reply_text("❌ Error processing request.")

@Client.on_callback_query(filters.regex("^clone_start_index:"))
async def handle_clone_start_index(client: Client, query):
    """Handle clone indexing start"""
    try:
        await query.answer("Starting indexing...", show_alert=True)
        
        _, chat_id, last_msg_id, clone_id = query.data.split(":")
        chat_id = int(chat_id)
        last_msg_id = int(last_msg_id)
        
        # Initialize indexing state
        clone_index_temp[clone_id] = {
            "cancel": False,
            "current": 0
        }
        
        await query.edit_message_text(
            "🔄 **Starting Clone Indexing**\n\n"
            "Indexing files to your clone's database...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")]
            ])
        )
        
        # Start indexing process
        await index_clone_files(client, query.message, chat_id, last_msg_id, clone_id)
        
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

async def index_clone_files(client: Client, msg: Message, chat_id: int, last_msg_id: int, clone_id: str):
    """Index files for a specific clone"""
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = 0
    
    try:
        async for message in client.iter_messages(chat_id, last_msg_id):
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
            
            current += 1
            clone_index_temp[clone_id]["current"] = current
            
            if current % 50 == 0:
                await msg.edit_text(
                    f"🔄 **Clone Indexing Progress**\n\n"
                    f"📊 Messages fetched: `{current}`\n"
                    f"✅ Files saved: `{total_files}`\n"
                    f"📋 Duplicates: `{duplicate}`\n"
                    f"🗑️ Deleted: `{deleted}`\n"
                    f"📄 Non-media: `{no_media + unsupported}`\n"
                    f"❌ Errors: `{errors}`",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛑 Cancel", callback_data=f"clone_cancel_index:{clone_id}")]
                    ])
                )
            
            if message.empty:
                deleted += 1
                continue
            elif not message.media:
                no_media += 1
                continue
            elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                unsupported += 1
                continue
            
            media = getattr(message, message.media.value, None)
            if not media:
                unsupported += 1
                continue
            
            # Extract file information
            file_name = getattr(media, 'file_name', None) or message.caption or f"File_{message.id}"
            file_size = getattr(media, 'file_size', 0)
            file_type = message.media.value
            caption = message.caption or ''
            
            try:
                # Add to clone's database
                file_data = {
                    "file_id": str(message.id),
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "caption": caption,
                    "user_id": message.from_user.id if message.from_user else 0,
                    "message_id": message.id,
                    "chat_id": chat_id
                }
                
                success = await add_file_to_clone_index(file_data, clone_id)
                if success:
                    total_files += 1
                else:
                    duplicate += 1
                    
            except Exception as e:
                logger.error(f"Error indexing file {message.id} for clone {clone_id}: {e}")
                errors += 1
        
        # Clean up temp data
        if clone_id in clone_index_temp:
            del clone_index_temp[clone_id]
        
        await msg.edit_text(
            f"✅ **Clone Indexing Complete**\n\n"
            f"📊 **Final Results:**\n"
            f"✅ Files saved: `{total_files}`\n"
            f"📋 Duplicates: `{duplicate}`\n"
            f"🗑️ Deleted: `{deleted}`\n"
            f"📄 Non-media: `{no_media + unsupported}`\n"
            f"❌ Errors: `{errors}`\n\n"
            f"Files are now available in your clone bot!"
        )
        
    except Exception as e:
        logger.error(f"Error indexing clone files: {e}")
        await msg.edit_text(f"❌ **Indexing Error**\n\nError: {str(e)}")
        
        # Clean up temp data
        if clone_id in clone_index_temp:
            del clone_index_temp[clone_id]
