
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *

# Store clone admin sessions
clone_admin_sessions = {}

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_panel(client: Client, message: Message):
    """Clone Admin Panel"""
    user_id = message.from_user.id
    
    # Find clone where user is admin
    clones_list = await get_all_clones()
    user_clone = None
    
    for clone in clones_list:
        if clone['admin_id'] == user_id:
            user_clone = clone
            break
    
    if not user_clone:
        return await message.reply_text(
            "❌ **Access Denied**\n\n"
            "You are not registered as a clone admin.\n"
            "Contact the Mother Bot admin to create your clone."
        )
    
    # Check subscription status
    sub_data = await get_subscription(user_clone['_id'])
    
    if not sub_data or sub_data['status'] != 'active':
        status_text = "❌ **Subscription Inactive**"
        if sub_data:
            if sub_data['status'] == 'expired':
                status_text += f"\n📅 Expired on: {sub_data['expiry_date'].strftime('%Y-%m-%d')}"
            elif sub_data['status'] == 'pending':
                status_text += "\n💰 Payment pending"
        
        return await message.reply_text(
            f"{status_text}\n\n"
            "Contact the Mother Bot admin to renew your subscription."
        )
    
    # Store session
    clone_admin_sessions[user_id] = user_clone['_id']
    
    # Calculate remaining days
    days_remaining = (sub_data['expiry_date'] - datetime.now()).days
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="clone_settings")],
        [InlineKeyboardButton("📢 Force Channels", callback_data="clone_force_channels")],
        [InlineKeyboardButton("🔔 Request Channels", callback_data="clone_request_channels")],
        [InlineKeyboardButton("🎫 Token Settings", callback_data="clone_token_settings")],
        [InlineKeyboardButton("💰 Subscription", callback_data="clone_subscription")],
        [InlineKeyboardButton("📊 Statistics", callback_data="clone_statistics")]
    ])
    
    await message.reply_text(
        f"🎛️ **Clone Admin Panel**\n\n"
        f"🤖 **Bot:** @{user_clone['username']}\n"
        f"📅 **Subscription:** {days_remaining} days remaining\n"
        f"💰 **Plan:** {sub_data['tier']}\n"
        f"✅ **Status:** Active\n\n"
        "Choose an option below:",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("^clone_settings$"))
async def clone_settings_callback(client: Client, query: CallbackQuery):
    """Clone settings panel"""
    user_id = query.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await query.answer("❌ Session expired. Use /cloneadmin again.", show_alert=True)
    
    config = await get_clone_config(clone_id)
    
    if not config:
        return await query.answer("❌ Configuration not found.", show_alert=True)
    
    features = config['features']
    
    # Create toggle buttons
    buttons = []
    for feature, enabled in features.items():
        status = "✅" if enabled else "❌"
        feature_name = feature.replace('_', ' ').title()
        buttons.append([
            InlineKeyboardButton(
                f"{status} {feature_name}", 
                callback_data=f"clone_toggle_{feature}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="clone_admin_back")])
    
    await query.edit_message_text(
        "⚙️ **Bot Features**\n\n"
        "Toggle features on/off for your bot:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^clone_toggle_"))
async def toggle_feature_callback(client: Client, query: CallbackQuery):
    """Toggle a feature on/off"""
    user_id = query.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await query.answer("❌ Session expired.", show_alert=True)
    
    feature = query.data.split("_", 2)[2]
    config = await get_clone_config(clone_id)
    
    # Toggle feature
    current_state = config['features'].get(feature, False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {
        f"features.{feature}": new_state
    })
    
    await query.answer(
        f"{'✅ Enabled' if new_state else '❌ Disabled'} {feature.title()}",
        show_alert=True
    )
    
    # Refresh the page
    await clone_settings_callback(client, query)

@Client.on_callback_query(filters.regex("^clone_force_channels$"))
async def clone_force_channels_callback(client: Client, query: CallbackQuery):
    """Manage force channels"""
    user_id = query.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await query.answer("❌ Session expired.", show_alert=True)
    
    config = await get_clone_config(clone_id)
    global_channels = await get_global_force_channels()
    local_channels = config['channels']['force_channels']
    
    text = "📢 **Force Channels**\n\n"
    
    if global_channels:
        text += "🌐 **Global Channels** (managed by Mother Bot):\n"
        for channel in global_channels:
            text += f"• {channel}\n"
        text += "\n"
    
    if local_channels:
        text += "🏠 **Your Local Channels:**\n"
        for channel in local_channels:
            text += f"• {channel}\n"
    else:
        text += "🏠 **Your Local Channels:** None\n"
    
    text += "\n📝 **Commands:**\n"
    text += "• `/addforce <channel_id>` - Add local force channel\n"
    text += "• `/removeforce <channel_id>` - Remove local force channel"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="clone_admin_back")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel(client: Client, message: Message):
    """Add local force channel"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addforce <channel_id>`")
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid channel ID.")
    
    config = await get_clone_config(clone_id)
    local_channels = config['channels']['force_channels']
    
    if channel_id in local_channels:
        return await message.reply_text("❌ Channel already added.")
    
    local_channels.append(channel_id)
    
    await update_clone_config(clone_id, {
        "channels.force_channels": local_channels
    })
    
    await message.reply_text(f"✅ Added force channel: {channel_id}")

@Client.on_message(filters.command("togglerandom") & filters.private)
async def toggle_random_button(client: Client, message: Message):
    """Toggle random button on/off"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('random_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {
        "features.random_button": new_state
    })
    
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Random button {status}!")

