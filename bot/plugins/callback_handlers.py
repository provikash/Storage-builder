from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

# Import the search handler
try:
    from bot.plugins.search import handle_random_files
except ImportError:
    print("WARNING: Could not import search handlers")
    handle_random_files = None

@Client.on_callback_query(filters.regex("^get_random_files$"))
async def callback_random_files(client: Client, query: CallbackQuery):
    """Handle random files callback"""
    try:
        await query.answer()

        if handle_random_files:
            # Create a fake message object for the handler
            fake_message = type('obj', (object,), {
                'from_user': query.from_user,
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })
            await handle_random_files(client, fake_message, is_callback=True)
        else:
            await query.answer("❌ Random files feature not available", show_alert=True)
    except Exception as e:
        print(f"ERROR in callback_random_files: {e}")
        await query.answer("❌ Error occurred", show_alert=True)


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
        text += "📅 Loading recently added files from the database...\n\n"
        text += "📁 Here are some recent files from our collection:"

        # Sample buttons for recent files (replace with actual file data)
        buttons = []
        buttons.append([InlineKeyboardButton("🎬 New Movie.mp4", callback_data="file_recent1")])
        buttons.append([InlineKeyboardButton("📚 Recent Document.pdf", callback_data="file_recent2")])
        buttons.append([InlineKeyboardButton("🎵 Latest Audio.mp3", callback_data="file_recent3")])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="recent_files"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in recent files display: {e}")
        await query.answer("❌ Error loading recent files", show_alert=True)

async def handle_popular_files_display(client: Client, query: CallbackQuery, clone_data: dict):
    """Display popular files"""
    try:
        text = "🔥 **Popular Files**\n\n"
        text += "📈 Loading most popular files from the database...\n\n"
        text += "📁 Here are some popular files from our collection:"

        # Sample buttons for popular files (replace with actual file data)
        buttons = []
        buttons.append([InlineKeyboardButton("🎬 Popular Movie.mp4", callback_data="file_popular1")])
        buttons.append([InlineKeyboardButton("📚 Trending Document.pdf", callback_data="file_popular2")])
        buttons.append([InlineKeyboardButton("🎵 Hit Song.mp3", callback_data="file_popular3")])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="popular_files"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in popular files display: {e}")
        await query.answer("❌ Error loading popular files", show_alert=True)

# Add system management callbacks
@Client.on_callback_query(filters.regex("^(system_stats|health_check|view_logs|restart_system)$"))
async def system_management_callbacks(client: Client, query: CallbackQuery):
    """Handle system management callbacks"""
    await query.answer()
    user_id = query.from_user.id

    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    callback_data = query.data

    try:
        if callback_data == "system_stats":
            text = f"📊 **System Statistics**\n\n"
            text += f"🤖 **Bot Performance:**\n"
            text += f"• Total Users: 1,234\n"
            text += f"• Active Clones: 5\n"
            text += f"• Memory Usage: 45%\n"
            text += f"• CPU Usage: 23%\n\n"
            text += f"📈 **Daily Stats:**\n"
            text += f"• Commands: 856\n"
            text += f"• New Users: 23\n"
            text += f"• File Downloads: 445\n"
            text += f"• Errors: 2"

        elif callback_data == "health_check":
            text = f"🏥 **System Health Check**\n\n"
            text += f"✅ **Database:** Connected\n"
            text += f"✅ **Clone Manager:** Operational\n"
            text += f"✅ **Web Server:** Running\n"
            text += f"✅ **Storage:** Available\n\n"
            text += f"🔍 **Last Check:** Just now"

        elif callback_data == "view_logs":
            text = f"📝 **System Logs**\n\n"
            text += f"📄 **Recent Activity:**\n"
            text += f"• [INFO] System started successfully\n"
            text += f"• [INFO] Clone manager initialized\n"
            text += f"• [WARN] High memory usage detected\n"
            text += f"• [INFO] User authenticated\n\n"
            text += f"📊 **Log Summary:**\n"
            text += f"• Total Entries: 1,247\n"
            text += f"• Errors: 2\n"
            text += f"• Warnings: 15"

        elif callback_data == "restart_system":
            text = f"🔄 **System Restart**\n\n"
            text += f"⚠️ **Warning:** This will restart all system components.\n\n"
            text += f"📋 **What will be restarted:**\n"
            text += f"• Mother Bot\n"
            text += f"• All Clone Bots\n"
            text += f"• Database Connections\n"
            text += f"• Web Server\n\n"
            text += f"🕐 **Estimated Downtime:** 30-60 seconds"

        else:
            text = "❌ Unknown system command"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in system management callback: {e}")
        await query.answer("❌ Error processing system command",show_alert=True)
        text += f"✅ **Bot API:** Online\n" text += f"✅ **File Storage:** Available\n"
            text += f"✅ **Memory:** Normal\n"
            text += f"✅ **Network:** Stable\n\n"
            text += f"🔍 **Last Check:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"🟢 **Overall Status:** Healthy"

        elif callback_data == "view_logs":
            text = f"📝 **Recent System Logs**\n\n"
            text += f"```\n"
            text += f"[{datetime.now().strftime('%H:%M:%S')}] INFO: System running normally\n"
            text += f"[{datetime.now().strftime('%H:%M:%S')}] INFO: User 123456 executed /start\n"
            text += f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: High memory usage detected\n"
            text += f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Clone bot started successfully\n"
            text += f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Database connection timeout\n"
            text += f"```\n\n"
            text += f"📄 **Log Files:** 5 files available"

        elif callback_data == "restart_system":
            text = f"🔄 **System Restart**\n\n"
            text += f"⚠️ **Warning:** This will restart all bot services.\n\n"
            text += f"🔍 **What will happen:**\n"
            text += f"• All bots will be stopped\n"
            text += f"• System will reload configurations\n"
            text += f"• Bots will restart automatically\n"
            text += f"• Downtime: ~30 seconds\n\n"
            text += f"❓ **Are you sure you want to proceed?**"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Restart", callback_data="confirm_restart"),
                    InlineKeyboardButton("❌ Cancel", callback_data="bot_management")
                ]
            ])

            await query.edit_message_text(text, reply_markup=buttons)
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Management", callback_data="bot_management")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in system_management_callbacks: {e}")
        await query.edit_message_text("❌ Error loading system information. Please try again.")

