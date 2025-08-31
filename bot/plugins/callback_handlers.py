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

# Define callback priorities to prevent conflicts
CALLBACK_PRIORITIES = {
    "admin": 1,      # Admin callbacks highest priority
    "approval": 2,   # Approval system
    "premium": 3,    # Premium features
    "search": 4,     # Search related
    "general": 5,    # General callbacks
    "catchall": 99   # Catch-all lowest priority
}

# Placeholder for creation sessions, assuming it's defined elsewhere or needs to be defined
# If creation_sessions is used globally, ensure it's accessible here.
# For this example, let's assume it's a dictionary.
creation_sessions = {}

# Placeholder for clone_config_loader, assuming it's defined elsewhere
class MockCloneConfigLoader:
    async def get_bot_config(self, bot_token):
        # Mock implementation, replace with actual loader
        return {
            "bot_info": {
                "admin_id": 123456789, # Example admin ID
                "bot_token": bot_token
            },
            "features": {
                "random_files": True,
                "recent_files": True,
                "popular_files": True,
                "force_join": True,
                "token_verification_mode": "strict",
                "url_shortener": True,
                "api_key_management": True
            }
        }
clone_config_loader = MockCloneConfigLoader()

# Placeholder for admin_sessions, assuming it's defined elsewhere
admin_sessions = {}

# Placeholder for debug_print, assuming it's defined elsewhere
def debug_print(message):
    print(f"DEBUG: {message}")

# Helper function to check if user is Mother Bot admin
def is_mother_admin(user_id):
    """Check if user is Mother Bot admin"""
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())

    # Convert to list if it's a tuple
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
        if bot_token == Config.BOT_TOKEN: # Not a clone bot
            return False

        # Assume we have a way to get clone data, e.g., from a database
        # For this example, let's use a mock lookup
        # In a real scenario, you'd fetch this from your database based on bot_token
        clone_data = {"admin_id": 123456789} # Mock data, replace with actual lookup

        if clone_data and clone_data.get('admin_id') == user_id:
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin status: {e}")
        return False

# Helper function to determine if the current bot instance is a clone bot
def is_clone_bot_instance(client: Client):
    """Checks if the current bot instance is a clone bot and returns its token if so."""
    bot_token = getattr(client, 'bot_token', None)
    if bot_token:
        try:
            # Simple check - if bot_token is different from Config.BOT_TOKEN, it's likely a clone
            from info import Config
            if bot_token != Config.BOT_TOKEN:
                return True, bot_token
        except Exception as e:
            logger.error(f"Error checking clone config in is_clone_bot_instance: {e}")
    return False, None

# Async version for use in async contexts
async def is_clone_bot_instance_async(client: Client):
    """Async version of clone bot detection"""
    bot_token = getattr(client, 'bot_token', None)
    if bot_token:
        try:
            from bot.utils.clone_config_loader import clone_config_loader
            from info import Config

            # First quick check
            if bot_token != Config.BOT_TOKEN:
                # Verify with database
                try:
                    from bot.database.clone_db import get_clone_by_bot_token
                    clone_data = await get_clone_by_bot_token(bot_token)
                    if clone_data:
                        return True, bot_token
                except:
                    pass
                return True, bot_token  # Assume clone if token is different
        except Exception as e:
            logger.error(f"Error in async clone detection: {e}")
    return False, None

