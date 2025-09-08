
"""
Statistics plugin for tracking bot usage and performance
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Show bot statistics"""
    try:
        user_id = message.from_user.id
        
        # Check if user is admin
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            await message.reply_text("❌ This command is only for administrators.")
            return
        
        # Basic stats
        stats_text = f"📊 **Bot Statistics**\n\n"
        stats_text += f"🤖 **Mother Bot:** Active\n"
        stats_text += f"📅 **Uptime:** Available\n"
        stats_text += f"🔧 **Status:** Running\n\n"
        stats_text += f"💾 **Database:** Connected\n"
        stats_text += f"🌐 **Web Dashboard:** Active"
        
        await message.reply_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")],
                [InlineKeyboardButton("« Back to Menu", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error loading statistics. Please try again.")

@Client.on_callback_query(filters.regex("^refresh_stats$"))
async def refresh_stats_callback(client: Client, query):
    """Refresh statistics"""
    try:
        await query.answer("🔄 Refreshing statistics...")
        
        # Basic stats
        stats_text = f"📊 **Bot Statistics** (Updated)\n\n"
        stats_text += f"🤖 **Mother Bot:** Active\n"
        stats_text += f"📅 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        stats_text += f"🔧 **Status:** Running\n\n"
        stats_text += f"💾 **Database:** Connected\n"
        stats_text += f"🌐 **Web Dashboard:** Active"
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")],
                [InlineKeyboardButton("« Back to Menu", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        await query.answer("❌ Error refreshing statistics.", show_alert=True)

@Client.on_message(filters.command("stats") & filters.private)
async def show_stats(client: Client, message: Message):
    """Show bot statistics"""
    try:
        if not await is_admin(message.from_user.id):
            await message.reply_text("❌ You don't have permission to use this command.")
            return
            
        # Get various statistics
        from bot.database.users import get_total_users
        from bot.database.clone_db import get_total_clones, get_active_clones_count
        
        total_users = await get_total_users()
        total_clones = await get_total_clones()
        active_clones = await get_active_clones_count()
        
        # Bot uptime
        from bot.utils.system_monitor import get_uptime
        uptime = get_uptime()
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Detailed Stats", callback_data="detailed_stats"),
                InlineKeyboardButton("📈 Usage Stats", callback_data="usage_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
                InlineKeyboardButton("❌ Close", callback_data="close_stats")
            ]
        ])
        
        text = f"📊 **Bot Statistics**\n\n"
        text += f"👥 **Users:** `{total_users}`\n"
        text += f"🤖 **Total Clones:** `{total_clones}`\n"
        text += f"✅ **Active Clones:** `{active_clones}`\n"
        text += f"⏰ **Uptime:** `{uptime}`\n"
        text += f"📅 **Date:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        await message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.reply_text("❌ Error retrieving statistics.")

@Client.on_callback_query(filters.regex("detailed_stats"))
async def detailed_stats(client: Client, query):
    """Show detailed statistics"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        # Get detailed stats
        from bot.database.users import get_users_by_date
        from bot.database.clone_db import get_clones_by_status
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        users_today = await get_users_by_date(today)
        users_yesterday = await get_users_by_date(yesterday)
        users_week = await get_users_by_date(week_ago)
        
        pending_clones = await get_clones_by_status('pending')
        active_clones = await get_clones_by_status('active')
        expired_clones = await get_clones_by_status('expired')
        
        text = f"📈 **Detailed Statistics**\n\n"
        text += f"📅 **User Growth:**\n"
        text += f"   • Today: `{len(users_today)}`\n"
        text += f"   • Yesterday: `{len(users_yesterday)}`\n"
        text += f"   • This Week: `{len(users_week)}`\n\n"
        text += f"🤖 **Clone Status:**\n"
        text += f"   • Active: `{len(active_clones)}`\n"
        text += f"   • Pending: `{len(pending_clones)}`\n"
        text += f"   • Expired: `{len(expired_clones)}`\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="refresh_stats")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing detailed stats: {e}")
        await query.answer("❌ Error retrieving detailed stats!")

@Client.on_callback_query(filters.regex("usage_stats"))
async def usage_stats(client: Client, query):
    """Show usage statistics"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        # Get usage stats
        from bot.database.command_usage_db import get_command_usage_stats
        
        command_stats = await get_command_usage_stats()
        
        text = f"📊 **Usage Statistics**\n\n"
        text += f"🔢 **Top Commands:**\n"
        
        for i, (command, count) in enumerate(command_stats[:10], 1):
            text += f"   {i}. `{command}`: {count} uses\n"
            
        # System stats
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            text += f"\n🖥️ **System Usage:**\n"
            text += f"   • CPU: `{cpu_percent}%`\n"
            text += f"   • RAM: `{memory.percent}%`\n"
            text += f"   • Disk: `{disk.percent}%`\n"
        except:
            text += f"\n🖥️ **System Usage:** Not available\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="refresh_stats")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing usage stats: {e}")
        await query.answer("❌ Error retrieving usage stats!")

@Client.on_callback_query(filters.regex("refresh_stats"))
async def refresh_stats(client: Client, query):
    """Refresh statistics"""
    try:
        await query.answer("🔄 Refreshing stats...")
        
        # Recreate the main stats message
        from bot.database.users import get_total_users
        from bot.database.clone_db import get_total_clones, get_active_clones_count
        
        total_users = await get_total_users()
        total_clones = await get_total_clones()
        active_clones = await get_active_clones_count()
        
        from bot.utils.system_monitor import get_uptime
        uptime = get_uptime()
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Detailed Stats", callback_data="detailed_stats"),
                InlineKeyboardButton("📈 Usage Stats", callback_data="usage_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
                InlineKeyboardButton("❌ Close", callback_data="close_stats")
            ]
        ])
        
        text = f"📊 **Bot Statistics**\n\n"
        text += f"👥 **Users:** `{total_users}`\n"
        text += f"🤖 **Total Clones:** `{total_clones}`\n"
        text += f"✅ **Active Clones:** `{active_clones}`\n"
        text += f"⏰ **Uptime:** `{uptime}`\n"
        text += f"📅 **Date:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        await query.answer("❌ Error refreshing stats!")

@Client.on_callback_query(filters.regex("close_stats"))
async def close_stats(client: Client, query):
    """Close statistics"""
    try:
        await query.message.delete()
    except:
        pass