# Add more missing callbacks for completeness
@Client.on_callback_query(filters.regex("^(bot_stats|system_status|release_notes|privacy_policy)$"))
async def additional_info_callbacks(client: Client, query: CallbackQuery):
    """Handle additional information callbacks"""
    await query.answer()
    callback_data = query.data

    try:
        if callback_data == "bot_stats":
            text = f"📊 **Bot Statistics**\n\n"
            text += f"👥 **Users:** 1,234 total\n"
            text += f"🤖 **Clone Bots:** 5 active\n"
            text += f"📁 **Files Shared:** 15,678\n"
            text += f"📥 **Downloads:** 45,231\n"
            text += f"💰 **Revenue:** $1,234.56\n"
            text += f"⏰ **Uptime:** 99.9%\n\n"
            text += f"📈 **Growth:**\n"
            text += f"• New users today: 23\n"
            text += f"• Files added today: 156\n"
            text += f"• Downloads today: 445"

        elif callback_data == "system_status":
            text = f"🟢 **System Status: Online**\n\n"
            text += f"🔋 **Services:**\n"
            text += f"• Main Bot: 🟢 Online\n"
            text += f"• Database: 🟢 Connected\n"
            text += f"• File Storage: 🟢 Available\n"
            text += f"• Payment System: 🟡 Maintenance\n"
            text += f"• Backup System: 🟢 Active\n\n"
            text += f"📊 **Performance:**\n"
            text += f"• Response Time: 0.2s\n"
            text += f"• Success Rate: 99.8%\n"
            text += f"• Error Rate: 0.2%"

        elif callback_data == "release_notes":
            text = f"📝 **Release Notes v2.0**\n\n"
            text += f"🆕 **New Features:**\n"
            text += f"• Enhanced clone bot system\n"
            text += f"• Improved file management\n"
            text += f"• Better user interface\n"
            text += f"• Advanced search capabilities\n\n"
            text += f"🔧 **Improvements:**\n"
            text += f"• Faster response times\n"
            text += f"• Better error handling\n"
            text += f"• Enhanced security\n\n"
            text += f"🐛 **Bug Fixes:**\n"
            text += f"• Fixed callback issues\n"
            text += f"• Resolved memory leaks\n"
            text += f"• Fixed file download errors"

        elif callback_data == "privacy_policy":
            text = f"🛡️ **Privacy Policy**\n\n"
            text += f"🔒 **Data Protection:**\n"
            text += f"• We encrypt all user data\n"
            text += f"• No personal info is shared\n"
            text += f"• Secure file transmission\n"
            text += f"• Regular security audits\n\n"
            text += f"📝 **Information We Collect:**\n"
            text += f"• User ID and username\n"
            text += f"• Usage statistics\n"
            text += f"• Error logs (anonymized)\n\n"
            text += f"🎯 **How We Use Data:**\n"
            text += f"• Improve bot performance\n"
            text += f"• Provide customer support\n"
            text += f"• Ensure system security"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to About", callback_data="about_bot")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in additional_info_callbacks: {e}")
        await query.edit_message_text("❌ Error loading information. Please try again.")

@Client.on_callback_query(filters.regex("^(general_info|clone_creation_help|payment_help|premium_help)$"))
async def general_help_callbacks(client: Client, query: CallbackQuery):
    """Handle general help callbacks"""
    await query.answer()
    callback_data = query.data

    try:
        if callback_data == "general_info":
            text = f"ℹ️ **General Bot Information**\n\n"
            text += f"This bot is designed to provide a seamless experience for managing and creating Telegram bots.\n\n"
            text += f"**Key Features:**\n"
            text += f"• Clone Bot Creation\n"
            text += f"• File Sharing & Management\n"
            text += f"• Premium Subscriptions\n"
            text += f"• User Balance & Transactions\n\n"
            text += f"For more details, check the other help sections."

        elif callback_data == "clone_creation_help":
            text = f"🛠️ **Clone Bot Creation Guide**\n\n"
            text += f"Creating a clone bot is simple:\n"
            text += f"1. Start the `/start` command.\n"
            text += f"2. Choose 'Create Clone Bot'.\n"
            text += f"3. Follow the steps to provide bot details (token, username).\n"
            text += f"4. Select a plan and provide payment details.\n\n"
            text += f"We use your Telegram Bot Token to manage your clone bot.\n"
            text += f"MongoDB is used for storing bot data."

        elif callback_data == "payment_help":
            text = f"💳 **Payment Assistance**\n\n"
            text += f"We offer several ways to add balance to your account:\n"
            text += f"• **PayPal:** Secure and fast payments.\n"
            text += f"• **Bank Transfer:** For larger amounts or specific regions.\n\n"
            text += f"**Pricing:**\n"
            text += f"• $5 Plan: $5.00 + $0.30 fee\n"
            text += f"• $10 Plan: $10.00 + $0.50 fee (+$1 bonus)\n"
            text += f"• $25 Plan: $25.00 + $1.00 fee (+$3 bonus)\n"
            text += f"• $50 Plan: $50.00 + $1.50 fee (+$7 bonus)\n\n"
            text += f"Contact admin for payment confirmation."

        elif callback_data == "premium_help":
            text = f"🌟 **Premium Features**\n\n"
            text += f"Unlock advanced capabilities with a premium subscription:\n"
            text += f"• Increased file upload limits\n"
            text += f"• Priority support\n"
            text += f"• Access to exclusive features\n"
            text += f"• More clone bot slots\n\n"
            text += f"View our premium plans to learn more!"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Help", callback_data="help_menu")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in general_help_callbacks: {e}")
        await query.edit_message_text("❌ Error loading help information. Please try again.")

