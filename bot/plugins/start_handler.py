import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database import add_user, get_user_balance
from bot.utils import get_readable_time, handle_force_sub
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user

    print(f"🚀 DEBUG COMMAND: /start command from user {user.id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user.id}, Username: @{user.username}, First: {user.first_name}")

    # Check if session has expired for the user
    if await session_expired(user.id):
        print(f"⏰ DEBUG SESSION: Session expired for user {user.id}, clearing session")
        await clear_session(user.id)
    else:
        print(f"✅ DEBUG SESSION: Session valid for user {user.id}")

    # Add user to database
    await add_user(user_id, message.from_user.first_name)

    # Check force subscription
    if not await handle_force_sub(client, message):
        return

    # Get user balance
    balance = await get_user_balance(user_id)

    # Check if user is admin
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)

    text = f"👋 **Welcome {message.from_user.first_name}!**\n\n"
    text += f"🤖 **Mother Bot + Clone System**\n"
    text += f"Advanced file sharing with clone management\n\n"
    text += f"💰 **Your Balance:** ${balance:.2f}\n\n"
    text += f"✨ **Features:**\n"
    text += f"• 📁 Secure file sharing\n"
    text += f"• 🔍 Advanced search\n"
    text += f"• 🤖 Create your own bot clone\n"
    text += f"• 💎 Premium features\n\n"
    text += f"🎯 **Ready to get started?**"

    # Build buttons
    buttons = []

    # First row - main features
    buttons.append([
        InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
        InlineKeyboardButton("💎 Premium", callback_data="premium_info")
    ])

    # Second row - user features
    buttons.append([
        InlineKeyboardButton("🔍 Random Files", callback_data="random_files"),
        InlineKeyboardButton("👤 Profile", callback_data="user_profile")
    ])

    # Third row - info
    buttons.append([
        InlineKeyboardButton("❓ Help", callback_data="help_menu"),
        InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
    ])

    # Admin panel for admins
    if is_admin:
        buttons.append([
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
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
    text += f"**📋 Commands:**\n"
    text += f"• `/start` - Main menu\n"
    text += f"• `/search` - Search files\n"
    text += f"• `/premium` - Premium info\n"
    text += f"• `/balance` - Check balance\n\n"
    text += f"**🆘 Need Help?**\n"
    text += f"Contact admin for support"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_callback(client: Client, query: CallbackQuery):
    """Show about information"""
    await query.answer()

    text = f"ℹ️ **About This Bot**\n\n"
    text += f"🤖 **Mother Bot + Clone System**\n"
    text += f"Advanced file sharing bot with multi-instance support\n\n"
    text += f"✨ **Features:**\n"
    text += f"• 🔒 Secure file storage\n"
    text += f"• 🤖 Clone bot creation\n"
    text += f"• 💰 Subscription management\n"
    text += f"• ⚙️ Advanced admin controls\n"
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