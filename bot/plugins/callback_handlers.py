import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.utils import get_messages, get_readable_time, schedule_manager, get_shortlink, handle_force_sub
from bot.database import add_user, present_user, is_verified, validate_token_and_verify, is_premium_user, increment_access_count
from bot.utils.command_verification import check_command_limit, use_command
from bot.database.verify_db import create_verification_token
import traceback
from bot.database.verify_db import is_verified
from bot.database.balance_db import get_user_balance
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Global session storage
creation_sessions = {}
admin_sessions = {}

# Define callback priorities to prevent conflicts
CALLBACK_PRIORITIES = {
    "emergency": -10,    # Emergency handlers highest priority
    "admin": 1,          # Admin callbacks
    "approval": 2,       # Approval system
    "premium": 3,        # Premium features
    "search": 4,         # Search related
    "general": 5,        # General callbacks
    "settings": 6,       # Settings handlers
    "catchall": 99       # Catch-all lowest priority
}

def debug_print(message):
    print(f"DEBUG: {message}")
    logger.info(f"DEBUG: {message}")

# Helper function to check if user is Mother Bot admin
def is_mother_admin(user_id):
    """Check if user is Mother Bot admin"""
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())

    if isinstance(admins, tuple):
        admin_list = list(admins)
    else:
        admin_list = admins if isinstance(admins, list) else []

    is_owner = user_id == owner_id
    is_admin = user_id in admin_list
    result = is_owner or is_admin

    return result

# Helper function to check if user is a clone bot admin
def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is a clone bot admin"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        # Mock lookup - replace with actual database lookup
        clone_data = {"admin_id": user_id}
        return clone_data.get('admin_id') == user_id
    except Exception as e:
        logger.error(f"Error checking clone admin status: {e}")
        return False

# Helper function to determine if the current bot instance is a clone bot
def is_clone_bot_instance(client: Client):
    """Checks if the current bot instance is a clone bot"""
    bot_token = getattr(client, 'bot_token', None)
    if bot_token and bot_token != Config.BOT_TOKEN:
        return True, bot_token
    return False, None

async def is_clone_bot_instance_async(client: Client):
    """Async version of clone bot detection"""
    return is_clone_bot_instance(client)

# Import safety wrapper
from bot.utils.callback_safety import safe_callback_handler

