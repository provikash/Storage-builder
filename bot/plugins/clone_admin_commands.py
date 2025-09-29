
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_config, update_clone_config, get_clone_by_bot_token, update_clone_setting, get_clone_user_count, get_clone_file_count, update_clone_token_verification, update_clone_shortener_settings
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("indexstatus") & filters.private)
async def clone_indexing_status_command(client: Client, message: Message):
    """Show indexing status and permissions for clone admin"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can check indexing status.")
    
    try:
        # Get indexing statistics if available
        from bot.database.mongo_db import get_clone_index_stats
        stats = await get_clone_index_stats(str(clone_data.get('bot_id', clone_data.get('_id'))))
        
        status_text = "📊 **Clone Indexing Status**\n\n"
        status_text += f"🤖 **Clone:** @{clone_data.get('username', 'Unknown')}\n"
        status_text += f"👤 **Admin:** You (ID: {user_id})\n\n"
        
        status_text += "🔒 **Permissions:**\n"
        status_text += "✅ Index commands access\n"
        status_text += "✅ Auto-index forwarded media\n"
        status_text += "✅ Bulk channel indexing\n"
        status_text += "✅ Index management\n\n"
        
        if stats:
            status_text += f"📈 **Statistics:**\n"
            status_text += f"• Total files: {stats.get('total_files', 0):,}\n"
            status_text += f"• Last indexed: {stats.get('last_indexed', 'Never')}\n"
        else:
            status_text += "📈 **Statistics:** No data available\n\n"
        
        status_text += "💡 **Available Commands:**\n"
        status_text += "• `/index <link>` - Index from channel link\n"
        status_text += "• `/index <start> <end>` - Index message range\n"
        status_text += "• `/batchindex` - Batch index multiple channels\n"
        status_text += "• `/skipdup` - Toggle skip duplicates\n"
        status_text += "• `/indexstats` - Show detailed statistics\n"
        status_text += "• `/clearindex` - Clear all indexed files\n\n"
        
        status_text += "⚙️ **Settings:**\n"
        status_text += f"• Skip Duplicates: {'✅ ON' if clone_data.get('skip_duplicates', True) else '❌ OFF'}\n"
        status_text += f"• Media Only: {'✅ ON' if clone_data.get('index_media_only', True) else '❌ OFF'}\n"
        status_text += f"• Auto Index: {'✅ ON' if clone_data.get('auto_index_forwarded', True) else '❌ OFF'}"
        
        await message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in indexing status command: {e}")
        await message.reply_text("❌ Error loading indexing status.")

@Client.on_message(filters.command("indexstats") & filters.private)
async def clone_indexing_stats_command(client: Client, message: Message):
    """Show detailed indexing statistics for clone admin"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can view indexing statistics.")
    
    try:
        from bot.database.mongo_db import get_detailed_clone_stats
        stats = await get_detailed_clone_stats(str(clone_data.get('bot_id', clone_data.get('_id'))))
        
        if not stats:
            await message.reply_text("📊 **No indexing data found**\n\nStart indexing files to see statistics.")
            return
        
        stats_text = "📊 **Detailed Indexing Statistics**\n\n"
        stats_text += f"🤖 **Clone:** @{clone_data.get('username', 'Unknown')}\n\n"
        
        stats_text += f"📁 **Total Files:** {stats.get('total_files', 0):,}\n"
        stats_text += f"💾 **Total Size:** {format_file_size(stats.get('total_size', 0))}\n\n"
        
        # File type breakdown
        file_types = stats.get('file_types', {})
        if file_types:
            stats_text += "📋 **File Types:**\n"
            for file_type, count in file_types.items():
                stats_text += f"• {file_type.title()}: {count:,}\n"
            stats_text += "\n"
        
        # Quality breakdown for videos
        quality_stats = stats.get('quality_breakdown', {})
        if quality_stats:
            stats_text += "🎬 **Video Quality:**\n"
            for quality, count in quality_stats.items():
                stats_text += f"• {quality}: {count:,}\n"
            stats_text += "\n"
        
        # Recent activity
        stats_text += f"📅 **Recent Activity:**\n"
        stats_text += f"• Last indexed: {stats.get('last_indexed', 'Never')}\n"
        stats_text += f"• Files this week: {stats.get('files_this_week', 0):,}\n"
        stats_text += f"• Most active day: {stats.get('most_active_day', 'N/A')}\n\n"
        
        # Top channels
        top_channels = stats.get('top_channels', [])
        if top_channels:
            stats_text += "🔥 **Top Source Channels:**\n"
            for i, (channel_id, count) in enumerate(top_channels[:5], 1):
                stats_text += f"{i}. Channel {channel_id}: {count:,} files\n"
        
        await message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error in indexing stats command: {e}")
        await message.reply_text("❌ Error loading indexing statistics.")

