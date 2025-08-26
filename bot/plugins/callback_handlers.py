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

# Admin Panel Callbacks (Priority 1)
@Client.on_callback_query(filters.regex("^(mother_|clone_|back_to_|refresh_dashboard)"), group=CALLBACK_PRIORITIES["admin"])
async def admin_callback_router(client: Client, query: CallbackQuery):
    """Route admin callbacks to appropriate handlers"""
    print(f"DEBUG: Admin callback router - {query.data} from user {query.from_user.id}")

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
        print(f"DEBUG: Error in admin callback router: {e}")
        if not query.data.startswith("back_to_") and query.data != "refresh_dashboard":
            await query.answer("❌ Error processing request!", show_alert=True)

# Handle start message admin buttons
@Client.on_callback_query(filters.regex("^(admin_panel|start|create_clone_button)$"), group=CALLBACK_PRIORITIES["admin"])
async def handle_start_admin_buttons(client: Client, query: CallbackQuery):
    """Handle admin panel and start buttons from start message"""
    user_id = query.from_user.id
    print(f"DEBUG: Start admin button - {query.data} from user {user_id}")

    if query.data == "admin_panel":
        # Check admin permissions
        if not is_mother_admin(user_id):
            return await query.answer("❌ Unauthorized access!", show_alert=True)

        # Route to admin panel
        from bot.plugins.admin_panel import mother_admin_panel
        await mother_admin_panel(client, query)

    elif query.data == "create_clone_button":
        # Handle create clone button - route to clone creation
        from bot.plugins.step_clone_creation import start_clone_creation_callback
        # Convert to proper callback format
        query.data = "start_clone_creation"
        await start_clone_creation_callback(client, query)

    elif query.data == "start":
        # Handle start button - show start message
        from bot.plugins.start_handler import start_command
        # Convert callback to message-like object
        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
            async def reply_text(self, text, reply_markup=None, **kwargs):
                await query.edit_message_text(text, reply_markup=reply_markup)

        fake_message = FakeMessage(query)
        await start_command(client, fake_message)

# Handle quick approval/rejection callbacks
@Client.on_callback_query(filters.regex("^(quick_approve|quick_reject|view_request):"), group=CALLBACK_PRIORITIES["approval"])
async def handle_quick_actions(client: Client, query: CallbackQuery):
    """Handle quick approval, rejection, and view request actions"""
    user_id = query.from_user.id
    print(f"DEBUG: Quick action callback - {query.data} from user {user_id}")

    # Check admin permissions
    if not is_mother_admin(user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

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
        print(f"ERROR: Error in quick action callback: {e}")
        await query.answer("❌ Error processing request!", show_alert=True)

async def handle_view_request_details(client: Client, query: CallbackQuery, request_id: str):
    """Show detailed view of a clone request"""
    try:
        from bot.database.clone_db import get_clone_request_by_id
        request = await get_clone_request_by_id(request_id)

        if not request:
            return await query.answer("❌ Request not found!", show_alert=True)

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
        print(f"ERROR: Error viewing request details: {e}")
        await query.answer("❌ Error loading request details!", show_alert=True)

# Mother Bot callback handlers
@Client.on_callback_query(filters.regex("^(mother_|back_to_mother_panel|admin_)"), group=CALLBACK_PRIORITIES["admin"])
async def mother_admin_callback_router(client: Client, query: CallbackQuery):
    """Route Mother Bot admin callbacks"""
    user_id = query.from_user.id
    print(f"DEBUG: Admin callback router - {query.data} from user {user_id}")

    # Let specific handlers handle their callbacks
    pass

# Add handlers for simplified clone creation flow
# Assuming these functions (step2_bot_token, start_clone_creation, cancel_creation, database_help) are defined elsewhere
# and creation_sessions is a global dictionary to store session data.

# Dummy function for step2_bot_token for context
async def step2_bot_token(client, query):
    """Placeholder for the actual step 2 handler"""
    user_id = query.from_user.id
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
async def back_to_step3_callback(client, query):
    """Handle back to step 3"""
    await query.answer()

    user_id = query.from_user.id
    session = creation_sessions.get(user_id)

    if not session:
        return await query.edit_message_text(
            "❌ Session expired! Please start over.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]
            ])
        )

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

# Placeholder for other callback handlers (Premium, Search, General, etc.)
# These are kept from the original code to ensure completeness.

# Premium System Callbacks (Priority 3)
@Client.on_callback_query(filters.regex("^(show_premium_plans|buy_premium)"), group=CALLBACK_PRIORITIES["premium"])
async def premium_callback_handler(client: Client, query: CallbackQuery):
    """Handle premium-related callbacks"""
    print(f"DEBUG: Premium callback - {query.data} from user {query.from_user.id}")

    # Import from existing callback handler
    if query.data == "show_premium_plans":
        from bot.plugins.callback import show_premium_callback
        await show_premium_callback(client, query)
    elif query.data.startswith("buy_premium"):
        from bot.plugins.callback import buy_premium_callback
        await buy_premium_callback(client, query)

