
"""
Clone-specific search functionality
"""
import logging
import re
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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

@Client.on_message(filters.command(['search', 'find']) & filters.private)
async def clone_search_command(client: Client, message: Message):
    """Search indexed files in clone database"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            # Mother bot search - use default search
            return
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or 'mongodb_url' not in clone_data:
            await message.reply_text("❌ Clone database not configured.")
            return
        
        if len(message.command) < 2:
            await message.reply_text(
                "🔍 **Clone Search**\n\n"
                "**Usage:** `/search <query>`\n\n"
                "**Examples:**\n"
                "• `/search movie 2024`\n"
                "• `/search python tutorial`\n"
                "• `/search .mp4` (search by extension)\n\n"
                "**Features:**\n"
                "• Searches your clone's indexed files\n"
                "• Supports partial matches\n"
                "• Case insensitive search\n\n"
                f"📊 **Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`"
            )
            return
        
        query = " ".join(message.command[1:]).strip()
        if len(query) < 2:
            await message.reply_text("❌ Search query must be at least 2 characters long.")
            return
        
        # Show searching message
        search_msg = await message.reply_text(f"🔍 **Searching for:** `{query}`\n\nPlease wait...")
        
        # Perform search
        results = await search_clone_files(clone_data, query, limit=50)
        
        if not results:
            await search_msg.edit_text(
                f"😔 **No Results Found**\n\n"
                f"**Query:** `{query}`\n"
                f"**Database:** `{clone_data.get('db_name')}`\n\n"
                f"Try:\n"
                f"• Different keywords\n"
                f"• Partial file names\n"
                f"• File extensions (.mp4, .pdf, etc.)\n\n"
                f"💡 Use `/dbinfo` to check indexed files count."
            )
            return
        
        # Format results
        results_text = f"🔍 **Search Results** ({len(results)} found)\n\n"
        results_text += f"**Query:** `{query}`\n"
        results_text += f"**Database:** `{clone_data.get('db_name')}`\n\n"
        
        # Show first 10 results
        for i, result in enumerate(results[:10], 1):
            file_name = result.get('file_name', 'Unknown')
            file_type = result.get('file_type', 'unknown')
            file_size = result.get('file_size', 0)
            
            # Format file size
            if file_size > 1024*1024*1024:  # GB
                size_str = f"{file_size/(1024*1024*1024):.1f} GB"
            elif file_size > 1024*1024:  # MB
                size_str = f"{file_size/(1024*1024):.1f} MB"
            elif file_size > 1024:  # KB
                size_str = f"{file_size/1024:.1f} KB"
            else:
                size_str = f"{file_size} B"
            
            results_text += f"{i}. **{file_name}**\n"
            results_text += f"   📁 {file_type.title()} • {size_str}\n\n"
        
        if len(results) > 10:
            results_text += f"... and {len(results) - 10} more results\n\n"
        
        results_text += f"🔍 Use `/get <filename>` to download files"
        
        # Create pagination buttons if needed
        buttons = []
        if len(results) > 10:
            buttons.append([
                InlineKeyboardButton("📄 Show All Results", callback_data=f"show_all_results:{clone_id}:{query[:50]}")
            ])
        
        buttons.extend([
            [
                InlineKeyboardButton("🔄 New Search", callback_data=f"new_search:{clone_id}"),
                InlineKeyboardButton("📊 Search Stats", callback_data=f"search_stats:{clone_id}")
            ]
        ])
        
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        await search_msg.edit_text(results_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in clone search: {e}")
        await message.reply_text("❌ Search error. Please try again.")

@Client.on_message(filters.command(['get', 'download']) & filters.private)
async def clone_get_file_command(client: Client, message: Message):
    """Get/download file from clone database"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        if len(message.command) < 2:
            await message.reply_text(
                "📥 **Get File**\n\n"
                "**Usage:** `/get <filename or file_id>`\n\n"
                "**Examples:**\n"
                "• `/get movie.mp4`\n"
                "• `/get python_tutorial.pdf`\n\n"
                "Use `/search` first to find files."
            )
            return
        
        filename = " ".join(message.command[1:]).strip()
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or 'mongodb_url' not in clone_data:
            await message.reply_text("❌ Clone database not configured.")
            return
        
        # Search for the file
        file_data = await find_file_in_clone_db(clone_data, filename)
        
        if not file_data:
            await message.reply_text(
                f"❌ **File Not Found**\n\n"
                f"**Query:** `{filename}`\n"
                f"Use `/search {filename}` to find similar files."
            )
            return
        
        # Send the file
        try:
            file_id = file_data.get('file_id')
            if not file_id:
                await message.reply_text("❌ File ID not found in database.")
                return
            
            caption = (
                f"📁 **{file_data.get('file_name', 'Unknown')}**\n"
                f"📊 Size: {get_readable_file_size(file_data.get('file_size', 0))}\n"
                f"📅 Indexed: {file_data.get('indexed_at', 'Unknown')}\n"
                f"🗄️ From: Clone Database"
            )
            
            # Increment download count
            await increment_file_download_count(clone_data, file_data['_id'])
            
            # Send file
            await client.send_cached_media(
                chat_id=message.chat.id,
                file_id=file_id,
                caption=caption
            )
            
        except Exception as send_error:
            logger.error(f"Error sending file: {send_error}")
            await message.reply_text(
                f"❌ **File Send Error**\n\n"
                f"Could not send the file. It may have been deleted from Telegram.\n"
                f"**Error:** {str(send_error)}"
            )
        
    except Exception as e:
        logger.error(f"Error in get file command: {e}")
        await message.reply_text("❌ Error retrieving file.")

