import asyncio
from datetime import datetime
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.utils.session_manager import get_session, clear_session, session_expired
from bot.database.users import add_user, present_user
from info import Config
from bot.database.premium_db import is_premium_user
from bot import get_user_balance
from bot.utils import handle_force_sub
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    user_id = user.id

    print(f"🚀 DEBUG COMMAND: /start command from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{user.username}, First: {user.first_name}")

    # Handle force subscription first (with admin exemption)
    if not await handle_force_sub(client, message):
        print(f"🔒 DEBUG: User {user_id} blocked by force subscription")
        return  # User hasn't joined required channels

    print(f"✅ DEBUG: User {user_id} passed force subscription check")

    # Check if session has expired for the user
    if await session_expired(user.id):
        print(f"⏰ DEBUG SESSION: Session expired for user {user.id}, clearing session")
        await clear_session(user.id)
    else:
        print(f"✅ DEBUG SESSION: Session valid for user {user.id}")

    # Add user to database
    await add_user(user.id)

    # Check if user is admin
    is_admin = user.id in [Config.OWNER_ID] + list(Config.ADMINS)

    # Check if user is premium
    user_premium = await is_premium_user(user.id)

    text = f"👋 **Hello {message.from_user.first_name}!**\n\n"
    text += f"🔐 **PS-LinkVault Bot**\n"
    text += f"Fast & secure file sharing with advanced features\n\n"

    if user_premium:
        text += f"💎 **Premium User** | Balance: ${balance:.2f}\n"
    else:
        text += f"👤 **Free User** | Balance: ${balance:.2f}\n"

    text += f"\n📊 **Quick Stats:**\n"
    text += f"• Files shared securely\n"
    text += f"• Token-based verification\n"
    text += f"• Force subscription support\n\n"
    text += f"🚀 **Choose an option below:**"

    # Build buttons similar to PS-LinkVault repository
    buttons = []

    # Row 1: Main Features
    buttons.append([
        InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
        InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
    ])

    # Row 2: File Operations
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🔗 Generate Link", callback_data="genlink_help"),
            InlineKeyboardButton("📦 Batch Mode", callback_data="batch_help")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🔍 Search Files", callback_data="search_files"),
            InlineKeyboardButton("🎲 Random Files", callback_data="random_files")
        ])

    # Row 3: Token & Premium
    buttons.append([
        InlineKeyboardButton("🔑 Get Token", callback_data="get_token"),
        InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info")
    ])

    # Row 4: Clone Management (for admins) or Help
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
        ])

    # Row 5: Help & About
    buttons.append([
        InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="about_bot")
    ])

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_callback(client: Client, query: CallbackQuery):
    """Show help menu"""
    await query.answer()

    text = f"❓ **Help & Support**\n\n"
    text += f"**🤖 For Users:**\n"
    text += f"• Send files to get sharing links\n"
    text += f"• Use search to find files\n"
    text += f"• Create your own bot clone\n"
    text += f"• Upgrade to premium features\n\n"
    text += f"**📋 Available Commands:**\n"
    text += f"• `/start` - Main menu & homepage\n"
    text += f"• `/token` - Generate access token\n"
    text += f"• `/stats` - View bot statistics\n"
    text += f"• `/search` - Search for files\n"
    text += f"• `/premium` - Premium plan info\n"
    text += f"• `/balance` - Check your balance\n\n"

    text += f"**⚙️ Admin Commands:**\n"
    text += f"• `/genlink` - Generate file links\n"
    text += f"• `/batch` - Batch file operations\n"
    text += f"• `/users` - Total user count\n"
    text += f"• `/broadcast` - Send announcements\n\n"
    text += f"**🆘 Need Help?**\n"
    text += f"Contact admin for support"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_callback(client: Client, query: CallbackQuery):
    """Show about information"""
    await query.answer()

    text = f"ℹ️ **About PS-LinkVault Bot**\n\n"
    text += f"🔐 **Advanced File Sharing System**\n"
    text += f"Fast, secure, and feature-rich Telegram file sharing bot\n\n"
    text += f"✨ **Key Features:**\n"
    text += f"• 🔗 Generate secure download links\n"
    text += f"• 🔑 Token-based verification system\n"
    text += f"• 📦 Batch file operations\n"
    text += f"• 🚫 Force subscription support\n"
    text += f"• 💎 Premium user benefits\n"
    text += f"• 🤖 Clone bot creation\n"
    text += f"• 📊 Advanced statistics\n\n"

    text += f"🛡️ **Security:**\n"
    text += f"All files are encrypted and access is logged for security.\n\n"

    text += f"💻 **Made with ❤️ using Python & Pyrogram**"
    text += f"• 🔍 Smart file search\n"
    text += f"• 💎 Premium features\n\n"
    text += f"💡 **Powered by:** Pyrogram & MongoDB\n"
    text += f"🔧 **Version:** 2.0.0\n"
    text += f"👨‍💻 **Developer:** @{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Developer", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^user_profile$"))