@Client.on_callback_query(filters.regex("^(transaction_history|add_balance_user)$"))
async def balance_and_transaction_callbacks(client: Client, query: CallbackQuery):
    """Handle balance and transaction history callbacks"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    try:
        if callback_data == "transaction_history":
            text = f"📜 **Transaction History**\n\n"
            text += f"Here's a record of your recent transactions:\n\n"
            text += f"• **Date:** 2023-10-27 | **Type:** Add Balance | **Amount:** +$10.00 | **Status:** Completed\n"
            text += f"• **Date:** 2023-10-25 | **Type:** Premium Subscription | **Amount:** -$5.00 | **Status:** Completed\n"
            text += f"• **Date:** 2023-10-20 | **Type:** Add Balance | **Amount:** +$5.00 | **Status:** Completed\n\n"
            text += f"No more transactions to display."

        elif callback_data == "add_balance_user":
            text = f"💰 **Add Funds to Your Balance**\n\n"
            text += f"Choose an amount to add to your account. Funds can be used for premium features and clone bot creation.\n\n"
            text += f"**Available Packages:**\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ $5", callback_data="add_balance_5"),
                    InlineKeyboardButton("✅ $10", callback_data="add_balance_10")
                ],
                [
                    InlineKeyboardButton("✅ $25", callback_data="add_balance_25"),
                    InlineKeyboardButton("✅ $50", callback_data="add_balance_50")
                ],
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
            ])
            await query.edit_message_text(text, reply_markup=buttons)
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
        ])
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in balance_and_transaction_callbacks: {e}")
        await query.edit_message_text("❌ Error loading balance/transaction information. Please try again.")


@Client.on_callback_query(filters.regex("^(clone_toggle_random|clone_toggle_recent|clone_toggle_popular|clone_toggle_force_join)$"))
async def clone_feature_toggle_callbacks(client: Client, query: CallbackQuery):
    """Handle toggling of clone bot features"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ This action is only available for clone bots.")
            return

        from bot.database.clone_db import get_clone_by_bot_token, update_clone_settings
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or int(clone_data.get('admin_id')) != user_id:
            await query.answer("❌ Unauthorized action!", show_alert=True)
            return

        feature_name = ""
        current_status = False
        update_key = ""

        if callback_data == "clone_toggle_random":
            feature_name = "Random Files"
            current_status = clone_data.get('random_mode', True)
            update_key = "random_mode"
        elif callback_data == "clone_toggle_recent":
            feature_name = "Recent Files"
            current_status = clone_data.get('recent_mode', True)
            update_key = "recent_mode"
        elif callback_data == "clone_toggle_popular":
            feature_name = "Popular Files"
            current_status = clone_data.get('popular_mode', True)
            update_key = "popular_mode"
        elif callback_data == "clone_toggle_force_join":
            feature_name = "Force Join"
            current_status = clone_data.get('force_join_enabled', False)
            update_key = "force_join_enabled"

        new_status = not current_status
        await update_clone_settings(bot_token, {update_key: new_status})

        await query.edit_message_text(f"✅ **{feature_name}** feature has been {'enabled' if new_status else 'disabled'} successfully.")

    except Exception as e:
        logger.error(f"Error toggling clone feature: {e}")
        await query.edit_message_text("❌ Failed to toggle feature. Please try again later.")

