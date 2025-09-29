
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.database.clone_db import get_clone_by_bot_token
from bot.database.mongo_db import get_collection
from info import Config
import matplotlib.pyplot as plt
import io
import base64

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

@Client.on_message(filters.command(['stats', 'analytics', 'statistics']) & filters.private)
async def show_analytics_command(client: Client, message: Message):
    """Show file analytics and statistics"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This command is only available in clone bots.")
            return
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        # Check if user is admin
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can view analytics.")
            return
        
        # Generate analytics
        analytics = await generate_file_analytics(clone_data)
        
        # Display analytics
        await display_analytics(message, analytics)
        
    except Exception as e:
        logger.error(f"Error showing analytics: {e}")
        await message.reply_text("❌ Error generating analytics.")

async def generate_file_analytics(clone_data):
    """Generate comprehensive file analytics"""
    try:
        db_name = clone_data.get('db_name', f"clone_{clone_data['bot_id']}")
        collection = await get_collection('files', db_name)
        
        analytics = {
            'overview': {},
            'file_types': {},
            'quality_distribution': {},
            'size_distribution': {},
            'upload_trends': {},
            'popular_files': [],
            'search_trends': {},
            'storage_usage': {}
        }
        
        # Overview statistics
        total_files = await collection.count_documents({})
        total_size = await collection.aggregate([
            {'$group': {'_id': None, 'total_size': {'$sum': '$file_size'}}}
        ]).to_list(1)
        total_size = total_size[0]['total_size'] if total_size else 0
        
        analytics['overview'] = {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': format_file_size(total_size),
            'avg_file_size': total_size / total_files if total_files > 0 else 0
        }
        
        # File types distribution
        file_types_pipeline = [
            {'$group': {'_id': '$file_type', 'count': {'$sum': 1}, 'size': {'$sum': '$file_size'}}},
            {'$sort': {'count': -1}}
        ]
        file_types_data = await collection.aggregate(file_types_pipeline).to_list(None)
        analytics['file_types'] = {item['_id']: item for item in file_types_data}
        
        # Quality distribution for videos
        quality_pipeline = [
            {'$match': {'file_type': 'video', 'quality': {'$exists': True}}},
            {'$group': {'_id': '$quality', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        quality_data = await collection.aggregate(quality_pipeline).to_list(None)
        analytics['quality_distribution'] = {item['_id']: item['count'] for item in quality_data}
        
        # Size distribution
        size_ranges = [
            ('< 10MB', 0, 10*1024*1024),
            ('10MB - 100MB', 10*1024*1024, 100*1024*1024),
            ('100MB - 1GB', 100*1024*1024, 1024*1024*1024),
            ('> 1GB', 1024*1024*1024, float('inf'))
        ]
        
        for range_name, min_size, max_size in size_ranges:
            if max_size == float('inf'):
                count = await collection.count_documents({'file_size': {'$gte': min_size}})
            else:
                count = await collection.count_documents({
                    'file_size': {'$gte': min_size, '$lt': max_size}
                })
            analytics['size_distribution'][range_name] = count
        
        # Upload trends (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_uploads_pipeline = [
            {'$match': {'date': {'$gte': thirty_days_ago}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date'}},
                'count': {'$sum': 1},
                'size': {'$sum': '$file_size'}
            }},
            {'$sort': {'_id': 1}}
        ]
        daily_uploads = await collection.aggregate(daily_uploads_pipeline).to_list(None)
        analytics['upload_trends'] = {item['_id']: item for item in daily_uploads}
        
        # Most popular files (by access count)
        popular_pipeline = [
            {'$match': {'access_count': {'$gt': 0}}},
            {'$sort': {'access_count': -1}},
            {'$limit': 10}
        ]
        popular_files = await collection.aggregate(popular_pipeline).to_list(10)
        analytics['popular_files'] = popular_files
        
        # Storage usage by file type
        storage_pipeline = [
            {'$group': {
                '_id': '$file_type',
                'total_size': {'$sum': '$file_size'},
                'count': {'$sum': 1},
                'avg_size': {'$avg': '$file_size'}
            }},
            {'$sort': {'total_size': -1}}
        ]
        storage_data = await collection.aggregate(storage_pipeline).to_list(None)
        analytics['storage_usage'] = {item['_id']: item for item in storage_data}
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        return {}

async def display_analytics(message: Message, analytics):
    """Display analytics in a formatted message"""
    if not analytics:
        await message.reply_text("❌ Unable to generate analytics.")
        return
    
    overview = analytics.get('overview', {})
    file_types = analytics.get('file_types', {})
    quality_dist = analytics.get('quality_distribution', {})
    size_dist = analytics.get('size_distribution', {})
    
    # Main analytics message
    analytics_text = (
        "📊 **File Analytics Dashboard**\n\n"
        f"**📋 Overview:**\n"
        f"• Total Files: `{overview.get('total_files', 0):,}`\n"
        f"• Total Storage: `{overview.get('total_size_formatted', '0 B')}`\n"
        f"• Average File Size: `{format_file_size(overview.get('avg_file_size', 0))}`\n\n"
        
        f"**📁 File Types:**\n"
    )
    
    # Add file types
    for file_type, data in list(file_types.items())[:5]:
        percentage = (data['count'] / overview['total_files'] * 100) if overview['total_files'] > 0 else 0
        analytics_text += f"• {file_type.title()}: `{data['count']:,}` ({percentage:.1f}%)\n"
    
    if quality_dist:
        analytics_text += f"\n**🎬 Video Quality:**\n"
        for quality, count in list(quality_dist.items())[:5]:
            analytics_text += f"• {quality}: `{count:,}` files\n"
    
    analytics_text += f"\n**📊 Size Distribution:**\n"
    for size_range, count in size_dist.items():
        if count > 0:
            analytics_text += f"• {size_range}: `{count:,}` files\n"
    
    # Buttons for detailed analytics
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Upload Trends", callback_data="analytics:trends"),
            InlineKeyboardButton("🔥 Popular Files", callback_data="analytics:popular")
        ],
        [
            InlineKeyboardButton("💾 Storage Usage", callback_data="analytics:storage"),
            InlineKeyboardButton("🔍 Search Analytics", callback_data="analytics:search")
        ],
        [
            InlineKeyboardButton("📤 Export Data", callback_data="analytics:export"),
            InlineKeyboardButton("🔄 Refresh", callback_data="analytics:refresh")
        ]
    ])
    
    await message.reply_text(analytics_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^analytics:"))
async def handle_analytics_callbacks(client: Client, query: CallbackQuery):
    """Handle analytics callback queries"""
    action = query.data.split(":")[1]
    
    if action == "trends":
        await show_upload_trends(client, query)
    elif action == "popular":
        await show_popular_files(client, query)
    elif action == "storage":
        await show_storage_usage(client, query)
    elif action == "search":
        await show_search_analytics(client, query)
    elif action == "export":
        await export_analytics_data(client, query)
    elif action == "refresh":
        await refresh_analytics(client, query)

async def show_upload_trends(client: Client, query: CallbackQuery):
    """Show upload trends for the last 30 days"""
    try:
        clone_id = get_clone_id_from_client(client)
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        
        if not clone_data:
            await query.answer("❌ Clone data not found", show_alert=True)
            return
        
        analytics = await generate_file_analytics(clone_data)
        upload_trends = analytics.get('upload_trends', {})
        
        trends_text = "📈 **Upload Trends (Last 30 Days)**\n\n"
        
        if not upload_trends:
            trends_text += "No upload data available for the last 30 days."
        else:
            total_recent = sum(data['count'] for data in upload_trends.values())
            total_size_recent = sum(data['size'] for data in upload_trends.values())
            
            trends_text += f"**Summary:**\n"
            trends_text += f"• Total Uploads: `{total_recent:,}`\n"
            trends_text += f"• Total Size: `{format_file_size(total_size_recent)}`\n"
            trends_text += f"• Daily Average: `{total_recent / 30:.1f}` files\n\n"
            
            trends_text += f"**Recent Activity:**\n"
            sorted_dates = sorted(upload_trends.items(), reverse=True)[:10]
            for date, data in sorted_dates:
                trends_text += f"• {date}: `{data['count']}` files ({format_file_size(data['size'])})\n"
        
        await query.edit_message_text(
            trends_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="analytics:refresh")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error showing upload trends: {e}")
        await query.answer("❌ Error loading trends", show_alert=True)

async def show_popular_files(client: Client, query: CallbackQuery):
    """Show most popular files"""
    try:
        clone_id = get_clone_id_from_client(client)
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        
        if not clone_data:
            await query.answer("❌ Clone data not found", show_alert=True)
            return
        
        analytics = await generate_file_analytics(clone_data)
        popular_files = analytics.get('popular_files', [])
        
        popular_text = "🔥 **Most Popular Files**\n\n"
        
        if not popular_files:
            popular_text += "No files have been accessed yet."
        else:
            for idx, file_data in enumerate(popular_files[:10], 1):
                file_name = file_data.get('file_name', 'Unknown')[:30]
                access_count = file_data.get('access_count', 0)
                file_type = file_data.get('file_type', 'unknown').title()
                file_size = format_file_size(file_data.get('file_size', 0))
                
                popular_text += f"**{idx}.** {file_name}...\n"
                popular_text += f"   👁️ {access_count} views • {file_type} • {file_size}\n\n"
        
        await query.edit_message_text(
            popular_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="analytics:refresh")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error showing popular files: {e}")
        await query.answer("❌ Error loading popular files", show_alert=True)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

async def track_file_access(file_id: str, user_id: int, clone_id: str):
    """Track file access for analytics"""
    try:
        # Update access count and last accessed time
        clone_data = await get_clone_by_bot_token(f"bot_token_for_{clone_id}")
        if not clone_data:
            return
        
        db_name = clone_data.get('db_name', f"clone_{clone_id}")
        collection = await get_collection('files', db_name)
        
        await collection.update_one(
            {'file_id': file_id},
            {
                '$inc': {'access_count': 1},
                '$set': {'last_accessed': datetime.now()},
                '$addToSet': {'accessed_by': user_id}
            }
        )
        
        # Log access for detailed analytics
        analytics_collection = await get_collection('file_access_logs', db_name)
        await analytics_collection.insert_one({
            'file_id': file_id,
            'user_id': user_id,
            'access_time': datetime.now(),
            'clone_id': clone_id
        })
        
    except Exception as e:
        logger.error(f"Error tracking file access: {e}")
