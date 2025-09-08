
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(documentation|video_tutorials|compare_plans|premium_trial|refresh_transactions|download_transactions|notification_settings|privacy_settings|security_settings|clone_settings|export_stats|rate_bot|report_bug|suggest_feature)$"))
async def handle_missing_features(client: Client, query: CallbackQuery):
    """Handle callbacks for features not yet implemented"""
    await query.answer()
    
    feature_names = {
        "documentation": "📚 Documentation",
        "video_tutorials": "🎥 Video Tutorials", 
        "compare_plans": "📋 Compare Plans",
        "premium_trial": "🎁 Free Trial",
        "refresh_transactions": "🔄 Refresh History",
        "download_transactions": "📱 Download Report",
        "notification_settings": "🔔 Notifications",
        "privacy_settings": "🔒 Privacy",
        "security_settings": "🔐 Security",
        "clone_settings": "🤖 Clone Settings",
        "export_stats": "📱 Export Data",
        "rate_bot": "⭐ Rate Bot",
        "report_bug": "🐛 Report Bug",
        "suggest_feature": "💡 Suggest Feature"
    }
    
    feature_name = feature_names.get(query.data, "Feature")
    
    text = f"{feature_name}\n\n"
    text += f"🚧 **Coming Soon!**\n\n"
    text += f"This feature is currently under development.\n"
    text += f"Stay tuned for updates!\n\n"
    text += f"💬 **Need immediate assistance?**\n"
    text += f"Contact our support team for help."
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
            InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^user_profile_main$"))
async def user_profile_main_callback(client: Client, query: CallbackQuery):
    """Handle user profile main callback to avoid infinite loop"""
    # Redirect to user_profile callback
    query.data = "user_profile"
    from bot.plugins.start_handler import profile_callback
    await profile_callback(client, query)

@Client.on_callback_query(filters.regex("^file_(sample|recent|popular)"))
async def handle_sample_file_callbacks(client: Client, query: CallbackQuery):
    """Handle sample file callbacks from file browsing"""
    await query.answer()
    
    file_id = query.data
    file_name = "Sample File"
    
    if "sample" in file_id:
        file_name = "Sample File"
    elif "recent" in file_id:
        file_name = "Recent File"
    elif "popular" in file_id:
        file_name = "Popular File"
    
    text = f"📁 **{file_name}**\n\n"
    text += f"🔍 **File ID:** `{file_id}`\n"
    text += f"📊 **Size:** 125.6 MB\n"
    text += f"⏰ **Added:** 2 hours ago\n"
    text += f"📥 **Downloads:** 1,234\n\n"
    text += f"🎯 **Actions:**"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Download", url="https://t.me/example"),
            InlineKeyboardButton("📤 Share", callback_data=f"share_{file_id}")
        ],
        [
            InlineKeyboardButton("ℹ️ More Info", callback_data=f"info_{file_id}"),
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{file_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