# Placeholder functions for clone admin callbacks
async def handle_clone_local_force_channels(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_local_force_channels")
    await query.edit_message_text("Local Force Channels Settings (Placeholder)")

async def handle_clone_request_channels(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_request_channels")
    await query.edit_message_text("Request Channels Settings (Placeholder)")

async def handle_clone_token_command_config(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_token_command_config")
    await query.edit_message_text("Token Command Configuration (Placeholder)")

async def handle_clone_token_pricing(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_token_pricing")
    await query.edit_message_text("Token Pricing Settings (Placeholder)")

async def handle_clone_bot_features(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_bot_features")
    await query.edit_message_text("Bot Features Settings (Placeholder)")

async def handle_clone_subscription_status(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_subscription_status")
    await query.edit_message_text("Subscription Status (Placeholder)")

async def handle_clone_toggle_token_system(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_toggle_token_system")
    await query.edit_message_text("Token System Toggle (Placeholder)")

async def clone_admin_panel(client, message):
    """Placeholder for the clone admin panel display function"""
    text = "Clone Admin Panel (Placeholder)"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Settings", callback_data="clone_settings_panel")],
        [InlineKeyboardButton("Back to Home", callback_data="back_to_start")]
    ])
    await message.reply_text(text, reply_markup=buttons)

async def handle_clone_about_water(client: Client, query: CallbackQuery):
    await query.answer("Handling clone_about_water")
    await query.edit_message_text("About Water Info (Placeholder)")

# Admin Panel Callbacks (Priority 1)
@Client.on_callback_query(filters.regex("^(mother_|clone_|back_to_|refresh_dashboard)"), group=CALLBACK_PRIORITIES["admin"])
async def admin_callback_router(client: Client, query: CallbackQuery):
    """Route admin callbacks to appropriate handlers"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Admin callback router - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    try:
        # Handle refresh dashboard
        if query.data == "refresh_dashboard":
            from bot.plugins.admin_commands import dashboard_command
            # Convert callback query to message-like object for dashboard_command
            class FakeMessage:
                def __init__(self, query):
                    self.from_user = query.from_user
                    self.command = ["dashboard"]
                async def reply_text(self, text, reply_markup=None):
                    await query.edit_message_text(text, reply_markup=reply_markup)

            fake_message = FakeMessage(query)
            await dashboard_command(client, fake_message)
            return

        # Only handle if not already processed by dedicated handlers
        # Check if this is a mother bot callback
        if query.data.startswith("mother_") or query.data.startswith("back_to_mother"):
            # Don't handle here, let the dedicated mother_admin_callbacks handle it
            pass
        # Check if this is a clone bot callback
        elif query.data.startswith("clone_") or query.data.startswith("back_to_clone"):
            # Don't handle here, let the dedicated clone_admin_callbacks handle it
            pass
    except Exception as e:
        print(f"❌ ERROR IN ADMIN CALLBACK ROUTER: {e}")
        traceback.print_exc()
        if not query.data.startswith("back_to_") and query.data != "refresh_dashboard":
            await query.answer("❌ Error processing request!", show_alert=True)

# Handle start message admin buttons
@Client.on_callback_query(filters.regex("^(admin_panel|bot_management)$"), group=CALLBACK_PRIORITIES["admin"])
async def handle_start_admin_buttons(client: Client, query: CallbackQuery):
    """Handle admin panel and bot management buttons from start message"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Start admin button - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    callback_data = query.data

    if callback_data == "admin_panel":
        # Block access in clone bots
        is_clone_bot_instance, _ = is_clone_bot_instance(client)
        if is_clone_bot_instance:
            await query.answer("❌ Admin panel not available in clone bots!", show_alert=True)
            return

        # Check admin permissions for mother bot
        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return

        # Route to admin panel
        try:
            from bot.plugins.mother_admin import mother_admin_panel
            await mother_admin_panel(client, query)
        except Exception as e:
            print(f"❌ ERROR LOADING ADMIN PANEL: {e}")
            await query.answer("❌ Error loading admin panel!", show_alert=True)

    elif callback_data == "bot_management":
        # Block access in clone bots
        is_clone_bot_instance, _ = is_clone_bot_instance(client)
        if is_clone_bot_instance:
            await query.answer("❌ Bot management not available in clone bots!", show_alert=True)
            return

        # Check admin permissions for mother bot
        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return

        # Show bot management options
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

# Handle quick approval/rejection callbacks
@Client.on_callback_query(filters.regex("^(quick_approve|quick_reject|view_request):"), group=CALLBACK_PRIORITIES["approval"])
async def handle_quick_actions(client: Client, query: CallbackQuery):
    """Handle quick approval, rejection, and view request actions"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Quick action callback - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

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
    print(f"🔄 DEBUG CALLBACK: View request details - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")
    try:
        from bot.database.clone_db import get_clone_request_by_id
        request = await get_clone_request_by_id(request_id)

        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        # Format request details
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
    print(f"🔄 DEBUG CALLBACK: Mother Bot admin callback router - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    # Block mother bot callbacks in clone bots
    is_clone_bot_instance, _ = is_clone_bot_instance(client)
    if is_clone_bot_instance:
        await query.answer("❌ Mother bot features not available in clone bots!", show_alert=True)
        return

    # Check if user is mother bot admin
    if not is_mother_admin(user_id):
        await query.answer("❌ Unauthorized access to mother bot features!", show_alert=True)
        return

    # Let specific handlers handle their callbacks
    pass

# Add handlers for simplified clone creation flow
# Assuming these functions (step2_bot_token, start_clone_creation, cancel_creation, database_help) are defined elsewhere
# and creation_sessions is a global dictionary to store session data.

# Dummy function for step2_bot_token for context
async def step2_bot_token(client, query):
    """Placeholder for the actual step 2 handler"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Step 2 Bot Token - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")
    session = creation_sessions.get(user_id)
    if not session:
        await query.edit_message_text("Session expired. Please start again.")
        return

    plan_id = session['data'].get('plan_id', 'monthly')
    plan_details = session['data'].get('plan_details', {})
    bot_username = session['data'].get('bot_username', 'your_bot') # Placeholder if not set

    text = f"🔑 **Step 2/3: Bot Token**\n\n"
    text += f"✅ **Bot:** @{bot_username}\n"
    text += f"✅ **Plan:** {plan_details.get('name', 'Selected Plan')}\n\n"
    text += f"Now, please provide your Telegram Bot Token.\n"
    text += f"You can get this from @BotFather.\n\n"
    text += f"**Example:** `1234567890:ABCdefGHIjklMNOpqrSTUvwxyzABCdefGHIjklMNOpqrSTUvwxyz-abcdefg`\n\n"
    text += f"Send your bot token now:"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ BotFather Help", url="https://core.telegram.org/bots#6-botfather")],
            [InlineKeyboardButton("🔙 Back to Plan Selection", callback_data="back_to_plan_selection")], # Assuming this callback exists
            [InlineKeyboardButton("➡️ Next: Database URL", callback_data="step3_db_url")], # This callback will lead to the new step 3
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")] # Assuming this callback exists
        ])
    )


@Client.on_callback_query(filters.regex("^back_to_step3$"))
async def back_to_step3_callback(client, query: CallbackQuery):
    """Handle back to step 3"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Back to Step 3 - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")
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

# Premium System Callbacks (Priority 3)
@Client.on_callback_query(filters.regex("^(show_premium_plans|buy_premium)"), group=CALLBACK_PRIORITIES["premium"])
async def premium_callback_handler(client: Client, query: CallbackQuery):
    """Handle premium-related callbacks"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Premium callback - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    # Import from existing callback handler
    if query.data == "show_premium_plans":
        from bot.plugins.callback import show_premium_callback
        await show_premium_callback(client, query)
    elif query.data.startswith("buy_premium"):
        from bot.plugins.callback import buy_premium_callback
        await buy_premium_callback(client, query)

# General Callbacks (Priority 5)
@Client.on_callback_query(filters.regex("^(about|help|my_stats|close|about_bot|help_menu|user_profile|transaction_history|back_to_start|add_balance|manage_my_clone|show_referral_main)$"), group=CALLBACK_PRIORITIES["general"])
async def general_callback_handler(client: Client, query: CallbackQuery):
    """Handle general purpose callbacks"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: General callback - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    callback_data = query.data

    if callback_data == "about":
        from bot.plugins.callback import about_callback
        await about_callback(client, query)
    elif callback_data in ["help", "help_menu"]:
        # These are now handled in start_handler.py
        from bot.plugins.start_handler import help_callback
        await help_callback(client, query)
    elif callback_data in ["about_bot"]:
        # These are now handled in start_handler.py
        from bot.plugins.start_handler import about_callback
        await about_callback(client, query)
    elif callback_data in ["user_profile"]:
        # These are now handled in start_handler.py
        from bot.plugins.start_handler import profile_callback
        await profile_callback(client, query)
    elif callback_data in ["transaction_history"]:
        # These are now handled in start_handler.py
        from bot.plugins.start_handler import transaction_history_callback
        await transaction_history_callback(client, query)
    elif callback_data == "back_to_start":
        # Handle back to start - should go to appropriate start menu
        is_clone, bot_token = await is_clone_bot_instance_async(client)
        debug_print(f"Back to start - Is clone: {is_clone}, User: {user_id}")

        if is_clone:
            # For clone bots, recreate clone start menu
            try:
                # Get clone data and user info
                from bot.database.clone_db import get_clone_by_bot_token
                from bot.database.premium_db import is_premium_user
                from bot.database.balance_db import get_user_balance

                clone_data = await get_clone_by_bot_token(bot_token)
                user_premium = await is_premium_user(user_id)
                balance = await get_user_balance(user_id)

                # Clone bot start message
                text = f"🤖 **Welcome {query.from_user.first_name}!**\n\n"
                text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
                text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
                text += f"🎯 Choose an option below:"

                # Create clone bot buttons
                start_buttons = []

                # Add settings button for clone admin
                if clone_data and clone_data.get('admin_id') == user_id:
                    start_buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data="clone_settings_panel")])

                # Get clone settings for file buttons
                show_random = clone_data.get('random_mode', True) if clone_data else True
                show_recent = clone_data.get('recent_mode', True) if clone_data else True
                show_popular = clone_data.get('popular_mode', True) if clone_data else True

                # File access buttons based on settings
                file_buttons = []

                # First row of file mode buttons (only if enabled)
                mode_row1 = []
                if show_random:
                    mode_row1.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
                if show_recent:
                    mode_row1.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

                if mode_row1:
                    file_buttons.append(mode_row1)

                # Second row for popular files (only if enabled)
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

                await query.edit_message_text(text, reply_markup=reply_markup)
                return

            except Exception as e:
                logger.error(f"❌ Error in clone back_to_start: {e}")
                await query.answer("❌ Error loading clone start menu", show_alert=True)
                return

        # For mother bot, use the dedicated callback
        try:
            from bot.plugins.start_handler import back_to_start_callback
            await back_to_start_callback(client, query)
        except Exception as e:
            debug_print(f"Error in mother bot back_to_start: {e}")
            await query.answer("❌ Error returning to start. Please use /start command.")

    elif callback_data == "add_balance":
        # Handle add balance
        from bot.plugins.balance_management import show_balance_options
        await show_balance_options(client, query)
    elif callback_data == "manage_my_clone":
        # Handle manage clone
        from bot.plugins.clone_management import manage_user_clone
        await manage_user_clone(client, query)
    elif callback_data == "show_referral_main":
        # Handle referral program
        from bot.plugins.referral_program import show_referral_main
        await show_referral_main(client, query)
    elif callback_data == "my_stats":
        from bot.plugins.callback import my_stats_callback
        await my_stats_callback(client, query)
    elif callback_data == "close":
        from bot.plugins.callback import close
        await close(client, query)

# Feature Toggle Callbacks
@Client.on_callback_query(filters.regex("^toggle_feature#"), group=CALLBACK_PRIORITIES["admin"])
async def feature_toggle_callback(client: Client, query: CallbackQuery):
    """Handle feature toggling callbacks"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Feature toggle callback - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    # Import from admin panel
    from bot.plugins.admin_panel import toggle_feature_handler
    await toggle_feature_handler(client, query)

# Clone creation callbacks are now handled directly in step_clone_creation.py
# This handler is removed to prevent conflicts

# Debug callback for unhandled cases (disabled to prevent conflicts)
# This handler is commented out to prevent callback conflicts
# Uncomment only for debugging purposes
# @Client.on_callback_query(filters.regex(".*"), group=CALLBACK_PRIORITIES["catchall"])
# async def debug_unhandled_callbacks(client: Client, query: CallbackQuery):
#     """Debug handler for unhandled callbacks"""
#     user_id = query.from_user.id
#     print(f"⚠️ UNHANDLED CALLBACK: {query.data} from user {user_id}")
#     print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")
#     pass

# Random, Recent, Popular file features are disabled in mother bot - only available in clone bots

@Client.on_callback_query(filters.regex("^random_files$"))
async def handle_random_files(client: Client, query: CallbackQuery):
    """Handle random files callback"""
    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is mother bot
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("🎲 **Random Files**\n\nRandom file features are disabled in the mother bot. This functionality is only available in clone bots.")
            return

        # Check if feature is enabled for this clone
        from bot.plugins.clone_random_files import check_clone_feature_enabled
        if not await check_clone_feature_enabled(client, 'random_button'):
            await query.edit_message_text("🎲 **Random Files**\n\nThis feature has been disabled by the admin.")
            return

        # Get clone ID and show random files
        clone_id = bot_token.split(':')[0]
        
        from bot.database.mongo_db import get_random_files
        files = await get_random_files(limit=10, clone_id=clone_id)
        
        if not files:
            await query.edit_message_text("🎲 **Random Files**\n\n❌ No files found in database. Index some files first.")
            return
        
        text = "🎲 **Random Files**\n\n"
        text += f"Found {len(files)} random files:\n\n"
        
        from bot.plugins.clone_random_files import format_file_text, create_file_buttons
        if files:
            text += format_file_text(files[0])
        
        buttons = create_file_buttons(files)
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in random files handler: {e}")
        try:
            await query.answer("❌ Error loading random files.", show_alert=True)
        except:
            pass

@Client.on_callback_query(filters.regex("^recent_files$"))
async def handle_recent_files(client: Client, query: CallbackQuery):
    """Handle recent files callback"""
    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is mother bot
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("🆕 **Recent Files**\n\nRecent file features are disabled in the mother bot. This functionality is only available in clone bots.")
            return

        # Check if feature is enabled for this clone
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or not clone_data.get('recent_mode', False):
            await query.edit_message_text(
                "❌ **Recent Files Disabled**\n\n"
                "This feature has been disabled by the bot admin.\n\n"
                "Contact the bot administrator if you need access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return

        # Check force subscription first
        from bot.utils import handle_force_sub
        if await handle_force_sub(client, query.message):
            return

        # Check command limit for non-admin users
        user_id = query.from_user.id

        # Skip command limit check for clone admin
        if clone_data.get('admin_id') != user_id:
            from bot.utils.command_verification import check_command_limit, use_command
            from bot.database.premium_db import is_premium_user

            needs_verification, remaining = await check_command_limit(user_id, client)
            is_premium = await is_premium_user(user_id)

            if needs_verification and not is_premium:
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                    [InlineKeyboardButton("💎 Buy Premium", callback_data="show_premium_plans")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
                await query.edit_message_text(
                    "🔐 **Command Limit Reached!**\n\n"
                    "You've used all your free commands. Please verify to get more commands or upgrade to Premium for unlimited access!",
                    reply_markup=buttons
                )
                return

            # Use command if not premium
            if not is_premium and not await use_command(user_id, client):
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                    [InlineKeyboardButton("💎 Buy Premium", callback_data="show_premium_plans")]
                ])
                await query.edit_message_text(
                    "🔐 **Command Limit Reached!**\n\nPlease verify to get more commands or upgrade to Premium!",
                    reply_markup=buttons
                )
                return

        # Get recent files from database
        from bot.database import get_recent_files

        try:
            files = await get_recent_files(limit=10)

            if not files:
                await query.edit_message_text(
                    "📁 **No Recent Files**\n\n"
                    "No recent files are available in the database yet.\n"
                    "Files will appear here once they are added to the bot.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                    ])
                )
                return

            # Format files for display
            text = "🆕 **Recent Files**\n\n"

            buttons = []
            for i, file_data in enumerate(files[:5], 1):  # Show first 5 files
                file_name = file_data.get('file_name', 'Unknown File')
                file_id = str(file_data.get('_id', ''))

                # Truncate long file names
                if len(file_name) > 35:
                    display_name = file_name[:32] + "..."
                else:
                    display_name = file_name

                text += f"{i}. `{display_name}`\n"

                # Add download button
                buttons.append([InlineKeyboardButton(
                    f"📥 {display_name}", 
                    callback_data=f"file_{file_id}"
                )])

            # Add navigation buttons
            nav_buttons = []
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh Recent", callback_data="recent_files"))
            nav_buttons.append(InlineKeyboardButton("📊 My Stats", callback_data="my_stats"))

            buttons.append(nav_buttons)
            buttons.append([InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")])

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as db_error:
            logger.error(f"Database error in recent files: {db_error}")
            await query.edit_message_text(
                "❌ **Database Error**\n\n"
                "Unable to fetch recent files at the moment.\n"
                "Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="recent_files")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in recent files handler: {e}")
        try:
            await query.answer("❌ Error loading recent files.", show_alert=True)
        except:
            pass

@Client.on_callback_query(filters.regex("^popular_files$"))
async def handle_popular_files(client: Client, query: CallbackQuery):
    """Handle popular files callback"""
    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is mother bot  
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("🔥 **Most Popular Files**\n\nPopular file features are disabled in the mother bot. This functionality is only available in clone bots.")
            return

        # Check if feature is enabled for this clone
        from bot.plugins.clone_admin_settings import is_feature_enabled_for_user
        if not await is_feature_enabled_for_user(client, 'popular_mode'):
            await query.edit_message_text("🔥 **Popular Files**\n\nThis feature has been disabled by the admin.")
            return

        # Feature is enabled - show popular files
        await query.edit_message_text("🔥 **Most Popular Files**\n\nShowing most popular files...")

    except Exception as e:
        logger.error(f"Error in popular files handler: {e}")
        try:
            await query.answer("❌ Error loading popular files.", show_alert=True)
        except:
            pass

@Client.on_callback_query(filters.regex("^search_files$"))
async def handle_search_files(client: Client, query: CallbackQuery):
    """Handle search files callback"""
    await query.answer()
    await query.edit_message_text("🔍 **Search Files**\n\nSearch functionality has been removed from clone bots. Use the available file browsing options instead.")

# Handle clone settings panel specifically with higher priority
@Client.on_callback_query(filters.regex("^clone_settings_panel$"), group=-1)
async def handle_clone_settings_panel(client: Client, query: CallbackQuery):
    """Handle clone settings panel callback specifically"""
    user_id = query.from_user.id
    debug_print(f"DEBUG: Clone settings panel callback from user {user_id}")

    # Check if this is a clone bot
    is_clone, bot_token = await is_clone_bot_instance_async(client)
    if not is_clone:
        await query.answer("❌ Settings not available in this bot.", show_alert=True)
        return

    try:
        # Verify user is clone admin
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data:
            await query.answer("❌ Clone configuration not found.", show_alert=True)
            return

        if clone_data.get('admin_id') != user_id:
            await query.answer("❌ Only clone admin can access settings.", show_alert=True)
            return

        # Load clone settings
        from bot.plugins.clone_admin_settings import clone_settings_command

        # Convert query to message-like object
        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
            async def reply_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)
            async def edit_message_text(self, text, reply_markup=None):
                await query.edit_message_text(text, reply_markup=reply_markup)

        fake_message = FakeMessage(query)
        await clone_settings_command(client, fake_message)

    except Exception as e:
        debug_print(f"Error handling clone settings: {e}")
        await query.answer("❌ Error loading settings panel.", show_alert=True)

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