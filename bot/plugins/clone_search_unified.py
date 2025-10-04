
"""
Unified Clone Search Module
Consolidates clone_search.py and clone_search_enhanced.py
"""
import logging
import re
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

@Client.on_message(filters.command(['search', 'find', 's']) & filters.private)
async def unified_clone_search(client: Client, message: Message):
    """Unified search command with advanced filters"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        bot_token = getattr(client, 'bot_token')
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or 'mongodb_url' not in clone_data:
            return await message.reply_text("❌ Clone database not configured.")
        
        if len(message.command) < 2:
            help_text = (
                "🔍 **Enhanced Clone Search**\n\n"
                "**Basic Usage:**\n"
                "`/search movie 2024`\n\n"
                
                "**Advanced Filters:**\n"
                "• **Type**: `type:video`, `type:audio`\n"
                "• **Size**: `size:>100mb`, `size:<50mb`\n"
                "• **Quality**: `quality:1080p`\n"
                "• **Extension**: `ext:mp4`, `ext:pdf`\n\n"
                
                "**Examples:**\n"
                "• `/search movie type:video quality:1080p`\n"
                "• `/search tutorial ext:pdf size:<100mb`\n\n"
                
                f"📊 **Database**: `{clone_data.get('db_name')}`"
            )
            return await message.reply_text(help_text)
        
        query = " ".join(message.command[1:]).strip()
        search_filters = parse_search_query(query)
        
        search_msg = await message.reply_text(f"🔍 **Searching**: `{query}`\n\n⏳ Processing...")
        
        results = await search_indexed_files(clone_data, search_filters)
        
        if not results:
            return await search_msg.edit_text(
                f"😔 **No Results Found**\n\n"
                f"**Query**: `{query}`\n"
                f"Try different keywords or use `/search *` to browse all files."
            )
        
        await display_search_results(search_msg, results, search_filters, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await message.reply_text("❌ Search error.")

def parse_search_query(query: str) -> dict:
    """Parse search query with filters"""
    filters = {
        "text_search": [],
        "file_type": None,
        "size_min": None,
        "size_max": None,
        "quality": None,
        "extension": None
    }
    
    # Extract filters
    filter_patterns = {
        r'type:(\w+)': 'file_type',
        r'quality:(\w+)': 'quality',
        r'ext:(\w+)': 'extension'
    }
    
    remaining_query = query
    for pattern, filter_key in filter_patterns.items():
        matches = re.findall(pattern, query, re.IGNORECASE)
        if matches:
            filters[filter_key] = matches[0].lower()
            remaining_query = re.sub(pattern, '', remaining_query, flags=re.IGNORECASE)
    
    # Parse size filters
    size_matches = re.findall(r'size:([><]?)(\d+(?:\.\d+)?)(kb|mb|gb)', query, re.IGNORECASE)
    for operator, size_value, unit in size_matches:
        size_bytes = parse_size_to_bytes(f"{size_value}{unit}")
        if operator == '>':
            filters["size_min"] = size_bytes
        elif operator == '<':
            filters["size_max"] = size_bytes
    
    filters["text_search"] = [word for word in remaining_query.strip().split() if word]
    return filters

def parse_size_to_bytes(size_str: str) -> int:
    """Convert size string to bytes"""
    units = {'kb': 1024, 'mb': 1024**2, 'gb': 1024**3}
    match = re.match(r'(\d+(?:\.\d+)?)(kb|mb|gb)', size_str.lower())
    if match:
        value, unit = match.groups()
        return int(float(value) * units[unit])
    return 0

async def search_indexed_files(clone_data: dict, search_filters: dict, limit: int = 50):
    """Search files with advanced filters"""
    try:
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name')]
        files_collection = clone_db['files']
        
        # Build query
        query = {}
        
        if search_filters['text_search']:
            search_conditions = []
            for term in search_filters['text_search']:
                search_conditions.extend([
                    {"file_name": {"$regex": re.escape(term), "$options": "i"}},
                    {"caption": {"$regex": re.escape(term), "$options": "i"}}
                ])
            query["$or"] = search_conditions
        
        if search_filters['file_type']:
            query["file_type"] = search_filters['file_type']
        
        if search_filters['extension']:
            query["file_name"] = {"$regex": f"\\.{search_filters['extension']}$", "$options": "i"}
        
        if search_filters['size_min'] or search_filters['size_max']:
            size_query = {}
            if search_filters['size_min']:
                size_query["$gte"] = search_filters['size_min']
            if search_filters['size_max']:
                size_query["$lte"] = search_filters['size_max']
            query["file_size"] = size_query
        
        cursor = files_collection.find(query).sort("indexed_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        
        clone_client.close()
        return results
        
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return []

async def display_search_results(message, results, filters, clone_id, clone_data):
    """Display search results"""
    results_text = f"🔍 **Search Results** ({len(results)} found)\n\n"
    
    for i, result in enumerate(results[:10], 1):
        file_name = result.get('file_name', 'Unknown')
        file_size = result.get('file_size', 0)
        
        # Format size
        if file_size > 1024*1024*1024:
            size_str = f"{file_size/(1024*1024*1024):.1f} GB"
        elif file_size > 1024*1024:
            size_str = f"{file_size/(1024*1024):.1f} MB"
        else:
            size_str = f"{file_size/1024:.1f} KB"
        
        results_text += f"{i}. **{file_name}**\n"
        results_text += f"   💾 {size_str}\n\n"
    
    if len(results) > 10:
        results_text += f"... and {len(results) - 10} more results\n"
    
    await message.edit_text(results_text)