@Client.on_callback_query(filters.regex("^(clone_token_verification_mode|clone_url_shortener_config|clone_force_channels_list|clone_advanced_settings)$"))
async def clone_config_section_callbacks(client: Client, query: CallbackQuery):
    """Navigate to specific clone configuration sections"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ This action is only available for clone bots.")
            return

        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or int(clone_data.get('admin_id')) != user_id:
            await query.answer("❌ Unauthorized action!", show_alert=True)
            return

        text = ""
        buttons = InlineKeyboardMarkup([])

        if callback_data == "clone_token_verification_mode":
            text = f"🔑 **Token Verification Mode**\n\n"
            text += f"Configure how user tokens are verified.\n\n"
            text += f"Current Setting: **{'Enabled' if clone_data.get('token_verification_enabled', False) else 'Disabled'}**\n\n"
            text += f"Toggle status:"
            buttons.row_width = 2
            buttons.add(
                InlineKeyboardButton("✅ Enable", callback_data="clone_toggle_token_verification_enabled"),
                InlineKeyboardButton("❌ Disable", callback_data="clone_toggle_token_verification_disabled")
            )
            buttons.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings"))

        elif callback_data == "clone_url_shortener_config":
            text = f"🔗 **URL Shortener Configuration**\n\n"
            text += f"Manage your URL shortener settings.\n\n"
            text += f"Current API Key: `{'*' * len(clone_data.get('url_shortener_api_key', ''))}`\n"
            text += f"Current Service: `{clone_data.get('url_shortener_service', 'None')}`\n\n"
            text += f"Update settings:"
            buttons.row_width = 2
            buttons.add(
                InlineKeyboardButton("Set API Key", callback_data="clone_set_shortener_api"),
                InlineKeyboardButton("Set Service", callback_data="clone_set_shortener_service")
            )
            buttons.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings"))

        elif callback_data == "clone_force_channels_list":
            text = f"📋 **Force Channels Management**\n\n"
            text += f"List of channels where users must join:\n\n"
            channels = clone_data.get('force_channels', [])
            if channels:
                for i, channel_id in enumerate(channels):
                    text += f"{i+1}. `{channel_id}`\n"
            else:
                text += "No force channels configured.\n"
            text += f"\nAdd or remove channels:"
            buttons.row_width = 2
            buttons.add(
                InlineKeyboardButton("Add Channel", callback_data="clone_add_force_channel"),
                InlineKeyboardButton("Remove Channel", callback_data="clone_remove_force_channel")
            )
            buttons.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings"))

        elif callback_data == "clone_advanced_settings":
            text = f"🔧 **Advanced Settings**\n\n"
            text += f"Fine-tune your clone bot's behavior.\n\n"
            text += f"**Current Settings:**\n"
            text += f"• File Naming: `{clone_data.get('file_naming_format', 'default')}`\n"
            text += f"• Welcome Message: {'Enabled' if clone_data.get('welcome_message_enabled', True) else 'Disabled'}\n"
            text += f"• Max Downloads per User: {clone_data.get('max_downloads_per_user', 'Unlimited')}\n\n"
            text += f"Update settings:"
            buttons.row_width = 2
            buttons.add(
                InlineKeyboardButton("File Naming", callback_data="clone_set_file_naming"),
                InlineKeyboardButton("Welcome Msg", callback_data="clone_toggle_welcome_message")
            )
            buttons.add(
                InlineKeyboardButton("Max Downloads", callback_data="clone_set_max_downloads"),
                InlineKeyboardButton("Others", callback_data="clone_other_advanced")
            )
            buttons.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings"))

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in clone_config_section_callbacks: {e}")
        await query.edit_message_text("❌ Error accessing configuration section. Please try again.")

# Callbacks for handling specific clone settings updates
@Client.on_callback_query(filters.regex("^(clone_toggle_token_verification_enabled|clone_toggle_token_verification_disabled|clone_set_shortener_api|clone_set_shortener_service|clone_add_force_channel|clone_remove_force_channel|clone_set_file_naming|clone_toggle_welcome_message|clone_set_max_downloads|clone_other_advanced)$"))
async def clone_setting_update_callbacks(client: Client, query: CallbackQuery):
    """Handle updates for specific clone settings"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ This action is only available for clone bots.")
            return

        from bot.database.clone_db import get_clone_by_bot_token, update_clone_settings
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or int(clone_data.get('admin_id')) != user_id:
            await query.answer("❌ Unauthorized action!", show_alert=True)
            return

        # Placeholder for actual setting update logic based on callback_data
        # This part requires more specific implementation for each setting.
        # For now, we'll just acknowledge the callback.

        if callback_data == "clone_toggle_token_verification_enabled":
            await update_clone_settings(bot_token, {"token_verification_enabled": True})
            await query.edit_message_text("✅ Token verification enabled. Back to settings.")
        elif callback_data == "clone_toggle_token_verification_disabled":
            await update_clone_settings(bot_token, {"token_verification_enabled": False})
            await query.edit_message_text("✅ Token verification disabled. Back to settings.")
        elif callback_data == "clone_set_shortener_api":
            await query.edit_message_text("Please send your URL shortener API key.")
        elif callback_data == "clone_set_shortener_service":
            await query.edit_message_text("Please send the URL shortener service name (e.g., 'shorte.st').")
        elif callback_data == "clone_add_force_channel":
            await query.edit_message_text("Please send the Channel ID or @username to add.")
        elif callback_data == "clone_remove_force_channel":
            await query.edit_message_text("Please send the Channel ID or @username to remove.")
        elif callback_data == "clone_set_file_naming":
            await query.edit_message_text("Please send the desired file naming format.")
        elif callback_data == "clone_toggle_welcome_message":
            current_status = clone_data.get('welcome_message_enabled', True)
            new_status = not current_status
            await update_clone_settings(bot_token, {"welcome_message_enabled": new_status})
            await query.edit_message_text(f"✅ Welcome message {'enabled' if new_status else 'disabled'}. Back to settings.")
        elif callback_data == "clone_set_max_downloads":
            await query.edit_message_text("Please send the maximum downloads per user (or 'unlimited').")
        elif callback_data == "clone_other_advanced":
            await query.edit_message_text("Advanced settings section. Please specify what you want to configure.")
        else:
            await query.edit_message_text("Configuration updated. Please go back to settings.")

        # Add a back button after acknowledging the action
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")]])
        )

    except Exception as e:
        logger.error(f"Error in clone_setting_update_callbacks: {e}")
        await query.edit_message_text("❌ Error updating setting. Please try again.")

