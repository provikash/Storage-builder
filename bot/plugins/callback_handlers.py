"""
Main callback query router - simplified and focused
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER
from info import Config

logger = LOGGER(__name__)

# Import all the focused handlers
from bot.handlers import emergency, file_browsing, admin, callback, commands, start, search
from bot.programs import clone_admin, clone_features, clone_indexing, clone_management, clone_random_files

# Define callback priorities to prevent conflicts
CALLBACK_PRIORITIES = {
    "emergency": -10,    # Emergency handlers highest priority
    "clone_settings": -8, # Clone settings high priority
    "admin": 1,          # Admin callbacks
    "search": 4,         # Search related
    "general": 5,        # General callbacks
    "settings": 6,       # Settings handlers
    "catchall": 99       # Catch-all lowest priority
}

# Clone Settings Button Handler
@Client.on_callback_query(filters.regex("^clone_settings_panel$"), group=1)
async def clone_settings_panel_callback(client: Client, query: CallbackQuery):
    """Handle clone settings panel callback"""
    user_id = query.from_user.id

    print(f"🎛️ DEBUG CALLBACK: clone_settings_panel triggered by user {user_id}")
    logger.info(f"Clone settings panel callback from user {user_id}")

    # Check if this is a clone bot and user is the admin
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or 
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    print(f"🎛️ DEBUG CALLBACK: is_clone_bot={is_clone_bot}, bot_token={bot_token[:10]}...")

    if not is_clone_bot or bot_token == Config.BOT_TOKEN:
        await query.answer("❌ Not available in this bot.", show_alert=True)
        return

    # Verify user is clone admin
    try:
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Only clone admin can access settings.", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        await query.answer("❌ Error verifying admin access.", show_alert=True)
        return

    # Answer the callback query first
    await query.answer()

    # Import and call clone settings handler
    try:
        from bot.plugins.clone_admin_settings import clone_settings_command
        await clone_settings_command(client, query)
    except Exception as e:
        logger.error(f"Error in clone settings panel: {e}")
        await query.edit_message_text("❌ Error loading settings panel.")

# File Browsing Handlers
@Client.on_callback_query(filters.regex(r"^(random_files|recent_files|popular_files)$"), group=3)
async def file_browsing_callback_handler(client: Client, query: CallbackQuery):
    """Handle file browsing callbacks for clone bots"""
    callback_data = query.data
    user_id = query.from_user.id

    print(f"📁 DEBUG CALLBACK: {callback_data} triggered by user {user_id}")
    logger.info(f"File browsing callback: {callback_data} from user {user_id}")

    try:
        # Answer the callback query first
        await query.answer()

        # Check if this is a clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot = bot_token != Config.BOT_TOKEN

        if not is_clone_bot:
            await query.edit_message_text(
                "📁 **File Browsing**\n\n"
                "File browsing features are only available in clone bots.\n"
                "Create a clone bot to access these features.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
            return

        # Check if feature is enabled for this clone
        try:
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)
            if clone_data:
                feature_enabled = False
                if callback_data == "random_files":
                    feature_enabled = clone_data.get('random_mode', False)
                elif callback_data == "recent_files":
                    feature_enabled = clone_data.get('recent_mode', False)
                elif callback_data == "popular_files":
                    feature_enabled = clone_data.get('popular_mode', False)

                if not feature_enabled:
                    await query.edit_message_text(
                        f"❌ **Feature Disabled**\n\n"
                        f"The {callback_data.replace('_', ' ').title()} feature has been disabled by the bot admin.\n\n"
                        f"Contact the bot administrator if you need access.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                        ])
                    )
                    return
        except Exception as e:
            logger.error(f"Error checking feature availability: {e}")

        # Handle the specific file browsing action
        if callback_data == "random_files":
            await handle_random_files(client, query)
        elif callback_data == "recent_files":
            await handle_recent_files(client, query)
        elif callback_data == "popular_files":
            await handle_popular_files(client, query)

    except Exception as e:
        logger.error(f"Error in file browsing callback handler: {e}")
        await query.edit_message_text("❌ An error occurred while processing your request.")

# Toggle settings handlers
@Client.on_callback_query(filters.regex(r"^toggle_(random|recent|popular)$"), group=-3)
async def handle_toggle_settings(client: Client, query: CallbackQuery):
    """Handle toggle settings"""
    await query.answer()
    user_id = query.from_user.id
    setting = query.data.split("_")[1]  # random, recent, or popular

    try:
        from bot.database.clone_db import get_clone_by_bot_token, update_clone_settings

        bot_token = getattr(client, 'bot_token', None)
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Unauthorized", show_alert=True)
            return

        # Toggle the setting
        setting_key = f"{setting}_mode"
        current_value = clone_data.get(setting_key, False)
        new_value = not current_value

        # Update in database
        await update_clone_settings(bot_token, {setting_key: new_value})

        # Show updated settings
        await clone_settings_panel_callback(client, query)

    except Exception as e:
        logger.error(f"Error toggling {setting}: {e}")
        await query.answer("❌ Error updating setting", show_alert=True)


# Add more callback handlers as needed for other features
@Client.on_callback_query(filters.regex("^(help_menu|about_bot|user_profile|premium_info|back_to_start|my_stats|add_balance)$"), group=2)
async def general_callback_handler(client: Client, query: CallbackQuery):
    """Handle general callback queries"""
    callback_data = query.data
    user_id = query.from_user.id

    print(f"🔄 DEBUG CALLBACK: {callback_data} triggered by user {user_id}")
    logger.info(f"General callback: {callback_data} from user {user_id}")

    try:
        await query.answer()

        if callback_data == "help_menu":
            await handle_help_menu(client, query)
        elif callback_data == "about_bot":
            await handle_about_bot(client, query)
        elif callback_data == "user_profile":
            await handle_user_profile(client, query)
        elif callback_data == "premium_info":
            await handle_premium_info(client, query)
        elif callback_data == "back_to_start":
            await handle_back_to_start(client, query)
        elif callback_data == "my_stats":
            await handle_my_stats(client, query)
        elif callback_data == "add_balance":
            await handle_add_balance(client, query)

    except Exception as e:
        logger.error(f"Error in general callback handler: {e}")
        await query.answer("❌ An error occurred.", show_alert=True)

# Test callback handler
@Client.on_callback_query(filters.regex("^test_callback$"), group=10)
async def test_callback(client: Client, query: CallbackQuery):
    """Test callback handler"""
    await query.answer("✅ Callback system is working!", show_alert=True)

# Catch-all callback handler for debugging
@Client.on_callback_query(group=99)
async def catch_all_callback_handler(client: Client, query: CallbackQuery):
    """Catch-all callback handler for unhandled callbacks"""
    callback_data = query.data
    user_id = query.from_user.id

    print(f"🚨 DEBUG CALLBACK: Unhandled callback '{callback_data}' from user {user_id}")
    logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")

    try:
        await query.answer("⚠️ This button is not yet implemented.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in catch-all callback handler: {e}")

# --- Helper Functions ---

async def handle_help_menu(client: Client, query: CallbackQuery):
    """Handle help menu callback"""
    try:
        text = "📚 **Help Menu**\n\n"
        text += "Here are some commands you can use:\n"
        text += "/start - Start the bot\n"
        text += "/help - Show this help menu\n"
        text += "/about - Get information about the bot\n"
        text += "/profile - View your profile\n"
        text += "/stats - View your statistics\n"
        text += "/add_balance - Add balance to your account\n"
        text += "/clone_settings - Access clone bot settings (for clone admins)\n"
        text += "/search <query> - Search for files\n"
        text += "/browse <type> - Browse files (random, recent, popular)\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error in help menu handler: {e}")
        await query.edit_message_text("❌ Error displaying help menu.")

async def handle_about_bot(client: Client, query: CallbackQuery):
    """Handle about bot callback"""
    try:
        text = "🤖 **About This Bot**\n\n"
        text += "This bot is a powerful tool for managing and accessing files.\n"
        text += "It supports various features including:\n"
        text += "• File browsing (random, recent, popular)\n"
        text += "• User statistics and balance management\n"
        text += "• Clone bot functionality for advanced users\n\n"
        text += "Version: 1.0.0\n"
        text += "Developed by: Your Name/Team"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error in about bot handler: {e}")
        await query.edit_message_text("❌ Error displaying bot information.")

async def handle_user_profile(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    user_id = query.from_user.id
    try:
        # Fetch user data from database
        from bot.database.users import get_user_data

        user_data = await get_user_data(user_id)
        if not user_data:
            await query.edit_message_text("❌ User profile not found.")
            return

        username = user_data.get('username', 'N/A')
        first_name = user_data.get('first_name', 'N/A')
        last_name = user_data.get('last_name', 'N/A')
        language_code = user_data.get('language_code', 'N/A')

        text = f"👤 **User Profile**\n\n"
        text += f"**User ID:** `{user_id}`\n"
        text += f"**Username:** @{username}\n"
        text += f"**First Name:** {first_name}\n"
        text += f"**Last Name:** {last_name}\n"
        text += f"**Language:** {language_code}\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error in user profile handler: {e}")
        await query.edit_message_text("❌ Error loading user profile.")

async def handle_premium_info(client: Client, query: CallbackQuery):
    """Handle premium info callback"""
    try:
        text = "🌟 **Premium Features**\n\n"
        text += "Unlock advanced features with our premium subscription!\n\n"
        text += "Premium benefits include:\n"
        text += "• Increased download speeds\n"
        text += "• Priority support\n"
        text += "• Access to exclusive content\n"
        text += "• No ads or limitations\n\n"
        text += "Contact the administrator to upgrade your account."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error in premium info handler: {e}")
        await query.edit_message_text("❌ Error displaying premium information.")

async def handle_back_to_start(client: Client, query: CallbackQuery):
    """Handle back to start callback"""
    try:
        # Call start handler to recreate the start message
        from bot.plugins.start_handler import start_command

        # Create a mock message object for the start handler
        class MockMessage:
            def __init__(self, from_user):
                self.from_user = from_user
                self.date = query.message.date
                self.id = query.message.id

            async def reply_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

        mock_message = MockMessage(query.from_user)
        await start_command(client, mock_message)

    except Exception as e:
        logger.error(f"Error in back to start handler: {e}")
        await query.edit_message_text("❌ Error returning to start menu.")

async def handle_my_stats(client: Client, query: CallbackQuery):
    """Handle my stats callback"""
    user_id = query.from_user.id
    try:
        # Get basic user stats
        from bot.database.users import get_user_stats
        from bot.database.balance_db import get_user_balance

        try:
            balance = await get_user_balance(user_id)
        except:
            balance = 0.0

        text = f"📊 **Your Statistics**\n\n"
        text += f"👤 **User ID:** `{user_id}`\n"
        text += f"💰 **Balance:** ${balance:.2f}\n"
        text += f"📅 **Member Since:** Today\n\n"
        text += f"🔧 **Bot Features:**\n"
        text += f"• File browsing available\n"
        text += f"• Search functionality\n"
        text += f"• Download support\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in my stats handler: {e}")
        await query.edit_message_text("❌ Error loading statistics.")

async def handle_add_balance(client: Client, query: CallbackQuery):
    """Handle add balance callback"""
    text = f"💰 **Add Balance**\n\n"
    text += f"Contact the administrator to add balance to your account.\n\n"
    text += f"💳 **Payment Methods:**\n"
    text += f"• Contact admin for details\n"
    text += f"• Various payment options available\n\n"
    text += f"📞 **Support:** Contact bot administrator"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

async def handle_random_files(client: Client, query: CallbackQuery):
    """Handle random files callback"""
    text = f"🎲 **Random Files**\n\n"
    text += f"📁 Browsing random files from the database...\n\n"
    text += f"⚠️ **Note:** This feature requires token verification.\n"
    text += f"Use /verify to get your access token first."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

async def handle_recent_files(client: Client, query: CallbackQuery):
    """Handle recent files callback"""
    text = f"🆕 **Recent Files**\n\n"
    text += f"📅 Showing latest uploaded files...\n\n"
    text += f"⚠️ **Note:** This feature requires token verification.\n"
    text += f"Use /verify to get your access token first."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

async def handle_popular_files(client: Client, query: CallbackQuery):
    """Handle popular files callback"""
    text = f"🔥 **Popular Files**\n\n"
    text += f"📊 Showing most downloaded files...\n\n"
    text += f"⚠️ **Note:** This feature requires token verification.\n"
    text += f"Use /verify to get your access token first."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)