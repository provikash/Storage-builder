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
    
    # Handle remaining unknown callbacks
    if callback_data.startswith("close"):
        try:
            await query.message.delete()
        except:
            await query.edit_message_text("✅ Session closed.")
    
    elif callback_data in ["premium_trial", "buy_premium"]:
        await query.answer("💎 Premium features coming soon! Stay tuned.", show_alert=True)
    
    elif callback_data in ["my_stats", "rand_recent", "rand_popular", "rand_stats", "execute_rand"]:
        await query.answer("🔄 This feature is being updated. Try again later.", show_alert=True)
    
    else:
        # Unknown callback - be more informative
        feature_map = {
            "help": "Help menu",
            "about": "About information", 
            "start": "Main menu",
            "premium_info": "Premium features",
            "random_files": "Random file browser",
            "user_profile": "User profile",
            "transaction_history": "Transaction history"
        }
        
        feature_name = feature_map.get(callback_data, callback_data)
        
        await query.answer(
            f"🔄 {feature_name} is loading...\n"
            "If this persists, contact support.",
            show_alert=True
        )
        
        # Log for debugging
        print(f"🔍 Fallback handled: {callback_data} from user {query.from_user.id}")