async def profile_callback(client: Client, query: CallbackQuery):
    """Show user profile"""
    await query.answer()

    user = query.from_user
    balance = await get_user_balance(user.id)

    text = f"👤 **Your Profile**\n\n"
    text += f"🆔 **User ID:** `{user.id}`\n"
    text += f"👤 **Name:** {user.first_name}"
    if user.last_name:
        text += f" {user.last_name}"
    if user.username:
        text += f"\n📱 **Username:** @{user.username}"
    text += f"\n💰 **Balance:** ${balance:.2f}\n"
    text += f"📅 **Joined:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
    text += f"**🎯 Quick Actions:**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance"),
            InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
        ],
        [
            InlineKeyboardButton("📋 Manage Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("💎 Premium", callback_data="premium_info")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^transaction_history$"))
async def transaction_history_callback(client: Client, query: CallbackQuery):
    """Show transaction history"""
    await query.answer()

    text = f"📊 **Transaction History**\n\n"
    text += f"🔄 Loading transaction history...\n"
    text += f"This feature is coming soon!\n\n"
    text += f"💡 **Available:**\n"
    text += f"• Balance tracking\n"
    text += f"• Clone purchases\n"
    text += f"• Premium subscriptions"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^premium_info$"))
async def premium_info_callback(client: Client, query: CallbackQuery):
    """Show premium information"""
    await query.answer()

    text = f"💎 **Premium Features**\n\n"
    text += f"🚀 **Upgrade your experience with Premium!**\n\n"
    text += f"✨ **Premium Benefits:**\n"
    text += f"• 🔥 Unlimited downloads\n"
    text += f"• ⚡ Faster file processing\n"
    text += f"• 🎯 Priority support\n"
    text += f"• 📊 Advanced statistics\n"
    text += f"• 🤖 Multiple clone bots\n"
    text += f"• 🔒 Enhanced security\n\n"
    text += f"💰 **Pricing:**\n"
    text += f"• Monthly: $9.99\n"
    text += f"• Yearly: $99.99 (Save 17%!)\n\n"
    text += f"🎁 **Special Offer:** First month 50% off!"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Buy Premium", callback_data="buy_premium"),
            InlineKeyboardButton("🎁 Free Trial", callback_data="premium_trial")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^random_files$"))
async def random_files_callback(client: Client, query: CallbackQuery):
    """Show random files menu"""
    await query.answer()

    text = f"🔍 **Random Files**\n\n"
    text += f"Discover amazing files from our database!\n\n"
    text += f"📋 **Options:**\n"
    text += f"• 🆕 Latest uploads\n"
    text += f"• 🔥 Popular files\n"
    text += f"• 🎲 Completely random\n"
    text += f"• 📊 File statistics\n\n"
    text += f"🎯 **Choose what you want to explore:**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆕 Latest", callback_data="rand_recent"),
            InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")
        ],
        [
            InlineKeyboardButton("🎲 Random", callback_data="execute_rand"),
            InlineKeyboardButton("📊 Stats", callback_data="rand_stats")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

# Add new callback handlers for PS-LinkVault features
@Client.on_callback_query(filters.regex("^user_stats$"))
async def user_stats_callback(client: Client, query: CallbackQuery):
    """Show user statistics"""
    await query.answer()

    user_id = query.from_user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)

    # Get additional stats (you can expand this)
    text = f"📊 **Your Statistics**\n\n"
    text += f"👤 **User Info:**\n"
    text += f"• ID: `{user_id}`\n"
    text += f"• Status: {'🌟 Premium' if user_premium else '🆓 Free User'}\n"
    text += f"• Balance: ${balance:.2f}\n\n"

    text += f"📈 **Usage Stats:**\n"
    text += f"• Files Accessed: Coming Soon\n"
    text += f"• Tokens Generated: Coming Soon\n"
    text += f"• Links Created: Coming Soon\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="user_stats")],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^get_token$"))
