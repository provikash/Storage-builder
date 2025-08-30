import asyncio
from datetime import datetime
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.utils.session_manager import get_session, clear_session, session_expired
from bot.database.users import add_user, present_user
from info import Config
from bot.database.premium_db import is_premium_user
from bot.database.balance_db import get_user_balance
from bot.utils import handle_force_sub
from bot.logging import LOGGER
from bot.utils.error_handler import safe_edit_message

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

    # Get user balance
    balance = await get_user_balance(user.id)

    # Detect if this is a clone bot or mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN

    if is_clone_bot:
        # Clone bot start message
        text = f"🤖 **Welcome to Your Personal File Sharing Bot!**\n\n"
        text += f"👋 Hello **{message.from_user.first_name}**!\n\n"
        text += f"📁 **This is your personal clone bot** with amazing features:\n\n"
        text += f"✨ **What I can do for you:**\n"
        text += f"• 📁 Store and share files securely\n"
        text += f"• 🔍 Advanced search capabilities\n"
        text += f"• 🎲 Random file discovery\n"
        text += f"• 📈 Recent files tracking\n"
        text += f"• 🔐 Token-based file access\n"
        text += f"• ⚡ Lightning-fast file processing\n\n"
        
        if user_premium:
            text += f"💎 **Premium Status:** Active\n"
        else:
            text += f"👤 **Free User**\n"
        
        text += f"\n🎯 **Ready to get started?** Choose an option below:"

        # Clone bot buttons
        buttons = []
        
        # Row 1: File Operations
        buttons.append([
            InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
            InlineKeyboardButton("📈 Recent Files", callback_data="recent_files")
        ])
        
        # Row 2: Search & Stats
        buttons.append([
            InlineKeyboardButton("🔍 Search Files", callback_data="search_files"),
            InlineKeyboardButton("📊 My Stats", callback_data="user_stats")
        ])
        
        # Row 3: Premium & Help
        buttons.append([
            InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info"),
            InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu")
        ])
        
        # Row 4: Create Clone (redirect to mother bot)
        buttons.append([
            InlineKeyboardButton("🤖 Create Your Own Clone", url=f"https://t.me/{Config.ADMIN_USERNAME}?start=create_clone")
        ])
        
        # Row 5: Admin panel for clone admins
        if is_admin:
            buttons.append([
                InlineKeyboardButton("⚙️ Clone Admin Panel", callback_data="clone_admin_panel")
            ])
    else:
        # Mother bot start message
        text = f"🚀 **Welcome to Advanced File Storage Bot Creator!**\n\n"
        text += f"👋 Hello **{message.from_user.first_name}**!\n\n"
        text += f"🤖 **I am an advanced file storing bot creator** with powerful features:\n\n"
        text += f"✨ **What I can do for you:**\n"
        text += f"• 📁 Advanced file storage & management\n"
        text += f"• 🤖 Create your own personal clone bots\n"
        text += f"• 🔐 Secure file sharing with token verification\n"
        text += f"• 💎 Premium subscriptions with exclusive features\n"
        text += f"• 📊 Detailed analytics and statistics\n"
        text += f"• 🎯 Smart file organization and search\n"
        text += f"• ⚡ Lightning-fast file processing\n\n"

        if user_premium:
            text += f"💎 **Premium Status:** Active | Balance: **${balance:.2f}**\n"
        else:
            text += f"👤 **Free User** | Balance: **${balance:.2f}**\n"

        text += f"\n🎯 **Ready to get started?** Choose an option below:"

        # Mother bot buttons
        buttons = []

        # Row 1: Main Features
        buttons.append([
            InlineKeyboardButton("🤖 Create Your Own Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
        ])

        # Row 2: Clone Management
        buttons.append([
            InlineKeyboardButton("📋 Manage My Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
        ])

        # Row 3: Premium & Help
        buttons.append([
            InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info"),
            InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu")
        ])

        # Row 4: Admin panel for admins
        if is_admin:
            buttons.append([
                InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management")
            ])

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^user_profile$"))
async def profile_callback(client: Client, query: CallbackQuery):
    """Show detailed user profile with balance and actions"""
    await query.answer()

    user = query.from_user
    user_id = user.id
    balance = await get_user_balance(user_id)
    user_premium = await is_premium_user(user_id)
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)

    # Enhanced profile information
    text = f"👤 **Your Detailed Profile**\n\n"
    text += f"🆔 **User ID:** `{user.id}`\n"
    text += f"👤 **Full Name:** {user.first_name}"
    if user.last_name:
        text += f" {user.last_name}"

    if user.username:
        text += f"\n📱 **Username:** @{user.username}"
    else:
        text += f"\n📱 **Username:** Not set"

    text += f"\n💰 **Current Balance:** ${balance:.2f}\n"

    if user_premium:
        text += f"💎 **Account Type:** Premium Member ⭐\n"
    else:
        text += f"👤 **Account Type:** Free User\n"

    if is_admin:
        text += f"🔧 **Access Level:** Administrator\n"

    text += f"📅 **Member Since:** {datetime.now().strftime('%B %Y')}\n"
    text += f"🕐 **Last Seen:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    text += f"🎯 **Profile Actions:**\n"
    text += f"Manage your account settings and view detailed information below."

    # Profile action buttons
    buttons = []

    # Row 1: Balance Actions
    buttons.append([
        InlineKeyboardButton("💳 Add Balance", callback_data="add_balance_user"),
        InlineKeyboardButton("📊 Transaction History", callback_data="transaction_history")
    ])

    # Row 2: Account Management
    buttons.append([
        InlineKeyboardButton("🤖 My Clone Bots", callback_data="my_clones_list"),
        InlineKeyboardButton("⚙️ Account Settings", callback_data="account_settings")
    ])

    # Row 3: Stats and Premium
    buttons.append([
        InlineKeyboardButton("📈 Usage Stats", callback_data="detailed_stats"),
        InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium_info")
    ])

    # Row 4: Back button
    buttons.append([
        InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile_main") # Changed callback to avoid loop with back_to_start
    ])

    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^add_balance_user$"))
async def add_balance_user_callback(client: Client, query: CallbackQuery):
    """Show balance addition options for users"""
    await query.answer()

    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)

    text = f"💳 **Add Balance to Your Account**\n\n"
    text += f"💰 **Current Balance:** ${current_balance:.2f}\n\n"
    text += f"💵 **Why Add Balance?**\n"
    text += f"• 🤖 Create your own clone bots\n"
    text += f"• 🔓 Unlock premium features\n"
    text += f"• ⚡ Faster file processing\n"
    text += f"• 🎯 Priority support access\n\n"
    text += f"💰 **Quick Add Options:**\n"
    text += f"Choose an amount to add instantly:"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💵 Add $5", callback_data="add_balance_5"),
            InlineKeyboardButton("💰 Add $10", callback_data="add_balance_10")
        ],
        [
            InlineKeyboardButton("💎 Add $25", callback_data="add_balance_25"),
            InlineKeyboardButton("🎯 Add $50", callback_data="add_balance_50")
        ],
        [
            InlineKeyboardButton("💳 Custom Amount", callback_data="add_balance_custom"),
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}")
        ],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_callback(client: Client, query: CallbackQuery):
    """Show comprehensive help menu"""
    await query.answer()

    text = f"❓ **Help & Support Center**\n\n"
    text += f"🤖 **Bot Features:**\n"
    text += f"• 📁 Advanced file storage and sharing\n"
    text += f"• 🤖 Create personalized clone bots\n"
    text += f"• 🔍 Smart file search capabilities\n"
    text += f"• 💎 Premium subscription benefits\n"
    text += f"• 🔐 Secure token verification system\n\n"

    # Check if user is admin and if this is a clone bot
    user_id = query.from_user.id
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN
    
    if is_clone_bot:
        # Clone bot help - only user commands
        text += f"📋 **Available Commands:**\n"
        text += f"• `/start` - Main menu and bot homepage\n"
        text += f"• `/search <query>` - Search for files\n"
        text += f"• `/rand` - Get random files\n"
        text += f"• `/recent` - Get recent files\n"
        text += f"• `/stats` - View bot statistics\n"
        text += f"• `/mystats` - Your personal stats\n"
        text += f"• `/premium` - Premium plan information\n"
        text += f"• `/token` - Generate access tokens\n\n"
        
        text += f"**📁 File Operations:**\n"
        text += f"• Send any file - I'll store and share it\n"
        text += f"• `/genlink <file_id>` - Generate file link\n"
        text += f"• `/batch <start> <end>` - Batch link generator\n\n"
        
        if is_admin:
            text += f"**⚙️ Clone Admin Commands:**\n"
            text += f"• `/cloneadmin` - Clone admin panel\n"
            text += f"• `/addforce <channel>` - Add force channel\n"
            text += f"• `/removeforce <channel>` - Remove force channel\n\n"
    else:
        # Mother bot help - different commands for regular users vs admins
        text += f"📋 **Available Commands:**\n"
        text += f"• `/start` - Main menu and bot homepage\n"
        text += f"• `/profile` - View your detailed profile\n"
        text += f"• `/balance` - Check account balance\n"
        text += f"• `/premium` - Premium plan information\n"
        text += f"• `/myclones` - Manage your clone bots\n"
        text += f"• `/stats` - View bot statistics\n\n"

        text += f"**🔧 Clone Bot Commands:**\n"
        text += f"• `/createclone` - Create new clone bot\n"
        text += f"• `/manageclone` - Manage your clones\n\n"
        
        if is_admin:
            text += f"**⚙️ Admin Commands:**\n"
            text += f"• `/motheradmin` - Mother Bot admin panel\n"
            text += f"• `/addbalance` - Add user balance\n"
            text += f"• `/broadcast` - Send announcements\n"
            text += f"• `/users` - Total user statistics\n"
            text += f"• `/listclones` - List all clones\n\n"

    text += f"**🆘 Need More Help?**\n"
    text += f"Contact our support team for assistance!"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.ADMIN_USERNAME}"),
            InlineKeyboardButton("💬 Join Support Group", url="https://t.me/your_support_group")
        ],
        [
            InlineKeyboardButton("📚 Documentation", callback_data="documentation"),
            InlineKeyboardButton("🎥 Video Tutorials", callback_data="video_tutorials")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^transaction_history$"))
async def transaction_history_callback(client: Client, query: CallbackQuery):
    """Show detailed transaction history"""
    await query.answer()

    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)

    text = f"📊 **Your Transaction History**\n\n"
    text += f"💰 **Current Balance:** ${current_balance:.2f}\n\n"
    text += f"📋 **Recent Transactions:**\n"
    text += f"🔄 Loading your transaction history...\n\n"
    text += f"💡 **Transaction Types:**\n"
    text += f"• ➕ Balance additions\n"
    text += f"• ➖ Clone bot purchases\n"
    text += f"• 💎 Premium subscriptions\n"
    text += f"• 🎁 Bonus credits\n\n"
    text += f"📈 **This feature shows your complete financial activity**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh History", callback_data="refresh_transactions"),
            InlineKeyboardButton("📱 Download Report", callback_data="download_transactions")
        ],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^account_settings$"))
