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
from bot.database.clone_db import get_clone_by_bot_token
from bot.utils import handle_force_sub
from bot.database import get_command_stats

logger = LOGGER(__name__)

# User settings storage (in-memory dictionary)
user_settings = {}

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

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    user_id = user.id

    print(f"🚀 DEBUG COMMAND: /start command from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{user.username}, First: {user.first_name}")

    # Handle force subscription first (with admin exemption)
    if not await utils.handle_force_sub(client, message):
        print(f"🔒 DEBUG: User {user_id} blocked by force subscription")
        return

    print(f"✅ DEBUG: User {user_id} passed force subscription check")

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
        # Clone bot start message
        text = f"🤖 **Welcome {message.from_user.first_name}!**\n\n"
        text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        text += f"🎯 Choose an option below:"

        # Clone bot menu - check admin vs user
        if is_admin_user:
            # Clone admin gets settings access
            buttons = [
                [InlineKeyboardButton("🎛️ Clone Settings", callback_data="clone_settings")],
                [InlineKeyboardButton("📊 Bot Stats", callback_data="clone_stats")]
            ]
        else:
            # Normal users get file access based on admin settings
            buttons = []

            # Get current clone data for feature settings
            clone_data = await get_clone_by_bot_token(bot_token)
            
            # Check each feature based on clone admin settings - default to True if no data
            show_random = clone_data.get('random_mode', True) if clone_data else True
            show_recent = clone_data.get('recent_mode', True) if clone_data else True  
            show_popular = clone_data.get('popular_mode', True) if clone_data else True

            logger.info(f"Feature states for clone {bot_token[:10]}... - Random: {show_random}, Recent: {show_recent}, Popular: {show_popular}")

            # Create file access buttons only if enabled by admin
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

            # Always show help and about for normal users
            buttons.append([InlineKeyboardButton("❓ Help", callback_data="help")])
            buttons.append([InlineKeyboardButton("ℹ️ About", callback_data="about")])
    else:
        # Mother bot start message
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

        # Row 3: Premium & Referral
        buttons.append([
            InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            InlineKeyboardButton("🎁 Referral Program", callback_data="show_referral_main")
        ])

        # Row 4: About
        buttons.append([
            InlineKeyboardButton("💧 About", callback_data="about_water")
        ])

        # Row 5: Help & Admin
        help_admin_row = [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        if not is_clone_bot and is_mother_admin:
            help_admin_row.append(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
            help_admin_row.append(InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management"))
        buttons.append(help_admin_row)

        reply_markup = InlineKeyboardMarkup(buttons)

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# File access handlers with enhanced feature checks
@Client.on_callback_query(filters.regex("^random_files$"))
async def random_files_callback(client: Client, query: CallbackQuery):
    """Handle random files callback"""
    await query.answer()
    
    # Check if feature is enabled by clone admin
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    clone_data = await get_clone_by_bot_token(bot_token)
    
    # Enhanced feature checking
    if clone_data:
        feature_enabled = clone_data.get('random_mode', True)
        logger.info(f"Random files access attempt - Feature enabled: {feature_enabled}")
        
        if not feature_enabled:
            await query.edit_message_text(
                "❌ **Random Files Disabled**\n\n"
                "This feature has been disabled by the bot admin.\n\n"
                "Contact the bot administrator if you need access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return
    
    # Feature is enabled - proceed with random files logic
    await query.edit_message_text("🎲 **Random Files**\n\nShowing random files...")

@Client.on_callback_query(filters.regex("^popular_files$"))
async def popular_files_callback(client: Client, query: CallbackQuery):
    """Handle popular files callback"""
    await query.answer()
    
    # Check if feature is enabled by clone admin
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    clone_data = await get_clone_by_bot_token(bot_token)
    
    # Enhanced feature checking
    if clone_data:
        feature_enabled = clone_data.get('popular_mode', True)
        logger.info(f"Popular files access attempt - Feature enabled: {feature_enabled}")
        
        if not feature_enabled:
            await query.edit_message_text(
                "❌ **Popular Files Disabled**\n\n"
                "This feature has been disabled by the bot admin.\n\n"
                "Contact the bot administrator if you need access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return

    # Feature is enabled - proceed with popular files logic
    await query.edit_message_text("🔥 **Most Popular Files**\n\nShowing popular files...")

@Client.on_callback_query(filters.regex("^recent_files$"))
async def recent_files_callback(client: Client, query: CallbackQuery):
    """Handle recent files callback"""
    await query.answer()
    
    # Check if feature is enabled by clone admin
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    clone_data = await get_clone_by_bot_token(bot_token)
    
    # Enhanced feature checking
    if clone_data:
        feature_enabled = clone_data.get('recent_mode', True)
        logger.info(f"Recent files access attempt - Feature enabled: {feature_enabled}")
        
        if not feature_enabled:
            await query.edit_message_text(
                "❌ **Recent Files Disabled**\n\n"
                "This feature has been disabled by the bot admin.\n\n"
                "Contact the bot administrator if you need access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return

    # Feature is enabled - proceed with recent files logic
    await query.edit_message_text("🆕 **Recent Files**\n\nShowing recent files...")

# Settings handlers
@Client.on_callback_query(filters.regex("^clone_settings$"))
async def clone_settings_callback(client: Client, query: CallbackQuery):
    """Handle clone settings callback"""
    await query.answer()
    user_id = query.from_user.id

    # Check if user is clone admin
    if not await is_clone_admin(client, user_id):
        await query.edit_message_text("❌ Only clone admin can access settings.")
        return

    settings = get_user_settings(user_id)

    text = f"⚙️ **Settings Panel**\n\n"
    text += f"Configure your bot features:\n\n"
    text += f"🎲 Random Files: {'✅ Enabled' if settings['random_files'] else '❌ Disabled'}\n"
    text += f"🔥 Most Popular: {'✅ Enabled' if settings['popular_files'] else '❌ Disabled'}\n"
    text += f"🆕 Recent Files: {'✅ Enabled' if settings['recent_files'] else '❌ Disabled'}\n"
    text += f"📢 Force Join: {'✅ Enabled' if settings['force_join'] else '❌ Disabled'}\n\n"
    text += f"🔗 Shortener URL: `{settings['shortener_url']}`\n"
    text += f"🔑 API Key: `{'*' * (len(settings['shortener_api_key']) - 4) + settings['shortener_api_key'][-4:] if len(settings['shortener_api_key']) > 4 else 'Not Set'}`\n\n"
    text += f"🔒 Token Verification: **{settings['token_verification_mode'].replace('_', ' ').title()}**" # Display current token verification mode

    buttons = [
        [
            InlineKeyboardButton(f"🎲 Random: {'✅' if settings['random_files'] else '❌'}", callback_data="toggle_random"),
            InlineKeyboardButton(f"🔥 Popular: {'✅' if settings['popular_files'] else '❌'}", callback_data="toggle_popular")
        ],
        [
            InlineKeyboardButton(f"🆕 Recent: {'✅' if settings['recent_files'] else '❌'}", callback_data="toggle_recent"),
            InlineKeyboardButton(f"📢 Force Join: {'✅' if settings['force_join'] else '❌'}", callback_data="toggle_force_join")
        ],
        [
            InlineKeyboardButton("🔗 Change Shortener URL", callback_data="change_shortener_url"),
            InlineKeyboardButton("🔑 Change API Key", callback_data="change_api_key")
        ],
        # New button for token verification mode
        [
            InlineKeyboardButton(f"🔒 Token Mode: {settings['token_verification_mode'].replace('_', ' ').title()}", callback_data="toggle_token_mode")
        ],
        [InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Toggle handlers
@Client.on_callback_query(filters.regex("^toggle_"))
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

# Change URL/API handlers
@Client.on_callback_query(filters.regex("^change_shortener_url$"))
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

@Client.on_callback_query(filters.regex("^change_api_key$"))
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

# Handle text input for URL/API changes
@Client.on_message(filters.text & filters.private)
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

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Return to main start menu"""
    await query.answer()

    # Recreate the start message by calling start_command logic
    user = query.from_user
    user_id = user.id
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)
    is_clone_bot, _ = await is_clone_bot_instance_async(client)

    if is_clone_bot:
        # Clone bot start message
        text = f"🤖 **Welcome {user.first_name}!**\n\n"
        text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'}\n\n"
        text += f"🎯 Choose an option below:"

        # Check if user is clone admin
        is_admin = await is_clone_admin(client, user_id)

        # Get clone data for feature settings
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        clone_data = await get_clone_by_bot_token(bot_token)

        # Create file access buttons based on clone admin settings
        file_buttons = []

        # Check admin settings for feature availability - default to True if no data
        show_random = clone_data.get('random_mode', True) if clone_data else True
        show_recent = clone_data.get('recent_mode', True) if clone_data else True
        show_popular = clone_data.get('popular_mode', True) if clone_data else True

        logger.info(f"Back to start feature states - Random: {show_random}, Recent: {show_recent}, Popular: {show_popular}")

        # Only show enabled file mode buttons
        mode_row1 = []
        if show_random:
            mode_row1.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
        if show_recent:
            mode_row1.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

        # Add first row if any buttons exist
        if mode_row1:
            file_buttons.append(mode_row1)

        # Add popular files button if enabled
        if show_popular:
            file_buttons.append([InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")])

        # Settings button - only for clone admin
        if is_admin:
            file_buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings")])

        # User action buttons
        file_buttons.append([
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
            InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
        ])

        file_buttons.append([
            InlineKeyboardButton("ℹ️ About", callback_data="about_bot"),
            InlineKeyboardButton("❓ Help", callback_data="help_menu")
        ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(file_buttons))
    else:
        # Mother bot logic (keep existing implementation)
        # Mother bot start message
        text = f"🚀 **Welcome {user.first_name}!**\n\n"
        text += f"🤖 **Advanced Bot Creator** - Create personal clone bots with file sharing.\n\n"
        text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
        text += f"🎯 Choose an option below:"

        # Mother bot buttons
        buttons = []
        buttons.append([
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
        ])
        buttons.append([
            InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("📊 Statistics", callback_data="user_stats")
        ])
        buttons.append([
            InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            InlineKeyboardButton("🎁 Referral Program", callback_data="show_referral_main")
        ])
        buttons.append([
            InlineKeyboardButton("💧 About", callback_data="about_water")
        ])

        help_admin_row = [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        if not is_clone_bot and is_mother_admin:
            help_admin_row.append(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
        buttons.append(help_admin_row)

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^user_profile$"))
async def user_profile_callback(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    await query.answer()
    user_id = query.from_user.id

    # Check force subscription first
    if await handle_force_sub(client, query.message):
        return

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