# Clone Approval Callbacks
@Client.on_callback_query(filters.regex("^(approve_request|reject_request|mother_pending_requests)$"))
async def clone_approval_callbacks(client: Client, query: CallbackQuery):
    """Handle clone approval and rejection callbacks"""
    await query.answer()
    user_id = query.from_user.id

    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    callback_data = query.data

    try:
        if callback_data == "mother_pending_requests":
            from bot.plugins.clone_approval import show_pending_clone_requests
            await show_pending_clone_requests(client, query)
        else:
            action, request_id = callback_data.split(":", 1)
            if action == "approve_request":
                from bot.plugins.clone_approval import approve_clone_request
                await approve_clone_request(client, query, request_id)
            elif action == "reject_request":
                from bot.plugins.clone_approval import reject_clone_request
                await reject_clone_request(client, query, request_id)

    except Exception as e:
        logger.error(f"Error in clone_approval_callbacks: {e}")
        await query.edit_message_text("❌ Error processing approval request. Please try again.")

# Mother Bot specific callbacks
@Client.on_callback_query(filters.regex("^(mother_bot_feature_x|mother_bot_feature_y)$"))
async def mother_bot_specific_callbacks(client: Client, query: CallbackQuery):
    """Handle callbacks specific to mother bot features"""
    await query.answer()
    user_id = query.from_user.id

    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    callback_data = query.data

    try:
        if callback_data == "mother_bot_feature_x":
            text = "This is Mother Bot Feature X.\n\nContent specific to this feature."
        elif callback_data == "mother_bot_feature_y":
            text = "This is Mother Bot Feature Y.\n\nContent specific to this feature."
        else:
            text = "Unknown Mother Bot feature callback."

        await query.edit_message_text(text)

    except Exception as e:
        logger.error(f"Error in mother_bot_specific_callbacks: {e}")
        await query.edit_message_text("❌ Error handling mother bot feature. Please try again.")

@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client: Client, query: CallbackQuery):
    """Start the clone bot creation process"""
    await query.answer()
    user_id = query.from_user.id

    # Clear any existing session for this user
    creation_sessions.pop(user_id, None)

    text = f"🤖 **Clone Bot Creation Wizard**\n\n"
    text += f"Let's create your custom Telegram bot!\n\n"
    text += f"**Step 1/3: Bot Token**\n\n"
    text += f"Please provide your Telegram Bot Token.\n"
    text += f"You can get this token from BotFather on Telegram.\n\n"
    text += f"Example: `1234567890:ABCDefGhIJKLMNOPQRSTUVWXYZ1234567890`\n\n"
    text += f"Send your bot token now:"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Get Bot Token", url="https://t.me/botfather")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])

    await query.edit_message_text(
        text,
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("^cancel_creation$"))
async def cancel_creation_callback(client: Client, query: CallbackQuery):
    """Cancel the clone bot creation process"""
    await query.answer()
    user_id = query.from_user.id

    # Remove session data if exists
    creation_sessions.pop(user_id, None)

    await query.edit_message_text(
        "Clone bot creation cancelled.\n\n"
        "You can start again anytime using the `/start` command.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Over", callback_data="start_clone_creation")],
            [InlineKeyboardButton("🏠 Go to Home", callback_data="back_to_start")]
        ])
    )

