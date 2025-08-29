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
@Client.on_callback_query(filters.regex("^(start|create_clone_button|create_clone_monthly|create_clone_quarterly|create_clone_semi_annual|create_clone_yearly)$"), group=CALLBACK_PRIORITIES["admin"])
async def handle_start_admin_buttons(client: Client, query: CallbackQuery):
    """Handle admin panel and start buttons from start message"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Start admin button - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

    callback_data = query.data

    if callback_data == "admin_panel":
        # Check admin permissions
        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return

        # Route to admin panel
        from bot.plugins.admin_panel import mother_admin_panel
        await mother_admin_panel(client, query)

    elif callback_data == "create_clone_button":
        # Handle create clone button - route to clone creation
        from bot.plugins.step_clone_creation import start_clone_creation_callback
        # Convert to proper callback format
        query.data = "start_clone_creation"
        await start_clone_creation_callback(client, query)

    elif callback_data.startswith("create_clone_"):
        # Handle direct plan selection callbacks
        plan_mapping = {
            "create_clone_monthly": "monthly",
            "create_clone_quarterly": "quarterly",
            "create_clone_semi_annual": "semi_annual",
            "create_clone_yearly": "yearly"
        }

        plan_id = plan_mapping.get(callback_data)
        if plan_id:
            # Redirect to plan selection with the specific plan
            from bot.plugins.step_clone_creation import select_plan_callback
            query.data = f"select_plan:{plan_id}"
            await select_plan_callback(client, query)

    elif callback_data == "start":
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

# Mother Bot callback handlers
@Client.on_callback_query(filters.regex("^(mother_|back_to_mother_panel|admin_)"), group=CALLBACK_PRIORITIES["admin"])
async def mother_admin_callback_router(client: Client, query: CallbackQuery):
    """Route Mother Bot admin callbacks"""
    user_id = query.from_user.id
    print(f"🔄 DEBUG CALLBACK: Mother Bot admin callback router - '{query.data}' from user {user_id}")
    print(f"🔍 DEBUG CALLBACK: User details - ID: {user_id}, Username: @{query.from_user.username}, First: {query.from_user.first_name}")

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
@Client.on_callback_query(filters.regex("^(about|help|my_stats|close|about_bot|help_menu|user_profile|transaction_history|back_to_start|add_balance|manage_my_clone)$"), group=CALLBACK_PRIORITIES["general"])
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
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.index_db import collection as files_collection
from info import Config
import random
from datetime import datetime, timedelta

@Client.on_callback_query(filters.regex("^random_files$"))
async def handle_random_files(client: Client, query: CallbackQuery):
    """Handle random files callback with proper file fetching"""
    user_id = query.from_user.id

    # Check user permissions
    from bot.database.users import present_user
    user_data = await present_user(user_id)

    if not user_data:
        return await query.answer("❌ Please start the bot first!", show_alert=True)

    # Check if admin (admins have unlimited access)
    from info import Config
    if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
        has_access = True
    else:
        has_tokens = user_data.get('tokens', 0) > 0 or user_data.get('tokens', 0) == -1
        has_access = has_tokens

    if not has_access:
        return await query.answer("❌ You need tokens to access files!", show_alert=True)

    # Get random files from database
    try:
        from bot.database.index_db import collection as files_collection
        from info import Config
        import random

        # First check if we have access to the index channel
        try:
            await client.get_chat(Config.INDEX_CHANNEL_ID)
        except Exception as e:
            return await query.answer("❌ Bot cannot access file storage channel!", show_alert=True)

        # Get random files from database
        random_files = await files_collection.aggregate([
            {"$sample": {"size": 10}}
        ]).to_list(length=10)

        if not random_files:
            return await query.answer("❌ No files found!", show_alert=True)

        # Send files directly to user
        sent_count = 0
        for file_info in random_files[:5]:  # Send only 5 files
            try:
                file_id = file_info.get('file_id')
                message_id = int(file_id) if file_id else None

                if message_id:
                    # Get message from index channel
                    file_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)
                    if file_message and not file_message.empty:
                        # Forward file to user
                        await file_message.copy(chat_id=query.from_user.id)
                        sent_count += 1
            except Exception as e:
                print(f"Error sending file {file_id}: {e}")
                continue

        if sent_count > 0:
            await query.edit_message_text(
                f"✅ Sent {sent_count} random files!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 More Random", callback_data="random_files")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ No files could be sent. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex("^recent_files$"))
async def handle_recent_files(client: Client, query: CallbackQuery):
    """Handle recent files callback"""
    user_id = query.from_user.id

    # Check user permissions
    from bot.database.users import present_user
    user_data = await present_user(user_id)

    if not user_data:
        return await query.answer("❌ Please start the bot first!", show_alert=True)

    # Check if admin (admins have unlimited access)
    from info import Config
    if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
        has_access = True
    else:
        has_tokens = user_data.get('tokens', 0) > 0 or user_data.get('tokens', 0) == -1
        has_access = has_tokens

    if not has_access:
        return await query.answer("❌ You need tokens to access files!", show_alert=True)

    # Get recent files (last 24 hours or latest)
    try:
        from bot.database.index_db import collection as files_collection
        from datetime import datetime, timedelta

        # First check if we have access to the index channel
        try:
            await client.get_chat(Config.INDEX_CHANNEL_ID)
        except Exception as e:
            return await query.answer("❌ Bot cannot access file storage channel!", show_alert=True)

        # Try to get files from last 24 hours
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        recent_files = await files_collection.find({
            "date": {"$gte": twenty_four_hours_ago}
        }).sort("date", -1).limit(10).to_list(length=10)

        if not recent_files:
            # Fallback to latest files if no files in last 24 hours
            recent_files = await files_collection.find({}).sort("_id", -1).limit(10).to_list(length=10)

        if not recent_files:
            return await query.answer("❌ No recent files found!", show_alert=True)

        # Send files directly to user
        sent_count = 0
        for file_info in recent_files[:5]:  # Send only 5 files
            try:
                file_id = file_info.get('file_id')
                message_id = int(file_id) if file_id else None

                if message_id:
                    # Get message from index channel
                    file_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)
                    if file_message and not file_message.empty:
                        # Forward file to user
                        await file_message.copy(chat_id=query.from_user.id)
                        sent_count += 1
            except Exception as e:
                print(f"Error sending recent file {file_id}: {e}")
                continue

        if sent_count > 0:
            await query.edit_message_text(
                f"✅ Sent {sent_count} recent files!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🆕 More Recent", callback_data="recent_files")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ No recent files could be sent. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)

async def handle_popular_files(client: Client, query: CallbackQuery):
    """Handle popular files callback"""
    user_id = query.from_user.id

    # Check user permissions
    from bot.database.users import present_user
    user_data = await present_user(user_id)

    if not user_data:
        return await query.answer("❌ Please start the bot first!", show_alert=True)

    # Check if admin (admins have unlimited access)
    from info import Config
    if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
        has_access = True
    else:
        has_tokens = user_data.get('tokens', 0) > 0 or user_data.get('tokens', 0) == -1
        has_access = has_tokens

    if not has_access:
        return await query.answer("❌ You need tokens to access files!", show_alert=True)

    # Get popular files (by access count)
    try:
        from bot.database.index_db import collection as files_collection

        # First check if we have access to the index channel
        try:
            await client.get_chat(Config.INDEX_CHANNEL_ID)
        except Exception as e:
            return await query.answer("❌ Bot cannot access file storage channel!", show_alert=True)

        # Get popular files sorted by access count
        popular_files = await files_collection.find({
            "access_count": {"$exists": True, "$gt": 0}
        }).sort("access_count", -1).limit(10).to_list(length=10)

        if not popular_files:
            # Fallback to random files if no popular files found
            popular_files = await files_collection.aggregate([
                {"$sample": {"size": 10}}
            ]).to_list(length=10)

        if not popular_files:
            return await query.answer("❌ No popular files found!", show_alert=True)

        # Send files directly to user
        sent_count = 0
        for file_info in popular_files[:5]:  # Send only 5 files
            try:
                file_id = file_info.get('file_id')
                message_id = int(file_id) if file_id else None

                if message_id:
                    # Get message from index channel
                    file_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)
                    if file_message and not file_message.empty:
                        # Forward file to user
                        await file_message.copy(chat_id=query.from_user.id)
                        sent_count += 1
            except Exception as e:
                print(f"Error sending popular file {file_id}: {e}")
                continue

        if sent_count > 0:
            await query.edit_message_text(
                f"✅ Sent {sent_count} popular files!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔥 More Popular", callback_data="popular_files")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ No popular files could be sent. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def handle_back_to_start(client: Client, query: CallbackQuery):
    """Handle back to start callback"""
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