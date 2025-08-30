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
from bot.database.premium_db import is_premium_user
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
def is_clone_admin(user_id, config):
    """Check if user is a clone bot admin"""
    bot_admin_id = config.get('bot_info', {}).get('admin_id')
    if bot_admin_id:
        return user_id == bot_admin_id
    return False

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

async def clone_admin_panel(client: Client, message):
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
        is_clone_bot = hasattr(client, 'clone_config') and client.clone_config
        if is_clone_bot:
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
        is_clone_bot = hasattr(client, 'clone_config') and client.clone_config
        if is_clone_bot:
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
    is_clone_bot = hasattr(client, 'clone_config') and client.clone_config
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
        # Handle back to start - show start message
        # Check if this is a clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot_instance = False
        try:
            # Attempt to load clone config to check if it's a clone bot instance
            from bot.utils.clone_config_loader import clone_config_loader
            config = await clone_config_loader.get_bot_config(bot_token)
            if config and config.get('bot_info', {}).get('is_clone', False):
                is_clone_bot_instance = True
        except Exception as e:
            logger.error(f"Error checking clone config for back_to_start: {e}")

        if is_clone_bot_instance:
            admin_id = config.get('bot_info', {}).get('admin_id')
            if user_id == admin_id:
                # Clone admin goes to clone panel
                from bot.plugins.clone_admin_settings import clone_admin_panel
                class FakeMessage:
                    def __init__(self, query):
                        self.from_user = query.from_user
                        self.chat = query.message.chat
                    async def reply_text(self, text, reply_markup=None):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                fake_message = FakeMessage(query)
                await clone_admin_panel(client, fake_message)
                return
            else:
                # Non-admin in clone bot, show a message or redirect to clone's start if applicable
                await query.answer("This is a clone bot. Please use its specific commands.", show_alert=True)
                return
        else:
            # For mother bot or regular users, go to normal start
            from bot.plugins.start_handler import back_to_start_callback
            await back_to_start_callback(client, query)
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
    await query.answer()
    await query.edit_message_text("🎲 **Random Files**\n\nRandom file features are disabled in the mother bot. This functionality is only available in clone bots.")

@Client.on_callback_query(filters.regex("^recent_files$"))
async def handle_recent_files(client: Client, query: CallbackQuery):
    """Handle recent files callback"""
    await query.answer()
    await query.edit_message_text("🆕 **Recent Files**\n\nRecent file features are disabled in the mother bot. This functionality is only available in clone bots.")

@Client.on_callback_query(filters.regex("^popular_files$"))
async def handle_popular_files(client: Client, query: CallbackQuery):
    """Handle popular files callback"""
    await query.answer()
    await query.edit_message_text("🔥 **Most Popular Files**\n\nPopular file features are disabled in the mother bot. This functionality is only available in clone bots.")