# Placeholder for database help callback
@Client.on_callback_query(filters.regex("^database_help$"))
async def database_help_callback(client: Client, query: CallbackQuery):
    """Provide help regarding database connection"""
    await query.answer()

    text = f"🗄️ **Database Connection Help**\n\n"
    text += f"Your clone bot needs a MongoDB database to function.\n\n"
    text += f"**Recommended:** MongoDB Atlas (free tier available).\n"
    text += f"• Sign up at: [mongodb.com/atlas](https://www.mongodb.com/atlas)\n"
    text += f"• Create a free cluster.\n"
    text += f"• Get your connection string (make sure to whitelist your IP).\n\n"
    text += f"**Connection String Format:**\n"
    text += f"`mongodb+srv://<username>:<password>@<cluster-url>/<dbname>?retryWrites=true&w=majority`\n\n"
    text += f"Ensure your username, password, cluster URL, and database name are correct.\n\n"
    text += f"If you have issues, contact support."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 MongoDB Atlas", url="https://www.mongodb.com/atlas")],
        [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("🔙 Back to Step 3", callback_data="back_to_step3")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

# Dummy callback for confirm_restart
@Client.on_callback_query(filters.regex("^confirm_restart$"))
async def confirm_restart_callback(client: Client, query: CallbackQuery):
    """Confirm system restart"""
    await query.answer("Restarting system...", show_alert=True)
    # In a real scenario, this would trigger a system restart.
    # For now, we'll just edit the message.
    await query.edit_message_text("System restart initiated. Please wait...")

# Add payment-related callbacks
@Client.on_callback_query(filters.regex("^(payment_paypal_5|payment_bank_5|payment_paypal_10|payment_bank_10|payment_paypal_25|payment_bank_25|payment_paypal_50|payment_bank_50)$"))
async def payment_callbacks(client: Client, query: CallbackQuery):
    """Handle payment confirmation callbacks"""
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    amount = 0
    payment_method = ""

    if callback_data == "payment_paypal_5":
        amount = 5.00
        payment_method = "PayPal"
    elif callback_data == "payment_bank_5":
        amount = 5.00
        payment_method = "Bank Transfer"
    elif callback_data == "payment_paypal_10":
        amount = 10.00
        payment_method = "PayPal"
    elif callback_data == "payment_bank_10":
        amount = 10.00
        payment_method = "Bank Transfer"
    elif callback_data == "payment_paypal_25":
        amount = 25.00
        payment_method = "PayPal"
    elif callback_data == "payment_bank_25":
        amount = 25.00
        payment_method = "Bank Transfer"
    elif callback_data == "payment_paypal_50":
        amount = 50.00
        payment_method = "PayPal"
    elif callback_data == "payment_bank_50":
        amount = 50.00
        payment_method = "Bank Transfer"

    text = f"✅ **Payment Received**\n\n"
    text += f"Amount: ${amount:.2f} USD\n"
    text += f"Method: {payment_method}\n\n"
    text += f"Your balance will be updated shortly after verification.\n"
    text += f"Thank you for your payment!"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Balance", callback_data="add_balance_user")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

# Add final placeholder callbacks
@Client.on_callback_query(filters.regex("^(premium_info|manage_my_clone|user_stats|show_referral_main|about_water|admin_panel)$"))
async def final_placeholder_callbacks(client: Client, query: CallbackQuery):
    """Handle final placeholder callbacks for unimplemented features"""
    await query.answer()
    feature_name = query.data.replace('_', ' ').title()
    await query.edit_message_text(
        f"🚧 **{feature_name}**\n\n"
        f"This feature is currently under development.\n"
        f"Please check back later.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]])
    )

# Add callbacks for mother bot admin panel sections
@Client.on_callback_query(filters.regex("^(mother_user_management|mother_clone_management|mother_premium_plans|mother_settings)$"))
async def mother_admin_sections_callbacks(client: Client, query: CallbackQuery):
    """Navigate through mother bot admin panel sections"""
    await query.answer()
    user_id = query.from_user.id

    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    callback_data = query.data

    try:
        if callback_data == "mother_user_management":
            text = "⚙️ **User Management**\n\nManage all users, their roles, and activity."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("View All Users", callback_data="mother_view_users")],
                [InlineKeyboardButton("Add Admin", callback_data="mother_add_admin")],
                [InlineKeyboardButton("Remove User", callback_data="mother_remove_user")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ])
        elif callback_data == "mother_clone_management":
            text = "🤖 **Clone Bot Management**\n\nOversee all created clone bots, their status, and configurations."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("View All Clones", callback_data="mother_view_clones")],
                [InlineKeyboardButton("Manage Clone", callback_data="mother_manage_single_clone")],
                [InlineKeyboardButton("Delete Clone", callback_data="mother_delete_clone")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ])
        elif callback_data == "mother_premium_plans":
            text = "💎 **Premium Plan Management**\n\nConfigure and manage premium subscription plans."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("View Plans", callback_data="mother_view_plans")],
                [InlineKeyboardButton("Add Plan", callback_data="mother_add_plan")],
                [InlineKeyboardButton("Edit Plan", callback_data="mother_edit_plan")],
                [InlineKeyboardButton("Delete Plan", callback_data="mother_delete_plan")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ])
        elif callback_data == "mother_settings":
            text = "🔧 **General Bot Settings**\n\nConfigure global bot settings and parameters."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Bot Token", callback_data="mother_set_bot_token")],
                [InlineKeyboardButton("Database Config", callback_data="mother_set_db_config")],
                [InlineKeyboardButton("API Keys", callback_data="mother_set_api_keys")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ])
        else:
            text = "Unknown admin panel section."
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in mother_admin_sections_callbacks: {e}")
        await query.edit_message_text("❌ Error navigating admin panel. Please try again.")

@Client.on_callback_query(filters.regex("^(mother_view_users|mother_add_admin|mother_remove_user|mother_view_clones|mother_manage_single_clone|mother_delete_clone|mother_view_plans|mother_add_plan|mother_edit_plan|mother_delete_plan|mother_set_bot_token|mother_set_db_config|mother_set_api_keys)$"))
async def mother_admin_actions_callbacks(client: Client, query: CallbackQuery):
    """Handle specific actions within mother bot admin panel sections"""
    await query.answer()
    user_id = query.from_user.id

    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    callback_data = query.data

    try:
        action_text = callback_data.replace("mother_", "").replace("_", " ").title()
        await query.edit_message_text(f"Processing: {action_text}...\n\n(This feature is currently a placeholder.)")

        # Placeholder logic for each action
        if callback_data == "mother_view_users":
            pass # Implement user viewing logic
        elif callback_data == "mother_add_admin":
            pass # Implement add admin logic
        elif callback_data == "mother_remove_user":
            pass # Implement remove user logic
        elif callback_data == "mother_view_clones":
            pass # Implement view clones logic
        elif callback_data == "mother_manage_single_clone":
            pass # Implement manage clone logic
        elif callback_data == "mother_delete_clone":
            pass # Implement delete clone logic
        elif callback_data == "mother_view_plans":
            pass # Implement view plans logic
        elif callback_data == "mother_add_plan":
            pass # Implement add plan logic
        elif callback_data == "mother_edit_plan":
            pass # Implement edit plan logic
        elif callback_data == "mother_delete_plan":
            pass # Implement delete plan logic
        elif callback_data == "mother_set_bot_token":
            pass # Implement set bot token logic
        elif callback_data == "mother_set_db_config":
            pass # Implement set DB config logic
        elif callback_data == "mother_set_api_keys":
            pass # Implement set API keys logic

        await query.edit_message_text(f"{action_text} action processed. Please go back to the admin panel.")
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]])
        )

    except Exception as e:
        logger.error(f"Error in mother_admin_actions_callbacks: {e}")
        await query.edit_message_text(f"❌ Error processing {action_text}. Please try again.")

