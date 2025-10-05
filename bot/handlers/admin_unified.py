
"""
Unified Admin Handler
Consolidates all admin-related functionality from multiple files into one
"""
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.database.balance_db import *
from bot.database import full_userbase, del_user, add_premium_user, remove_premium, get_users_count
from bot.database.premium_db import get_all_premium_users
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager
from bot.logging import LOGGER
from dotenv import set_key

logger = LOGGER(__name__)

# Store admin sessions
admin_sessions = {}

# Premium plans
PREMIUM_PLANS = {
    "monthly": {
        "name": "Monthly Plan",
        "price": "$2.99",
        "duration": "1 Month",
        "per_month": "$2.99",
        "discount": "0%",
        "description": "Simple, accessible entry point"
    },
    "quarterly": {
        "name": "3-Month Plan", 
        "price": "$7.99",
        "duration": "3 Months",
        "per_month": "$2.66",
        "discount": "11%",
        "description": "Slight discount for commitment"
    },
    "biannual": {
        "name": "6-Month Plan",
        "price": "$14.99", 
        "duration": "6 Months",
        "per_month": "$2.50",
        "discount": "16%",
        "description": "Moderate discount for longer commitment"
    },
    "annual": {
        "name": "12-Month Plan",
        "price": "$26.99",
        "duration": "12 Months", 
        "per_month": "$2.25",
        "discount": "25%",
        "description": "Best value with maximum savings"
    }
}

# =====================================================
# PERMISSION HELPERS
# =====================================================

def is_mother_admin(user_id: int) -> bool:
    """Check if user is Mother Bot admin"""
    try:
        owner_id = getattr(Config, 'OWNER_ID', None)
        admins = getattr(Config, 'ADMINS', ())
        
        if isinstance(admins, tuple):
            admin_list = list(admins)
        else:
            admin_list = admins if isinstance(admins, list) else []
        
        return user_id == owner_id or user_id in admin_list
    except Exception as e:
        logger.error(f"Error checking mother admin: {e}")
        return False

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is clone bot admin"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False
        
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return False
            
        return int(user_id) == int(clone_data.get('admin_id', 0))
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

# =====================================================
# MAIN ADMIN COMMAND
# =====================================================

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command_handler(client: Client, message: Message):
    """Main admin command - routes to appropriate panel"""
    user_id = message.from_user.id
    logger.info(f"Admin command from user {user_id}")
    
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    is_clone = config['bot_info'].get('is_clone', False)
    
    if not is_clone:
        # Mother Bot
        if is_mother_admin(user_id):
            await mother_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only Mother Bot administrators can access this panel.")
    else:
        # Clone Bot
        if await is_clone_admin(client, user_id):
            await clone_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only the clone administrator can access this panel.")

# =====================================================
# MOTHER BOT ADMIN PANEL
# =====================================================

async def mother_admin_panel(client: Client, query_or_message):
    """Display Mother Bot admin panel"""
    user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id
    
    if not is_mother_admin(user_id):
        if hasattr(query_or_message, 'answer'):
            await query_or_message.answer("❌ Unauthorized!", show_alert=True)
            return
        else:
            await query_or_message.reply_text("❌ Access denied.")
            return
    
    try:
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())
    except:
        total_clones = active_clones = running_clones = total_subscriptions = 0
    
    panel_text = f"🎛️ **Mother Bot Admin Panel**\n\n"
    panel_text += f"📊 **System Overview:**\n"
    panel_text += f"• Total Clones: {total_clones}\n"
    panel_text += f"• Active Clones: {active_clones}\n"
    panel_text += f"• Running Clones: {running_clones}\n"
    panel_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
    panel_text += f"🕐 **Panel Access:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Manage Clones", callback_data="mother_manage_clones")],
        [InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions")],
        [InlineKeyboardButton("💳 User Balances", callback_data="mother_user_balances")],
        [InlineKeyboardButton("⚙️ Global Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("📊 Statistics", callback_data="mother_statistics")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="mother_broadcast")]
    ])
    
    admin_sessions[user_id] = {
        'type': 'mother_admin',
        'timestamp': datetime.now(),
        'last_content': panel_text
    }
    
    if hasattr(query_or_message, 'edit_message_text'):
        try:
            await query_or_message.edit_message_text(panel_text, reply_markup=buttons)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" in str(e):
                await query_or_message.answer("Panel refreshed!", show_alert=False)
    else:
        await query_or_message.reply_text(panel_text, reply_markup=buttons)

# =====================================================
# CLONE ADMIN PANEL
# =====================================================

async def clone_admin_panel(client: Client, message: Message):
    """Clone Bot admin panel"""
    user_id = message.from_user.id
    
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not await is_clone_admin(client, user_id):
        return await message.reply_text("❌ Unauthorized access.")
    
    admin_sessions[user_id] = {'type': 'clone', 'timestamp': datetime.now(), 'bot_token': bot_token}
    
    me = await client.get_me()
    subscription = config.get('subscription', {})
    
    panel_text = f"⚙️ **Clone Admin Panel**\n"
    panel_text += f"🤖 **Bot:** @{me.username}\n\n"
    panel_text += f"📊 **Status:**\n"
    panel_text += f"• Subscription: {subscription.get('tier', 'Unknown')}\n"
    panel_text += f"• Status: {subscription.get('status', 'Unknown')}\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Force Channels", callback_data="clone_local_force_channels")],
        [InlineKeyboardButton("🔔 Request Channels", callback_data="clone_request_channels")],
        [InlineKeyboardButton("🎫 Token Settings", callback_data="clone_token_command_config")],
        [InlineKeyboardButton("💰 Token Pricing", callback_data="clone_token_pricing")],
        [InlineKeyboardButton("⚙️ Bot Features", callback_data="clone_bot_features")],
        [InlineKeyboardButton("📊 Subscription", callback_data="clone_subscription_status")]
    ])
    
    await message.reply_text(panel_text, reply_markup=buttons)

