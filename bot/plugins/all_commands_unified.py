
"""
Unified Commands System - All Commands Merged
Consolidates all command handlers from the entire project
"""
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database import add_user, present_user, is_premium_user, get_command_stats
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.database.balance_db import get_user_balance
from bot.database.users import get_users_count, get_user_stats
from bot.utils import handle_force_sub
from bot.utils.command_verification import check_command_limit
from bot.utils.clone_config_loader import clone_config_loader
from bot.logging import LOGGER
from clone_manager import clone_manager

logger = LOGGER(__name__)

# Store clone admin sessions
clone_admin_sessions = {}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False
        if hasattr(client, 'clone_admin_id'):
            return user_id == client.clone_admin_id
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

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

# =====================================================
# BASIC COMMANDS (from commands_unified.py)
# =====================================================

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle help command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    help_text = """
📚 **Help & Commands**

🤖 **Basic Commands:**
/start - Start the bot
/help - Show this help message
/about - About this bot

💎 **Premium Commands:**
/premium - View premium plans
/balance - Check your balance
/profile - View your profile

🔍 **Search & Files:**
Use the search feature to find files

👨‍💼 **Admin Commands:**
/admin - Admin panel (Admins only)
/broadcast - Broadcast message (Admins only)
/stats - Bot statistics (Admins only)

Need more help? Contact support!
"""
    
    await message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )

@Client.on_message(filters.command("profile") & filters.private)
async def profile_command(client: Client, message: Message):
    """Handle profile command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    try:
        stats = await get_user_stats(user_id)
        is_premium = await is_premium_user(user_id)
        
        profile_text = f"""
👤 **Your Profile**

🆔 User ID: `{user_id}`
👤 Name: {message.from_user.first_name}
"""
        if message.from_user.username:
            profile_text += f"📝 Username: @{message.from_user.username}\n"
        
        profile_text += f"""
💎 Status: {'Premium ⭐' if is_premium else 'Free User'}
📊 Commands Used: {stats.get('command_count', 0)}
🤖 Clone Bots: {stats.get('clone_count', 0)}
"""
        
        await message.reply_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium", callback_data="show_premium_plans")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await message.reply_text("❌ Error loading profile. Please try again.")

@Client.on_message(filters.command("balance") & filters.private)
async def balance_command(client: Client, message: Message):
    """Handle balance command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    try:
        balance = await get_user_balance(user_id)
        
        balance_text = f"""
💰 **Your Balance**

Current Balance: **{balance} tokens**

Use tokens to:
• Create clone bots
• Access premium features
• Remove command limits
"""
        
        await message.reply_text(
            balance_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Balance", callback_data="show_balance_options")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await message.reply_text("❌ Error loading balance. Please try again.")

@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client: Client, message: Message):
    """Handle premium command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    is_premium = await is_premium_user(user_id)
    
    if is_premium:
        await message.reply_text(
            "✨ **You're already a Premium Member!**\n\n"
            "Enjoy unlimited access to all features.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
        return
    
    premium_text = """
💎 **Premium Membership**

✨ Premium Benefits:
• Unlimited commands
• No verification required
• Priority support
• Exclusive features
• Ad-free experience

📦 Choose Your Plan:
"""
    
    await message.reply_text(
        premium_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 View Plans", callback_data="show_premium_plans")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@Client.on_message(filters.command("mystats") & filters.private)
async def my_stats_command(client: Client, message: Message):
    """Show user's command usage stats"""
    user_id = message.from_user.id
    
    try:
        stats = await get_command_stats(user_id)
        needs_verification, remaining = await check_command_limit(user_id)
        
        status_text = "🔥 **Unlimited**" if remaining == -1 else f"🆓 **{remaining}/3**" if remaining > 0 else "❌ **Limit Reached**"
        
        stats_text = f"""📊 **Your Command Usage Stats**

👤 **User:** {message.from_user.first_name}
🎯 **Current Status:** {status_text}
📈 **Total Commands Used:** {stats['command_count']}

⏰ **Last Command:** {stats['last_command_at'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_command_at'] else 'Never'}
🔄 **Last Reset:** {stats['last_reset'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_reset'] else 'Never'}

💡 **Get Premium** for unlimited access without verification!"""
        
        await message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error in mystats command: {e}")
        await message.reply_text("❌ Error retrieving stats. Please try again later.")

# =====================================================
# ADMIN COMMANDS (from admin_commands.py)
# =====================================================

@Client.on_message(filters.command("activate_clone") & filters.private)
async def activate_clone_command(client: Client, message: Message):
    """Activate a clone bot"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    
    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can activate clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/activate_clone <bot_id>`")

    bot_id = message.command[1]

    try:
        clone_data = await get_clone(bot_id)
        if not clone_data:
            return await message.reply_text(f"❌ Clone {bot_id} not found.")

        await update_clone_status(bot_id, 'active')
        success, result = await clone_manager.start_clone(bot_id)

        if success:
            await message.reply_text(
                f"✅ **Clone Activated Successfully!**\n\n"
                f"🤖 **Bot:** @{clone_data.get('username', 'Unknown')}\n"
                f"🆔 **Bot ID:** {bot_id}\n"
                f"📊 **Status:** Active & Running"
            )
        else:
            await message.reply_text(f"⚠️ Clone activated but failed to start: {result}")

    except Exception as e:
        logger.error(f"Error activating clone: {e}")
        await message.reply_text(f"❌ Error activating clone: {str(e)}")

@Client.on_message(filters.command("dashboard") & filters.private)
async def dashboard_command(client: Client, message: Message):
    """Show dashboard with system overview"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    
    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can access dashboard.")

    try:
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())

        dashboard_text = f"📊 **System Dashboard**\n\n"
        dashboard_text += f"🤖 **Clone Statistics:**\n"
        dashboard_text += f"• Total Clones: {total_clones}\n"
        dashboard_text += f"• Active Clones: {active_clones}\n"
        dashboard_text += f"• Running Clones: {running_clones}\n\n"
        dashboard_text += f"💰 **Subscriptions:**\n"
        dashboard_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
        dashboard_text += f"⏱️ **System Status:**\n"
        dashboard_text += f"• Mother Bot: Running\n"
        dashboard_text += f"• Clone Manager: Active\n"
        dashboard_text += f"• Database: Connected\n"
        dashboard_text += f"• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎛️ Admin Panel", callback_data="mother_admin_panel")],
            [InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="refresh_dashboard")]
        ])

        await message.reply_text(dashboard_text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        await message.reply_text(f"❌ Error loading dashboard: {str(e)}")

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle stats command"""
    user_id = message.from_user.id
    
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ This command is only for admins.")
    
    try:
        from bot.database.users import get_total_users
        
        total_users = await get_total_users()
        all_clones = await get_all_clones()
        active_clones = len([c for c in all_clones if c.get('status') == 'active'])
        
        stats_text = f"""
📊 **Bot Statistics**

👥 Total Users: {total_users}
🤖 Total Clones: {len(all_clones)}
✅ Active Clones: {active_clones}
❌ Inactive Clones: {len(all_clones) - active_clones}
"""
        
        await message.reply_text(stats_text)
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error loading statistics.")

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle broadcast command"""
    user_id = message.from_user.id
    
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ This command is only for admins.")
    
    await message.reply_text(
        "📢 **Broadcast Message**\n\n"
        "Reply to any message with `/broadcast` to send it to all users.\n\n"
        "Usage: Reply to a message and use /broadcast"
    )

logger.info("✅ All unified commands module loaded successfully")
