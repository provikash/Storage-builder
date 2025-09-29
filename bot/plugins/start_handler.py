import asyncio
from datetime import datetime
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.logging import LOGGER
from bot.plugins.handler_registry import handler_registry

# Import with error handling
try:
    from bot.utils.session_manager import get_session, clear_session, session_expired
except ImportError:
    async def session_expired(user_id): return False
    async def clear_session(user_id): pass
    async def get_session(user_id): return None

try:
    from bot.database.users import add_user, present_user
except ImportError:
    async def add_user(user_id): pass
    async def present_user(user_id): return True

try:
    from bot.database.premium_db import is_premium_user
except ImportError:
    async def is_premium_user(user_id): return False

try:
    from bot.database.balance_db import get_user_balance
except ImportError:
    async def get_user_balance(user_id): return 0.0

try:
    from bot.utils.error_handler import safe_edit_message
except ImportError:
    async def safe_edit_message(query, text, **kwargs):
        return await query.edit_message_text(text, **kwargs)

try:
    import bot.utils.clone_config_loader as clone_config_loader
except ImportError:
    clone_config_loader = None

try:
    from bot.database.clone_db import get_clone_by_bot_token
except ImportError:
    async def get_clone_by_bot_token(token): return None

try:
    from bot.database import get_command_stats
except ImportError:
    async def get_command_stats(user_id): return {'command_count': 0}

try:
    from bot.utils import helper as utils
except ImportError:
    # Create a minimal utils mock if import fails
    class utils:
        @staticmethod
        async def handle_force_sub(client, message):
            return False  # Allow all users if force sub is not available

logger = LOGGER(__name__)

# User settings storage (in-memory dictionary)
user_settings = {}

async def get_start_keyboard_for_clone_user(clone_data, bot_token=None):
    """
    Create start menu keyboard for clone bot users - ALWAYS show file browsing buttons
    Returns list of button rows
    """
    buttons = []

    # ALWAYS show file browsing buttons to all users - token verification handles access control
    file_buttons_row1 = []
    file_buttons_row1.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
    file_buttons_row1.append(InlineKeyboardButton("🆕 Recent Upload", callback_data="recent_files"))

    # Add first row
    buttons.append(file_buttons_row1)

    # Add popular files button in its own row
    buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

    logger.info(f"Clone user buttons: ALWAYS showing all file browsing buttons to user")

    return buttons

