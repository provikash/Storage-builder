
import asyncio
import uuid
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

# Store admin sessions to prevent unauthorized access
admin_sessions = {}

# Helper function to check Mother Bot admin permissions
def is_mother_admin(user_id):
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    
    if isinstance(admins, tuple):
        admin_list = list(admins)
    else:
        admin_list = admins if isinstance(admins, list) else []

    is_owner = user_id == owner_id
    is_admin = user_id in admin_list
    return is_owner or is_admin

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command_handler(client: Client, message: Message):
    """Main admin command handler - routes to appropriate panel"""
    user_id = message.from_user.id
    
    # Check if this is Mother Bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    is_clone = config['bot_info'].get('is_clone', False)
    
    if not is_clone:
        # This is Mother Bot - check for Mother Bot admin
        if is_mother_admin(user_id):
            await mother_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only Mother Bot administrators can access this panel.")
    else:
        # Clone bot - handled elsewhere
        await message.reply_text("❌ This command is for Mother Bot only.")

async def mother_admin_panel(client: Client, query_or_message):
    """Display Mother Bot admin panel with comprehensive options"""
    user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id
    
    # Check admin permissions
    if not is_mother_admin(user_id):
        if hasattr(query_or_message, 'answer'):
            await query_or_message.answer("❌ Unauthorized access!", show_alert=True)
            return
        else:
            await query_or_message.reply_text("❌ You don't have permission to access this panel.")
            return

    # Get statistics
    try:
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())
    except Exception as e:
        total_clones = active_clones = running_clones = total_subscriptions = 0

    panel_text = f"🎛️ **Mother Bot Admin Panel**\n\n"
    panel_text += f"📊 **System Overview:**\n"
    panel_text += f"• Total Clones: {total_clones}\n"
    panel_text += f"• Active Clones: {active_clones}\n"
    panel_text += f"• Running Clones: {running_clones}\n"
    panel_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
    panel_text += f"🕐 **Panel Access Time:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Manage Clones", callback_data="mother_manage_clones")],
        [InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions")],
        [InlineKeyboardButton("💳 User Balances", callback_data="mother_user_balances")],
        [InlineKeyboardButton("⚙️ Global Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("📊 System Statistics", callback_data="mother_statistics")]
    ])

    # Store admin session
    admin_sessions[user_id] = {
        'type': 'mother_admin',
        'timestamp': datetime.now(),
        'last_content': panel_text
    }

    if hasattr(query_or_message, 'edit_message_text'):
        try:
            await query_or_message.edit_message_text(panel_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" in str(e):
                await query_or_message.answer("Panel refreshed!", show_alert=False)
            else:
                await query_or_message.answer("❌ Error updating panel!", show_alert=True)
    else:
        await query_or_message.reply_text(panel_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
