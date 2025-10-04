
"""
Clone Features Program
Handles clone bot feature toggles and management
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_clone_admin
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER

logger = LOGGER(__name__)

class CloneFeaturesProgram:
    """Clone features management program"""
    
    def __init__(self):
        self.name = "Clone Features"
        self.available_features = [
            {"key": "random_mode", "name": "Random Files", "emoji": "🎲"},
            {"key": "recent_mode", "name": "Recent Files", "emoji": "🆕"},
            {"key": "popular_mode", "name": "Popular Files", "emoji": "🔥"},
            {"key": "search_mode", "name": "Search", "emoji": "🔍"}
        ]
    
    async def get_feature_status(self, client: Client, bot_token: str):
        """Get current feature status"""
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        return clone_data if clone_data else {}
    
    async def toggle_feature(self, client: Client, bot_token: str, feature_key: str):
        """Toggle a feature on/off"""
        from bot.database.clone_db import get_clone_by_bot_token, update_clone_setting
        
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return False
        
        current_value = clone_data.get(feature_key, False)
        new_value = not current_value
        
        success = await update_clone_setting(bot_token, feature_key, new_value)
        return success
    
    def register_handlers(self, app: Client):
        """Register feature toggle handlers"""
        
        @app.on_callback_query(filters.regex("^toggle_feature_"))
        @safe_callback_handler
        async def handle_feature_toggle(client: Client, query: CallbackQuery):
            feature_key = query.data.replace("toggle_feature_", "")
            bot_token = getattr(client, 'bot_token', None)
            
            if not bot_token:
                await query.answer("❌ Configuration error", show_alert=True)
                return
            
            success = await self.toggle_feature(client, bot_token, feature_key)
            
            if success:
                await query.answer("✅ Feature toggled successfully")
                # Refresh the panel
                await self.show_features_panel(client, query)
            else:
                await query.answer("❌ Failed to toggle feature", show_alert=True)
    
    async def show_features_panel(self, client: Client, query: CallbackQuery):
        """Show features management panel"""
        bot_token = getattr(client, 'bot_token', None)
        features = await self.get_feature_status(client, bot_token)
        
        text = "🎛️ **Clone Features Management**\n\n"
        text += "Toggle features on/off for your clone bot:\n\n"
        
        buttons = []
        for feature in self.available_features:
            status = "✅" if features.get(feature['key'], False) else "❌"
            text += f"{feature['emoji']} {feature['name']}: {status}\n"
            
            buttons.append([
                InlineKeyboardButton(
                    f"{feature['emoji']} Toggle {feature['name']}", 
                    callback_data=f"toggle_feature_{feature['key']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="clone_admin_panel")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Global instance
clone_features_program = CloneFeaturesProgram()
