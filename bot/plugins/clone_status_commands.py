
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.clone_db import get_clone_by_bot_token, get_all_clones
from bot.database.mongo_db import get_clone_database_stats

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

@Client.on_message(filters.command(['clones', 'clonestatus']) & filters.private)
async def clones_status_command(client: Client, message: Message):
    """Show clone status - works in both mother bot and clone bots"""
    try:
        user_id = message.from_user.id
        
        # Check if this is mother bot or clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_mother_bot = bot_token == Config.BOT_TOKEN
        
        if is_mother_bot:
            # Mother bot - show all clones (admin only)
            # Add admin check here if needed
            await show_all_clones_status(client, message)
        else:
            # Clone bot - show this clone's status
            clone_data = await get_clone_by_bot_token(bot_token)
            if not clone_data:
                await message.reply_text("❌ Clone configuration not found.")
                return
            
            # Check if user is admin of this clone
            if user_id != clone_data['admin_id']:
                await message.reply_text("❌ Only clone admin can view clone status.")
                return
            
            await show_single_clone_status(client, message, clone_data)
        
    except Exception as e:
        logger.error(f"Error in clones status command: {e}")
        await message.reply_text("❌ Error retrieving clone status.")

async def show_all_clones_status(client: Client, message: Message):
    """Show status of all clones (mother bot)"""
    try:
        all_clones = await get_all_clones()
        
        if not all_clones:
            await message.reply_text("📋 **Clone Status**\n\nNo clones found.")
            return
        
        text = f"📋 **All Clones Status** ({len(all_clones)} total)\n\n"
        
        active_count = 0
        inactive_count = 0
        
        for clone in all_clones[:10]:  # Show first 10
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'unknown')
            bot_id = clone.get('bot_id', 'unknown')
            
            if status == 'active':
                status_emoji = "🟢"
                active_count += 1
            elif status == 'pending_payment':
                status_emoji = "🟡"
            else:
                status_emoji = "🔴"
                inactive_count += 1
            
            text += f"{status_emoji} **@{username}** (`{bot_id}`)\n"
            text += f"   Status: {status.title()}\n\n"
        
        if len(all_clones) > 10:
            text += f"... and {len(all_clones) - 10} more clones\n\n"
        
        text += f"📊 **Summary:**\n"
        text += f"🟢 Active: {active_count}\n"
        text += f"🔴 Inactive: {inactive_count}\n"
        text += f"🟡 Pending: {len(all_clones) - active_count - inactive_count}"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_all_clones"),
                InlineKeyboardButton("📊 Detailed Stats", callback_data="detailed_clone_stats")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error showing all clones status: {e}")
        await message.reply_text("❌ Error retrieving clones status.")

async def show_single_clone_status(client: Client, message: Message, clone_data: dict):
    """Show status of single clone"""
    try:
        username = clone_data.get('username', 'Unknown')
        status = clone_data.get('status', 'unknown')
        bot_id = clone_data.get('bot_id', 'unknown')
        admin_id = clone_data.get('admin_id', 'unknown')
        created_at = clone_data.get('created_at', 'Unknown')
        
        # Get database stats
        clone_id = str(bot_id)
        db_stats = await get_clone_database_stats(clone_id)
        
        text = f"📋 **Clone Status**\n\n"
        text += f"🤖 **Bot:** @{username}\n"
        text += f"🆔 **Bot ID:** `{bot_id}`\n"
        text += f"👤 **Admin ID:** `{admin_id}`\n"
        text += f"📅 **Created:** {created_at}\n\n"
        
        # Status
        if status == 'active':
            status_emoji = "🟢"
        elif status == 'pending_payment':
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"
        
        text += f"📊 **Status:** {status_emoji} {status.title()}\n\n"
        
        # Database stats
        if db_stats:
            text += f"💾 **Database Stats:**\n"
            text += f"• Files: `{db_stats['total_files']:,}`\n"
            text += f"• Users: `{db_stats['total_users']:,}`\n"
            text += f"• Size: `{get_readable_file_size(db_stats['total_size'])}`\n"
            text += f"• Recent (24h): `{db_stats['recent_files']}`\n\n"
        else:
            text += f"💾 **Database:** Not accessible\n\n"
        
        # Features status
        text += f"⚙️ **Features:**\n"
        text += f"• Random Files: {'✅' if clone_data.get('random_mode', False) else '❌'}\n"
        text += f"• Recent Files: {'✅' if clone_data.get('recent_mode', False) else '❌'}\n"
        text += f"• Popular Files: {'✅' if clone_data.get('popular_mode', False) else '❌'}\n"
        text += f"• Auto-Index: {'✅' if clone_data.get('auto_index_forwarded', True) else '❌'}\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_clone_status:{clone_id}"),
                InlineKeyboardButton("🗄️ Database Test", callback_data=f"clone_test_db:{clone_id}")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings_panel"),
                InlineKeyboardButton("📊 Full Stats", callback_data=f"clone_refresh_stats:{clone_id}")
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error showing single clone status: {e}")
        await message.reply_text("❌ Error retrieving clone status.")

def get_readable_file_size(size_bytes):
    """Convert bytes to readable format"""
    if size_bytes == 0:
        return "0 B"
    size_name = ["B", "KB", "MB", "GB", "TB"]
    i = int(size_bytes.bit_length() // 10) if size_bytes > 0 else 0
    if i >= len(size_name):
        i = len(size_name) - 1
    p = 1024 ** i
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@Client.on_callback_query(filters.regex("^refresh_clone_status:"))
async def handle_refresh_clone_status(client: Client, query):
    """Handle refresh clone status callback"""
    try:
        clone_id = query.data.split(":")[1]
        
        await query.answer("Refreshing clone status...", show_alert=False)
        
        # Get updated clone data
        from bot.database.clone_db import get_clone
        clone_data = await get_clone(clone_id)
        
        if not clone_data:
            await query.edit_message_text("❌ Clone not found.")
            return
        
        await show_single_clone_status(client, query, clone_data)
        
    except Exception as e:
        logger.error(f"Error refreshing clone status: {e}")
        await query.answer("❌ Error refreshing status.", show_alert=True)
