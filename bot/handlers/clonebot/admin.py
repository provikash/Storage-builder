
"""
Unified Clone Admin Handler
Handles all clone bot admin features and settings
"""
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token, update_clone_config, get_clone_config
from bot.logging import LOGGER

logger = LOGGER(__name__)

admin_sessions = {}

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

def create_admin_panel_keyboard():
    """Create clone admin panel keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎛️ Bot Features", callback_data="clone_bot_features"),
            InlineKeyboardButton("📊 Statistics", callback_data="clone_stats")
        ],
        [
            InlineKeyboardButton("🔐 Force Channels", callback_data="clone_local_force_channels"),
            InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_command_config")
        ],
        [
            InlineKeyboardButton("💰 Token Pricing", callback_data="clone_token_pricing"),
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener")
        ],
        [
            InlineKeyboardButton("📋 Request Channels", callback_data="clone_request_channels"),
            InlineKeyboardButton("🔄 Toggle Features", callback_data="clone_toggle_features")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_command(client: Client, message: Message):
    """Clone admin panel command"""
    user_id = message.from_user.id
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    
    if bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ Clone admin panel is only available in clone bots!")

    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data:
        return await message.reply_text("❌ Clone configuration not found!")

    if clone_data.get('admin_id') != user_id:
        return await message.reply_text("❌ Only clone admin can access this panel!")

    admin_sessions[user_id] = {
        'type': 'clone',
        'timestamp': datetime.now(),
        'bot_token': bot_token,
        'clone_id': clone_data['_id']
    }

    text = f"⚙️ **Clone Bot Admin Panel**\n\n"
    text += f"🤖 **Bot:** @{clone_data.get('username', 'Unknown')}\n"
    text += f"🆔 **Bot ID:** `{clone_data['_id']}`\n"
    text += f"📊 **Status:** {clone_data.get('status', 'Unknown').title()}\n\n"
    text += f"**Manage your clone bot settings below:**"

    await message.reply_text(text, reply_markup=create_admin_panel_keyboard())

@Client.on_message(filters.command("clonesettings") & filters.private)
async def clone_settings_command(client: Client, message: Message):
    """Clone settings command - alias for cloneadmin"""
    await clone_admin_command(client, message)

@Client.on_message(filters.command("togglerandom") & filters.private)
async def toggle_random_button(client: Client, message: Message):
    """Toggle random button feature"""
    user_id = message.from_user.id
    
    if user_id not in admin_sessions:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    clone_id = admin_sessions[user_id].get('clone_id')
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('random_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {"features.random_button": new_state})
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Random button {status}!")

@Client.on_message(filters.command("togglerecent") & filters.private)
async def toggle_recent_button(client: Client, message: Message):
    """Toggle recent button feature"""
    user_id = message.from_user.id
    
    if user_id not in admin_sessions:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    clone_id = admin_sessions[user_id].get('clone_id')
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('recent_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {"features.recent_button": new_state})
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Recent button {status}!")

@Client.on_callback_query(filters.regex("^clone_bot_features$"))
async def clone_bot_features_callback(client: Client, query: CallbackQuery):
    """Handle clone bot features callback"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access.", show_alert=True)
    
    await query.answer("Loading features...")
    # Implementation continues in the actual feature management

@Client.on_callback_query(filters.regex("^clone_stats$"))
async def clone_stats_callback(client: Client, query: CallbackQuery):
    """Handle clone stats callback"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access.", show_alert=True)
    
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    clone_data = await get_clone_by_bot_token(bot_token)
    
    text = f"📊 **Clone Bot Statistics**\n\n"
    text += f"🤖 **Bot:** @{clone_data.get('username', 'Unknown')}\n"
    text += f"📅 **Created:** {clone_data.get('created_at', 'Unknown')}\n"
    text += f"👥 **Total Users:** {clone_data.get('total_users', 0)}\n"
    text += f"📁 **Total Files:** {clone_data.get('total_files', 0)}\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="goto_clone_admin")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^clone_toggle_features$"))
async def clone_toggle_features_callback(client: Client, query: CallbackQuery):
    """Handle clone features toggle"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access.", show_alert=True)
    
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    clone_data = await get_clone_by_bot_token(bot_token)
    
    if not clone_data:
        return await query.answer("❌ Clone configuration not found!", show_alert=True)
    
    text = f"🎛️ **Clone Features Management**\n\n"
    text += f"Toggle features on/off for your clone bot:\n\n"
    
    features = {
        'random_mode': {'name': 'Random Files', 'emoji': '🎲'},
        'recent_mode': {'name': 'Recent Files', 'emoji': '🆕'},
        'popular_mode': {'name': 'Popular Files', 'emoji': '🔥'},
        'search_mode': {'name': 'Search', 'emoji': '🔍'}
    }
    
    buttons = []
    for feature_key, feature_info in features.items():
        status = "✅" if clone_data.get(feature_key, False) else "❌"
        text += f"{feature_info['emoji']} {feature_info['name']}: {status}\n"
        
        buttons.append([
            InlineKeyboardButton(
                f"{feature_info['emoji']} Toggle {feature_info['name']}", 
                callback_data=f"toggle_feature_{feature_key}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="goto_clone_admin")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^toggle_feature_"))
async def handle_feature_toggle(client: Client, query: CallbackQuery):
    """Toggle a specific feature"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access.", show_alert=True)
    
    feature_key = query.data.replace("toggle_feature_", "")
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    
    clone_data = await get_clone_by_bot_token(bot_token)
    if not clone_data:
        return await query.answer("❌ Configuration error", show_alert=True)
    
    current_value = clone_data.get(feature_key, False)
    new_value = not current_value
    
    success = await update_clone_config(clone_data['_id'], {feature_key: new_value})
    
    if success:
        await query.answer("✅ Feature toggled successfully")
        await clone_toggle_features_callback(client, query)
    else:
        await query.answer("❌ Failed to toggle feature", show_alert=True)

@Client.on_callback_query(filters.regex("^goto_clone_admin$"))
async def goto_clone_admin_callback(client: Client, query: CallbackQuery):
    """Return to clone admin panel"""
    await clone_admin_command(client, query.message)
