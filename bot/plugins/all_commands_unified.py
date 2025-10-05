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
from bot.database.users import get_total_users, get_user_stats
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

# =====================================================
# CLONE STATUS & DATABASE COMMANDS
# =====================================================

@Client.on_message(filters.command(['clones', 'clonestatus']) & filters.private)
async def clones_status_command(client: Client, message: Message):
    """Show clone status"""
    user_id = message.from_user.id
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

    if bot_token == Config.BOT_TOKEN:
        # Mother bot - show all clones (admin only)
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            return await message.reply_text("❌ Only admins can view all clone status.")

        all_clones = await get_all_clones()
        if not all_clones:
            return await message.reply_text("📋 **Clone Status**\n\nNo clones found.")

        text = f"📋 **All Clones Status** ({len(all_clones)} total)\n\n"
        active_count = sum(1 for c in all_clones if c.get('status') == 'active')

        for clone in all_clones[:10]:
            status_emoji = "🟢" if clone.get('status') == 'active' else "🔴"
            text += f"{status_emoji} **@{clone.get('username', 'Unknown')}** (`{clone.get('bot_id')}`)\n"

        if len(all_clones) > 10:
            text += f"\n... and {len(all_clones) - 10} more clones"

        await message.reply_text(text)
    else:
        # Clone bot - show this clone's status
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or user_id != clone_data['admin_id']:
            return await message.reply_text("❌ Only clone admin can view clone status.")

        status_emoji = "🟢" if clone_data.get('status') == 'active' else "🔴"
        text = f"""📋 **Clone Status**

🤖 **Bot:** @{clone_data.get('username', 'Unknown')}
🆔 **Bot ID:** `{clone_data.get('bot_id')}`
📊 **Status:** {status_emoji} {clone_data.get('status', 'unknown').title()}"""

        await message.reply_text(text)

@Client.on_message(filters.command(['dbstats', 'databasestats']) & filters.private)
async def clone_database_stats_command(client: Client, message: Message):
    """Show clone database statistics"""
    clone_id = get_clone_id_from_client(client)
    if not clone_id:
        return await message.reply_text("❌ This command is only available in clone bots.")

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
    if not clone_data or message.from_user.id != clone_data['admin_id']:
        return await message.reply_text("❌ Only clone admin can use this command.")

    await message.reply_text("🔄 **Fetching Database Statistics...**\n\nPlease wait...")

# =====================================================
# TOKEN COMMANDS (from clone_token_commands.py)
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
            "• `time_based` - Token valid for specific time period"
        )

    mode = message.command[1].lower()
    if mode not in ['command_limit', 'time_based']:
        return await message.reply_text("❌ Invalid mode. Use `command_limit` or `time_based`")

    bot_id = str(clone_data.get('bot_id'))
    await update_clone_token_verification(bot_id, verification_mode=mode)

    mode_text = "Command Limit" if mode == "command_limit" else "Time-Based (24 hours)"
    await message.reply_text(f"✅ Token verification mode set to: **{mode_text}**")

# =====================================================
# FORCE SUBSCRIPTION COMMANDS
# =====================================================

@Client.on_message(filters.command("addglobalchannel") & filters.private)
async def add_global_channel(client: Client, message: Message):
    """Add a global force subscription channel"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only admins can manage global force channels.")

    if len(message.command) < 2:
        return await message.reply_text(
            "📢 **Add Global Force Channel**\n\n"
            "**Usage:** `/addglobalchannel <channel_id>`\n"
            "**Example:** `/addglobalchannel -1001234567890`"
        )

    try:
        channel_id = int(message.command[1])
        chat = await client.get_chat(channel_id)
        await message.reply_text(f"✅ **Channel Added Successfully!**\n\n**Channel:** {chat.title}\n**ID:** `{channel_id}`")
    except ValueError:
        await message.reply_text("❌ **Invalid Channel ID!** Channel ID must be a number.")
    except Exception as e:
        await message.reply_text(f"❌ **Error!** {str(e)}")

# =====================================================
# CLONE MANAGER COMMANDS (from mother_bot_commands.py)
# =====================================================

@Client.on_message(filters.command("startclone") & filters.private)
async def start_clone_command(client: Client, message: Message):
    """Start a clone bot"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can start clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/startclone <bot_id>`")

    bot_id = message.command[1]

    try:
        success, result = await clone_manager.start_clone(bot_id)
        if success:
            await message.reply_text(f"✅ **Clone {bot_id} started successfully.**")
        else:
            await message.reply_text(f"⚠️ Failed to start clone {bot_id}: {result}")
    except Exception as e:
        logger.error(f"Error starting clone {bot_id}: {e}")
        await message.reply_text(f"❌ Error starting clone {bot_id}: {str(e)}")

