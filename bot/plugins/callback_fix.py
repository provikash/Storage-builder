from bot.utils.command_verification import check_command_limit, use_command
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config

@Client.on_callback_query(filters.regex(".*"), group=99)
async def handle_all_callbacks(client: Client, query: CallbackQuery):
    """Catch-all handler for unhandled callbacks - lowest priority"""
    callback_data = query.data
    
    # Skip if already handled by other handlers
    handled_patterns = [
        "mother_", "clone_", "back_to_", "manage_", "start_", "stop_",
        "verify_", "deactivate_", "extend_", "toggle_", "settings_",
        "subscription_", "statistics_", "global_", "force_", "request_",
        "approve_request", "reject_request", "rand_", "about", "help",
        "close", "get_token", "show_premium_plans", "buy_premium",
        "begin_step1_plan", "select_plan:", "step2_bot_token", "step3_db_url",
        "cancel_creation", "database_help", "admin_panel", "create_clone_button"
    ]
    
    if any(callback_data.startswith(pattern) for pattern in handled_patterns):
        return
    
    # Handle unknown callbacks
    if callback_data == "help":
        await query.edit_message_text(
            "❓ **Help & Support**\n\n"
            "This is a file sharing bot with clone management capabilities.\n\n"
            "**For Users:**\n"
            "• Send files to get sharing links\n"
            "• Use /search to find files\n"
            "• Use /premium for premium features\n\n"
            "**For Admins:**\n"
            "• Use /motheradmin for admin panel\n"
            "• Use /createclone to create new clones\n"
            "• Use /cloneadmin for clone management",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="start")]
            ])
        )
    
    elif callback_data == "about":
        await query.edit_message_text(
            "ℹ️ **About This Bot**\n\n"
            "🤖 **Mother Bot + Clone System**\n"
            "Advanced file sharing bot with multi-instance support\n\n"
            "✨ **Features:**\n"
            "• Secure file storage\n"
            "• Clone bot creation\n"
            "• Subscription management\n"
            "• Advanced admin controls\n\n"
            "💡 **Powered by:** Pyrogram & MongoDB\n"
            "🔧 **Version:** 2.0.0",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="start")]
            ])
        )
    
    elif callback_data == "start":
        # Redirect to main start message
        from bot.plugins.start_handler import start_handler
        await start_handler(client, query.message)
    
    elif callback_data.startswith("close"):
        try:
            await query.message.delete()
        except:
            await query.edit_message_text("✅ Session closed.")
    
    elif callback_data.startswith("select_plan:") or callback_data == "begin_step1_plan":
        # Redirect to clone creation handler
        from bot.plugins.step_clone_creation import clone_creation_callback_handler
        await clone_creation_callback_handler(client, query)
    
    else:
        # Unknown callback
        await query.answer(
            f"⚠️ Unknown action: {callback_data[:20]}...\n"
            "This feature may not be implemented yet.",
            show_alert=True
        )
        
        # Log unknown callbacks for debugging
        print(f"🔍 Unhandled callback: {callback_data} from user {query.from_user.id}")