async def get_token_callback(client: Client, query: CallbackQuery):
    """Handle token generation request"""
    await query.answer()

    text = f"🔑 **Access Token Generation**\n\n"
    text += f"🔐 **What is a Token?**\n"
    text += f"Access tokens provide temporary access to premium files and features.\n\n"

    text += f"⏱️ **Token Info:**\n"
    text += f"• Valid for: 6 hours\n"
    text += f"• Access: Premium content\n"
    text += f"• Cost: Based on your plan\n\n"

    text += f"📋 **How to Generate:**\n"
    text += f"Use the command: `/token`\n\n"
    text += f"💡 **Tip:** Tokens expire after use for security."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Generate Now", callback_data="generate_token_now")],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^genlink_help$"))
async def genlink_help_callback(client: Client, query: CallbackQuery):
    """Show genlink help for admins"""
    await query.answer()

    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        await query.answer("❌ Admin access required!", show_alert=True)
        return

    text = f"🔗 **Generate File Links**\n\n"
    text += f"📋 **Commands:**\n"
    text += f"• `/genlink` - Reply to a file\n"
    text += f"• `/genlink file_id` - Using file ID\n\n"

    text += f"✨ **Features:**\n"
    text += f"• Secure download links\n"
    text += f"• Token verification support\n"
    text += f"• Custom expiry times\n"
    text += f"• Access tracking\n\n"

    text += f"🔒 **Security:**\n"
    text += f"All links are encrypted and tracked for security."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^batch_help$"))
async def batch_help_callback(client: Client, query: CallbackQuery):
    """Show batch mode help for admins"""
    await query.answer()

    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        await query.answer("❌ Admin access required!", show_alert=True)
        return

    text = f"📦 **Batch File Operations**\n\n"
    text += f"📋 **Commands:**\n"
    text += f"• `/batch start_id end_id` - Generate multiple links\n"
    text += f"• `/batch 100 150` - Links for files 100-150\n\n"

    text += f"⚡ **Features:**\n"
    text += f"• Bulk link generation\n"
    text += f"• Range-based file processing\n"
    text += f"• Efficient batch operations\n\n"

    text += f"📊 **Limits:**\n"
    text += f"• Max 50 files per batch\n"
    text += f"• Admin access required\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Go back to start menu"""
    await query.answer()

    # Recreate the start message
    user = query.from_user
    user_premium = await is_premium_user(user.id)
    balance = await get_user_balance(user.id)
    is_admin = user.id in [Config.OWNER_ID] + list(Config.ADMINS)

    text = f"👋 **Hello {user.first_name}!**\n\n"
    text += f"🔐 **PS-LinkVault Bot**\n"
    text += f"Fast & secure file sharing with advanced features\n\n"

    if user_premium:
        text += f"💎 **Premium User** | Balance: ${balance:.2f}\n"
    else:
        text += f"👤 **Free User** | Balance: ${balance:.2f}\n"

    text += f"\n📊 **Quick Stats:**\n"
    text += f"• Files shared securely\n"
    text += f"• Token-based verification\n"
    text += f"• Force subscription support\n\n"
    text += f"🚀 **Choose an option below:**"

    # Rebuild buttons
    buttons = []

    # Row 1: Main Features
    buttons.append([
        InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
        InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
    ])

    # Row 2: File Operations
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🔗 Generate Link", callback_data="genlink_help"),
            InlineKeyboardButton("📦 Batch Mode", callback_data="batch_help")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🔍 Search Files", callback_data="search_files"),
            InlineKeyboardButton("🎲 Random Files", callback_data="random_files")
        ])

    # Row 3: Token & Premium
    buttons.append([
        InlineKeyboardButton("🔑 Get Token", callback_data="get_token"),
        InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info")
    ])

    # Row 4: Clone Management (for admins) or Help
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
        ])

    # Row 5: Help & About
    buttons.append([
        InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="about_bot")
    ])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))