# Emergency callback handlers with highest priority to catch button issues
@Client.on_callback_query(filters.regex("^(clone_settings_panel|settings|back_to_start)$"), group=CALLBACK_PRIORITIES["emergency"])
@safe_callback_handler
async def emergency_callback_handler(client: Client, query: CallbackQuery):
    """Emergency handler for critical non-responsive buttons"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.info(f"🚨 EMERGENCY HANDLER: {callback_data} from user {user_id}")
    print(f"🚨 EMERGENCY HANDLER: {callback_data} from user {user_id}")

    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        if callback_data == "clone_settings_panel" or callback_data == "settings":
            # Handle settings panel
            if bot_token == Config.BOT_TOKEN:
                await query.edit_message_text("❌ Settings panel is only available in clone bots!")
                return

            # Get clone data and verify admin
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            if not clone_data:
                await query.edit_message_text("❌ Clone configuration not found!")
                return

            stored_admin_id = clone_data.get('admin_id')

            if int(user_id) != int(stored_admin_id):
                await query.edit_message_text("❌ Only clone admin can access settings!")
                return

            # Create settings panel directly
            show_random = clone_data.get('random_mode', True)
            show_recent = clone_data.get('recent_mode', True)
            show_popular = clone_data.get('popular_mode', True)
            force_join = clone_data.get('force_join_enabled', False)

            text = f"⚙️ **Clone Bot Settings**\n\n"
            text += f"🔧 **Configuration Panel**\n"
            text += f"Manage your clone bot's features and behavior.\n\n"
            text += f"📋 **Current Settings:**\n"
            text += f"• 🎲 Random Files: {'✅ Enabled' if show_random else '❌ Disabled'}\n"
            text += f"• 🆕 Recent Files: {'✅ Enabled' if show_recent else '❌ Disabled'}\n"
            text += f"• 🔥 Popular Files: {'✅ Enabled' if show_popular else '❌ Disabled'}\n"
            text += f"• 🔐 Force Join: {'✅ Enabled' if force_join else '❌ Disabled'}\n\n"
            text += f"⚡ **Quick Actions:**"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🎲 Random: {'✅' if show_random else '❌'}", callback_data="clone_toggle_random"),
                    InlineKeyboardButton(f"🆕 Recent: {'✅' if show_recent else '❌'}", callback_data="clone_toggle_recent")
                ],
                [
                    InlineKeyboardButton(f"🔥 Popular: {'✅' if show_popular else '❌'}", callback_data="clone_toggle_popular"),
                    InlineKeyboardButton(f"🔐 Force Join: {'✅' if force_join else '❌'}", callback_data="clone_toggle_force_join")
                ],
                [
                    InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_verification_mode"),
                    InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener_config")
                ],
                [
                    InlineKeyboardButton("📋 Force Channels", callback_data="clone_force_channels_list"),
                    InlineKeyboardButton("🔧 Advanced Settings", callback_data="clone_advanced_settings")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
                ]
            ])

            await query.edit_message_text(text, reply_markup=buttons)
            return

        elif callback_data in ["random_files", "recent_files", "popular_files"]:
            # Handle file callbacks
            if bot_token == Config.BOT_TOKEN:
                feature_name = callback_data.replace('_files', '').replace('_', ' ').title()
                await query.edit_message_text(f"📁 **{feature_name} Files**\n\n{feature_name} file features are disabled in the mother bot. This functionality is only available in clone bots.")
                return

            # Get clone data to check feature status
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            if not clone_data:
                await query.edit_message_text("❌ Clone configuration not found!")
                return

            # Check feature enablement with proper defaults
            feature_enabled = True
            feature_display_name = ""

            if callback_data == "random_files":
                feature_enabled = clone_data.get('random_mode', True)
                feature_display_name = "Random Files"
            elif callback_data == "recent_files":
                feature_enabled = clone_data.get('recent_mode', True)
                feature_display_name = "Recent Files"
            elif callback_data == "popular_files":
                feature_enabled = clone_data.get('popular_mode', True)
                feature_display_name = "Popular Files"

            if not feature_enabled:
                await query.edit_message_text(
                    f"❌ **{feature_display_name} Disabled**\n\n"
                    "This feature has been disabled by the bot admin.\n\n"
                    "Contact the bot administrator if you need access.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                    ])
                )
                return

            # Route to clone random files handlers with proper callback data mapping
            try:
                if callback_data == "random_files":
                    # Import and call the handler directly
                    from bot.plugins.clone_random_files import handle_clone_random_files
                    # Create a modified query with the correct callback data
                    query.data = "clone_random_files"
                    await handle_clone_random_files(client, query)
                elif callback_data == "recent_files":
                    # Import and call the handler directly
                    from bot.plugins.clone_random_files import handle_clone_recent_files
                    # Create a modified query with the correct callback data
                    query.data = "clone_recent_files"
                    await handle_clone_recent_files(client, query)
                elif callback_data == "popular_files":
                    # Import and call the handler directly
                    from bot.plugins.clone_random_files import handle_clone_popular_files
                    # Create a modified query with the correct callback data
                    query.data = "clone_popular_files"
                    await handle_clone_popular_files(client, query)
            except Exception as handler_error:
                logger.error(f"Error in {callback_data} handler: {handler_error}")
                traceback.print_exc()
                await query.edit_message_text(f"❌ Error loading {feature_display_name.lower()}. Please try again.")

        elif callback_data == "back_to_start":
            # Handle back to start
            is_clone, bot_token = await is_clone_bot_instance_async(client)

            if is_clone:
                try:
                    from bot.database.clone_db import get_clone_by_bot_token
                    from bot.database.balance_db import get_user_balance

                    clone_data = await get_clone_by_bot_token(bot_token)
                    balance = await get_user_balance(user_id)

                    text = f"🤖 **Welcome {query.from_user.first_name}!**\n\n"
                    text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
                    text += f"💰 Balance: ${balance:.2f}\n\n"
                    text += f"🎯 Choose an option below:"

                    start_buttons = []

                    if clone_data and clone_data.get('admin_id') == user_id:
                        start_buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings_panel")])

                    show_random = clone_data.get('random_mode', True) if clone_data else True
                    show_recent = clone_data.get('recent_mode', True) if clone_data else True
                    show_popular = clone_data.get('popular_mode', True) if clone_data else True

                    file_buttons = []

                    mode_row1 = []
                    if show_random:
                        mode_row1.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
                    if show_recent:
                        mode_row1.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

                    if mode_row1:
                        file_buttons.append(mode_row1)

                    if show_popular:
                        file_buttons.append([InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")])

                    file_buttons.append([
                        InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
                        InlineKeyboardButton("💰 Add Balance", callback_data="add_balance")
                    ])

                    file_buttons.extend(start_buttons)

                    file_buttons.append([
                        InlineKeyboardButton("ℹ️ About", callback_data="about_bot"),
                        InlineKeyboardButton("❓ Help", callback_data="help_menu")
                    ])

                    reply_markup = InlineKeyboardMarkup(file_buttons)
                    await query.edit_message_text(text, reply_markup=reply_markup)
                    return

                except Exception as e:
                    logger.error(f"Error in clone back_to_start: {e}")
                    await query.answer("❌ Error loading clone start menu", show_alert=True)
                    return

            # For mother bot
            try:
                from bot.plugins.start_handler import back_to_start_callback
                await back_to_start_callback(client, query)
            except Exception as e:
                debug_print(f"Error in mother bot back_to_start: {e}")
                await query.answer("❌ Error returning to start. Please use /start command.")

    except Exception as e:
        logger.error(f"Error in emergency callback handler: {e}")
        traceback.print_exc()
        try:
            await query.answer("❌ Button error. Please try again.", show_alert=True)
        except:
            pass

# Admin Panel Callbacks
@Client.on_callback_query(filters.regex("^(admin_panel|bot_management)$"), group=CALLBACK_PRIORITIES["admin"])
async def handle_start_admin_buttons(client: Client, query: CallbackQuery):
    """Handle admin panel and bot management buttons from start message"""
    user_id = query.from_user.id
    callback_data = query.data

    if callback_data == "admin_panel":
        is_clone_bot, _ = is_clone_bot_instance(client)
        if is_clone_bot:
            await query.answer("❌ Admin panel not available in clone bots!", show_alert=True)
            return

        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return

        try:
            from bot.plugins.mother_admin import mother_admin_panel
            await mother_admin_panel(client, query)
        except Exception as e:
            await query.answer("❌ Error loading admin panel!", show_alert=True)

    elif callback_data == "bot_management":
        is_clone_bot, _ = is_clone_bot_instance(client)
        if is_clone_bot:
            await query.answer("❌ Bot management not available in clone bots!", show_alert=True)
            return

        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return

        text = f"🔧 **Bot Management Panel**\n\n"
        text += f"🤖 **System Operations:**\n"
        text += f"• Monitor bot performance\n"
        text += f"• Manage system resources\n"
        text += f"• View system logs\n"
        text += f"• Check bot health status\n\n"
        text += f"📊 **Quick Actions:**"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 System Stats", callback_data="system_stats"),
                InlineKeyboardButton("🔄 Restart Bots", callback_data="restart_system")
            ],
            [
                InlineKeyboardButton("📝 View Logs", callback_data="view_logs"),
                InlineKeyboardButton("🏥 Health Check", callback_data="health_check")
            ],
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

# File browsing callbacks with higher priority than emergency handler
@Client.on_callback_query(filters.regex("^(random_files|recent_files|popular_files)$"), group=CALLBACK_PRIORITIES["search"])
async def file_browsing_callback_handler(client: Client, query: CallbackQuery):
    """Handle file browsing callbacks with proper routing"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.info(f"📁 File browsing callback: {callback_data} from user {user_id}")
    print(f"📁 File browsing callback: {callback_data} from user {user_id}")

    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is mother bot
        if bot_token == Config.BOT_TOKEN:
            feature_name = callback_data.replace('_files', '').replace('_', ' ').title()
            await query.edit_message_text(
                f"📁 **{feature_name} Files**\n\n"
                f"{feature_name} file features are disabled in the mother bot. "
                f"This functionality is only available in clone bots.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return

        # Get clone data to check feature status
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found!")
            return

        # Check feature enablement with proper defaults
        feature_enabled = True
        feature_display_name = ""

        if callback_data == "random_files":
            feature_enabled = clone_data.get('random_mode', True)
            feature_display_name = "Random Files"
        elif callback_data == "recent_files":
            feature_enabled = clone_data.get('recent_mode', True)
            feature_display_name = "Recent Files"
        elif callback_data == "popular_files":
            feature_enabled = clone_data.get('popular_mode', True)
            feature_display_name = "Popular Files"

        if not feature_enabled:
            await query.edit_message_text(
                f"❌ **{feature_display_name} Disabled**\n\n"
                "This feature has been disabled by the bot admin.\n\n"
                "Contact the bot administrator if you need access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return

        # Handle file browsing directly here instead of routing to external handlers
        if callback_data == "random_files":
            await handle_random_files_display(client, query, clone_data)
        elif callback_data == "recent_files":
            await handle_recent_files_display(client, query, clone_data)
        elif callback_data == "popular_files":
            await handle_popular_files_display(client, query, clone_data)

    except Exception as e:
        logger.error(f"Error in file browsing callback handler: {e}")
        traceback.print_exc()
        await query.answer("❌ Error processing request. Please try again.", show_alert=True)

async def handle_random_files_display(client: Client, query: CallbackQuery, clone_data: dict):
    """Display random files"""
    try:
        text = "🎲 **Random Files**\n\n"
        text += "🔄 Loading random files from the database...\n\n"
        text += "📁 Here are some random files from our collection:"

        # Sample buttons for random files (replace with actual file data)
        buttons = []
        buttons.append([InlineKeyboardButton("🎬 Sample Movie.mp4", callback_data="file_sample1")])
        buttons.append([InlineKeyboardButton("📚 Sample Document.pdf", callback_data="file_sample2")])
        buttons.append([InlineKeyboardButton("🎵 Sample Audio.mp3", callback_data="file_sample3")])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="random_files"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in handle_random_files_display: {e}")
        await query.edit_message_text("❌ Error loading random files. Please try again.")

async def handle_recent_files_display(client: Client, query: CallbackQuery, clone_data: dict):
    """Display recent files"""
    try:
        text = "🆕 **Recent Files**\n\n"
        text += "📅 Showing the most recently uploaded files...\n\n"
        text += "🕐 All files are sorted by upload time:"

        # Sample buttons for recent files (replace with actual file data)
        buttons = []
        buttons.append([InlineKeyboardButton("🆕 New Movie (2 hours ago)", callback_data="file_recent1")])
        buttons.append([InlineKeyboardButton("📄 Document (5 hours ago)", callback_data="file_recent2")])
        buttons.append([InlineKeyboardButton("🎵 Music Album (1 day ago)", callback_data="file_recent3")])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="recent_files"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in handle_recent_files_display: {e}")
        await query.edit_message_text("❌ Error loading recent files. Please try again.")

async def handle_popular_files_display(client: Client, query: CallbackQuery, clone_data: dict):
    """Display popular files"""
    try:
        text = "🔥 **Most Popular Files**\n\n"
        text += "📈 These are the most downloaded files:\n\n"
        text += "⭐ Ranked by download count and user ratings:"

        # Sample buttons for popular files (replace with actual file data)
        buttons = []
        buttons.append([InlineKeyboardButton("🔥 Trending Movie (1.2k downloads)", callback_data="file_popular1")])
        buttons.append([InlineKeyboardButton("📖 Popular eBook (980 downloads)", callback_data="file_popular2")])
        buttons.append([InlineKeyboardButton("🎶 Hit Song (756 downloads)", callback_data="file_popular3")])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="popular_files"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in handle_popular_files_display: {e}")
        await query.edit_message_text("❌ Error loading popular files. Please try again.")

# General Callbacks
@Client.on_callback_query(filters.regex("^(about|help|my_stats|close|about_bot|help_menu|user_profile|transaction_history|add_balance|manage_my_clone|show_referral_main)$"), group=CALLBACK_PRIORITIES["general"])
async def general_callback_handler(client: Client, query: CallbackQuery):
    """Handle general purpose callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    if callback_data == "about":
        from bot.plugins.callback import about_callback
        await about_callback(client, query)
    elif callback_data in ["help", "help_menu"]:
        from bot.plugins.start_handler import help_callback
        await help_callback(client, query)
    elif callback_data == "about_bot":
        from bot.plugins.start_handler import about_callback
        await about_callback(client, query)
    elif callback_data == "user_profile":
        from bot.plugins.start_handler import profile_callback
        await profile_callback(client, query)
    elif callback_data == "transaction_history":
        from bot.plugins.start_handler import transaction_history_callback
        await transaction_history_callback(client, query)
    elif callback_data == "add_balance":
        from bot.plugins.balance_management import show_balance_options
        await show_balance_options(client, query)
    elif callback_data == "manage_my_clone":
        from bot.plugins.clone_management import manage_user_clone
        await manage_user_clone(client, query)
    elif callback_data == "show_referral_main":
        from bot.plugins.referral_program import show_referral_main
        await show_referral_main(client, query)
    elif callback_data == "my_stats":
        from bot.plugins.callback import my_stats_callback
        await my_stats_callback(client, query)
    elif callback_data == "close":
        from bot.plugins.callback import close
        await close(client, query)

# Premium System Callbacks
@Client.on_callback_query(filters.regex("^(show_premium_plans|buy_premium)"), group=CALLBACK_PRIORITIES["premium"])
async def premium_callback_handler(client: Client, query: CallbackQuery):
    """Handle premium-related callbacks"""
    try:
        if query.data == "show_premium_plans":
            from bot.plugins.callback import show_premium_callback
            await show_premium_callback(client, query)
        elif query.data.startswith("buy_premium"):
            from bot.plugins.callback import buy_premium_callback
            await buy_premium_callback(client, query)
    except Exception as e:
        logger.error(f"Error in premium callback: {e}")
        await query.answer("❌ Error processing request", show_alert=True)

# Quick approval/rejection callbacks
@Client.on_callback_query(filters.regex("^(quick_approve|quick_reject|view_request):"), group=CALLBACK_PRIORITIES["approval"])
async def handle_quick_actions(client: Client, query: CallbackQuery):
    """Handle quick approval, rejection, and view request actions"""
    user_id = query.from_user.id

    # Check admin permissions
    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    try:
        action, request_id = query.data.split(":", 1)

        if action == "quick_approve":
            from bot.plugins.clone_approval import approve_clone_request
            await approve_clone_request(client, query, request_id)
        elif action == "quick_reject":
            from bot.plugins.clone_approval import reject_clone_request
            await reject_clone_request(client, query, request_id)
        elif action == "view_request":
            await handle_view_request_details(client, query, request_id)

    except Exception as e:
        print(f"❌ ERROR IN QUICK ACTIONS CALLBACK: {e}")
        traceback.print_exc()
        await query.answer("❌ Error processing request!", show_alert=True)

async def handle_view_request_details(client: Client, query: CallbackQuery, request_id: str):
    """Show detailed view of a clone request"""
    user_id = query.from_user.id
    try:
        from bot.database.clone_db import get_clone_request_by_id
        request = await get_clone_request_by_id(request_id)

        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        plan_details = request.get('plan_details', {})
        text = f"📋 **Clone Request Details**\n\n"
        text += f"🆔 **Request ID:** `{request['request_id']}`\n"
        text += f"👤 **User ID:** `{request['user_id']}`\n"
        text += f"🤖 **Bot Username:** @{request.get('bot_username', 'Unknown')}\n"
        text += f"🔑 **Bot Token:** `{request['bot_token'][:8]}...{request['bot_token'][-4:]}`\n"
        text += f"🗄️ **MongoDB URL:** `{request['mongodb_url'][:30]}...`\n"
        text += f"💰 **Plan:** {plan_details.get('name', 'Unknown')}\n"
        text += f"💵 **Price:** ${plan_details.get('price', 'N/A')}\n"
        text += f"📅 **Duration:** {plan_details.get('duration_days', 'N/A')} days\n"
        text += f"📊 **Status:** {request['status']}\n"
        text += f"🕐 **Submitted:** {request['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_request:{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_request:{request_id}")
            ],
            [InlineKeyboardButton("🔙 Back to Pending Requests", callback_data="mother_pending_requests")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        print(f"❌ ERROR VIEWING REQUEST DETAILS: {e}")
        traceback.print_exc()
        await query.answer("❌ Error loading request details!", show_alert=True)

# Add handlers for bot management callbacks
@Client.on_callback_query(filters.regex("^(system_stats|restart_system|view_logs|health_check)$"), group=CALLBACK_PRIORITIES["admin"])
async def handle_bot_management_callbacks(client: Client, query: CallbackQuery):
    """Handle bot management callbacks"""
    user_id = query.from_user.id

    # Check admin permissions
    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    if query.data == "system_stats":
        try:
            from clone_manager import clone_manager
            running_clones = len(clone_manager.get_running_clones()) if hasattr(clone_manager, 'get_running_clones') else 0

            text = f"📊 **System Statistics**\n\n"
            text += f"🤖 **Bot Status:**\n"
            text += f"• Mother Bot: ✅ Online\n"
            text += f"• Running Clones: {running_clones}\n"
            text += f"• System Status: ✅ Healthy\n\n"

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="system_stats")],
                [InlineKeyboardButton("🔙 Back to Management", callback_data="bot_management")]
            ])

            await query.edit_message_text(text, reply_markup=buttons)
        except Exception as e:
            await query.answer(f"❌ Error loading stats: {str(e)}", show_alert=True)

    elif query.data == "health_check":
        text = f"🏥 **System Health Check**\n\n"
        text += f"✅ **All Systems Operational**\n\n"
        text += f"🔍 **Health Status:**\n"
        text += f"• Database Connection: ✅ OK\n"
        text += f"• Telegram API: ✅ OK\n"
        text += f"• Clone Services: ✅ OK\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Run Check Again", callback_data="health_check")],
            [InlineKeyboardButton("🔙 Back to Management", callback_data="bot_management")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

# Mother Bot callback handlers
@Client.on_callback_query(filters.regex("^(mother_|back_to_mother_panel|admin_)"), group=CALLBACK_PRIORITIES["admin"])
async def mother_admin_callback_router(client: Client, query: CallbackQuery):
    """Route Mother Bot admin callbacks"""
    user_id = query.from_user.id

    # Block mother bot callbacks in clone bots
    is_clone_bot, _ = is_clone_bot_instance(client)
    if is_clone_bot:
        await query.answer("❌ Mother bot features not available in clone bots!", show_alert=True)
        return

    # Check if user is mother bot admin
    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access to mother bot features!", show_alert=True)
        return

    # Let specific handlers handle their callbacks
    pass

# Add handlers for simplified clone creation flow
@Client.on_callback_query(filters.regex("^back_to_step3$"))
async def back_to_step3_callback(client, query: CallbackQuery):
    """Handle back to step 3"""
    user_id = query.from_user.id
    await query.answer()

    session = creation_sessions.get(user_id)

    if not session:
        await query.edit_message_text(
            "❌ Session expired! Please start over.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]
            ])
        )
        return

    # Show step 3 (database) directly
    data = session['data']
    plan = data.get('plan_details', {})
    bot_username = data.get('bot_username', 'your_bot')

    text = f"🗄️ **Step 3/3: Database URL**\n\n"
    text += f"✅ **Bot:** @{bot_username}\n"
    text += f"✅ **Plan:** {plan.get('name', 'Selected Plan')}\n\n"
    text += f"Now provide your MongoDB connection URL.\n\n"
    text += f"**📋 Quick Options:**\n\n"
    text += f"**Option 1: Free MongoDB Atlas**\n"
    text += f"• Sign up at mongodb.com/atlas\n"
    text += f"• Create free cluster\n"
    text += f"• Get connection string\n\n"
    text += f"**Option 2: Contact Admin**\n"
    text += f"• Get shared database access\n"
    text += f"• Ready-to-use connection\n\n"
    text += f"**📝 URL Format:**\n"
    text += f"`mongodb+srv://user:pass@cluster.mongodb.net/dbname`\n\n"
    text += f"Please send your MongoDB URL now:"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Get MongoDB Atlas", url="https://www.mongodb.com/atlas")],
            [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
            [InlineKeyboardButton("❓ Database Help", callback_data="database_help")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
        ])
    )

# Feature Toggle Callbacks
@Client.on_callback_query(filters.regex("^toggle_feature#"), group=CALLBACK_PRIORITIES["admin"])
async def feature_toggle_callback(client: Client, query: CallbackQuery):
    """Handle feature toggling callbacks"""
    user_id = query.from_user.id

    # Import from admin panel
    from bot.plugins.admin_panel import toggle_feature_handler
    await toggle_feature_handler(client, query)

# Clone Random Files Callbacks - Higher priority to catch them before catch-all
@Client.on_callback_query(filters.regex("^(clone_random_files|clone_recent_files|clone_popular_files)$"), group=CALLBACK_PRIORITIES["general"])
@safe_callback_handler
async def handle_clone_files_callbacks(client: Client, query: CallbackQuery):
    """Handle clone-specific file callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.info(f"🎲 Clone files callback: {callback_data} from user {user_id}")

    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Ensure this is a clone bot
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ This feature is only available in clone bots!")
            return

        # Route to appropriate handler
        if callback_data == "clone_random_files":
            from bot.plugins.clone_random_files import handle_clone_random_files
            await handle_clone_random_files(client, query)
        elif callback_data == "clone_recent_files":
            from bot.plugins.clone_random_files import handle_clone_recent_files
            await handle_clone_recent_files(client, query)
        elif callback_data == "clone_popular_files":
            from bot.plugins.clone_random_files import handle_clone_popular_files
            await handle_clone_popular_files(client, query)

    except Exception as e:
        logger.error(f"Error in clone files callback handler: {e}")
        await query.answer("❌ Error processing request", show_alert=True)

# Catch-all handler for unhandled callbacks
@Client.on_callback_query(group=CALLBACK_PRIORITIES["catchall"])
@safe_callback_handler
async def catchall_callback_handler(client: Client, query: CallbackQuery):
    """Handle any unhandled callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    logger.warning(f"🚨 UNHANDLED CALLBACK: {callback_data} from user {user_id}")
    print(f"🚨 UNHANDLED CALLBACK: {callback_data} from user {user_id}")

    # Handle common unmatched callbacks
    if callback_data in ["clone_settings_panel", "settings"]:
        await query.answer("🔧 Settings access - redirecting...", show_alert=False)
        # Force redirect to settings handler
        from bot.plugins.clone_admin_settings import clone_settings_command

        class MessageProxy:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat if query.message else None
                self.message_id = query.message.id if query.message else None

            async def reply_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

            async def edit_message_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

        proxy_message = MessageProxy(query)
        await clone_settings_command(client, proxy_message)
        return

    # For other unhandled callbacks, provide generic error
    await query.answer("❌ Button not responding. Please try again or contact support.", show_alert=True)

# Additional callback handlers for new features
@Client.on_callback_query(filters.regex("^add_balance_5$"))
async def add_balance_5_callback(client: Client, query: CallbackQuery):
    """Handle $5 balance addition"""
    await query.answer()

    text = f"💵 **Add $5.00 to Balance**\n\n"
    text += f"💳 **Payment Information:**\n"
    text += f"• Amount: $5.00 USD\n"
    text += f"• Processing Fee: $0.30\n"
    text += f"• Total: $5.30\n\n"
    text += f"📞 **To complete payment:**\n"
    text += f"Contact admin with payment method preference."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Pay via PayPal", callback_data="payment_paypal_5"),
            InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank_5")
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
        ],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="add_balance_user")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^add_balance_10$"))
async def add_balance_10_callback(client: Client, query: CallbackQuery):
    """Handle $10 balance addition"""
    await query.answer()

    text = f"💰 **Add $10.00 to Balance**\n\n"
    text += f"💳 **Payment Information:**\n"
    text += f"• Amount: $10.00 USD\n"
    text += f"• Processing Fee: $0.50\n"
    text += f"• Total: $10.50\n\n"
    text += f"🎁 **Bonus:** Get $1 extra credit!\n"
    text += f"📞 **To complete payment:**\n"
    text += f"Contact admin with payment method preference."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Pay via PayPal", callback_data="payment_paypal_10"),
            InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank_10")
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
        ],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="add_balance_user")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^add_balance_25$"))
async def add_balance_25_callback(client: Client, query: CallbackQuery):
    """Handle $25 balance addition"""
    await query.answer()

    text = f"💎 **Add $25.00 to Balance**\n\n"
    text += f"💳 **Payment Information:**\n"
    text += f"• Amount: $25.00 USD\n"
    text += f"• Processing Fee: $1.00\n"
    text += f"• Total: $26.00\n\n"
    text += f"🎁 **Special Bonus:** Get $3 extra credit!\n"
    text += f"⭐ **Perfect for:** Multiple clone bot creation\n"
    text += f"📞 **To complete payment:**\n"
    text += f"Contact admin with payment method preference."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Pay via PayPal", callback_data="payment_paypal_25"),
            InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank_25")
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
        ],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="add_balance_user")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^add_balance_50$"))
async def add_balance_50_callback(client: Client, query: CallbackQuery):
    """Handle $50 balance addition"""
    await query.answer()

    text = f"🎯 **Add $50.00 to Balance**\n\n"
    text += f"💳 **Payment Information:**\n"
    text += f"• Amount: $50.00 USD\n"
    text += f"• Processing Fee: $1.50\n"
    text += f"• Total: $51.50\n\n"
    text += f"🔥 **Mega Bonus:** Get $7 extra credit!\n"
    text += f"⭐ **Perfect for:** Premium features & multiple clones\n"
    text += f"🎁 **Includes:** Priority support access\n"
    text += f"📞 **To complete payment:**\n"
    text += f"Contact admin with payment method preference."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Pay via PayPal", callback_data="payment_paypal_50"),
            InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank_50")
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
        ],
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="add_balance_user")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(back_to_start|restart)$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Handle back to start callback"""
    try:
        await query.answer()

        # Simulate start command
        user = query.from_user
        user_id = user.id

        # Check if this is mother bot or clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot = bot_token != Config.BOT_TOKEN

        if is_clone_bot:
            text = f"🤖 **Welcome back {user.first_name}!**\n\n"
            text += f"📁 **Your Personal File Bot**\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                    InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files")
                ],
                [InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")],
                [
                    InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
                    InlineKeyboardButton("❓ Help", callback_data="help_menu")
                ]
            ])
        else:
            text = f"🚀 **Welcome back {user.first_name}!**\n\n"
            text += f"🤖 **Bot Creator Dashboard**\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
                    InlineKeyboardButton("👤 Profile", callback_data="user_profile")
                ],
                [
                    InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone"),
                    InlineKeyboardButton("❓ Help", callback_data="help_menu")
                ]
            ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"❌ Error in back_to_start callback: {e}")
        await query.answer("❌ Error occurred. Please try /start command.", show_alert=True)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_callback(client: Client, query: CallbackQuery):
    """Handle help menu callback"""
    try:
        await query.answer()

        help_text = """
🤖 **Bot Help**

**Available Features:**
• File sharing and management
• Clone bot creation
• Premium subscriptions
• User profiles and balances

**Commands:**
• `/start` - Start the bot
• `/help` - Show help
• `/profile` - View profile

**Need Support?**
Contact the administrator for assistance.
        """

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
        ])

        await query.edit_message_text(help_text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"❌ Error in help menu: {e}")
        await query.answer("❌ Error loading help.", show_alert=True)