# =====================================================
# MOTHER BOT CALLBACKS
# =====================================================

@Client.on_callback_query(filters.regex("^mother_"), group=0)
async def mother_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Mother Bot callbacks"""
    user_id = query.from_user.id
    
    if not is_mother_admin(user_id):
        return await query.answer("❌ Unauthorized!", show_alert=True)
    
    callback_data = query.data
    
    if callback_data == "mother_manage_clones":
        await handle_manage_clones(client, query)
    elif callback_data == "mother_statistics":
        await handle_statistics(client, query)
    elif callback_data == "mother_broadcast":
        await handle_broadcast_info(client, query)
    elif callback_data == "back_to_mother_panel":
        await mother_admin_panel(client, query)
    else:
        await query.answer("⚠️ Feature in development", show_alert=True)

async def handle_manage_clones(client: Client, query: CallbackQuery):
    """Show clone management"""
    clones = await get_all_clones()
    running_clones = clone_manager.get_running_clones()
    
    if not clones:
        text = "📝 **No Clones Found**\n\nCreate a clone to get started!"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")]
        ])
        await query.edit_message_text(text, reply_markup=buttons)
        return
    
    text = f"🤖 **Clone Management** ({len(clones)} total)\n\n"
    buttons = []
    
    for clone in clones[:10]:
        status_emoji = "🟢" if clone['_id'] in running_clones else "🔴"
        text += f"{status_emoji} @{clone.get('username', 'Unknown')}\n"
        buttons.append([
            InlineKeyboardButton(
                f"⚙️ {clone.get('username', clone['_id'][:8])}", 
                callback_data=f"manage_clone#{clone['_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def handle_statistics(client: Client, query: CallbackQuery):
    """Show statistics"""
    try:
        total_users = await get_users_count()
        all_clones = await get_all_clones()
        active_clones = len([c for c in all_clones if c.get('status') == 'active'])
        
        text = f"📊 **System Statistics**\n\n"
        text += f"👥 Total Users: {total_users:,}\n"
        text += f"🤖 Total Clones: {len(all_clones)}\n"
        text += f"✅ Active Clones: {active_clones}\n"
        text += f"❌ Inactive: {len(all_clones) - active_clones}\n"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")]
        ])
        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

async def handle_broadcast_info(client: Client, query: CallbackQuery):
    """Show broadcast information"""
    text = "📢 **Broadcast Message**\n\n"
    text += "To broadcast a message:\n"
    text += "1. Use `/broadcast` command\n"
    text += "2. Reply to any message with `/broadcast`\n\n"
    text += "The message will be sent to all users."
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")]
    ])
    await query.edit_message_text(text, reply_markup=buttons)

# =====================================================
# BROADCAST COMMAND
# =====================================================

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users"""
    if not is_mother_admin(message.from_user.id):
        return await message.reply_text("❌ Admin only command")
    
    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to broadcast it")
    
    users = await full_userbase()
    original = message.reply_to_message
    status = {"total": 0, "sent": 0, "blocked": 0, "deleted": 0, "failed": 0}
    
    wait = await message.reply("<i>Broadcasting...</i>")
    
    for user_id in users:
        try:
            await original.copy(user_id)
            status["sent"] += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await original.copy(user_id)
            status["sent"] += 1
        except UserIsBlocked:
            await del_user(user_id)
            status["blocked"] += 1
        except InputUserDeactivated:
            await del_user(user_id)
            status["deleted"] += 1
        except:
            status["failed"] += 1
        status["total"] += 1
    
    summary = f"📢 **Broadcast Summary**\n\n"
    summary += f"👥 Total: {status['total']}\n"
    summary += f"✅ Sent: {status['sent']}\n"
    summary += f"⛔ Blocked: {status['blocked']}\n"
    summary += f"❌ Deleted: {status['deleted']}\n"
    summary += f"⚠️ Failed: {status['failed']}"
    
    await wait.edit(summary)

# =====================================================
# ADMIN COMMANDS
# =====================================================

@Client.on_message(filters.command("users") & filters.private)
async def users_command(client: Client, message: Message):
    """Get user count"""
    if not is_mother_admin(message.from_user.id):
        return
    
    try:
        total = await get_users_count()
        await message.reply_text(f"📊 **Total Users:** {total:,}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Show statistics"""
    if not is_mother_admin(message.from_user.id):
        return
    
    try:
        total_users = await get_users_count()
        premium_users = await get_all_premium_users()
        premium_count = len(premium_users) if premium_users else 0
        
        text = f"📊 **Bot Statistics**\n\n"
        text += f"👥 Total Users: {total_users:,}\n"
        text += f"💎 Premium Users: {premium_count:,}\n"
        text += f"🆓 Free Users: {total_users - premium_count:,}\n"
        
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# All other admin commands follow similar pattern...
# Consolidating them into this single file
