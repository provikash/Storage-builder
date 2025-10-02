
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
async def enhanced_clone_search(client: Client, message: Message):
    """Enhanced search for indexed files with advanced filters"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return  # Let mother bot handle
        
        # Get clone data
        bot_token = getattr(client, 'bot_token')
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or 'mongodb_url' not in clone_data:
            await message.reply_text("❌ Clone database not configured.")
            return
        
        if len(message.command) < 2:
            help_text = (
                "🔍 **Enhanced Clone Search**\n\n"
                "**Basic Usage:**\n"
                "`/search movie 2024`\n"
                "`/search python tutorial`\n\n"
                
                "**Advanced Filters:**\n"
                "• **File Type**: `type:video`, `type:audio`, `type:document`\n"
                "• **Size Range**: `size:>100mb`, `size:<50mb`\n"
                "• **Quality**: `quality:1080p`, `quality:720p`\n"
                "• **Duration**: `duration:>30min`, `duration:<5min`\n"
                "• **Extension**: `ext:mp4`, `ext:pdf`, `ext:zip`\n"
                "• **Date Range**: `date:today`, `date:week`, `date:month`\n\n"
                
                "**Examples:**\n"
                "• `/search movie type:video quality:1080p`\n"
                "• `/search tutorial type:document size:<100mb`\n"
                "• `/search music type:audio date:week`\n"
                "• `/search python ext:pdf size:>10mb`\n\n"
                
                "**Quick Commands:**\n"
                "• `/search *` - Show all files\n"
                "• `/search type:video` - All videos\n"
                "• `/search size:>1gb` - Large files\n\n"
                
                f"📊 **Database**: `{clone_data.get('db_name')}`"
            )
            await message.reply_text(help_text)
            return
        
        # Parse search query
        query = " ".join(message.command[1:]).strip()
        search_filters = parse_search_query(query)
        
        # Show searching message
        search_msg = await message.reply_text(f"🔍 **Searching**: `{query}`\n\n⏳ Processing your request...")
        
        # Perform search
        results = await search_indexed_files(clone_data, search_filters)
        
        if not results:
            no_results_text = (
                f"😔 **No Results Found**\n\n"
                f"**Query**: `{query}`\n"
                f"**Database**: `{clone_data.get('db_name')}`\n\n"
                f"**Suggestions**:\n"
                f"• Try different keywords\n"
                f"• Use broader search terms\n"
                f"• Check file type filters\n"
                f"• Use `/search *` to browse all files\n\n"
                f"💡 **Tip**: Use `/indexstats` to see what's available"
            )
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Database Stats", callback_data=f"clone_stats:{clone_id}"),
                    InlineKeyboardButton("🔄 New Search", callback_data=f"new_search:{clone_id}")
                ]
            ])
            
            await search_msg.edit_text(no_results_text, reply_markup=buttons)
            return
        
        # Format and display results
        await display_search_results(search_msg, results, search_filters, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error in enhanced search: {e}")
        await message.reply_text("❌ Search error. Please try again.")

def parse_search_query(query: str) -> dict:
    """Parse search query with filters"""
    filters = {
        "text_search": [],
        "file_type": None,
        "size_min": None,
        "size_max": None,
        "quality": None,
        "duration_min": None,
        "duration_max": None,
        "extension": None,
        "date_range": None,
        "sort_by": "relevance"
    }
    
    # Extract filter patterns
    filter_patterns = {
        r'type:(\w+)': 'file_type',
        r'quality:(\w+)': 'quality',
        r'ext:(\w+)': 'extension',
        r'date:(\w+)': 'date_range',
        r'sort:(\w+)': 'sort_by'
    }
    
    remaining_query = query
    
    # Process simple filters
    for pattern, filter_key in filter_patterns.items():
        matches = re.findall(pattern, query, re.IGNORECASE)
        if matches:
            filters[filter_key] = matches[0].lower()
            remaining_query = re.sub(pattern, '', remaining_query, flags=re.IGNORECASE)
    
    # Process size filters
    size_matches = re.findall(r'size:([><]?)(\d+(?:\.\d+)?)(kb|mb|gb)', query, re.IGNORECASE)
    for operator, size_value, unit in size_matches:
        size_bytes = parse_size_to_bytes(f"{size_value}{unit}")
        if operator == '>':
            filters["size_min"] = size_bytes
        elif operator == '<':
            filters["size_max"] = size_bytes
        else:
            filters["size_min"] = size_bytes // 2
            filters["size_max"] = size_bytes * 2
        
        remaining_query = re.sub(r'size:[><]?\d+(?:\.\d+)?(?:kb|mb|gb)', '', remaining_query, flags=re.IGNORECASE)
    
    # Process duration filters
    duration_matches = re.findall(r'duration:([><]?)(\d+)(min|hr|sec)', query, re.IGNORECASE)
    for operator, duration_value, unit in duration_matches:
        duration_seconds = parse_duration_to_seconds(f"{duration_value}{unit}")
        if operator == '>':
            filters["duration_min"] = duration_seconds
        elif operator == '<':
            filters["duration_max"] = duration_seconds
        else:
            filters["duration_min"] = duration_seconds // 2
            filters["duration_max"] = duration_seconds * 2
        
        remaining_query = re.sub(r'duration:[><]?\d+(?:min|hr|sec)', '', remaining_query, flags=re.IGNORECASE)
    
    # Remaining text becomes search terms
    remaining_query = re.sub(r'\s+', ' ', remaining_query).strip()
    if remaining_query and remaining_query != '*':
        filters["text_search"] = remaining_query.split()
    
    return filters

def parse_size_to_bytes(size_str: str) -> int:
    """Convert size string to bytes"""
    units = {'kb': 1024, 'mb': 1024**2, 'gb': 1024**3}
    match = re.match(r'(\d+(?:\.\d+)?)(kb|mb|gb)', size_str.lower())
    if match:
        value, unit = match.groups()
        return int(float(value) * units[unit])
    return 0

def parse_duration_to_seconds(duration_str: str) -> int:
    """Convert duration string to seconds"""
    units = {'sec': 1, 'min': 60, 'hr': 3600}
    match = re.match(r'(\d+)(sec|min|hr)', duration_str.lower())
    if match:
        value, unit = match.groups()
        return int(value) * units[unit]
    return 0

async def search_indexed_files(clone_data: dict, search_filters: dict, limit: int = 50):
    """Search indexed files with advanced filters"""
    try:
        # Connect to clone database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db['files']
        
        # Build MongoDB query
        query = {}
        
        # Text search
        if search_filters["text_search"]:
            text_conditions = []
            for term in search_filters["text_search"]:
                text_conditions.extend([
                    {"file_name": {"$regex": re.escape(term), "$options": "i"}},
                    {"caption": {"$regex": re.escape(term), "$options": "i"}},
                    {"keywords": {"$in": [term.lower()]}}
                ])
            
            query["$or"] = text_conditions
        
        # File type filter
        if search_filters["file_type"]:
            type_mapping = {
                'video': 'video',
                'audio': 'audio', 
                'document': 'document',
                'photo': 'photo',
                'image': 'photo'
            }
            if search_filters["file_type"] in type_mapping:
                query["file_type"] = type_mapping[search_filters["file_type"]]
        
        # Size filters
        if search_filters["size_min"] or search_filters["size_max"]:
            size_query = {}
            if search_filters["size_min"]:
                size_query["$gte"] = search_filters["size_min"]
            if search_filters["size_max"]:
                size_query["$lte"] = search_filters["size_max"]
            query["file_size"] = size_query
        
        # Quality filter
        if search_filters["quality"]:
            query["quality"] = search_filters["quality"]
        
        # Duration filters
        if search_filters["duration_min"] or search_filters["duration_max"]:
            duration_query = {}
            if search_filters["duration_min"]:
                duration_query["$gte"] = search_filters["duration_min"]
            if search_filters["duration_max"]:
                duration_query["$lte"] = search_filters["duration_max"]
            query["duration"] = duration_query
        
        # Extension filter
        if search_filters["extension"]:
            query["file_extension"] = search_filters["extension"].lower()
        
        # Date range filter
        if search_filters["date_range"]:
            date_query = get_date_range_query(search_filters["date_range"])
            if date_query:
                query["indexed_at"] = date_query
        
        # Sort options
        sort_options = {
            "relevance": [("_id", -1)],
            "name": [("file_name", 1)],
            "size": [("file_size", -1)],
            "date": [("indexed_at", -1)],
            "downloads": [("download_count", -1)]
        }
        
        sort_by = sort_options.get(search_filters["sort_by"], [("indexed_at", -1)])
        
        # Execute search
        cursor = files_collection.find(query).sort(sort_by).limit(limit)
        results = await cursor.to_list(length=limit)
        
        # Update access statistics
        if results:
            await files_collection.update_many(
                {"_id": {"$in": [r["_id"] for r in results]}},
                {"$inc": {"access_count": 1}, "$set": {"last_accessed": datetime.now()}}
            )
        
        clone_client.close()
        return results
        
    except Exception as e:
        logger.error(f"Error searching indexed files: {e}")
        return []

def get_date_range_query(date_range: str) -> dict:
    """Get MongoDB date range query"""
    now = datetime.now()
    
    ranges = {
        'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'yesterday': now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1),
        'week': now - timedelta(days=7),
        'month': now - timedelta(days=30),
        'year': now - timedelta(days=365)
    }
    
    if date_range in ranges:
        return {"$gte": ranges[date_range]}
    
    return None

async def display_search_results(msg: Message, results: list, search_filters: dict, clone_id: str, clone_data: dict):
    """Display search results with pagination"""
    try:
        total_results = len(results)
        page_size = 10
        current_page = 0
        
        # Format results
        query_text = " ".join(search_filters.get("text_search", []))
        if not query_text:
            query_text = "Advanced search"
        
        def format_results_page(page: int):
            start_idx = page * page_size
            end_idx = min(start_idx + page_size, total_results)
            page_results = results[start_idx:end_idx]
            
            results_text = (
                f"🔍 **Search Results** ({total_results} found)\n\n"
                f"**Query**: `{query_text}`"
            )
            
            # Add active filters
            active_filters = []
            if search_filters.get("file_type"):
                active_filters.append(f"Type: {search_filters['file_type']}")
            if search_filters.get("quality"):
                active_filters.append(f"Quality: {search_filters['quality']}")
            if search_filters.get("extension"):
                active_filters.append(f"Ext: {search_filters['extension']}")
            
            if active_filters:
                results_text += f"\n**Filters**: {', '.join(active_filters)}"
            
            results_text += f"\n**Database**: `{clone_data.get('db_name')}`\n\n"
            results_text += f"**Page {page + 1} of {(total_results - 1) // page_size + 1}**\n\n"
            
            # Display results
            for i, result in enumerate(page_results, start_idx + 1):
                file_name = result.get('file_name', 'Unknown')[:40]
                file_type = result.get('file_type', 'unknown')
                file_size = get_readable_size(result.get('file_size', 0))
                
                # Quality info
                quality_info = ""
                if result.get('quality') and result['quality'] != 'unknown':
                    quality_info = f" ({result['quality']})"
                
                # Duration info
                duration_info = ""
                if result.get('duration', 0) > 0:
                    duration = result['duration']
                    if duration > 3600:
                        duration_info = f" - {duration//3600}h{(duration%3600)//60}m"
                    elif duration > 60:
                        duration_info = f" - {duration//60}m{duration%60}s"
                    else:
                        duration_info = f" - {duration}s"
                
                results_text += (
                    f"**{i}.** `{file_name}`\n"
                    f"   📁 {file_type.title()} • {file_size}{quality_info}{duration_info}\n\n"
                )
            
            return results_text
        
        # Create pagination buttons
        def create_pagination_buttons(page: int):
            buttons = []
            
            # Navigation row
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_page:{clone_id}:{page-1}"))
            if (page + 1) * page_size < total_results:
                nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page:{clone_id}:{page+1}"))
            
            if nav_row:
                buttons.append(nav_row)
            
            # Action buttons
            buttons.extend([
                [
                    InlineKeyboardButton("📥 Download", callback_data=f"download_search:{clone_id}:{page}"),
                    InlineKeyboardButton("🔗 Get Links", callback_data=f"links_search:{clone_id}:{page}")
                ],
                [
                    InlineKeyboardButton("🔄 Refine Search", callback_data=f"refine_search:{clone_id}"),
                    InlineKeyboardButton("📊 Filter Stats", callback_data=f"filter_stats:{clone_id}")
                ],
                [
                    InlineKeyboardButton("🔍 New Search", callback_data=f"new_search:{clone_id}")
                ]
            ])
            
            return InlineKeyboardMarkup(buttons)
        
        # Store results for pagination callbacks
        search_cache[f"{clone_id}_results"] = results
        search_cache[f"{clone_id}_filters"] = search_filters
        
        # Display first page
        results_text = format_results_page(current_page)
        buttons = create_pagination_buttons(current_page)
        
        await msg.edit_text(results_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error displaying search results: {e}")
        await msg.edit_text("❌ Error displaying results.")

# Search results cache for pagination
search_cache = {}

@Client.on_callback_query(filters.regex("^search_page:"))
async def handle_search_pagination(client: Client, query: CallbackQuery):
    """Handle search result pagination"""
    try:
        await query.answer()
        
        data_parts = query.data.split(":")
        clone_id = data_parts[1]
        page = int(data_parts[2])
        
        # Retrieve cached results
        results = search_cache.get(f"{clone_id}_results", [])
        search_filters = search_cache.get(f"{clone_id}_filters", {})
        
        if not results:
            await query.edit_message_text("❌ Search results expired. Please search again.")
            return
        
        # Get clone data
        bot_token = getattr(client, 'bot_token')
        clone_data = await get_clone_by_bot_token(bot_token)
        
        # Display requested page
        await display_search_results(query.message, results, search_filters, clone_id, clone_data)
        
    except Exception as e:
        logger.error(f"Error in search pagination: {e}")
        await query.answer("❌ Error loading page.", show_alert=True)

def get_readable_size(size_bytes: int) -> str:
    """Convert bytes to readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"

