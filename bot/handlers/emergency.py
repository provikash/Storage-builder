
"""
Emergency callback handlers for critical button failures
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.utils.permissions import require_clone_admin, is_clone_bot_instance
from bot.utils.ui_builders import build_clone_settings_panel, build_clone_start_menu, CALLBACK_DATA
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Emergency callback handlers with highest priority to catch button issues
@Client.on_callback_query(filters.regex("^(clone_settings_panel|settings|back_to_start)$"), group=-10)
@safe_callback_handler
async def emergency_callback_handler(client: Client, query: CallbackQuery):
    """Emergency handler for critical non-responsive buttons"""
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"🚨 EMERGENCY HANDLER: {callback_data} from user {user_id}")
    
    await query.answer()
    
    is_clone, bot_token = is_clone_bot_instance(client)
    
    if callback_data in ["clone_settings_panel", "settings"]:
        # Handle settings panel
        if not is_clone:
            await query.edit_message_text("❌ Settings panel is only available in clone bots!")
            return
            
        # Get clone data and verify admin
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        
        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found!")
            return
            
        if int(user_id) != int(clone_data.get('admin_id')):
            await query.edit_message_text("❌ Only clone admin can access settings!")
            return
            
        text, buttons = build_clone_settings_panel(clone_data, user_id)
        await query.edit_message_text(text, reply_markup=buttons)
        
    elif callback_data == "back_to_start":
        # Handle back to start
        if is_clone:
            try:
                from bot.database.clone_db import get_clone_by_bot_token
                from bot.database.balance_db import get_user_balance
                
                clone_data = await get_clone_by_bot_token(bot_token)
                balance = await get_user_balance(user_id)
                
                text, buttons = build_clone_start_menu(
                    clone_data, 
                    user_id, 
                    query.from_user.first_name, 
                    balance
                )
                await query.edit_message_text(text, reply_markup=buttons)
                
            except Exception as e:
                logger.error(f"Error in clone back_to_start: {e}")
                await query.answer("❌ Error loading clone start menu", show_alert=True)
        else:
            # For mother bot, delegate to start handler
            try:
                from bot.plugins.start_handler import back_to_start_callback
                await back_to_start_callback(client, query)
            except Exception as e:
                logger.error(f"Error in mother bot back_to_start: {e}")
                await query.answer("❌ Error returning to start. Please use /start command.")
