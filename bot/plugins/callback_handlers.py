
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

# Approval callbacks are now handled by clone_approval.py handlers

# View request details handler
@Client.on_callback_query(filters.regex("^view_request:"), group=CALLBACK_PRIORITIES["approval"])
async def handle_view_request_details(client: Client, query: CallbackQuery):
    """Handle viewing request details"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
        
    request_id = query.data.split(":", 1)[1]
    
    try:
        from bot.database.clone_db import get_clone_request_by_id
        request = await get_clone_request_by_id(request_id)
        
        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return
        
        # Format request details
        masked_token = f"{request['bot_token'][:8]}...{request['bot_token'][-4:]}"
        plan_details = request.get('plan_details', {})
        plan_name = plan_details.get('name', request.get('plan', 'monthly'))
        
        text = f"📋 **Clone Request Details**\n\n"
        text += f"🆔 **Request ID:** `{request_id}`\n"
        text += f"👤 **User ID:** `{request['user_id']}`\n"
        text += f"🤖 **Bot Username:** @{request.get('bot_username', 'Unknown')}\n"
        text += f"🔑 **Bot Token:** `{masked_token}`\n"
        text += f"🗄️ **Database URL:** `{request['mongodb_url'][:30]}...`\n"
        text += f"💰 **Plan:** {plan_name.title()}\n"
        text += f"📅 **Created:** {request['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n"
        text += f"⚡ **Status:** {request['status'].title()}\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_request:{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_request:{request_id}")
            ],
            [InlineKeyboardButton("🔙 Back to Pending", callback_data="mother_pending_requests")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        print(f"ERROR: Error viewing request details: {e}")
        await query.answer("❌ Error loading request details!", show_alert=True)

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
@Client.on_callback_query(filters.regex("^(about|help|my_stats|close)$"), group=CALLBACK_PRIORITIES["general"])
async def general_callback_handler(client: Client, query: CallbackQuery):
    """Handle general purpose callbacks"""
    print(f"DEBUG: General callback - {query.data} from user {query.from_user.id}")
    
    callback_data = query.data
    
    if callback_data == "about":
        from bot.plugins.callback import about_callback
        await about_callback(client, query)
    elif callback_data == "help":
        await query.edit_message_text(
            "❓ **Help & Support**\n\n"
            "This is a file sharing bot with clone management capabilities.\n\n"
            "**For Users:**\n"
            "• Send files to get sharing links\n"
            "• Use /search to find files\n"
            "• Use /premium for premium features\n\n"
            "**For Admins:**\n"
            "• Use /admin for admin panel\n"
            "• Use /createclone to create new clones\n"
            "• Use /requestclone to request a clone",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="start")]
            ])
        )
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

# Debug callback for unhandled cases
@Client.on_callback_query(filters.regex(".*"), group=CALLBACK_PRIORITIES["catchall"])
async def debug_unhandled_callbacks(client: Client, query: CallbackQuery):
    """Debug handler for unhandled callbacks"""
    callback_data = query.data
    
    print(f"⚠️ UNHANDLED CALLBACK: {callback_data} from user {query.from_user.id}")
    
    # Don't respond to avoid conflicts, just log
    pass