@Client.on_callback_query(filters.regex("^new_search:"))
async def handle_new_search(client: Client, query: CallbackQuery):
    """Handle new search request"""
    try:
        clone_id = query.data.split(":")[1]
        
        search_help = (
            "🔍 **Start a New Search**\n\n"
            "**Usage**: `/search <your query>`\n\n"
            "**Quick Examples**:\n"
            "• `/search movie 2024`\n"
            "• `/search type:video quality:1080p`\n"
            "• `/search python tutorial ext:pdf`\n"
            "• `/search size:>100mb date:week`\n\n"
            "**Advanced Filters Available**:\n"
            "• File type, size, quality\n"
            "• Duration, extension, date\n"
            "• And much more!\n\n"
            "💡 Type `/search` without arguments for full help."
        )
        
        await query.edit_message_text(search_help)
        
    except Exception as e:
        logger.error(f"Error handling new search: {e}")

@Client.on_message(filters.command(['searchstats', 'searchanalytics']) & filters.private)
async def search_analytics_command(client: Client, message: Message):
    """Show search analytics for clone"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        bot_token = getattr(client, 'bot_token')
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != message.from_user.id:
            await message.reply_text("❌ Only clone admin can view search analytics.")
            return
        
        # Get search analytics from database
        analytics = await get_search_analytics(clone_data)
        
        analytics_text = (
            f"📊 **Search Analytics**\n\n"
            f"**Database**: `{clone_data.get('db_name')}`\n"
            f"**Total Searches**: {analytics.get('total_searches', 0):,}\n"
            f"**Unique Users**: {analytics.get('unique_users', 0):,}\n"
            f"**Avg Results per Search**: {analytics.get('avg_results', 0):.1f}\n\n"
            
            f"**Popular Search Terms**:\n"
        )
        
        for term, count in analytics.get('popular_terms', [])[:5]:
            analytics_text += f"• `{term}`: {count} searches\n"
        
        analytics_text += f"\n**Popular File Types**:\n"
        for file_type, count in analytics.get('popular_types', [])[:5]:
            analytics_text += f"• {file_type.title()}: {count} requests\n"
        
        await message.reply_text(analytics_text)
        
    except Exception as e:
        logger.error(f"Error in search analytics: {e}")
        await message.reply_text("❌ Error retrieving analytics.")

async def get_search_analytics(clone_data: dict) -> dict:
    """Get search analytics from database"""
    try:
        # This would integrate with your analytics system
        # For now, return mock data structure
        return {
            'total_searches': 0,
            'unique_users': 0, 
            'avg_results': 0,
            'popular_terms': [],
            'popular_types': []
        }
    except Exception as e:
        logger.error(f"Error getting search analytics: {e}")
        return {}
