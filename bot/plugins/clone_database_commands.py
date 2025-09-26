
"""
Clone database management commands for clone bots
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from motor.motor_asyncio import AsyncIOMotorClient
from bot.utils.helper import get_readable_file_size

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

@Client.on_message(filters.command(['dbstats', 'databasestats', 'clones']) & filters.private)
async def clone_database_stats_command(client: Client, message: Message):
    """Show clone database statistics"""
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
        
        # Show loading message
        loading_msg = await message.reply_text("🔄 **Fetching Database Statistics...**\n\nPlease wait...")
        
        # Get database stats using clone's MongoDB URL
        stats = await get_clone_database_stats(clone_data)
        if not stats:
            await loading_msg.edit_text("❌ **Error**\n\nFailed to fetch database statistics.")
            return
        
        # Format file types
        file_types_text = ""
        if stats['file_types']:
            for file_type, count in list(stats['file_types'].items())[:5]:  # Show top 5
                file_types_text += f"• **{file_type.title()}**: `{count}`\n"
            if len(stats['file_types']) > 5:
                file_types_text += f"• **Others**: `{sum(list(stats['file_types'].values())[5:])}`\n"
        else:
            file_types_text = "• No files indexed yet\n"
        
        # Format total size
        total_size_readable = get_readable_file_size(stats['total_size'])
        
        stats_text = (
            f"📊 **Clone Database Statistics**\n\n"
            f"🗄️ **Database**: `{stats['database_name']}`\n\n"
            f"📁 **Files Overview:**\n"
            f"• **Total Files**: `{stats['total_files']:,}`\n"
            f"• **Total Size**: `{total_size_readable}`\n"
            f"• **Recent (24h)**: `{stats['recent_files']}`\n\n"
            f"📂 **File Types:**\n{file_types_text}\n"
            f"👥 **Users**: `{stats['total_users']:,}`\n\n"
            f"🔄 **Last Updated**: Just now"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"clone_refresh_stats:{clone_id}"),
                InlineKeyboardButton("🔍 Test Connection", callback_data=f"clone_test_db:{clone_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        
        await loading_msg.edit_text(stats_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone database stats command: {e}")
        await message.reply_text("❌ Error fetching database statistics.")

@Client.on_message(filters.command(['dbtest', 'testdb']) & filters.private)
async def clone_database_test_command(client: Client, message: Message):
    """Test clone database connection"""
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
        
        # Show loading message
        loading_msg = await message.reply_text("🔄 **Testing Database Connection...**\n\nPlease wait...")
        
        # Test connection using clone's MongoDB URL
        success, message_text = await check_clone_database_connection(clone_data)
        
        if success:
            result_text = (
                f"✅ **Database Connection Test**\n\n"
                f"🔗 **Status**: Connected\n"
                f"📝 **Message**: {message_text}\n"
                f"🗄️ **Database**: `{clone_data.get('db_name', f'clone_{clone_id}')}`\n\n"
                f"💡 Your database is working properly!"
            )
            emoji = "✅"
        else:
            result_text = (
                f"❌ **Database Connection Test**\n\n"
                f"🔗 **Status**: Failed\n"
                f"📝 **Error**: {message_text}\n"
                f"🗄️ **Database**: `{clone_data.get('db_name', f'clone_{clone_id}')}`\n\n"
                f"⚠️ Please check your database configuration!"
            )
            emoji = "❌"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Test Again", callback_data=f"clone_test_db:{clone_id}"),
                InlineKeyboardButton("📊 View Stats", callback_data=f"clone_refresh_stats:{clone_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        
        await loading_msg.edit_text(result_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone database test command: {e}")
        await message.reply_text("❌ Error testing database connection.")

@Client.on_callback_query(filters.regex("^clone_refresh_stats:"))
async def handle_clone_refresh_stats(client: Client, query: CallbackQuery):
    """Handle refresh stats callback"""
    try:
        clone_id = query.data.split(":")[1]
        
        await query.answer("Refreshing statistics...", show_alert=False)
        
        # Get clone data for database stats
        from bot.database.clone_db import get_clone
        clone_data = await get_clone(clone_id)
        if not clone_data:
            await query.edit_message_text("❌ **Error**\n\nClone configuration not found.")
            return
            
        # Get database stats
        stats = await get_clone_database_stats(clone_data)
        if not stats:
            await query.edit_message_text("❌ **Error**\n\nFailed to fetch database statistics.")
            return
        
        # Format file types
        file_types_text = ""
        if stats['file_types']:
            for file_type, count in list(stats['file_types'].items())[:5]:  # Show top 5
                file_types_text += f"• **{file_type.title()}**: `{count}`\n"
            if len(stats['file_types']) > 5:
                file_types_text += f"• **Others**: `{sum(list(stats['file_types'].values())[5:])}`\n"
        else:
            file_types_text = "• No files indexed yet\n"
        
        # Format total size
        total_size_readable = get_readable_file_size(stats['total_size'])
        
        stats_text = (
            f"📊 **Clone Database Statistics**\n\n"
            f"🗄️ **Database**: `{stats['database_name']}`\n\n"
            f"📁 **Files Overview:**\n"
            f"• **Total Files**: `{stats['total_files']:,}`\n"
            f"• **Total Size**: `{total_size_readable}`\n"
            f"• **Recent (24h)**: `{stats['recent_files']}`\n\n"
            f"📂 **File Types:**\n{file_types_text}\n"
            f"👥 **Users**: `{stats['total_users']:,}`\n\n"
            f"🔄 **Last Updated**: Just now"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"clone_refresh_stats:{clone_id}"),
                InlineKeyboardButton("🔍 Test Connection", callback_data=f"clone_test_db:{clone_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        
        await query.edit_message_text(stats_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error refreshing clone stats: {e}")
        await query.answer("❌ Error refreshing statistics.", show_alert=True)

@Client.on_callback_query(filters.regex("^clone_test_db:"))
async def handle_clone_test_db(client: Client, query: CallbackQuery):
    """Handle test database callback"""
    try:
        clone_id = query.data.split(":")[1]
        
        await query.answer("Testing database connection...", show_alert=False)
        
        # Get clone data for database testing
        from bot.database.clone_db import get_clone
        clone_data = await get_clone(clone_id)
        if not clone_data:
            await query.edit_message_text("❌ **Error**\n\nClone configuration not found.")
            return
        
        # Test connection using clone's MongoDB URL
        success, message_text = await check_clone_database_connection(clone_data)
        
        if success:
            result_text = (
                f"✅ **Database Connection Test**\n\n"
                f"🔗 **Status**: Connected\n"
                f"📝 **Message**: {message_text}\n"
                f"🗄️ **Database**: `{clone_data.get('db_name', f'clone_{clone_id}') if clone_data else 'N/A'}`\n\n"
                f"💡 Your database is working properly!"
            )
        else:
            result_text = (
                f"❌ **Database Connection Test**\n\n"
                f"🔗 **Status**: Failed\n"
                f"📝 **Error**: {message_text}\n"
                f"🗄️ **Database**: `{clone_data.get('db_name', f'clone_{clone_id}') if clone_data else 'N/A'}`\n\n"
                f"⚠️ Please check your database configuration!"
            )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Test Again", callback_data=f"clone_test_db:{clone_id}"),
                InlineKeyboardButton("📊 View Stats", callback_data=f"clone_refresh_stats:{clone_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        
        await query.edit_message_text(result_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error testing clone database: {e}")
        await query.answer("❌ Error testing database connection.", show_alert=True)

# Database utility functions
async def get_clone_database_stats(clone_data: dict):
    """Get database statistics for a specific clone using its MongoDB URL"""
    try:
        mongodb_url = clone_data.get('mongodb_url')
        if not mongodb_url:
            logger.error(f"No MongoDB URL found for clone {clone_data.get('_id')}")
            return None
            
        # Connect to clone's specific database with better timeout settings
        clone_client = AsyncIOMotorClient(
            mongodb_url, 
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test connection first
        await clone_client.admin.command('ping')
        
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        files_collection = clone_db.files
        
        # Get total files count
        total_files = await files_collection.count_documents({})
        
        # Get total file size
        pipeline = [
            {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
        ]
        total_size = 0
        async for result in files_collection.aggregate(pipeline):
            total_size = result.get('total_size', 0)
        
        # Get file types distribution
        file_types_pipeline = [
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        file_types = {}
        async for result in files_collection.aggregate(file_types_pipeline):
            file_types[result['_id']] = result['count']
        
        # Get recent files (last 24 hours)
        import time
        yesterday = time.time() - (24 * 60 * 60)
        recent_files = await files_collection.count_documents({
            "indexed_at": {"$gte": yesterday}
        })
        
        # Get unique users count
        users_pipeline = [
            {"$group": {"_id": "$user_id"}},
            {"$count": "total_users"}
        ]
        total_users = 0
        async for result in files_collection.aggregate(users_pipeline):
            total_users = result.get('total_users', 0)
        
        # Close the connection
        clone_client.close()
        
        return {
            'database_name': clone_data.get('db_name', f"clone_{clone_data.get('_id')}"),
            'total_files': total_files,
            'total_size': total_size,
            'file_types': file_types,
            'recent_files': recent_files,
            'total_users': total_users
        }
        
    except Exception as e:
        logger.error(f"Error getting clone database stats: {e}")
        return None

async def check_clone_database_connection(clone_data: dict):
    """Check database connection for a specific clone using its MongoDB URL"""
    try:
        mongodb_url = clone_data.get('mongodb_url')
        if not mongodb_url:
            return False, "No MongoDB URL configured for this clone"
            
        # Test connection to clone's specific database
        clone_client = AsyncIOMotorClient(
            mongodb_url, 
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        
        # Test with ping command
        await clone_client.admin.command("ping")
        
        # Test database access
        clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_data.get('_id')}")]
        collections = await clone_db.list_collection_names()
        
        # Close the connection
        clone_client.close()
        
        return True, f"Connection successful. Database has {len(collections)} collections."
        
    except Exception as e:
        logger.error(f"Error checking clone database connection: {e}")
        return False, f"Connection failed: {str(e)}"