@Client.on_message(filters.command("togglerecent") & filters.private)
async def toggle_recent_button(client: Client, message: Message):
    """Toggle recent button on/off"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    config = await get_clone_config(clone_id)
    current_state = config['features'].get('recent_button', False)
    new_state = not current_state
    
    await update_clone_config(clone_id, {
        "features.recent_button": new_state
    })
    
    status = "enabled" if new_state else "disabled"
    await message.reply_text(f"✅ Recent button {status}!")

@Client.on_message(filters.command("removeforce") & filters.private)
async def remove_force_channel(client: Client, message: Message):
    """Remove local force channel"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/removeforce <channel_id>`")
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Invalid channel ID.")
    
    config = await get_clone_config(clone_id)
    local_channels = config['channels']['force_channels']
    
    if channel_id not in local_channels:
        return await message.reply_text("❌ Channel not found.")
    
    local_channels.remove(channel_id)
    
    await update_clone_config(clone_id, {
        "channels.force_channels": local_channels
    })
    
    await message.reply_text(f"✅ Removed force channel: {channel_id}")

@Client.on_callback_query(filters.regex("^clone_token_settings$"))
async def clone_token_settings_callback(client: Client, query: CallbackQuery):
    """Token settings panel"""
    user_id = query.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await query.answer("❌ Session expired.", show_alert=True)
    
    config = await get_clone_config(clone_id)
    token_settings = config['token_settings']
    
    status = "✅ Enabled" if token_settings['enabled'] else "❌ Disabled"
    mode = token_settings['mode'].replace('_', ' ').title()
    
    text = f"🎫 **Token Verification Settings**\n\n"
    text += f"📊 **Status:** {status}\n"
    text += f"🔧 **Mode:** {mode}\n"
    text += f"🎯 **Command Limit:** {token_settings['command_limit']}\n"
    text += f"💰 **Pricing:** ${token_settings['pricing']}\n\n"
    text += "**Commands:**\n"
    text += "• `/tokenmode <one_time|command_limit>`\n"
    text += "• `/tokenlimit <number>`\n"
    text += "• `/tokenprice <price>`\n"
    text += "• `/toggletoken` - Enable/disable"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔄 Toggle Token System", 
            callback_data="clone_toggle_token_system"
        )],
        [InlineKeyboardButton("🔙 Back", callback_data="clone_admin_back")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_message(filters.command("tokenmode") & filters.private)
async def set_token_mode(client: Client, message: Message):
    """Set token verification mode"""
    user_id = message.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await message.reply_text("❌ Use /cloneadmin first.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/tokenmode <one_time|command_limit>`")
    
    mode = message.command[1].lower()
    
    if mode not in ['one_time', 'command_limit']:
        return await message.reply_text("❌ Invalid mode. Use 'one_time' or 'command_limit'.")
    
    await update_clone_config(clone_id, {
        "token_settings.mode": mode
    })
    
    await message.reply_text(f"✅ Token mode set to: {mode.replace('_', ' ').title()}")

@Client.on_callback_query(filters.regex("^clone_admin_back$"))
async def clone_admin_back_callback(client: Client, query: CallbackQuery):
    """Go back to clone admin panel"""
    user_id = query.from_user.id
    clone_id = clone_admin_sessions.get(user_id)
    
    if not clone_id:
        return await query.answer("❌ Session expired. Use /cloneadmin again.", show_alert=True)
    
    clone_data = await get_clone(clone_id)
    sub_data = await get_subscription(clone_id)
    
    days_remaining = (sub_data['expiry_date'] - datetime.now()).days
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="clone_settings")],
        [InlineKeyboardButton("📢 Force Channels", callback_data="clone_force_channels")],
        [InlineKeyboardButton("🔔 Request Channels", callback_data="clone_request_channels")],
        [InlineKeyboardButton("🎫 Token Settings", callback_data="clone_token_settings")],
        [InlineKeyboardButton("💰 Subscription", callback_data="clone_subscription")],
        [InlineKeyboardButton("📊 Statistics", callback_data="clone_statistics")]
    ])
    
    await query.edit_message_text(
        f"🎛️ **Clone Admin Panel**\n\n"
        f"🤖 **Bot:** @{clone_data['username']}\n"
        f"📅 **Subscription:** {days_remaining} days remaining\n"
        f"💰 **Plan:** {sub_data['tier']}\n"
        f"✅ **Status:** Active\n\n"
        "Choose an option below:",
        reply_markup=buttons
    )
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_config, update_clone_config, get_clone
from bot.utils.clone_config_loader import clone_config_loader

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_panel(client: Client, message: Message):
    """Clone Administrator Panel"""
    # Get bot configuration
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    # Check if this is a clone and user is the admin
    if not config['bot_info'].get('is_clone', False):
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only the clone administrator can access this panel.")
    
    me = await client.get_me()
    subscription = config.get('subscription', {})
    
    panel_text = f"⚙️ **Clone Admin Panel**\n"
    panel_text += f"🤖 **Bot:** @{me.username}\n\n"
    
    panel_text += f"📊 **Status Information:**\n"
    panel_text += f"• Subscription: {subscription.get('tier', 'Unknown')}\n"
    panel_text += f"• Status: {subscription.get('status', 'Unknown')}\n"
    if subscription.get('expiry'):
        panel_text += f"• Expires: {subscription['expiry'].strftime('%Y-%m-%d %H:%M')}\n"
    
    panel_text += f"\n✨ **Enabled Features:**\n"
    features = config.get('features', {})
    for feature, enabled in features.items():
        emoji = "✅" if enabled else "❌"
        feature_name = feature.replace('_', ' ').title()
        panel_text += f"• {emoji} {feature_name}\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎛️ Feature Settings", callback_data="clone_features")],
        [InlineKeyboardButton("🎯 Token Settings", callback_data="clone_token_settings")],
        [InlineKeyboardButton("📢 Channel Settings", callback_data="clone_channels")],
        [InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_shortener")],
        [InlineKeyboardButton("💬 Custom Messages", callback_data="clone_messages")],
        [InlineKeyboardButton("📊 Statistics", callback_data="clone_statistics")]
    ])
    
    await message.reply_text(panel_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^clone_admin_panel$"))
async def clone_admin_panel_callback(client: Client, query: CallbackQuery):
    """Handle clone admin panel callback"""
    await clone_admin_panel(client, query.message)

@Client.on_callback_query(filters.regex("^clone_features$"))
async def clone_features_panel(client: Client, query: CallbackQuery):
    """Manage clone features"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if query.from_user.id != config['bot_info'].get('admin_id'):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    features = config.get('features', {})
    
    text = "🎛️ **Feature Management**\n\n"
    text += "Toggle features on/off for your clone bot:\n\n"
    
    buttons = []
    for feature, enabled in features.items():
        if feature not in ['clone_creation', 'admin_panel']:  # These are restricted
            emoji = "✅" if enabled else "❌"
            feature_name = feature.replace('_', ' ').title()
            text += f"{emoji} **{feature_name}**: {'Enabled' if enabled else 'Disabled'}\n"
            
            button_text = f"{'🔴 Disable' if enabled else '🟢 Enable'} {feature_name}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"toggle_feature#{feature}")])
    
    buttons.append([InlineKeyboardButton("« Back to Panel", callback_data="clone_admin_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^toggle_feature#"))
async def toggle_feature(client: Client, query: CallbackQuery):
    """Toggle a specific feature"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if query.from_user.id != config['bot_info'].get('admin_id'):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    feature = query.data.split("#")[1]
    bot_id = bot_token.split(':')[0]
    
    # Get current config from database
    current_config = await get_clone_config(bot_id)
    current_features = current_config.get('features', {})
    
    # Toggle the feature
    current_features[feature] = not current_features.get(feature, False)
    
    # Update in database
    await update_clone_config(bot_id, {'features': current_features})
    
    # Clear cache to force reload
    clone_config_loader.clear_cache(bot_token)
    
    status = "enabled" if current_features[feature] else "disabled"
    feature_name = feature.replace('_', ' ').title()
    
    await query.answer(f"✅ {feature_name} {status}!", show_alert=True)
    
    # Refresh the features panel
    await clone_features_panel(client, query)

@Client.on_callback_query(filters.regex("^clone_token_settings$"))
async def clone_token_settings(client: Client, query: CallbackQuery):
    """Manage token verification settings"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if query.from_user.id != config['bot_info'].get('admin_id'):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    token_settings = config.get('token_settings', {})
    
    text = "🎯 **Token Verification Settings**\n\n"
    text += f"**Current Mode:** {token_settings.get('mode', 'one_time').replace('_', ' ').title()}\n"
    text += f"**Command Limit:** {token_settings.get('command_limit', 100)}\n"
    text += f"**Token Price:** ${token_settings.get('pricing', 1.0)}\n"
    text += f"**Status:** {'Enabled' if token_settings.get('enabled', True) else 'Disabled'}\n\n"
    
    text += "Use the commands below to modify settings:\n"
    text += "• `/settokenmode one_time` or `/settokenmode command_limit`\n"
    text += "• `/setcommandlimit <number>`\n"
    text += "• `/settokenprice <price>`\n"
    text += "• `/toggletoken` - Enable/disable token system\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Toggle Token System", callback_data="toggle_token_system")],
        [InlineKeyboardButton("« Back to Panel", callback_data="clone_admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^clone_channels$"))
async def clone_channels_panel(client: Client, query: CallbackQuery):
    """Manage channel settings"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if query.from_user.id != config['bot_info'].get('admin_id'):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    channels = config.get('channels', {})
    
    text = "📢 **Channel Management**\n\n"
    
    text += "**Global Force Channels** (Set by Mother Bot):\n"
    global_channels = channels.get('global_force_channels', [])
    if global_channels:
        for channel in global_channels:
            text += f"• {channel}\n"
    else:
        text += "• None set\n"
    
    text += "\n**Local Force Channels** (Your channels):\n"
    local_channels = channels.get('local_force_channels', [])
    if local_channels:
        for channel in local_channels:
            text += f"• {channel}\n"
    else:
        text += "• None set\n"
    
    text += "\n**Request Channels:**\n"
    request_channels = channels.get('request_channels', [])
    if request_channels:
        for channel in request_channels:
            text += f"• {channel}\n"
    else:
        text += "• None set\n"
    
    text += "\n**Commands:**\n"
    text += "• `/addforce <channel>` - Add force channel\n"
    text += "• `/removeforce <channel>` - Remove force channel\n"
    text += "• `/addrequest <channel>` - Add request channel\n"
    text += "• `/removerequest <channel>` - Remove request channel\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back to Panel", callback_data="clone_admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_mode(client: Client, message: Message):
    """Set token verification mode"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/settokenmode <mode>`\n\n"
            "Available modes:\n"
            "• `one_time` - Single use tokens\n"
            "• `command_limit` - Limited uses per token"
        )
    
    mode = message.command[1].lower()
    if mode not in ['one_time', 'command_limit']:
        return await message.reply_text("❌ Invalid mode. Use 'one_time' or 'command_limit'")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['mode'] = mode
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    await message.reply_text(f"✅ Token mode set to: {mode.replace('_', ' ').title()}")

@Client.on_message(filters.command("setcommandlimit") & filters.private)
async def set_command_limit(client: Client, message: Message):
    """Set command limit for tokens"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/setcommandlimit <number>`")
    
    try:
        limit = int(message.command[1])
        if limit < 1:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Please provide a valid positive number.")
    
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['command_limit'] = limit
    
    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)
    
    await message.reply_text(f"✅ Command limit set to: {limit}")

@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel(client: Client, message: Message):
    """Add local force channel"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if not config['bot_info'].get('is_clone', False):
        return
    
    if message.from_user.id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only clone admin can modify settings.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addforce <channel_id_or_username>`")
    
    channel = message.command[1]
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    
    channels = current_config.get('channels', {})
    local_force = channels.get('force_channels', [])
    
    if channel not in local_force:
        local_force.append(channel)
        channels['force_channels'] = local_force
        
        await update_clone_config(bot_id, {'channels': channels})
        clone_config_loader.clear_cache(bot_token)
        
        await message.reply_text(f"✅ Added force channel: {channel}")
    else:
        await message.reply_text("❌ Channel already in force list.")
