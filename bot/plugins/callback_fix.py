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
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER
import traceback

logger = LOGGER(__name__)

# Emergency callback handlers with highest priority to catch button issues
@Client.on_callback_query(filters.regex("^(clone_settings_panel|random_files|recent_files|popular_files)$"), group=-10)
async def emergency_callback_handler(client: Client, query: CallbackQuery):
    """Emergency handler for non-responsive buttons"""
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"🚨 EMERGENCY HANDLER: {callback_data} from user {user_id}")
    print(f"🚨 EMERGENCY HANDLER: {callback_data} from user {user_id}")
    
    try:
        await query.answer()
        
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        
        if callback_data == "clone_settings_panel":
            # Handle settings panel
            if bot_token == Config.BOT_TOKEN:
                await query.edit_message_text("❌ Settings panel is only available in clone bots!")
                return
                
            # Get clone data and verify admin
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)
            
            if not clone_data:
                await query.edit_message_text("❌ Clone configuration not found!")
                return
                
            stored_admin_id = clone_data.get('admin_id')
            
            if int(user_id) != int(stored_admin_id):
                await query.edit_message_text("❌ Only clone admin can access settings!")
                return
                
            # Create settings panel directly
            show_random = clone_data.get('random_mode', False)
            show_recent = clone_data.get('recent_mode', False) 
            show_popular = clone_data.get('popular_mode', False)
            force_join = clone_data.get('force_join_enabled', False)
            
            text = f"⚙️ **Clone Bot Settings**\n\n"
            text += f"🔧 **Configuration Panel**\n"
            text += f"Manage your clone bot's features and behavior.\n\n"
            text += f"📋 **Current Settings:**\n"
            text += f"• 🎲 Random Files: {'✅ Enabled' if show_random else '❌ Disabled'}\n"
            text += f"• 🆕 Recent Files: {'✅ Enabled' if show_recent else '❌ Disabled'}\n"
            text += f"• 🔥 Popular Files: {'✅ Enabled' if show_popular else '❌ Disabled'}\n"
            text += f"• 🔐 Force Join: {'✅ Enabled' if force_join else '❌ Disabled'}\n\n"
            text += f"⚡ **Quick Actions:**"

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🎲 Random: {'✅' if show_random else '❌'}", callback_data="clone_toggle_random"),
                    InlineKeyboardButton(f"🆕 Recent: {'✅' if show_recent else '❌'}", callback_data="clone_toggle_recent")
                ],
                [
                    InlineKeyboardButton(f"🔥 Popular: {'✅' if show_popular else '❌'}", callback_data="clone_toggle_popular"),
                    InlineKeyboardButton(f"🔐 Force Join: {'✅' if force_join else '❌'}", callback_data="clone_toggle_force_join")
                ],
                [
                    InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_verification_mode"),
                    InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener_config")
                ],
                [
                    InlineKeyboardButton("📋 Force Channels", callback_data="clone_force_channels_list"),
                    InlineKeyboardButton("🔧 Advanced Settings", callback_data="clone_advanced_settings")
                ],
                [
                    InlineKeyboardButton("🔍 Debug Settings", callback_data="clone_debug_settings"),
                    InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
                ]
            ])
            
            await query.edit_message_text(text, reply_markup=buttons)
            return
            
        elif callback_data in ["random_files", "recent_files", "popular_files"]:
            # Handle file callbacks
            if bot_token == Config.BOT_TOKEN:
                feature_name = callback_data.replace('_files', '').replace('_', ' ').title()
                await query.edit_message_text(f"📁 **{feature_name} Files**\n\n{feature_name} file features are disabled in the mother bot. This functionality is only available in clone bots.")
                return
                
            # Get clone data to check feature status
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            if not clone_data:
                await query.edit_message_text("❌ Clone configuration not found!")
                return

            # Check feature enablement
            feature_enabled = True
            feature_display_name = ""
            
            if callback_data == "random_files":
                feature_enabled = clone_data.get('random_mode', True)
                feature_display_name = "Random Files"
            elif callback_data == "recent_files":
                feature_enabled = clone_data.get('recent_mode', True)
                feature_display_name = "Recent Files"
            elif callback_data == "popular_files":
                feature_enabled = clone_data.get('popular_mode', True)
                feature_display_name = "Popular Files"

            if not feature_enabled:
                await query.edit_message_text(
                    f"❌ **{feature_display_name} Disabled**\n\n"
                    "This feature has been disabled by the bot admin.\n\n"
                    "Contact the bot administrator if you need access.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                    ])
                )
                return

            # Check force subscription
            from bot.utils import handle_force_sub
            if await handle_force_sub(client, query.message):
                return

            # Route to search handlers
            try:
                if callback_data == "random_files":
                    from bot.plugins.search import handle_random_files
                    await handle_random_files(client, query.message, is_callback=True)
                elif callback_data == "recent_files":
                    from bot.plugins.search import handle_recent_files_direct
                    await handle_recent_files_direct(client, query.message, is_callback=True)
                elif callback_data == "popular_files":
                    from bot.plugins.search import show_popular_files
                    await show_popular_files(client, query)
            except Exception as handler_error:
                logger.error(f"Error in {callback_data} handler: {handler_error}")
                await query.edit_message_text(f"❌ Error loading {feature_display_name.lower()}. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in emergency callback handler: {e}")
        traceback.print_exc()
        try:
            await query.answer("❌ Button error. Please try again.", show_alert=True)
        except:
            pass