def get_start_keyboard(settings):
    """
    Create start menu keyboard based on admin settings
    Args:
        settings: dict with feature flags (random_files, recent_files, popular_files)
    Returns:
        InlineKeyboardMarkup with enabled features
    """
    buttons = []

    # Get feature states from settings
    show_random = settings.get('random_files', False) or settings.get('random_mode', False)
    show_recent = settings.get('recent_files', False) or settings.get('recent_mode', False)
    show_popular = settings.get('popular_files', False) or settings.get('popular_mode', False)

    # Create file access buttons only if enabled
    file_buttons_row1 = []

    # Add buttons only if their corresponding features are enabled
    if show_random:
        file_buttons_row1.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
    if show_recent:
        file_buttons_row1.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

    # Add first row if any buttons exist
    if file_buttons_row1:
        buttons.append(file_buttons_row1)

    # Add popular files button in its own row if enabled
    if show_popular:
        buttons.append([InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")])

    # Always show help and about
    buttons.append([InlineKeyboardButton("❓ Help", callback_data="help")])
    buttons.append([InlineKeyboardButton("ℹ️ About", callback_data="about")])

    return InlineKeyboardMarkup(buttons)

def get_user_settings(user_id):
    """Get user settings with defaults"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            'random_files': True,
            'popular_files': True,
            'recent_files': True,
            'force_join': True,
            'shortener_url': 'https://teraboxlinks.com/',
            'shortener_api_key': '',
            'token_verification_mode': 'command_limit' # Added default for new setting
        }
    return user_settings[user_id]

def update_user_setting(user_id, key, value):
    """Update a specific user setting"""
    if user_id not in user_settings:
        get_user_settings(user_id)  # Initialize defaults
    user_settings[user_id][key] = value

async def is_clone_bot_instance_async(client):
    """Detect if this is a clone bot instance"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = hasattr(client, 'is_clone') and client.is_clone

        if not is_clone:
            is_clone = (
                bot_token != Config.BOT_TOKEN or
                hasattr(client, 'clone_config') and client.clone_config or
                hasattr(client, 'clone_data')
            )

        return is_clone, bot_token
    except:
        return False, Config.BOT_TOKEN

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

@Client.on_message(filters.command(["start"]) & filters.private, group=1)
async def start_command(client: Client, message: Message):
    user = message.from_user
    user_id = user.id

    try:
        print(f"🚀 DEBUG COMMAND: /start command from user {user_id}")
        print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{user.username}, First: {user.first_name}")
        logger.info(f"Start command received from user {user_id}")

        # Prevent duplicate processing using registry
        if await handler_registry.is_processing(user_id, "start"):
            logger.info(f"Start command already processing for user {user_id}")
            return

        await handler_registry.start_processing(user_id, "start")

        try:
            # Handle force subscription first (with admin exemption)
            force_sub_blocked = await utils.handle_force_sub(client, message)
            if force_sub_blocked:
                print(f"🔒 DEBUG: User {user_id} blocked by force subscription")
                logger.info(f"User {user_id} blocked by force subscription")
                return

            print(f"✅ DEBUG: User {user_id} passed force subscription check")
            logger.info(f"User {user_id} passed force subscription check")
        finally:
            # Remove from processing using registry
            await handler_registry.stop_processing(user_id, "start")

    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        await message.reply_text("❌ An error occurred. Please try again later.")
        # Ensure cleanup on error using registry
        await handler_registry.stop_processing(user_id, "start")
        return

    # Check if session has expired for the user
    if await session_expired(user.id):
        print(f"⏰ DEBUG SESSION: Session expired for user {user.id}, clearing session")
        await clear_session(user.id)
    else:
        print(f"✅ DEBUG SESSION: Session valid for user {user.id}")

    # Add user to database
    await add_user(user.id)

    # Check if user is premium
    user_premium = await is_premium_user(user.id)

    # Get user balance
    balance = await get_user_balance(user.id)

    # Enhanced bot type detection
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN
    config = None

    try:
        clone_data = await get_clone_by_bot_token(bot_token)

        if clone_data:
            is_clone_bot = True
            config = {
                'bot_info': {
                    'is_clone': True,
                    'admin_id': clone_data.get('admin_id'),
                    'bot_id': clone_data.get('_id')
                }
            }
            logger.info(f"📋 Clone bot detected - Admin: {clone_data.get('admin_id')}, Token: {bot_token[:10]}...")

            # Ensure clone is marked as active if it's responding
            if clone_data.get('status') != 'active':
                from bot.database.clone_db import activate_clone
                await activate_clone(clone_data.get('_id'))
                logger.info(f"🔄 Marked clone {clone_data.get('_id')} as active")
        else:
            config = await clone_config_loader.get_bot_config(bot_token)
            if config and config.get('bot_info', {}).get('is_clone', False):
                is_clone_bot = True

        logger.info(f"📋 Config loaded for bot_token: {bot_token[:10]}... (is_clone: {is_clone_bot})")

    except Exception as e:
        logger.error(f"❌ Error loading config: {e}")
        config = None

    is_admin_user = await is_clone_admin(client, user_id) # Check if the current user is an admin for this clone bot

    # Create main menu buttons based on bot type
    if is_clone_bot:
        # Clone bot start message - simplified version
        start_text = f"🤖 **Welcome {message.from_user.first_name}!**\n\n"
        start_text += f"📁 **Your Personal File Bot** - Browse, search, and download files instantly.\n\n"
        start_text += f"🌟 **Features Available:**\n"
        start_text += f"• 🎲 Random file discovery\n"
        start_text += f"• 🆕 Latest uploaded content\n"
        start_text += f"• 🔥 Most popular downloads\n"
        start_text += f"• 🔍 Advanced search functionality\n\n"
        start_text += f"💎 Status: {'Premium' if user_premium else 'Free'}\n\n"
        start_text += f"🎯 **Choose an option below:**"

        # Clone bot menu - check admin vs user
        if is_admin_user:
            # Clone admin gets settings access AND file access
            logger.info(f"🎛️ ADMIN ACCESS: Showing settings button to clone admin {user_id}")
            print(f"🎛️ ADMIN ACCESS: Showing settings button to clone admin {user_id}")

            buttons = []

            # Settings button for admin - ensure exact match
            settings_button = InlineKeyboardButton("⚙️ Clone Settings", callback_data="clone_settings_panel")
            buttons.append([settings_button])
            logger.info(f"🎛️ BUTTON CREATED: Added clone settings button with callback_data='clone_settings_panel' for admin {user_id}")

            # Debug: Log the exact button being created
            logger.debug(f"Button details: text='{settings_button.text}', callback_data='{settings_button.callback_data}'")

            # File access buttons (ALWAYS show for admin)
            buttons.append([
                InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files")
            ])
            buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

            # Admin info buttons
            buttons.append([
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
                InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
            ])
            buttons.append([
                InlineKeyboardButton("💎 Plans", callback_data="premium_info"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ])
            buttons.append([InlineKeyboardButton("ℹ️ About", callback_data="about_bot")])
        else:
            # Normal clone bot users - check database settings for feature visibility
            buttons = []

            # Get current settings from database to determine which buttons to show
            try:
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    # Default to True if settings not explicitly set (backwards compatibility)
                    show_random = clone_data.get('random_mode', True)
                    show_recent = clone_data.get('recent_mode', True)
                    show_popular = clone_data.get('popular_mode', True)

                    logger.info(f"Clone {clone_data.get('bot_id')} settings for regular user in start: random={show_random}, recent={show_recent}, popular={show_popular}")

                    # Show file browsing buttons (default to enabled if not explicitly disabled)
                    file_buttons_row = []
                    if show_random:
                        file_buttons_row.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
                    if show_recent:
                        file_buttons_row.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

                    # Add file buttons row if any buttons exist
                    if file_buttons_row:
                        buttons.append(file_buttons_row)

                    # Add popular files button in its own row if enabled
                    if show_popular:
                        buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

                else:
                    logger.warning(f"No clone data found for bot_token in start: {bot_token}")
                    # Default buttons if no clone data found
                    buttons.append([
                        InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                        InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files")
                    ])
                    buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])
            except Exception as e:
                logger.error(f"Error getting clone settings in start: {e}")
                # Default buttons on error
                buttons.append([
                    InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                    InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files")
                ])
                buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

            # User action buttons as specified in requirements (always visible)
            buttons.append([
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ])
            buttons.append([
                InlineKeyboardButton("💎 Plans", callback_data="premium_info"),
                InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
            ])
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send start message
        try:
            await message.reply_text(
                text=start_text,
                reply_markup=reply_markup,
                quote=True
            )
            logger.info(f"✅ Start message sent successfully to user {user_id}")
        except Exception as send_error:
            logger.error(f"❌ Error sending start message to user {user_id}: {send_error}")
            # Fallback simple message
            await message.reply_text(
                "🤖 **Bot is Online!**\n\nWelcome! The bot is working but there was an issue loading the full interface.",
                quote=True
            )
    else:
        # Mother bot start message - simplified version
        start_text = f"🚀 **Welcome back to Advanced Bot Creator, {message.from_user.first_name}!**\n\n"
        start_text += f"🤖 **Create & Manage Personal Clone Bots**\n"
        start_text += f"Build your own file-sharing bot network with advanced features.\n\n"
        start_text += f"🌟 **What You Can Do:**\n"
        start_text += f"• 🤖 Create unlimited clone bots\n"
        start_text += f"• 📁 Advanced file management system\n"
        start_text += f"• 👥 User management & analytics\n"
        start_text += f"• 💎 Premium features & monetization\n"
        start_text += f"• 🔧 Complete customization control\n\n"
        start_text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        start_text += f"🎯 **Get Started:**"

        # Mother bot buttons - as specified in requirements
        buttons = []

        # Row 1: Main Features - Create Clone, My Clones, My Profile, Plans
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone")
        ])
        buttons.append([
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
            InlineKeyboardButton("💎 Plans", callback_data="premium_info")
        ])

        # Row 2: Help & About
        buttons.append([InlineKeyboardButton("❓ Help", callback_data="help_menu"), InlineKeyboardButton("ℹ️ About", callback_data="about_water")])

        # Admin panel for admins
        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        if not is_clone_bot and is_mother_admin:
            buttons.append([
                InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management")
            ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            start_text,
            reply_markup=reply_markup
        )

# File access handlers with enhanced feature checks
# Random files callback is now handled in callback_handlers.py

# Recent and popular files callbacks are now handled in callback_handlers.py

# Settings handlers are now handled in callback_handlers.py

# Toggle handlers - Unified toggle handling
@Client.on_callback_query(filters.regex("^toggle_"), group=3)
async def toggle_feature_callback(client: Client, query: CallbackQuery):
    """Handle feature toggle callbacks"""
    await query.answer()
    user_id = query.from_user.id

    # Check if user is clone admin
    if not await is_clone_admin(client, user_id):
        await query.edit_message_text("❌ Only clone admin can access settings.")
        return

    feature = query.data.replace("toggle_", "")
    settings = get_user_settings(user_id)

    # Toggle the feature
    feature_map = {
        'random': 'random_files',
        'popular': 'popular_files',
        'recent': 'recent_files',
        'force_join': 'force_join',
        'token_mode': 'token_verification_mode' # Map for the new setting
    }

    if feature in feature_map:
        setting_key = feature_map[feature]

        if setting_key == 'token_verification_mode':
            current_mode = settings[setting_key]
            new_mode = 'time_based' if current_mode == 'command_limit' else 'command_limit'
            update_user_setting(user_id, setting_key, new_mode)
            await query.answer(f"Token verification mode changed to {new_mode.replace('_', ' ').title()}", show_alert=True)
        else:
            current_value = settings[setting_key]
            new_value = not current_value
            update_user_setting(user_id, setting_key, new_value)
            feature_name = feature.replace('_', ' ').title()
            await query.answer(f"{feature_name} {'enabled' if new_value else 'disabled'}!", show_alert=True)

        # Refresh settings panel
        await clone_settings_callback(client, query)

# Change URL/API handlers - Prevent conflicts
@Client.on_callback_query(filters.regex("^change_shortener_url$"), group=4)
async def change_shortener_url_callback(client: Client, query: CallbackQuery):
    """Handle shortener URL change"""
    await query.answer()
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        await query.edit_message_text("❌ Only clone admin can access settings.")
        return

    text = f"🔗 **Change Shortener URL**\n\n"
    text += f"Send the new shortener URL:\n\n"
    text += f"**Examples:**\n"
    text += f"• `https://teraboxlinks.com/`\n"
    text += f"• `https://short.io/`\n"
    text += f"• `https://tinyurl.com/`\n\n"
    text += f"Send 'cancel' to abort."

    await query.edit_message_text(text)

    # Set waiting state (you can implement this with a session manager)
    user_settings[user_id]['waiting_for'] = 'shortener_url'

@Client.on_callback_query(filters.regex("^change_api_key$"), group=5)
async def change_api_key_callback(client: Client, query: CallbackQuery):
    """Handle API key change"""
    await query.answer()
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        await query.edit_message_text("❌ Only clone admin can access settings.")
        return

    text = f"🔑 **Change API Key**\n\n"
    text += f"Send your new API key:\n\n"
    text += f"**Note:** Your API key will be stored securely.\n\n"
    text += f"Send 'cancel' to abort."

    await query.edit_message_text(text)

    # Set waiting state
    user_settings[user_id]['waiting_for'] = 'api_key'

# Handle text input for URL/API changes - Specific to settings
@Client.on_message(filters.text & filters.private, group=6)
async def handle_settings_input(client: Client, message: Message):
    """Handle text input for settings changes"""
    user_id = message.from_user.id

    # Check if user is waiting for input
    if user_id not in user_settings or 'waiting_for' not in user_settings[user_id]:
        return

    if not await is_clone_admin(client, user_id):
        return

    waiting_for = user_settings[user_id]['waiting_for']
    text = message.text.strip()

    if text.lower() == 'cancel':
        del user_settings[user_id]['waiting_for']
        await message.reply_text("❌ **Cancelled**\n\nNo changes were made.")
        return

    if waiting_for == 'shortener_url':
        if text.startswith('http'):
            update_user_setting(user_id, 'shortener_url', text)
            del user_settings[user_id]['waiting_for']
            await message.reply_text(f"✅ **Shortener URL Updated**\n\nNew URL: `{text}`")
        else:
            await message.reply_text("❌ **Invalid URL**\n\nPlease send a valid URL starting with http:// or https://")

    elif waiting_for == 'api_key':
        update_user_setting(user_id, 'shortener_api_key', text)
        del user_settings[user_id]['waiting_for']
        await message.reply_text("✅ **API Key Updated**\n\nYour API key has been saved securely.")

@Client.on_callback_query(filters.regex("^back_to_start$"), group=7)
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Return to main start menu"""
    await query.answer()

    # Recreate the start message by calling start_command logic
    user = query.from_user
    user_id = query.from_user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)
    is_clone_bot, bot_token = await is_clone_bot_instance_async(client)

    if is_clone_bot:
        # Clone bot start message - standardized version
        text = f"🤖 **Welcome {user.first_name}!**\n\n"
        text += f"📁 **Your Personal File Bot** - Browse, search, and download files instantly.\n\n"
        text += f"🌟 **Features Available:**\n"
        text += f"• 🎲 Random file discovery\n"
        text += f"• 🆕 Latest uploaded content\n"
        text += f"• 🔥 Most popular downloads\n"
        text += f"• 🔍 Advanced search functionality\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'}\n\n"
        text += f"🎯 **Choose an option below:**"

        # Check if user is clone admin
        is_admin = await is_clone_admin(client, user_id)

        # Get clone data for feature settings
        clone_data = await get_clone_by_bot_token(bot_token)

        # Create file access buttons based on clone admin settings
        file_buttons = await get_start_keyboard_for_clone_user(clone_data, bot_token)

        if is_admin:
            # Admin buttons
            file_buttons = [
                [InlineKeyboardButton("⚙️ Clone Settings", callback_data="clone_settings_panel")],
                [InlineKeyboardButton("📊 Bot Stats", callback_data="clone_stats")],
                [InlineKeyboardButton("👤 My Profile", callback_data="user_profile")],
                [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
                [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")]
            ]
        else:
            # Normal clone bot users - check database settings for feature visibility
            buttons = []

            # Get current settings from database to determine which buttons to show
            try:
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    show_random = clone_data.get('random_mode', False)
                    show_recent = clone_data.get('recent_mode', False)
                    show_popular = clone_data.get('popular_mode', False)

                    logger.info(f"Clone {clone_data.get('bot_id')} settings for regular user in back_to_start: random={show_random}, recent={show_recent}, popular={show_popular}")

                    # Only show file browsing buttons if enabled by admin
                    file_buttons_row = []
                    if show_random:
                        file_buttons_row.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
                    if show_recent:
                        file_buttons_row.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

                    # Add file buttons row if any buttons exist
                    if file_buttons_row:
                        buttons.append(file_buttons_row)

                    # Add popular files button in its own row if enabled
                    if show_popular:
                        buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

                else:
                    logger.warning(f"No clone data found for bot_token in back_to_start: {bot_token}")
            except Exception as e:
                logger.error(f"Error getting clone settings in back_to_start: {e}")

            # User action buttons as specified in requirements (always visible)
            buttons.append([
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ])
            buttons.append([
                InlineKeyboardButton("💎 Plans", callback_data="premium_info"),
                InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
            ])
            file_buttons = buttons # Assign the dynamically generated buttons

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(file_buttons))
    else:
        # Mother bot logic (keep existing implementation)
        # Mother bot start message
        text = f"🚀 **Welcome back to Advanced Bot Creator, {user.first_name}!**\n\n"
        text += f"🤖 **Create & Manage Personal Clone Bots**\n"
        text += f"Build your own file-sharing bot network with advanced features.\n\n"
        text += f"🌟 **What You Can Do:**\n"
        text += f"• 🤖 Create unlimited clone bots\n"
        text += f"• 📁 Advanced file management system\n"
        text += f"• 👥 User management & analytics\n"
        text += f"• 💎 Premium features & monetization\n"
        text += f"• 🔧 Complete customization control\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        text += f"🎯 **Get Started:**"

        # Mother bot buttons - Updated layout
        buttons = []
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone")
        ])
        buttons.append([
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
            InlineKeyboardButton("💎 Plans", callback_data="premium_info")
        ])
        buttons.append([
            InlineKeyboardButton("❓ Help", callback_data="help_menu"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_water")
        ])

        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        if not is_clone_bot and is_mother_admin:
            buttons.append([
                InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management")
            ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^user_profile$"))
async def user_profile_callback(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    await query.answer()
    user_id = query.from_user.id

    # Check force subscription first
    try:
        if await utils.handle_force_sub(client, query.message):
            return
    except:
        # Continue if force sub check fails
        pass

    # Check if this is a clone bot
    is_clone, bot_token = await is_clone_bot_instance_async(client)

    if is_clone:
        # For clone bots, show simplified profile without balance features
        stats = await get_command_stats(user_id)

        text = f"👤 **Your Profile**\n\n"
        text += f"🆔 **User ID:** `{user_id}`\n"
        text += f"👤 **Name:** {query.from_user.first_name}\n"
        if query.from_user.username:
            text += f"📞 **Username:** @{query.from_user.username}\n"

        text += f"📈 **Commands Used:** {stats['command_count']}\n\n"
        text += f"📋 **Account Information:**\n"
        text += f"View your usage statistics and account details."

        # Clone bot profile buttons (no balance features)
        buttons = []
        buttons.append([
            InlineKeyboardButton("📈 Usage Stats", callback_data="detailed_stats"),
            InlineKeyboardButton("💎 Premium Info", callback_data="premium_info")
        ])
        buttons.append([
            InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")
        ])

        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # Mother bot profile with full features
    from bot.database.balance_db import create_user_profile
    user_profile = await create_user_profile(
        user_id=user_id,
        username=query.from_user.username,
        first_name=query.from_user.first_name
    )

    if not user_profile:
        text = "❌ Error accessing your profile. Please try again."
        await safe_edit_message(query, text)
        return

    # Get additional stats
    stats = await get_command_stats(user_id)

    # Profile information
    text = f"👤 **Your Profile**\n\n"
    text += f"🆔 **User ID:** `{user_id}`\n"
    text += f"👤 **Name:** {query.from_user.first_name}\n"
    if query.from_user.username:
        text += f"📞 **Username:** @{query.from_user.username}\n"

    text += f"💰 **Balance:** ${user_profile['balance']:.2f}\n"
    text += f"💸 **Total Spent:** ${user_profile.get('total_spent', 0):.2f}\n"
    text += f"📈 **Commands Used:** {stats['command_count']}\n"
    text += f"📅 **Member Since:** {user_profile['created_at'].strftime('%Y-%m-%d')}\n\n"
    text += f"📋 **Account Management:**\n"
    text += f"Manage your account settings and view detailed information below."

    # Profile action buttons
    buttons = []
    buttons.append([
        InlineKeyboardButton("💳 Add Balance", callback_data="add_balance_user"),
        InlineKeyboardButton("📊 Transaction History", callback_data="transaction_history")
    ])
    buttons.append([
        InlineKeyboardButton("🤖 My Clone Bots", callback_data="my_clones_list"),
        InlineKeyboardButton("⚙️ Account Settings", callback_data="account_settings")
    ])
    buttons.append([
        InlineKeyboardButton("📈 Usage Stats", callback_data="detailed_stats"),
        InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium_info")
    ])
    buttons.append([
        InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")
    ])

    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))

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
    is_clone_bot, _ = await is_clone_bot_instance_async(client)

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

        if await is_clone_admin(client, user_id):
            text += f"**⚙️ Clone Admin Commands:**\n"
            text += f"• Use ⚙️ Settings button for configuration\n"
            text += f"• Toggle features on/off\n"
            text += f"• Configure URL shortener\n\n"
    else:
        # Mother bot help
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

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_callback(client: Client, query: CallbackQuery):
    """Show about information for clone bot"""
    await query.answer()

    text = f"ℹ️ **About Advanced File Storage Bot**\n\n"
    text += f"🔐 **Next-Generation File Management System**\n"
    text += f"Your personal file storage and sharing solution\n\n"
    text += f"🌟 **Core Features:**\n"
    text += f"• 🔗 Generate secure download links\n"
    text += f"• 🔑 Advanced token verification system\n"
    text += f"• 📦 Intelligent batch file operations\n"
    text += f"• 🚫 Robust force subscription system\n"
    text += f"• 💎 Premium user tier benefits\n"
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
    text += f"👨‍💻 **Developer:** @{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Developer", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
            InlineKeyboardButton("⭐ Rate Bot", callback_data="rate_bot")
        ],
        [
            InlineKeyboardButton("🐛 Report Bug", callback_data="report_bug"),
            InlineKeyboardButton("💡 Suggest Feature", callback_data="suggest_feature")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^about_water$"))
async def about_water_callback(client: Client, query: CallbackQuery):
    """Show about information for mother bot"""
    await query.answer()

    text = f"💧 **About Water Bot Creator System**\n\n"
    text += f"🚀 **Advanced Bot Creation Platform**\n"
    text += f"The most sophisticated Telegram bot cloning and management system\n\n"
    text += f"🌟 **Platform Features:**\n"
    text += f"• 🤖 Unlimited clone bot creation\n"
    text += f"• 📁 Advanced file management system\n"
    text += f"• 👥 Comprehensive user management\n"
    text += f"• 💎 Premium monetization features\n"
    text += f"• 🔧 Complete customization control\n"
    text += f"• 📊 Real-time analytics & monitoring\n"
    text += f"• 🔒 Enterprise-grade security\n"
    text += f"• ⚡ Lightning-fast performance\n\n"

    text += f"🛡️ **Security & Reliability:**\n"
    text += f"Built with enterprise-grade security protocols and 99.9% uptime guarantee.\n\n"

    text += f"💻 **Advanced Technology Stack:**\n"
    text += f"• Python 3.11+ with Pyrogram\n"
    text += f"• MongoDB with advanced indexing\n"
    text += f"• Redis caching layer\n"
    text += f"• Distributed architecture\n"
    text += f"• Real-time health monitoring\n\n"

    text += f"🔧 **Version:** 3.0.0 Advanced\n"
    text += f"👨‍💻 **Developer:** @{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}\n"
    text += f"🌊 **Powered by Water Technology**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Developer", url=f"https://t.me/{Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'}"),
            InlineKeyboardButton("⭐ Rate Platform", callback_data="rate_bot")
        ],
        [
            InlineKeyboardButton("📚 Documentation", callback_data="documentation"),
            InlineKeyboardButton("💡 Feature Request", callback_data="suggest_feature")
        ],
        [
            InlineKeyboardButton("🐛 Report Issue", callback_data="report_bug"),
            InlineKeyboardButton("💬 Join Community", url="https://t.me/your_support_group")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

# Add a new handler for media forwarding to trigger auto-indexing for clone bots.
@Client.on_message(filters.media & filters.private, group=8)
async def handle_media_forward(client: Client, message: Message):
    """
    Handles incoming media messages. If it's a forwarded message to a clone bot,
    it triggers the auto-indexing process for that clone's database.
    """
    user_id = message.from_user.id
    is_clone, bot_token = await is_clone_bot_instance_async(client)

    # Auto-indexing for forwarded media is handled by dedicated handlers in clone_auto_index.py and clone_forward_indexer.py
    # No need to handle it here in start_handler.py

# Command to check database by clone admin
@Client.on_message(filters.command(["checkdb"]) & filters.private, group=9)
async def check_db_command(client: Client, message: Message):
    """
    Allows clone admins to check the database status of their clone bot.
    """
    user_id = message.from_user.id
    is_clone, bot_token = await is_clone_bot_instance_async(client)

    if not is_clone:
        await message.reply_text("This command is only available for clone bot instances.", quote=True)
        return

    if not await is_clone_admin(client, user_id):
        await message.reply_text("❌ Only the clone admin can use this command.", quote=True)
        return

    logger.info(f"Received /checkdb command from clone admin {user_id} for bot {bot_token[:10]}...")

    try:
        # Get clone data to access its specific MongoDB URL
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            logger.warning(f"Clone data not found for bot_token {bot_token[:10]}...")
            await message.reply_text("Could not retrieve clone configuration. Please contact support.", quote=True)
            return

        mongo_url = clone_data.get('mongodb_url')
        if not mongo_url:
            logger.warning(f"MongoDB URL not found for clone {bot_token[:10]}...")
            await message.reply_text("MongoDB URL not configured for this clone bot. Please check settings.", quote=True)
            return

        # Import the database checking utility
        from bot.utils.db_checker import check_database_status

        # Check the database status using the specific MongoDB URL
        logger.info(f"Checking database status for clone bot {bot_token[:10]} using URL: {mongo_url[:20]}...")
        status_message = await check_database_status(mongo_url)

        await message.reply_text(f"**Database Status for Clone Bot `{bot_token[:10]}...`:**\n\n{status_message}", quote=True)

    except ImportError:
        logger.error("bot.utils.db_checker module not found. Database check is unavailable.")
        await message.reply_text("Database checking utility is not available.", quote=True)
    except Exception as e:
        logger.error(f"Error during database check for clone {bot_token[:10]}...: {e}")
        await message.reply_text(f"An error occurred while checking the database: {e}", quote=True)


# Handle search queries and other text
        return