
"""
Admin panel callback handlers
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_mother_admin, is_clone_bot_instance
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(admin_panel|bot_management)$"), group=1)
@safe_callback_handler
async def handle_admin_buttons(client: Client, query: CallbackQuery):
    """Handle admin panel and bot management buttons"""
    user_id = query.from_user.id
    callback_data = query.data
    
    is_clone_bot, _ = is_clone_bot_instance(client)
    if is_clone_bot:
        await query.answer("❌ Admin panel not available in clone bots!", show_alert=True)
        return
        
    if callback_data == "admin_panel":
        @require_mother_admin
        async def admin_panel_handler(client: Client, query: CallbackQuery):
            try:
                from bot.plugins.mother_admin import mother_admin_panel
                await mother_admin_panel(client, query)
            except Exception as e:
                await query.answer("❌ Error loading admin panel!", show_alert=True)
                
        await admin_panel_handler(client, query)
        
    elif callback_data == "bot_management":
        @require_mother_admin
        async def bot_management_handler(client: Client, query: CallbackQuery):
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
            
        await bot_management_handler(client, query)
