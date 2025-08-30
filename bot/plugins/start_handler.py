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
from bot import utils
from bot.logging import LOGGER
from bot.utils.error_handler import safe_edit_message
import bot.utils.clone_config_loader as clone_config_loader
from bot.database.clone_db import get_clone_by_bot_token # Added import

logger = LOGGER(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    user_id = user.id

    print(f"🚀 DEBUG COMMAND: /start command from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{user.username}, First: {user.first_name}")

    # Handle force subscription first (with admin exemption)
    if not await utils.handle_force_sub(client, message):
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
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)

    # Check if user is premium
    user_premium = await is_premium_user(user.id)

    # Get user balance
    balance = await get_user_balance(user.id)

    # Detect if this is a clone bot or mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN

    if is_clone_bot:
        # Clone bot start message (shortened)
        text = f"🤖 **Welcome {message.from_user.first_name}!**\n\n"
        text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        text += f"🎯 Choose an option below:"

        # Load clone configuration for admin checks and settings
        start_buttons = []
        clone_admin_id = None
        
        try:
            # Get clone data from database using bot token
            clone_data = await get_clone_by_bot_token(bot_token)
            if clone_data:
                clone_admin_id = clone_data.get('admin_id')
                logger.info(f"Clone admin ID: {clone_admin_id}, Current user: {user_id}")
                
                # Add settings button for clone admin
                if user_id == clone_admin_id:
                    start_buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings_panel")])
                    logger.info(f"Added settings button for clone admin {user_id}")
            else:
                logger.warning(f"No clone data found for bot token: {bot_token}")
                
        except Exception as e:
            logger.error(f"Error checking clone admin status: {e}")

        # Get clone settings to determine which buttons to show
        try:
            if not 'clone_data' in locals() or clone_data is None:
                clone_data = await get_clone_by_bot_token(bot_token)
            show_random = clone_data.get('random_mode', True) if clone_data else True
            show_recent = clone_data.get('recent_mode', True) if clone_data else True
            show_popular = clone_data.get('popular_mode', True) if clone_data else True
        except Exception as e:
            # Default to showing all buttons if there's an error
            logger.error(f"Error fetching clone settings: {e}")
            show_random = show_recent = show_popular = True

        # Create file access buttons
        file_buttons = []

        # Always show search button
        file_buttons.append([InlineKeyboardButton("🔍 Search Files", callback_data="search_files")])

        # Show file mode buttons based on settings
        mode_buttons = []
        if show_random:
            mode_buttons.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
        if show_recent:
            mode_buttons.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

        # Add mode buttons in rows of 2
        if mode_buttons:
            if len(mode_buttons) == 2:
                file_buttons.append(mode_buttons)
            else:
                file_buttons.append([mode_buttons[0]])
                if len(mode_buttons) > 1:
                    file_buttons.append([mode_buttons[1]])

        # Add popular files button if enabled
        if show_popular:
            file_buttons.append([InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")])

        # User action buttons
        file_buttons.append([
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
            InlineKeyboardButton("💰 Add Balance", callback_data="add_balance")
        ])

        # Admin buttons for clone admin
        file_buttons.extend(start_buttons) # Add the settings button if applicable

        file_buttons.append([
            InlineKeyboardButton("ℹ️ About", callback_data="about_bot"),
            InlineKeyboardButton("❓ Help", callback_data="help_menu")
        ])

        reply_markup = InlineKeyboardMarkup(file_buttons)

    else:
        # Mother bot start message (shortened)
        text = f"🚀 **Welcome {message.from_user.first_name}!**\n\n"
        text += f"🤖 **Advanced Bot Creator** - Create personal clone bots with file sharing.\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        text += f"🎯 Choose an option below:"

        # Mother bot buttons
        buttons = []

        # Row 1: Main Features
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
        ])

        # Row 2: Management & Stats
        buttons.append([
            InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
        ])

        # Row 3: Premium & About
        buttons.append([
            InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            InlineKeyboardButton("💧 About", callback_data="about_water")
        ])

        # Row 4: Help & Admin
        help_admin_row = [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        # Add admin panel button for Mother Bot admins only (not in clone bots)
        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        if not is_clone_bot and is_mother_admin:
            help_admin_row.append(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
            help_admin_row.append(InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management"))
        buttons.append(help_admin_row)

        reply_markup = InlineKeyboardMarkup(buttons)


    await message.reply_text(
        text,
        reply_markup=reply_markup
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

    # Enhanced welcome message (shortened)
    text = f"🚀 **Welcome {user.first_name}!**\n\n"
    text += f"🤖 **Advanced Bot Creator** - Create personal clone bots with file sharing.\n\n"
    text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
    text += f"🎯 Choose an option below:"

    # Rebuild main menu buttons
    buttons = []

    # Row 1: Main Features
    buttons.append([
        InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
        InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
    ])

    # Row 2: Management & Stats
    buttons.append([
        InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone"),
        InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
    ])

    # Row 3: Premium & About
    buttons.append([
        InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
        InlineKeyboardButton("💧 About", callback_data="about_water")
    ])

    # Row 4: Help & Admin
    help_admin_row = [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
    if is_admin:
        help_admin_row.append(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    buttons.append(help_admin_row)

    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^about_water$"))
async def about_water_callback(client: Client, query: CallbackQuery):
    """Show water-related about information"""
    await query.answer()

    # Check if this is clone bot or mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN

    if is_clone_bot:
        # Clone bot water information
        text = f"💧 **About WaterFlow Clone Bot**\n\n"
        text += f"🌊 **Pure File Streaming Technology**\n"
        text += f"Like water flowing through channels, your files move seamlessly through our secure network.\n\n"
        text += f"💧 **Water-Inspired Features:**\n"
        text += f"• 🌊 **Fluid File Sharing** - Smooth as water\n"
        text += f"• 💎 **Crystal Clear** - Transparent operations\n"
        text += f"• 🔄 **Continuous Flow** - Never-ending service\n"
        text += f"• 🏔️ **Pure & Clean** - No ads, no clutter\n"
        text += f"• 🌀 **Adaptive Stream** - Adjusts to your needs\n\n"
        text += f"🔮 **Like a drop in the ocean, every file matters.**\n\n"
        text += f"🌐 **Clone Bot Technology**\n"
        text += f"This personal clone brings the power of water to your fingertips - "
        text += f"pure, essential, and life-giving file management."
    else:
        # Mother bot water information
        text = f"💧 **About AquaCore Mother Bot**\n\n"
        text += f"🌊 **The Source of All Streams**\n"
        text += f"Like a mighty river feeding countless streams, this Mother Bot powers an entire network of clone bots.\n\n"
        text += f"💧 **Water Cycle Technology:**\n"
        text += f"• ☁️ **Evaporation** - Your files rise to the cloud\n"
        text += f"• 🌧️ **Precipitation** - Data flows to clone networks\n"
        text += f"• 🏔️ **Collection** - Files gather in secure reservoirs\n"
        text += f"• 🌊 **Distribution** - Streams reach every user\n\n"
        text += f"🔋 **Hydro-Powered Features:**\n"
        text += f"• 🤖 **Clone Generation** - Birth new bot streams\n"
        text += f"• 💎 **Premium Aquifers** - Deep feature wells\n"
        text += f"• 🔐 **Water-tight Security** - No leaks, ever\n"
        text += f"• 📊 **Flow Analytics** - Monitor every drop\n\n"
        text += f"🌍 **Sustaining Digital Life**\n"
        text += f"Just as water is essential for life, this bot system is essential for your digital file ecosystem."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌊 Water Facts", callback_data="water_facts"),
            InlineKeyboardButton("💧 Tech Details", callback_data="water_tech")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^water_facts$"))
async def water_facts_callback(client: Client, query: CallbackQuery):
    """Show interesting water facts"""
    await query.answer()

    text = f"🌊 **Amazing Water Facts**\n\n"
    text += f"💧 **Did You Know?**\n"
    text += f"• Earth is 71% water, just like this bot covers 71% of your file needs\n"
    text += f"• Water can exist in 3 states - like our bot's flexible deployment\n"
    text += f"• The human body is 60% water - essential for life\n"
    text += f"• Water has no taste, smell, or color - pure like our code\n"
    text += f"• Water freezes at 0°C and boils at 100°C\n"
    text += f"• A water molecule contains 2 hydrogen and 1 oxygen atom\n\n"
    text += f"🔬 **Water & Technology:**\n"
    text += f"• Data flows like water through networks\n"
    text += f"• Cloud computing mimics the water cycle\n"
    text += f"• Streaming services are named after water flow\n"
    text += f"• Server cooling requires massive amounts of water\n\n"
    text += f"🌍 **Water Conservation:**\n"
    text += f"Just as we optimize code, we should conserve water for future generations."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💧 Back to About", callback_data="about_water")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^water_tech$"))
async def water_tech_callback(client: Client, query: CallbackQuery):
    """Show water technology information"""
    await query.answer()

    text = f"💧 **Water Technology Integration**\n\n"
    text += f"🔬 **Hydro-Inspired Bot Architecture:**\n"
    text += f"• **Flow Control** - Like water pressure regulation\n"
    text += f"• **Stream Processing** - Continuous data flow\n"
    text += f"• **Filtration System** - Clean, secure file processing\n"
    text += f"• **Reservoir Storage** - Massive file capacity\n"
    text += f"• **Distribution Network** - Global clone deployment\n\n"
    text += f"⚡ **Liquid Computing Principles:**\n"
    text += f"• **Fluidity** - Seamless user experience\n"
    text += f"• **Transparency** - Clear operations and pricing\n"
    text += f"• **Adaptability** - Shapes to user needs\n"
    text += f"• **Purity** - No malicious code or tracking\n\n"
    text += f"🌐 **Digital Water Cycle:**\n"
    text += f"1. **Upload** (Evaporation) - Files rise to our servers\n"
    text += f"2. **Process** (Condensation) - Data organizing and indexing\n"
    text += f"3. **Share** (Precipitation) - Files rain down to users\n"
    text += f"4. **Archive** (Collection) - Stored in digital reservoirs"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💧 Back to About", callback_data="about_water")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

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