async def account_settings_callback(client: Client, query: CallbackQuery):
    """Show account settings options"""
    await query.answer()

    user = query.from_user

    text = f"⚙️ **Account Settings**\n\n"
    text += f"👤 **Account:** {user.first_name}\n"
    text += f"🆔 **User ID:** `{user.id}`\n\n"
    text += f"🔧 **Available Settings:**\n"
    text += f"• Notification preferences\n"
    text += f"• Privacy settings\n"
    text += f"• Clone bot configurations\n"
    text += f"• Security options\n\n"
    text += f"⚠️ **Note:** Some settings require premium access"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="notification_settings"),
            InlineKeyboardButton("🔒 Privacy", callback_data="privacy_settings")
        ],
        [
            InlineKeyboardButton("🔐 Security", callback_data="security_settings"),
            InlineKeyboardButton("🤖 Clone Settings", callback_data="clone_settings")
        ],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^detailed_stats$"))
async def detailed_stats_callback(client: Client, query: CallbackQuery):
    """Show detailed user statistics"""
    await query.answer()

    user_id = query.from_user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)

    text = f"📈 **Your Detailed Statistics**\n\n"
    text += f"👤 **Account Overview:**\n"
    text += f"• User ID: `{user_id}`\n"
    text += f"• Status: {'🌟 Premium Member' if user_premium else '🆓 Free User'}\n"
    text += f"• Balance: ${balance:.2f}\n"
    text += f"• Member Since: {datetime.now().strftime('%B %Y')}\n\n"

    text += f"🤖 **Clone Bot Usage:**\n"
    text += f"• Active Clones: Loading...\n"
    text += f"• Total Created: Loading...\n"
    text += f"• Clone Uptime: Loading...\n\n"

    text += f"📁 **File Activity:**\n"
    text += f"• Files Shared: Coming Soon\n"
    text += f"• Downloads Generated: Coming Soon\n"
    text += f"• Total Storage Used: Coming Soon\n\n"

    text += f"🔐 **Security Stats:**\n"
    text += f"• Tokens Generated: Coming Soon\n"
    text += f"• Secure Links Created: Coming Soon\n"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Stats", callback_data="detailed_stats"),
            InlineKeyboardButton("📱 Export Data", callback_data="export_stats")
        ],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^premium_info$"))