@Client.on_callback_query(filters.regex("^user_profile$"))
async def user_profile_callback(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    try:
        await query.answer()
        user = query.from_user

        profile_text = f"""
👤 **User Profile**

**Name:** {user.first_name}
**Username:** @{user.username or 'Not set'}
**User ID:** `{user.id}`
**Status:** Free User

**Account Info:**
• Joined: Recently
• Files Shared: 0
• Premium: No

**Actions:**
        """

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💎 Get Premium", callback_data="premium_info"),
                InlineKeyboardButton("💰 Add Balance", callback_data="add_balance")
            ],
            [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
        ])

        await query.edit_message_text(profile_text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"❌ Error in user profile: {e}")
        await query.answer("❌ Error loading profile.", show_alert=True)

# Placeholder callbacks for features not yet implemented
@Client.on_callback_query(filters.regex("^(random_files|recent_files|popular_files|premium_info|add_balance|manage_my_clone|user_stats|show_referral_main|about_water|admin_panel|start_clone_creation)$"))
async def placeholder_callbacks(client: Client, query: CallbackQuery):
    """Handle placeholder callbacks for features under development"""
    try:
        await query.answer()

        feature_name = query.data.replace('_', ' ').title()

        text = f"🚧 **{feature_name}**\n\n"
        text += f"This feature is currently under development.\n\n"
        text += f"Please check back later or contact the administrator."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Start", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"❌ Error in placeholder callback: {e}")
        await query.answer("❌ Feature under development.", show_alert=True)
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(back_to_start|restart)$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Handle back to start callback"""
    try:
        await query.answer()

        # Simulate start command
        user = query.from_user
        user_id = user.id

        # Check if this is mother bot or clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot = bot_token != Config.BOT_TOKEN

        if is_clone_bot:
            text = f"🤖 **Welcome back {user.first_name}!**\n\n"
            text += f"📁 **Your Personal File Bot**\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                    InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files")
                ],
                [InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")],
                [
                    InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
                    InlineKeyboardButton("❓ Help", callback_data="help_menu")
                ]
            ])
        else:
            text = f"🚀 **Welcome back {user.first_name}!**\n\n"
            text += f"🤖 **Advanced Bot Creator**\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
                    InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
                ],
                [
                    InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone"),
                    InlineKeyboardButton("💎 Premium", callback_data="premium_info")
                ],
                [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
            ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in back_to_start_callback: {e}")
        await query.answer("❌ Error occurred. Please try /start command.", show_alert=True)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_callback(client: Client, query: CallbackQuery):
    """Show help menu"""
    await query.answer()

    text = f"❓ **Help & Support**\n\n"
    text += f"**Available Commands:**\n"
    text += f"• `/start` - Main menu\n"
    text += f"• `/help` - Show this help\n\n"
    text += f"**Need assistance?**\n"
    text += f"Contact support for help!"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^about_"))
async def about_callback(client: Client, query: CallbackQuery):
    """Handle about callbacks"""
    await query.answer()

    text = f"ℹ️ **About This Bot**\n\n"
    text += f"Advanced Telegram bot with file sharing capabilities.\n\n"
    text += f"🔧 **Version:** 3.0.0\n"
    text += f"👨‍💻 **Developer:** @admin"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query()
async def catch_all_callback(client: Client, query: CallbackQuery):
    """Handle unhandled callbacks"""
    logger.warning(f"Unhandled callback: {query.data} from user {query.from_user.id}")
    await query.answer("⚠️ This feature is not available yet.", show_alert=True)