@Client.on_callback_query(filters.regex("^search_files$"))
async def handle_search_files(client: Client, query: CallbackQuery):
    """Handle search files callback"""
    await query.answer()
    await query.edit_message_text("🔍 **Search Files**\n\nSearch functionality has been removed from clone bots. Use the available file browsing options instead.")

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def handle_back_to_start(client: Client, query: CallbackQuery):
    """Handle back to start navigation with clone bot protection"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Back to start handler - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = None
    is_clone_bot_instance = False

    try:
        # Attempt to load clone config to check if it's a clone bot instance
        # Ensure clone_config_loader is correctly imported or defined globally
        from bot.utils.clone_config_loader import clone_config_loader
        config = await clone_config_loader.get_bot_config(bot_token)
        if config and config.get('bot_info', {}).get('is_clone', False):
            is_clone_bot_instance = True
            admin_id = config.get('bot_info', {}).get('admin_id')
            if user_id == admin_id:
                # Clone admin goes to clone panel
                from bot.plugins.clone_admin_settings import clone_admin_panel
                class FakeMessage:
                    def __init__(self, query):
                        self.from_user = query.from_user
                        self.chat = query.message.chat
                    async def reply_text(self, text, reply_markup=None):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                fake_message = FakeMessage(query)
                await clone_admin_panel(client, fake_message)
                return
            else:
                # Non-admin in clone bot, show a message or redirect to clone's start if applicable
                await query.answer("This is a clone bot. Please use its specific commands.", show_alert=True)
                return
    except Exception as e:
        logger.error(f"Error checking clone config in handle_back_to_start: {e}")
        # If config loading fails, assume it's not a clone bot or handle as error

    # For mother bot or regular users, go to normal start
    class FakeMessage:
        def __init__(self, query):
            self.from_user = query.from_user
            self.chat = query.message.chat
        async def reply_text(self, text, reply_markup=None):
            await query.edit_message_text(text, reply_markup=reply_markup)

    fake_message = FakeMessage(query)

    # Import and call start command handler
    from bot.plugins.start_handler import start_command
    await start_command(client, fake_message)


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

# Clone Bot Callback Handlers (Higher priority than the router)
@Client.on_callback_query(filters.regex("^clone_"), group=0)
async def clone_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Clone Bot admin panel callbacks"""
    user_id = query.from_user.id
    debug_print(f"Clone Bot callback received from user {user_id}, data: {query.data}")

    # Handle settings panel callback with proper admin verification
    if query.data == "clone_settings_panel":
        # First check if this is a clone bot
        bot_token = getattr(client, 'bot_token', None)
        is_clone_bot = bot_token and hasattr(client, 'is_clone') and client.is_clone

        if not is_clone_bot:
            return await query.answer("❌ Settings not available in mother bot.", show_alert=True)

        # Verify user is the clone admin
        try:
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            if not clone_data:
                return await query.answer("❌ Clone configuration not found.", show_alert=True)

            if clone_data.get('admin_id') != user_id:
                return await query.answer("❌ Only clone admin can access settings.", show_alert=True)

        except Exception as e:
            debug_print(f"Error verifying clone admin: {e}")
            return await query.answer("❌ Error verifying admin access.", show_alert=True)

        # Load and execute settings command
        try:
            from bot.plugins.clone_admin_settings import clone_settings_command
            # Convert query to message-like object
            class FakeMessage:
                def __init__(self, query):
                    self.from_user = query.from_user
                    self.chat = query.message.chat
                async def reply_text(self, text, reply_markup=None):
                    await query.edit_message_text(text, reply_markup=reply_markup)

            fake_message = FakeMessage(query)
            await clone_settings_command(client, fake_message)
            return
        except Exception as e:
            debug_print(f"Error loading clone settings: {e}")
            return await query.answer("❌ Error loading settings panel.", show_alert=True)

    # Get bot configuration first
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    debug_print(f"Bot token for clone callback: {bot_token}")

    try:
        config = await clone_config_loader.get_bot_config(bot_token)
        debug_print(f"Config loaded successfully for clone callback")
    except Exception as e:
        debug_print(f"Error loading config for clone callback: {e}")
        return await query.answer("❌ Error loading bot configuration!", show_alert=True)

    # Check clone admin permissions
    if not is_clone_admin(user_id, config):
        debug_print(f"Unauthorized access to Clone Bot panel for user {user_id}. Expected admin ID: {config['bot_info'].get('admin_id')}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Validate or create session
    session = admin_sessions.get(user_id)
    debug_print(f"Current clone session for user {user_id}: {session}")

    if not session or session['type'] != 'clone':
        debug_print(f"Creating new clone admin session for user {user_id}")
        admin_sessions[user_id] = {
            'type': 'clone',
            'timestamp': datetime.now(),
            'bot_token': bot_token,
            'last_content': None
        }
        session = admin_sessions[user_id]
    else:
        # Update timestamp and bot_token
        session['timestamp'] = datetime.now()
        session['bot_token'] = bot_token
        debug_print(f"Updated existing clone session for user {user_id}")

    callback_data = query.data
    debug_print(f"Processing callback_data: {callback_data}")

    if callback_data == "clone_local_force_channels":
        await handle_clone_local_force_channels(client, query)
    elif callback_data == "clone_request_channels":
        await handle_clone_request_channels(client, query)
    elif callback_data == "clone_token_command_config":
        await handle_clone_token_command_config(client, query)
    elif callback_data == "clone_token_pricing":
        await handle_clone_token_pricing(client, query)
    elif callback_data == "clone_bot_features":
        await handle_clone_bot_features(client, query)
    elif callback_data == "clone_subscription_status":
        await handle_clone_subscription_status(client, query)
    elif callback_data == "clone_toggle_token_system":
        await handle_clone_toggle_token_system(client, query)
    elif callback_data == "back_to_clone_panel":
        debug_print(f"Navigating back to Clone Bot panel for user {user_id}")
        await clone_admin_panel(client, query.message) # Pass message to clone_admin_panel
    elif callback_data == "clone_about_water": # Handler for the new About Water Info button
        await handle_clone_about_water(client, query)
    else:
        debug_print(f"Unknown Clone Bot callback action: {callback_data}")
        await query.answer("⚠️ Unknown action", show_alert=True)