
"""
Clone database management commands for clone bots
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from bot.database.mongo_db import get_clone_database_stats, check_clone_database_connection
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
        
        # Get database stats
        stats = await get_clone_database_stats(clone_id)
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
        
        # Test connection
        success, message_text = await check_clone_database_connection(clone_id)
        
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
        
        # Get database stats
        stats = await get_clone_database_stats(clone_id)
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
        
        # Test connection
        success, message_text = await check_clone_database_connection(clone_id)
        
        # Get clone data for database name
        from bot.database.clone_db import get_clone
        clone_data = await get_clone(clone_id)
        
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
```
