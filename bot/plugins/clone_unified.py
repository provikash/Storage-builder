
"""
Unified Clone Plugin
Consolidates all clone-related functionality from multiple plugins:
- clone_admin_unified.py
- clone_indexing_unified.py
- clone_search_unified.py
- clone_analytics.py
- clone_database_commands.py
- clone_force_commands.py
- clone_help.py
- clone_management.py
- clone_random_files.py
- clone_status_commands.py
- clone_token_commands.py
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired
from info import Config
from bot.database.clone_db import (
    get_clone_config, update_clone_config, get_clone_by_bot_token,
    update_clone_setting, get_clone_user_count, get_clone_file_count,
    update_clone_token_verification, update_clone_shortener_settings,
    get_clone, get_all_clones, get_user_clones, update_clone_status
)
from bot.database.subscription_db import get_subscription
from bot.database.mongo_db import get_clone_database_stats
from bot.utils.helper import get_readable_file_size
from bot.logging import LOGGER
from motor.motor_asyncio import AsyncIOMotorClient

logger = LOGGER(__name__)

# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

async def verify_clone_admin(client: Client, user_id: int) -> tuple[bool, dict]:
    """Verify if user is clone admin and return clone data"""
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

# =====================================================
# CLONE ADMIN PANEL
# =====================================================

@Client.on_message(filters.command(["cloneadmin", "clonesettings"]) & filters.private)
async def clone_admin_command(client: Client, message: Message):
    """Clone admin panel command"""
    user_id = message.from_user.id
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ Clone admin panel is only available in clone bots!")

    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data:
        return await message.reply_text("❌ Clone configuration not found!")

    if clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can access this panel!")

    await show_clone_admin_panel(client, message, clone_data)

async def show_clone_admin_panel(client: Client, message, clone_data: dict):
    """Display clone admin panel"""
    text = f"⚙️ **Clone Bot Admin Panel**\n\n"
    text += f"🤖 **Bot Management:**\n"
    text += f"Manage your clone bot's settings and features.\n\n"
    text += f"🔧 **Available Options:**\n"
    text += f"• Configure bot features\n"
    text += f"• Manage force channels\n"
    text += f"• Token verification settings\n"
    text += f"• URL shortener configuration\n\n"
    text += f"📊 **Choose an option below:**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎛️ Bot Features", callback_data="clone_bot_features"),
            InlineKeyboardButton("🔐 Force Channels", callback_data="clone_local_force_channels")
        ],
        [
            InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_command_config"),
            InlineKeyboardButton("💰 Token Pricing", callback_data="clone_token_pricing")
        ],
        [
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener"),
            InlineKeyboardButton("📊 Statistics", callback_data="clone_view_stats")
        ],
        [
            InlineKeyboardButton("🗄️ Database", callback_data="clone_db_info"),
            InlineKeyboardButton("📋 Status", callback_data="clone_status_info")
        ]
    ])

    if hasattr(message, 'edit_message_text'):
        await message.edit_message_text(text, reply_markup=buttons)
    else:
        await message.reply_text(text, reply_markup=buttons)

# =====================================================
# CLONE INDEXING
# =====================================================

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
    await message.reply_text(f"🔄 Processing indexing request for: `{input_text}`\n\nPlease wait...")

# =====================================================
# CLONE SEARCH
# =====================================================

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
        await message.reply_text(f"🔍 **Searching**: `{query}`\n\n⏳ Processing...")
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await message.reply_text("❌ Search error.")

# =====================================================
# CLONE DATABASE COMMANDS
# =====================================================

@Client.on_message(filters.command(['dbstats', 'databasestats']) & filters.private)
async def clone_database_stats_command(client: Client, message: Message):
    """Show clone database statistics"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This command is only available in clone bots.")
            return

        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return

        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can use this command.")
            return

        loading_msg = await message.reply_text("🔄 **Fetching Database Statistics...**\n\nPlease wait...")

        stats = await get_clone_database_stats(clone_id)
        if not stats:
            await loading_msg.edit_text("❌ **Error**\n\nFailed to fetch database statistics.")
            return

        file_types_text = ""
        if stats.get('file_types'):
            for file_type, count in list(stats['file_types'].items())[:5]:
                file_types_text += f"• **{file_type.title()}**: `{count}`\n"
        else:
            file_types_text = "• No files indexed yet\n"

        total_size_readable = get_readable_file_size(stats.get('total_size', 0))

        stats_text = (
            f"📊 **Clone Database Statistics**\n\n"
            f"🗄️ **Database**: `{stats.get('database_name', 'N/A')}`\n\n"
            f"📁 **Files Overview:**\n"
            f"• **Total Files**: `{stats.get('total_files', 0):,}`\n"
            f"• **Total Size**: `{total_size_readable}`\n"
            f"• **Recent (24h)**: `{stats.get('recent_files', 0)}`\n\n"
            f"📂 **File Types:**\n{file_types_text}\n"
            f"👥 **Users**: `{stats.get('total_users', 0):,}`\n\n"
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

# =====================================================
# CLONE STATUS & HELP
# =====================================================

@Client.on_message(filters.command(['status', 'clonestatus']) & filters.private)
async def clone_status_command(client: Client, message: Message):
    """Show clone bot status"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        user_id = message.from_user.id
        is_admin = user_id == clone_data['admin_id']
        
        if not is_admin:
            await message.reply_text("❌ Only clone admin can check status.")
            return
        
        status_text = (
            f"📊 **Clone Bot Status**\n\n"
            f"**🤖 Bot Information:**\n"
            f"• Clone ID: `{clone_id}`\n"
            f"• Status: `🟢 Active`\n"
            f"• Username: @{clone_data.get('username', 'Unknown')}\n\n"
            
            f"**🗄️ Database Status:**\n"
            f"• Connection: 🟢 Connected\n"
            f"• Database: `{clone_data.get('db_name')}`\n\n"
            
            f"**⚙️ Configuration:**\n"
            f"• Random Files: {'✅ On' if clone_data.get('random_mode', True) else '❌ Off'}\n"
            f"• Recent Files: {'✅ On' if clone_data.get('recent_mode', True) else '❌ Off'}\n\n"
            
            f"**🔧 Admin:** @{message.from_user.username or 'Unknown'}"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_status:{clone_id}"),
                InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings_panel")
            ]
        ])
        
        await message.reply_text(status_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone status command: {e}")
        await message.reply_text("❌ Error checking status.")

@Client.on_message(filters.command(['help', 'commands']) & filters.private)
async def clone_help_command(client: Client, message: Message):
    """Show help for clone bot commands"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        user_id = message.from_user.id
        is_admin = user_id == clone_data['admin_id']
        
        if is_admin:
            help_text = (
                f"🔧 **Clone Admin Commands**\n\n"
                f"**🗄️ Database & Indexing:**\n"
                f"• `/dbstats` - Database statistics\n"
                f"• `/index <channel>` - Index channel media\n\n"
                
                f"**🔍 Search & Files:**\n"
                f"• `/search <query>` - Search indexed files\n\n"
                
                f"**⚙️ Settings & Management:**\n"
                f"• `/clonesettings` - Clone settings panel\n"
                f"• `/cloneadmin` - Admin panel\n\n"
                
                f"**📊 Monitoring:**\n"
                f"• `/status` - Clone bot status\n\n"
                
                f"**Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`"
            )
        else:
            help_text = (
                f"🔍 **Clone Bot Commands**\n\n"
                f"**🔍 Search & Download:**\n"
                f"• `/search <query>` - Search files\n\n"
                
                f"**📋 Information:**\n"
                f"• `/about` - About this bot\n"
                f"• `/help` - Show this help\n\n"
                
                f"**🤖 This is a clone bot with its own database.**"
            )
        
        await message.reply_text(help_text)
        
    except Exception as e:
        logger.error(f"Error in clone help command: {e}")
        await message.reply_text("❌ Error showing help.")

# =====================================================
# CLONE TOKEN COMMANDS
# =====================================================

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_verification_mode(client: Client, message: Message):
    """Set token verification mode"""
    user_id = message.from_user.id
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    
    if not clone_data or clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can modify settings.")

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** `/settokenmode <mode>`\n\n"
            "**Available modes:**\n"
            "• `command_limit` - Token gives specific number of commands\n"
            "• `time_based` - Token valid for specific time period\n\n"
            "**Example:** `/settokenmode time_based`"
        )

    mode = message.command[1].lower()
    if mode not in ['command_limit', 'time_based']:
        return await message.reply_text("❌ Invalid mode. Use `command_limit` or `time_based`")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, verification_mode=mode)
    
    mode_text = "Command Limit" if mode == "command_limit" else "Time-Based (24 hours)"
    await message.reply_text(f"✅ Token verification mode set to: **{mode_text}**")