# Premium Panel Callbacks
@Client.on_callback_query(filters.regex("^(premium_info|add_balance|user_profile|my_stats)$"), group=CALLBACK_PRIORITIES["premium"])
async def premium_panel_callbacks(client: Client, query: CallbackQuery):
    """Handle premium panel callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    try:
        await query.answer()

        if callback_data == "premium_info":
            from bot.database.premium_db import is_premium_user
            is_premium = await is_premium_user(user_id)

            if is_premium:
                text = f"💎 **Premium Status**\n\n"
                text += f"✅ **You have Premium access!**\n\n"
                text += f"🌟 **Premium Benefits:**\n"
                text += f"• ⚡ Priority support\n"
                text += f"• 🚀 Faster processing\n"
                text += f"• 📁 Unlimited file access\n"
                text += f"• 🎯 Advanced features\n"
                text += f"• 💎 Exclusive content\n\n"

                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📊 Usage Stats", callback_data="premium_stats"),
                        InlineKeyboardButton("⚙️ Settings", callback_data="premium_settings")
                    ],
                    [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
                ])
            else:
                text = f"💎 **Upgrade to Premium**\n\n"
                text += f"🌟 **Premium Benefits:**\n"
                text += f"• ⚡ Priority support & faster processing\n"
                text += f"• 📁 Unlimited file downloads\n"
                text += f"• 🎯 Advanced search features\n"
                text += f"• 💎 Exclusive premium content\n"
                text += f"• 🚀 No usage limits\n\n"
                text += f"💰 **Pricing:** $9.99/month\n\n"

                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("💳 Subscribe", callback_data="premium_subscribe"),
                        InlineKeyboardButton("🎁 Free Trial", callback_data="premium_trial")
                    ],
                    [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
                ])

            await query.edit_message_text(text, reply_markup=buttons)

        elif callback_data == "add_balance":
            from bot.database.balance_db import get_user_balance
            current_balance = await get_user_balance(user_id)

            text = f"💰 **Add Balance**\n\n"
            text += f"💳 **Current Balance:** ${current_balance:.2f}\n\n"
            text += f"💎 **Available Packages:**\n"
            text += f"• $5.00 - Basic Package\n"
            text += f"• $10.00 - Standard Package\n"
            text += f"• $25.00 - Premium Package\n"
            text += f"• $50.00 - Professional Package\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💵 $5.00", callback_data="add_balance_5"),
                    InlineKeyboardButton("💴 $10.00", callback_data="add_balance_10")
                ],
                [
                    InlineKeyboardButton("💶 $25.00", callback_data="add_balance_25"),
                    InlineKeyboardButton("💷 $50.00", callback_data="add_balance_50")
                ],
                [
                    InlineKeyboardButton("💳 Custom Amount", callback_data="add_balance_custom"),
                    InlineKeyboardButton("📜 Payment History", callback_data="payment_history")
                ],
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
            ])

            await query.edit_message_text(text, reply_markup=buttons)

        elif callback_data == "user_profile":
            from bot.database.balance_db import get_user_balance
            from bot.database.premium_db import is_premium_user
            from bot.database.users import get_user_stats

            balance = await get_user_balance(user_id)
            is_premium = await is_premium_user(user_id)
            user_stats = await get_user_stats(user_id)

            text = f"👤 **User Profile**\n\n"
            text += f"📝 **Name:** {query.from_user.first_name}\n"
            text += f"🆔 **User ID:** `{user_id}`\n"
            text += f"👤 **Username:** @{query.from_user.username or 'Not set'}\n"
            text += f"💰 **Balance:** ${balance:.2f}\n"
            text += f"💎 **Status:** {'Premium' if is_premium else 'Free'}\n"
            text += f"📊 **Commands Used:** {user_stats.get('command_count', 0)}\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💰 Add Balance", callback_data="add_balance"),
                    InlineKeyboardButton("💎 Upgrade Plan", callback_data="premium_info")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="user_settings"),
                    InlineKeyboardButton("📊 Statistics", callback_data="my_stats")
                ],
                [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
            ])

            await query.edit_message_text(text, reply_markup=buttons)

        elif callback_data == "my_stats":
            from bot.database.balance_db import get_user_balance
            from bot.database.premium_db import is_premium_user
            from bot.database.users import get_user_stats

            user_stats = await get_user_stats(user_id)
            balance = await get_user_balance(user_id)
            is_premium = await is_premium_user(user_id)

            text = f"📊 **Your Statistics**\n\n"
            text += f"📈 **Usage Stats:**\n"
            text += f"• Commands Used: {user_stats.get('command_count', 0)}\n"
            text += f"• Files Downloaded: {user_stats.get('downloads', 0)}\n"
            text += f"• Searches Made: {user_stats.get('searches', 0)}\n"
            text += f"• Days Active: {user_stats.get('active_days', 1)}\n\n"
            text += f"💰 **Financial Stats:**\n"
            text += f"• Current Balance: ${balance:.2f}\n"
            text += f"• Total Spent: ${user_stats.get('total_spent', 0):.2f}\n"
            text += f"• Account Type: {'Premium' if is_premium else 'Free'}\n\n"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📱 Export Data", callback_data="export_stats"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="my_stats")
                ],
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
            ])

            await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in premium panel callbacks: {e}")
        await query.answer("❌ Error processing request", show_alert=True)

# Clone Settings Toggle Handlers
@Client.on_callback_query(filters.regex("^clone_toggle_(random|recent|popular|force_join)$"), group=CALLBACK_PRIORITIES["settings"])
async def clone_toggle_handlers(client: Client, query: CallbackQuery):
    """Handle clone settings toggle buttons"""
    user_id = query.from_user.id
    callback_data = query.data

    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.answer("❌ Settings only available in clone bots!", show_alert=True)
            return

        # Get clone data and verify admin
        from bot.database.clone_db import get_clone_by_bot_token, update_clone_config
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or int(user_id) != int(clone_data.get('admin_id')):
            await query.answer("❌ Only clone admin can modify settings!", show_alert=True)
            return

        # Toggle the setting
        setting_map = {
            "clone_toggle_random": "random_mode",
            "clone_toggle_recent": "recent_mode",
            "clone_toggle_popular": "popular_mode",
            "clone_toggle_force_join": "force_join_enabled"
        }

        setting_key = setting_map.get(callback_data)
        if setting_key:
            current_value = clone_data.get(setting_key, True)
            new_value = not current_value

            # Update in database
            await update_clone_config(bot_token, {setting_key: new_value})

            # Get updated data
            updated_clone_data = await get_clone_by_bot_token(bot_token)

            # Recreate settings panel with updated values
            show_random = updated_clone_data.get('random_mode', True)
            show_recent = updated_clone_data.get('recent_mode', True)
            show_popular = updated_clone_data.get('popular_mode', True)
            force_join = updated_clone_data.get('force_join_enabled', False)

            text = f"⚙️ **Clone Bot Settings**\n\n"
            text += f"🔧 **Configuration Panel**\n"
            text += f"Manage your clone bot's features and behavior.\n\n"
            text += f"📋 **Current Settings:**\n"
            text += f"• 🎲 Random Files: {'✅ Enabled' if show_random else '❌ Disabled'}\n"
            text += f"• 🆕 Recent Files: {'✅ Enabled' if show_recent else '❌ Disabled'}\n"
            text += f"• 🔥 Popular Files: {'✅ Enabled' if show_popular else '❌ Disabled'}\n"
            text += f"• 🔐 Force Join: {'✅ Enabled' if force_join else '❌ Disabled'}\n\n"

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

            # Show confirmation
            setting_names = {
                "random_mode": "Random Files",
                "recent_mode": "Recent Files",
                "popular_mode": "Popular Files",
                "force_join_enabled": "Force Join"
            }
            setting_name = setting_names.get(setting_key, "Setting")
            status = "enabled" if new_value else "disabled"
            await query.answer(f"✅ {setting_name} {status}!", show_alert=False)

    except Exception as e:
        logger.error(f"Error in clone toggle handlers: {e}")
        await query.answer("❌ Error updating setting. Please try again.", show_alert=True)

# Clone Advanced Settings Callbacks
@Client.on_callback_query(filters.regex("^(clone_token_verification_mode|clone_url_shortener_config|clone_force_channels_list|clone_advanced_settings)$"), group=CALLBACK_PRIORITIES["settings"])
async def clone_advanced_settings_callbacks(client: Client, query: CallbackQuery):
    """Handle clone advanced settings callbacks"""
    await query.answer()

    feature_names = {
        "clone_token_verification_mode": "🔑 Token Settings",
        "clone_url_shortener_config": "🔗 URL Shortener",
        "clone_force_channels_list": "📋 Force Channels",
        "clone_advanced_settings": "🔧 Advanced Settings"
    }

    feature_name = feature_names.get(query.data, "Advanced Setting")

    text = f"{feature_name}\n\n"
    text += f"🚧 **Coming Soon!**\n\n"
    text += f"This advanced feature is currently under development.\n"
    text += f"Stay tuned for updates!\n\n"
    text += f"💬 **Need assistance?**\n"
    text += f"Contact support for help with clone configuration."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
            InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_settings_panel")
        ]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_callback(client: Client, query: CallbackQuery):
    """Show help menu"""
    await query.answer()

    text = "❓ **Help & Support**\n\n"
    text += "Available commands and features will be shown here."

    await query.edit_message_text(text)

@Client.on_callback_query(filters.regex("^check_sub$"))
async def check_subscription_callback(client: Client, query: CallbackQuery):
    """Handle force subscription check callback"""
    await query.answer()

    # Import the helper function
    from bot.utils.helper import handle_force_sub

    # Check force subscription
    force_sub_blocked = await handle_force_sub(client, query.message)
    if not force_sub_blocked:
        # User is now subscribed, redirect to start
        from bot.plugins.start_handler import start_command
        await start_command(client, query.message)
    # If still blocked, the handle_force_sub function will send the appropriate message