@Client.on_message(filters.command("clearindex") & filters.private)
async def clear_index_command(client: Client, message: Message):
    """Clear all indexed files - ADMIN ONLY with confirmation"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can clear the index.")
    
    try:
        # Get current file count
        from bot.database.mongo_db import get_clone_index_stats
        stats = await get_clone_index_stats(str(clone_data.get('bot_id', clone_data.get('_id'))))
        file_count = stats.get('total_files', 0) if stats else 0
        
        if file_count == 0:
            await message.reply_text("📭 **Index is already empty**\n\nNo files to clear.")
            return
        
        # Show confirmation
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ CONFIRM CLEAR ALL", 
                               callback_data=f"confirm_clear_index:{clone_data.get('_id')}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        await message.reply_text(
            f"⚠️ **WARNING: Clear All Indexed Files**\n\n"
            f"🤖 **Clone:** @{clone_data.get('username', 'Unknown')}\n"
            f"📁 **Files to delete:** {file_count:,}\n\n"
            f"**This action will:**\n"
            f"• Delete ALL indexed files from your clone\n"
            f"• Remove ALL search data\n"
            f"• Clear ALL file metadata\n"
            f"• Make ALL files unsearchable\n\n"
            f"**⚠️ This action CANNOT be undone!**\n\n"
            f"Are you absolutely sure?",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error in clear index command: {e}")
        await message.reply_text("❌ Error processing clear index request.")

@Client.on_callback_query(filters.regex("^confirm_clear_index:"))
async def confirm_clear_index_callback(client: Client, query: CallbackQuery):
    """Confirm and execute index clearing"""
    try:
        clone_id = query.data.split(":")[1]
        
        # Verify admin access
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data or query.from_user.id != clone_data.get('admin_id'):
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        await query.answer("Clearing index... This may take a moment.", show_alert=True)
        
        # Clear the index
        from bot.database.mongo_db import clear_clone_index
        result = await clear_clone_index(clone_id)
        
        if result:
            await query.edit_message_text(
                "✅ **Index Cleared Successfully**\n\n"
                f"🤖 **Clone:** @{clone_data.get('username', 'Unknown')}\n"
                f"🗑️ **All indexed files deleted**\n"
                f"🔍 **Search data cleared**\n\n"
                f"💡 You can start indexing new files anytime using `/index` commands."
            )
        else:
            await query.edit_message_text(
                "❌ **Error Clearing Index**\n\n"
                "Failed to clear the index. Please try again later."
            )
        
    except Exception as e:
        logger.error(f"Error confirming clear index: {e}")
        await query.answer("❌ Error clearing index.", show_alert=True)

@Client.on_message(filters.command("togglemediaonly") & filters.private)
async def toggle_media_only_command(client: Client, message: Message):
    """Toggle media-only indexing setting"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can change indexing settings.")
    
    try:
        bot_id = str(clone_data.get('bot_id'))
        current_setting = clone_data.get('index_media_only', True)
        new_setting = not current_setting
        
        await update_clone_config(bot_id, {"index_media_only": new_setting})
        
        status = "enabled" if new_setting else "disabled"
        description = "Only media files" if new_setting else "All message types"
        
        await message.reply_text(
            f"✅ **Media-only indexing {status}**\n\n"
            f"🔧 **Setting:** {description} will be indexed\n"
            f"💡 This affects new indexing operations only."
        )
        
    except Exception as e:
        logger.error(f"Error toggling media only: {e}")
        await message.reply_text("❌ Error updating setting.")

@Client.on_message(filters.command("toggleautoindex") & filters.private)
async def toggle_auto_index_command(client: Client, message: Message):
    """Toggle auto-indexing of forwarded messages"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can change auto-indexing settings.")
    
    try:
        bot_id = str(clone_data.get('bot_id'))
        current_setting = clone_data.get('auto_index_forwarded', True)
        new_setting = not current_setting
        
        await update_clone_config(bot_id, {"auto_index_forwarded": new_setting})
        
        status = "enabled" if new_setting else "disabled"
        
        await message.reply_text(
            f"✅ **Auto-indexing {status}**\n\n"
            f"🔧 **Setting:** Forwarded media will {'be automatically indexed' if new_setting else 'require manual indexing'}\n"
            f"💡 This affects forwarded messages from admins only."
        )
        
    except Exception as e:
        logger.error(f"Error toggling auto index: {e}")
        await message.reply_text("❌ Error updating setting.")

@Client.on_message(filters.command("indexhelp") & filters.private)
async def indexing_help_command(client: Client, message: Message):
    """Show comprehensive indexing help"""
    user_id = message.from_user.id
    
    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    # Verify admin access
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can access indexing help.")
    
    help_text = """
📚 **Complete Indexing Guide**

🎯 **Basic Commands:**
• `/index <link>` - Index from Telegram channel link
• `/index <start> <end>` - Index message range (reply to forwarded message)
• `/index <channel_id> <start> <end>` - Index specific channel range

📝 **Examples:**
• `/index https://t.me/channel/123`
• `/index 100 500`
• `/index -1001234567890 1 1000`

🔄 **Batch Operations:**
• `/batchindex` - Start batch indexing session
• Add multiple channels, then `/startbatch`
• `/cancelbatch` - Cancel batch session

⚙️ **Settings:**
• `/skipdup` - Toggle skip duplicates
• `/togglemediaonly` - Toggle media-only indexing
• `/toggleautoindex` - Toggle auto-indexing forwarded files

📊 **Statistics:**
• `/indexstatus` - Show indexing status
• `/indexstats` - Detailed statistics
• `/clearindex` - Clear all indexed files (⚠️ WARNING)

🛡️ **Admin Only:**
All indexing commands are restricted to clone administrators only.

💡 **Tips:**
• Bot must be admin in channels to index
• Large ranges may take time to process
• Use batch indexing for multiple channels
• Auto-indexing works on forwarded admin messages
"""
    
    await message.reply_text(help_text)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
