
"""
Reusable UI builders for keyboards and messages
"""
from typing import Dict, Any, Optional, List
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Constants for callback data
CALLBACK_DATA = {
    'RANDOM_FILES': 'random_files',
    'POPULAR_FILES': 'popular_files',
    'SETTINGS': 'clone_settings_panel',
    'BACK_TO_START': 'back_to_start',
    'USER_PROFILE': 'user_profile',
    'ADD_BALANCE': 'add_balance',
    'ABOUT': 'about_bot',
    'HELP': 'help_menu'
}

def build_clone_settings_panel(clone_data: Dict[str, Any], user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Build clone settings panel text and keyboard"""
    show_random = clone_data.get('random_mode', True)
    show_recent = clone_data.get('recent_mode', True)
    show_popular = clone_data.get('popular_mode', True)
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
            InlineKeyboardButton("🔙 Back to Home", callback_data=CALLBACK_DATA['BACK_TO_START'])
        ]
    ])
    
    return text, buttons

def build_clone_start_menu(clone_data: Optional[Dict[str, Any]], user_id: int, user_name: str, balance: float) -> tuple[str, InlineKeyboardMarkup]:
    """Build clone bot start menu"""
    text = f"🤖 **Welcome {user_name}!**\n\n"
    text += f"📁 **Your Personal File Bot** with secure sharing and search.\n\n"
    text += f"💰 Balance: ${balance:.2f}\n\n"
    text += f"🎯 Choose an option below:"
    
    start_buttons = []
    
    # Admin settings button
    if clone_data and clone_data.get('admin_id') == user_id:
        start_buttons.append([InlineKeyboardButton("⚙️ Settings", callback_data=CALLBACK_DATA['SETTINGS'])])
    
    # Feature buttons based on clone settings
    show_random = clone_data.get('random_mode', True) if clone_data else True
    show_popular = clone_data.get('popular_mode', True) if clone_data else True
    
    file_buttons = []
    
    # File mode buttons
    mode_row = []
    if show_random:
        mode_row.append(InlineKeyboardButton("🎲 Random Files", callback_data=CALLBACK_DATA['RANDOM_FILES']))
    if show_popular:
        mode_row.append(InlineKeyboardButton("🔥 Popular Files", callback_data=CALLBACK_DATA['POPULAR_FILES']))
    
    if mode_row:
        file_buttons.append(mode_row)
    
    # User actions
    file_buttons.append([
        InlineKeyboardButton("👤 My Profile", callback_data=CALLBACK_DATA['USER_PROFILE']),
        InlineKeyboardButton("💰 Add Balance", callback_data=CALLBACK_DATA['ADD_BALANCE'])
    ])
    
    # Add admin buttons if any
    file_buttons.extend(start_buttons)
    
    # Help and about
    file_buttons.append([
        InlineKeyboardButton("ℹ️ About", callback_data=CALLBACK_DATA['ABOUT']),
        InlineKeyboardButton("❓ Help", callback_data=CALLBACK_DATA['HELP'])
    ])
    
    return text, InlineKeyboardMarkup(file_buttons)

def build_feature_disabled_message(feature_name: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build message for disabled features"""
    text = f"❌ **{feature_name} Disabled**\n\n"
    text += "This feature has been disabled by the bot admin.\n\n"
    text += "Contact the bot administrator if you need access."
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Home", callback_data=CALLBACK_DATA['BACK_TO_START'])]
    ])
    
    return text, buttons

def build_mother_bot_feature_message(feature_name: str) -> str:
    """Build message for features not available in mother bot"""
    return (f"📁 **{feature_name}**\n\n"
            f"{feature_name} features are disabled in the mother bot. "
            f"This functionality is only available in clone bots.")