async def search_clone_files(clone_data: dict, query: str, limit: int = 50):
    """Search files in clone database"""
    try:
        # Connect to clone database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db['files']
        
        # Create search filter
        search_terms = query.lower().split()
        search_conditions = []
        
        for term in search_terms:
            search_conditions.extend([
                {"file_name": {"$regex": re.escape(term), "$options": "i"}},
                {"caption": {"$regex": re.escape(term), "$options": "i"}}
            ])
        
        # Search query
        search_filter = {"$or": search_conditions}
        
        # Execute search
        cursor = files_collection.find(search_filter).sort("indexed_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        
        clone_client.close()
        return results
        
    except Exception as e:
        logger.error(f"Error searching clone files: {e}")
        return []

async def find_file_in_clone_db(clone_data: dict, filename: str):
    """Find specific file in clone database"""
    try:
        # Connect to clone database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db['files']
        
        # Try exact match first
        file_data = await files_collection.find_one({"file_name": {"$regex": f"^{re.escape(filename)}$", "$options": "i"}})
        
        # If not found, try partial match
        if not file_data:
            file_data = await files_collection.find_one({"file_name": {"$regex": re.escape(filename), "$options": "i"}})
        
        clone_client.close()
        return file_data
        
    except Exception as e:
        logger.error(f"Error finding file in clone DB: {e}")
        return None

async def increment_file_download_count(clone_data: dict, file_doc_id: str):
    """Increment download count for a file"""
    try:
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db['files']
        
        await files_collection.update_one(
            {"_id": file_doc_id},
            {
                "$inc": {"download_count": 1},
                "$set": {"last_downloaded": datetime.now()}
            }
        )
        
        clone_client.close()
        
    except Exception as e:
        logger.error(f"Error incrementing download count: {e}")

def get_readable_file_size(size_bytes):
    """Convert bytes to readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"

# Add command to show indexing statistics
@Client.on_message(filters.command(['indexstats', 'statistics']) & filters.private)
async def clone_index_statistics_command(client: Client, message: Message):
    """Show indexing statistics for clone"""
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
        
        # Get comprehensive stats
        stats = await get_clone_indexing_statistics(clone_data)
        
        if not stats:
            await message.reply_text("❌ Error retrieving statistics.")
            return
        
        stats_text = (
            f"📊 **Clone Indexing Statistics**\n\n"
            f"**Database:** `{stats['database_name']}`\n"
            f"**Clone ID:** `{clone_id}`\n\n"
            
            f"**File Statistics:**\n"
            f"• Total Files: `{stats['total_files']:,}`\n"
            f"• Total Size: `{stats['total_size_readable']}`\n"
            f"• Average Size: `{stats['average_size_readable']}`\n\n"
            
            f"**Recent Activity:**\n"
            f"• Today: `{stats['today_files']}`\n"
            f"• This Week: `{stats['week_files']}`\n"
            f"• This Month: `{stats['month_files']}`\n\n"
            
            f"**File Types:**\n"
        )
        
        for file_type, count in list(stats['file_types'].items())[:6]:
            percentage = (count / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
            stats_text += f"• {file_type.title()}: `{count}` ({percentage:.1f}%)\n"
        
        stats_text += (
            f"\n**Download Statistics:**\n"
            f"• Total Downloads: `{stats['total_downloads']:,}`\n"
            f"• Most Downloaded: `{stats['most_downloaded_file']}`\n"
            f"• Downloads Today: `{stats['downloads_today']}`\n\n"
            
            f"**Search Performance:**\n"
            f"• Search Queries Today: `{stats.get('search_queries_today', 0)}`\n"
            f"• Average Response Time: `{stats.get('avg_response_time', 0)}ms`"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_index_stats:{clone_id}"),
                InlineKeyboardButton("📈 Detailed Stats", callback_data=f"detailed_stats:{clone_id}")
            ],
            [
                InlineKeyboardButton("🗄️ Database Info", callback_data=f"refresh_db_info:{clone_id}"),
                InlineKeyboardButton("⚙️ Index Settings", callback_data=f"index_settings:{clone_id}")
            ]
        ])
        
        await message.reply_text(stats_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in index statistics command: {e}")
        await message.reply_text("❌ Error retrieving statistics.")

async def get_clone_indexing_statistics(clone_data: dict):
    """Get comprehensive indexing statistics"""
    try:
        # Connect to clone database
        clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db['files']
        
        # Get basic counts
        total_files = await files_collection.count_documents({})
        
        if total_files == 0:
            clone_client.close()
            return {
                'database_name': clone_data.get('db_name'),
                'total_files': 0,
                'total_size_readable': '0 B',
                'average_size_readable': '0 B',
                'today_files': 0,
                'week_files': 0,
                'month_files': 0,
                'file_types': {},
                'total_downloads': 0,
                'most_downloaded_file': 'None',
                'downloads_today': 0
            }
        
        # Get size statistics
        size_pipeline = [
            {"$group": {
                "_id": None,
                "total_size": {"$sum": "$file_size"},
                "avg_size": {"$avg": "$file_size"}
            }}
        ]
        size_stats = await files_collection.aggregate(size_pipeline).to_list(1)
        total_size = size_stats[0]['total_size'] if size_stats else 0
        avg_size = size_stats[0]['avg_size'] if size_stats else 0
        
        # Get time-based statistics
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        today_files = await files_collection.count_documents({"indexed_at": {"$gte": today_start}})
        week_files = await files_collection.count_documents({"indexed_at": {"$gte": week_start}})
        month_files = await files_collection.count_documents({"indexed_at": {"$gte": month_start}})
        
        # Get file types distribution
        types_pipeline = [
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        file_types = {}
        async for result in files_collection.aggregate(types_pipeline):
            file_types[result['_id']] = result['count']
        
        # Get download statistics
        download_pipeline = [
            {"$group": {
                "_id": None,
                "total_downloads": {"$sum": "$download_count"}
            }}
        ]
        download_stats = await files_collection.aggregate(download_pipeline).to_list(1)
        total_downloads = download_stats[0]['total_downloads'] if download_stats else 0
        
        # Get most downloaded file
        most_downloaded = await files_collection.find_one(
            sort=[("download_count", -1)]
        )
        most_downloaded_file = most_downloaded['file_name'] if most_downloaded else 'None'
        
        # Get downloads today
        downloads_today = await files_collection.count_documents({
            "last_downloaded": {"$gte": today_start}
        })
        
        clone_client.close()
        
        return {
            'database_name': clone_data.get('db_name'),
            'total_files': total_files,
            'total_size_readable': get_readable_file_size(total_size),
            'average_size_readable': get_readable_file_size(avg_size),
            'today_files': today_files,
            'week_files': week_files,
            'month_files': month_files,
            'file_types': file_types,
            'total_downloads': total_downloads,
            'most_downloaded_file': most_downloaded_file,
            'downloads_today': downloads_today
        }
        
    except Exception as e:
        logger.error(f"Error getting indexing statistics: {e}")
        return None
