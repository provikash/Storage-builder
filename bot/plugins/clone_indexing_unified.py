
"""
Unified Clone Indexing Module
Consolidates clone_index.py, clone_indexing.py, clone_auto_index.py, 
clone_forward_indexer.py, clone_bulk_indexer.py
"""
import logging
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Storage for indexing state
clone_index_temp = {}
indexing_progress = {}
indexing_tasks = {}
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

async def verify_clone_admin(client: Client, user_id: int) -> tuple[bool, dict]:
    """Verify if user is clone admin"""
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

@Client.on_message(filters.command(['index', 'indexing', 'cloneindex']) & filters.private)
async def clone_index_command(client: Client, message: Message):
    """Unified indexing command"""
    is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
    if not is_admin:
        return await message.reply_text("❌ **Access Denied**\n\nThis command is only available to clone administrators.")
    
    clone_id = get_clone_id_from_client(client)
    
    if len(message.command) < 2:
        help_text = (
            "📚 **Clone Indexing System**\n\n"
            "**Available Commands:**\n"
            "• `/index <channel_link>` - Index from channel link\n"
            "• `/index <username>` - Index from channel username\n"
            "• `/bulkindex <channels>` - Bulk index multiple channels\n"
            "• `/indexstats` - View indexing statistics\n\n"
            
            "**Supported Formats:**\n"
            "• `https://t.me/channel/123`\n"
            "• `@channelname`\n"
            "• Channel ID: `-1001234567890`\n\n"
            
            "**Features:**\n"
            "✅ Auto-duplicate detection\n"
            "✅ Progress tracking\n"
            "✅ Error recovery\n\n"
            
            f"**Clone Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`"
        )
        return await message.reply_text(help_text)
    
    input_text = " ".join(message.command[1:]).strip()
    await process_index_request(client, message, input_text, clone_id, clone_data)

@Client.on_message(filters.command(['bulkindex', 'batchindex']) & filters.private)
async def bulk_index_command(client: Client, message: Message):
    """Bulk indexing command"""
    is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
    if not is_admin:
        return await message.reply_text("❌ Only clone admin can use bulk indexing.")
    
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
        )
        return await message.reply_text(help_text)
    
    channels = message.command[1:]
    await process_bulk_index_request(client, message, channels, clone_id, clone_data)

async def process_index_request(client: Client, message: Message, input_text: str, clone_id: str, clone_data: dict):
    """Process indexing request"""
    try:
        channel_id = None
        
        # Parse input format
        if input_text.startswith('@'):
            username = input_text[1:]
            chat = await client.get_chat(username)
            channel_id = chat.id
        elif input_text.startswith('https://t.me/'):
            if '/c/' in input_text:
                regex = re.compile(r"https://t\.me/c/(\d+)/(\d+)")
                match = regex.match(input_text)
                if match:
                    channel_id = int(f"-100{match.group(1)}")
            else:
                regex = re.compile(r"https://t\.me/([^/]+)/?(\d+)?")
                match = regex.match(input_text)
                if match:
                    username = match.group(1)
                    chat = await client.get_chat(username)
                    channel_id = chat.id
        elif input_text.startswith('-100'):
            channel_id = int(input_text)
        
        if not channel_id:
            return await message.reply_text("❌ Invalid channel format.")
        
        # Get channel info and start indexing
        chat = await client.get_chat(channel_id)
        channel_title = chat.title or "Unknown Channel"
        
        # Get latest message ID
        async for latest_msg in client.iter_messages(channel_id, limit=1):
            last_msg_id = latest_msg.id
            break
        else:
            return await message.reply_text("❌ Channel appears to be empty.")
        
        # Show confirmation
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Indexing", callback_data=f"start_index:{clone_id}:{channel_id}:{last_msg_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        await message.reply_text(
            f"🔍 **Indexing Confirmation**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**Total Messages:** ~{last_msg_id:,}\n"
            f"**Database:** `{clone_data.get('db_name')}`\n\n"
            f"Ready to start indexing?",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error processing index request: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

async def process_bulk_index_request(client: Client, message: Message, channels: list, clone_id: str, clone_data: dict):
    """Process bulk indexing"""
    try:
        channel_info = []
        
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
                    continue
                
                async for latest_msg in client.iter_messages(channel_id, limit=1):
                    last_msg_id = latest_msg.id
                    break
                else:
                    continue
                
                channel_info.append({
                    "id": channel_id,
                    "title": chat.title,
                    "last_msg_id": last_msg_id
                })
            except:
                continue
        
        if not channel_info:
            return await message.reply_text("❌ No valid channels found.")
        
        total_messages = sum(ch['last_msg_id'] for ch in channel_info)
        
        text = f"📋 **Bulk Indexing Confirmation**\n\n"
        text += f"**Valid Channels ({len(channel_info)}):**\n"
        for i, ch in enumerate(channel_info[:10], 1):
            text += f"{i}. {ch['title']} (~{ch['last_msg_id']:,} messages)\n"
        
        text += f"\n**Total Estimated Messages:** {total_messages:,}\n"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Bulk Indexing", callback_data=f"start_bulk:{clone_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        bulk_progress[clone_id] = {
            "channels": channel_info,
            "status": "pending"
        }
        
        await message.reply_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error processing bulk request: {e}")
        await message.reply_text("❌ Error processing request.")

# Auto-index forwarded media
@Client.on_message(filters.media & filters.forwarded & filters.private, group=10)
async def auto_index_forwarded_media(client: Client, message: Message):
    """Auto-index forwarded media from clone admin"""
    clone_id = get_clone_id_from_client(client)
    if not clone_id:
        return
    
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
    if not clone_data or message.from_user.id != clone_data['admin_id']:
        return
    
    if not message.forward_from_chat:
        return
    
    forward_chat = message.forward_from_chat
    if forward_chat.type not in ["channel", "supergroup"]:
        return
    
    # Auto-indexing logic here
    logger.info(f"Auto-index triggered for clone {clone_id}")