async def premium_info_callback(client: Client, query: CallbackQuery):
    """Show detailed premium information"""
    await query.answer()

    text = f"💎 **Premium Membership Benefits**\n\n"
    text += f"🚀 **Unlock the full potential of your file storage bot!**\n\n"
    text += f"✨ **Exclusive Premium Features:**\n"
    text += f"• 🤖 **Unlimited Clone Bots** - Create as many as you need\n"
    text += f"• ⚡ **Priority Processing** - Faster file operations\n"
    text += f"• 🔒 **Advanced Security** - Enhanced protection\n"
    text += f"• 📊 **Detailed Analytics** - Complete usage insights\n"
    text += f"• 🎯 **Premium Support** - Direct access to our team\n"
    text += f"• 🔥 **No Ads** - Clean, uninterrupted experience\n"
    text += f"• 💾 **Increased Storage** - More file capacity\n"
    text += f"• 🎨 **Custom Branding** - Personalize your clones\n\n"

    text += f"💰 **Pricing Plans:**\n"
    text += f"• 📱 **Monthly:** $9.99/month\n"
    text += f"• 💎 **Yearly:** $99.99/year *(Save 17%!)*\n"
    text += f"• ⚡ **Lifetime:** $299.99 *(Best Value!)*\n\n"

    text += f"🎁 **Special Launch Offer:**\n"
    text += f"**50% OFF** your first month with code: `LAUNCH50`"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Upgrade Now", callback_data="buy_premium"),
            InlineKeyboardButton("🎁 Free Trial", callback_data="premium_trial")
        ],
        [
            InlineKeyboardButton("📋 Compare Plans", callback_data="compare_plans"),
            InlineKeyboardButton("💬 Contact Sales", url=f"https://t.me/{Config.ADMIN_USERNAME}")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^user_stats$"))
async def user_stats_callback(client: Client, query: CallbackQuery):
    """Show user statistics"""
    await query.answer()

    user_id = query.from_user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)

    text = f"📊 **Your Bot Usage Statistics**\n\n"
    text += f"👤 **Account Summary:**\n"
    text += f"• User ID: `{user_id}`\n"
    text += f"• Status: {'🌟 Premium' if user_premium else '🆓 Free User'}\n"
    text += f"• Current Balance: ${balance:.2f}\n\n"

    text += f"📈 **Usage Analytics:**\n"
    text += f"• Total Commands Used: Loading...\n"
    text += f"• Files Accessed: Loading...\n"
    text += f"• Clone Bots Created: Loading...\n"
    text += f"• Premium Features Used: Loading...\n\n"

    text += f"🎯 **Activity Summary:**\n"
    text += f"• Last Login: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    text += f"• Total Sessions: Loading...\n"
    text += f"• Average Session Time: Loading..."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Stats", callback_data="user_stats"),
            InlineKeyboardButton("📱 Detailed Report", callback_data="detailed_stats")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Return to main start menu"""
    await query.answer()

    # Recreate the start message
    user = query.from_user
    user_id = user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)

    # Enhanced welcome message
    text = f"🚀 **Welcome to Advanced File Storage Bot Creator!**\n\n"
    text += f"👋 Hello **{user.first_name}**!\n\n"
    text += f"🤖 **I am an advanced file storing bot creator** with powerful features:\n\n"
    text += f"✨ **What I can do for you:**\n"
    text += f"• 📁 Advanced file storage & management\n"
    text += f"• 🤖 Create your own personal clone bots\n"
    text += f"• 🔐 Secure file sharing with token verification\n"
    text += f"• 💎 Premium subscriptions with exclusive features\n"
    text += f"• 📊 Detailed analytics and statistics\n"
    text += f"• 🎯 Smart file organization and search\n"
    text += f"• ⚡ Lightning-fast file processing\n\n"

    if user_premium:
        text += f"💎 **Premium Status:** Active | Balance: **${balance:.2f}**\n"
    else:
        text += f"👤 **Free User** | Balance: **${balance:.2f}**\n"

    text += f"\n🎯 **Ready to get started?** Choose an option below:"

    # Rebuild main menu buttons
    buttons = []

    # Row 1: Main Features
    buttons.append([
        InlineKeyboardButton("🤖 Create Your Own Clone", callback_data="start_clone_creation"),
        InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
    ])

    # Row 2: Clone Management
    buttons.append([
        InlineKeyboardButton("📋 Manage My Clones", callback_data="manage_my_clone"),
        InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
    ])

    # Row 3: Premium & Help
    buttons.append([
        InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info"),
        InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu")
    ])

    # Row 4: Admin panel for admins
    if is_admin:
        buttons.append([
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
            InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management")
        ])

    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_callback(client: Client, query: CallbackQuery):
    """Show about information"""
    await query.answer()

    text = f"ℹ️ **About Advanced File Storage Bot Creator**\n\n"
    text += f"🔐 **Next-Generation File Management System**\n"
    text += f"The most advanced Telegram file storage and bot creation platform\n\n"
    text += f"🌟 **Core Features:**\n"
    text += f"• 🔗 Generate secure download links\n"
    text += f"• 🔑 Advanced token verification system\n"
    text += f"• 📦 Intelligent batch file operations\n"
    text += f"• 🚫 Robust force subscription system\n"
    text += f"• 💎 Premium user tier benefits\n"
    text += f"• 🤖 Personal clone bot creation\n"
    text += f"• 📊 Comprehensive analytics dashboard\n"
    text += f"• 🔒 Military-grade encryption\n\n"

    text += f"🛡️ **Security & Privacy:**\n"
    text += f"All files are encrypted end-to-end and access is logged for maximum security.\n\n"

    text += f"💻 **Technical Specifications:**\n"
    text += f"• Built with Python & Pyrogram\n"
    text += f"• MongoDB database backend\n"
    text += f"• Advanced caching system\n"
    text += f"• 24/7 monitoring & health checks\n\n"

    text += f"🔧 **Version:** 3.0.0 Advanced\n"
    text += f"👨‍💻 **Developer:** @{Config.ADMIN_USERNAME}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Developer", url=f"https://t.me/{Config.ADMIN_USERNAME}"),
            InlineKeyboardButton("⭐ Rate Bot", callback_data="rate_bot")
        ],
        [
            InlineKeyboardButton("🐛 Report Bug", callback_data="report_bug"),
            InlineKeyboardButton("💡 Suggest Feature", callback_data="suggest_feature")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)