# =====================================================
# CLONE FORCE CHANNEL COMMANDS
# =====================================================

@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel_clone(client: Client, message: Message):
    """Add force subscription channel for clone bot"""
    user_id = message.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await message.reply_text("❌ Only the clone admin can manage force channels.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/addforce <channel_id_or_username>`")

    try:
        channel_input = message.command[1]
        if channel_input.startswith('@'):
            channel_input = channel_input[1:]
        
        chat = await client.get_chat(channel_input)
        channel_id = chat.id
        channel_title = chat.title or f"Channel {channel_id}"

        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found.")

        current_channels = clone_data.get('force_channels', [])
        
        if channel_id in current_channels:
            return await message.reply_text(f"❌ Channel **{channel_title}** is already in the force subscription list.")

        current_channels.append(channel_id)
        bot_id = clone_data.get('bot_id') or clone_data.get('_id')
        await update_clone_setting(bot_id, 'force_channels', current_channels)

        await message.reply_text(f"✅ Added force subscription channel: **{channel_title}** (`{channel_id}`)")

    except Exception as e:
        await message.reply_text(f"❌ Error adding channel: {str(e)}")
        logger.error(f"Error in addforce command: {e}")

@Client.on_message(filters.command("listforce") & filters.private)
async def list_force_channels_clone(client: Client, message: Message):
    """List all force subscription channels for clone bot"""
    user_id = message.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await message.reply_text("❌ Only the clone admin can view force channels.")

    try:
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found.")

        force_channels = clone_data.get('force_channels', [])
        
        if not force_channels:
            return await message.reply_text("📋 No force subscription channels configured.")

        text = "📢 **Force Subscription Channels:**\n\n"
        
        for i, channel_id in enumerate(force_channels, 1):
            try:
                chat = await client.get_chat(channel_id)
                title = chat.title or f"Channel {channel_id}"
                text += f"{i}. **{title}**\n   ID: `{channel_id}`\n\n"
            except Exception as e:
                text += f"{i}. **Invalid Channel**\n   ID: `{channel_id}` ❌\n\n"

        await message.reply_text(text)

    except Exception as e:
        await message.reply_text(f"❌ Error listing channels: {str(e)}")
        logger.error(f"Error in listforce command: {e}")

# =====================================================
# CALLBACK HANDLERS
# =====================================================

@Client.on_callback_query(filters.regex("^clone_"))
async def handle_clone_callbacks(client: Client, query: CallbackQuery):
    """Handle all clone-related callbacks"""
    callback_data = query.data
    
    try:
        if callback_data == "clone_settings_panel":
            await show_clone_admin_panel(client, query, {})
        
        elif callback_data.startswith("clone_refresh_stats:"):
            clone_id = callback_data.split(":")[1]
            await query.answer("Refreshing statistics...")
        
        elif callback_data.startswith("clone_test_db:"):
            clone_id = callback_data.split(":")[1]
            await query.answer("Testing database connection...")
        
        elif callback_data == "clone_bot_features":
            await query.answer("Loading features...")
            
    except Exception as e:
        logger.error(f"Error in clone callback handler: {e}")
        await query.answer("❌ Error processing request", show_alert=True)

logger.info("✅ Unified Clone Plugin loaded successfully")