# Search & Random Callbacks (Priority 4)
@Client.on_callback_query(filters.regex("^(rand_|execute_rand|get_token)"), group=CALLBACK_PRIORITIES["search"])
async def search_callback_handler(client: Client, query: CallbackQuery):
    """Handle search and random file callbacks"""
    print(f"DEBUG: Search callback - {query.data} from user {query.from_user.id}")

    callback_data = query.data

    # Route to existing handlers
    if callback_data == "execute_rand":
        from bot.plugins.callback import execute_rand_callback
        await execute_rand_callback(client, query)
    elif callback_data == "rand_recent":
        from bot.plugins.callback import recent_files_callback
        await recent_files_callback(client, query)
    elif callback_data == "rand_popular":
        from bot.plugins.callback import popular_files_callback
        await popular_files_callback(client, query)
    elif callback_data == "rand_stats":
        from bot.plugins.callback import rand_stats_callback
        await rand_stats_callback(client, query)
    elif callback_data == "rand_new":
        from bot.plugins.callback import new_random_callback
        await new_random_callback(client, query)
    elif callback_data == "get_token":
        from bot.plugins.callback import get_token_callback
        await get_token_callback(client, query)

# General Callbacks (Priority 5)
@Client.on_callback_query(filters.regex("^(about|help|my_stats|close|about_bot|help_menu|user_profile|transaction_history|back_to_start|add_balance|manage_my_clone)$"), group=CALLBACK_PRIORITIES["general"])
async def general_callback_handler(client: Client, query: CallbackQuery):
    """Handle general purpose callbacks"""
    print(f"DEBUG: General callback - {query.data} from user {query.from_user.id}")

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
        from bot.plugins.start_handler import start_command
        # Convert callback to message-like object
        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
            async def reply_text(self, text, reply_markup=None, **kwargs):
                await query.edit_message_text(text, reply_markup=reply_markup)

        fake_message = FakeMessage(query)
        await start_command(client, fake_message)
    elif callback_data == "add_balance":
        # Handle add balance
        from bot.plugins.balance_management import show_balance_options
        await show_balance_options(client, query)
    elif callback_data == "manage_my_clone":
        # Handle manage clone
        from bot.plugins.clone_management import manage_user_clone
        await manage_user_clone(client, query)
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
    print(f"DEBUG: Feature toggle callback - {query.data} from user {query.from_user.id}")

    # Import from admin panel
    from bot.plugins.admin_panel import toggle_feature_handler
    await toggle_feature_handler(client, query)

# Clone creation callbacks (Priority 2)
@Client.on_callback_query(filters.regex("^(start_clone_creation|begin_step1_plan|select_plan:|creation_help|token_help|database_help|back_to_step3|confirm_final_creation|cancel_creation|insufficient_balance)"), group=CALLBACK_PRIORITIES["approval"])
async def clone_creation_callback_handler(client: Client, query: CallbackQuery):
    """Handle clone creation callbacks"""
    print(f"DEBUG: Clone creation callback - {query.data} from user {query.from_user.id}")
    
    # Import handlers from step_clone_creation
    from bot.plugins import step_clone_creation
    
    # Route to appropriate handler based on callback data
    if query.data == "start_clone_creation":
        await step_clone_creation.start_clone_creation_callback(client, query)
    elif query.data == "begin_step1_plan":
        await step_clone_creation.step1_choose_plan(client, query)
    elif query.data.startswith("select_plan:"):
        await step_clone_creation.step2_bot_token(client, query)
    elif query.data == "creation_help":
        await step_clone_creation.creation_help_callback(client, query)
    elif query.data == "token_help":
        await step_clone_creation.token_help_callback(client, query)
    elif query.data == "database_help":
        await step_clone_creation.database_help_callback(client, query)
    elif query.data == "back_to_step3":
        await back_to_step3_callback(client, query)
    elif query.data == "confirm_final_creation":
        await step_clone_creation.handle_final_confirmation(client, query)
    elif query.data == "cancel_creation":
        await step_clone_creation.handle_creation_cancellation(client, query)
    elif query.data == "insufficient_balance":
        await step_clone_creation.handle_insufficient_balance(client, query)

# Debug callback for unhandled cases
@Client.on_callback_query(filters.regex(".*"), group=CALLBACK_PRIORITIES["catchall"])
async def debug_unhandled_callbacks(client: Client, query: CallbackQuery):
    """Debug handler for unhandled callbacks"""
    callback_data = query.data

    print(f"⚠️ UNHANDLED CALLBACK: {callback_data} from user {query.from_user.id}")

    # Don't respond to avoid conflicts, just log
    pass