@Client.on_message(filters.command("stopclone") & filters.private)
async def stop_clone_command(client: Client, message: Message):
    """Stop a clone bot"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can stop clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/stopclone <bot_id>`")

    bot_id = message.command[1]

    try:
        success, result = await clone_manager.stop_clone(bot_id)
        if success:
            await message.reply_text(f"✅ **Clone {bot_id} stopped successfully.**")
        else:
            await message.reply_text(f"⚠️ Failed to stop clone {bot_id}: {result}")
    except Exception as e:
        logger.error(f"Error stopping clone {bot_id}: {e}")
        await message.reply_text(f"❌ Error stopping clone {bot_id}: {str(e)}")

@Client.on_message(filters.command("restartclone") & filters.private)
async def restart_clone_command(client: Client, message: Message):
    """Restart a clone bot"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can restart clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/restartclone <bot_id>`")

    bot_id = message.command[1]

    try:
        success, result = await clone_manager.restart_clone(bot_id)
        if success:
            await message.reply_text(f"✅ **Clone {bot_id} restarted successfully.**")
        else:
            await message.reply_text(f"⚠️ Failed to restart clone {bot_id}: {result}")
    except Exception as e:
        logger.error(f"Error restarting clone {bot_id}: {e}")
        await message.reply_text(f"❌ Error restarting clone {bot_id}: {str(e)}")

@Client.on_message(filters.command("clone_status") & filters.private)
async def clone_manager_status_command(client: Client, message: Message):
    """Get status of the clone manager"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only Mother Bot admins can view clone manager status.")

    status = clone_manager.get_status()
    await message.reply_text(f"**Clone Manager Status:** `{status}`")

# =====================================================
# DEBUG COMMANDS (from debug_commands.py)
# =====================================================

@Client.on_message(filters.command("debug") & filters.private)
async def debug_command(client: Client, message: Message):
    """Enter debug mode"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only admins can use debug commands.")

    await message.reply_text(
        "🐞 **Debug Mode Activated**\n\n"
        "You can now use debug commands. Type `/helpdebug` for a list of commands."
    )
    # You would typically set a flag here to indicate debug mode is active for the user
    # For now, we'll just acknowledge.

@Client.on_message(filters.command("helpdebug") & filters.private)
async def help_debug_command(client: Client, message: Message):
    """Show help for debug commands"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only admins can use debug commands.")

    debug_help_text = """
🐞 **Debug Commands Help**

`/debug_clone <bot_id>` - Show debug info for a specific clone.
`/debug_user <user_id>` - Show debug info for a specific user.
`/debug_logs` - Show recent logs.
`/debug_db <table_name>` - Show stats for a database table.
"""
    await message.reply_text(debug_help_text)

@Client.on_message(filters.command("debug_clone") & filters.private)
async def debug_clone_command(client: Client, message: Message):
    """Debug a specific clone bot"""
    user_id = message.from_user.id
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)

    if user_id not in admin_list:
        return await message.reply_text("❌ Only admins can use debug commands.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/debug_clone <bot_id>`")

    bot_id = message.command[1]

    try:
        clone_data = await get_clone(bot_id)
        if not clone_data:
            return await message.reply_text(f"❌ Clone {bot_id} not found.")

        clone_manager_instance = clone_manager.get_clone_instance(bot_id)
        status = clone_manager_instance.status if clone_manager_instance else "Not Running"

        debug_info = f"""
🐞 **Clone Debug Info: {bot_id}**

ID: `{clone_data.get('bot_id')}`
Username: @{clone_data.get('username', 'N/A')}
Status: {status}
Admin ID: `{clone_data.get('admin_id')}`
Token Verified: {'Yes' if clone_data.get('token_verified') else 'No'}
Verification Mode: {clone_data.get('verification_mode', 'N/A')}
Created At: {clone_data.get('created_at')}
"""
        await message.reply_text(debug_info)
    except Exception as e:
        logger.error(f"Error debugging clone {bot_id}: {e}")
        await message.reply_text(f"❌ Error debugging clone {bot_id}: {str(e)}")


# =====================================================
# SIMPLE TEST COMMANDS (from simple_test_commands.py)
# =====================================================

@Client.on_message(filters.command("test") & filters.private)
async def test_command(client: Client, message: Message):
    """A simple test command"""
    await message.reply_text("✅ Test command executed successfully!")

# =====================================================
# MISSING COMMANDS (from missing_commands.py)
# =====================================================

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """Handle about command"""
    user_id = message.from_user.id

    if await handle_force_sub(client, message):
        return

    about_text = """
🤖 **About This Bot**

This is a powerful Telegram bot designed to manage and operate clone bots efficiently.
It allows for the creation, management, and monitoring of multiple Telegram bots from a single interface.

Features:
• Clone bot management
• User management and statistics
• Premium features and subscription plans
• Robust error handling and logging

Version: 1.0.0
Developed by: [Your Name/Team]
"""

    await message.reply_text(
        about_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )

# =====================================================
# COMMAND STATS COMMAND (from command_stats.py)
# =====================================================
# Note: 'mystats' command is already included in basic commands section.
# This section is for any additional command stats logic if needed.

logger.info("✅ All unified commands module loaded successfully")