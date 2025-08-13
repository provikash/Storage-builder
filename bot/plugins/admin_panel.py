
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

# Store admin sessions to prevent unauthorized access
admin_sessions = {}

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command_handler(client: Client, message: Message):
    """Main admin command handler - routes to appropriate panel"""
    user_id = message.from_user.id
    
    # Check if this is Mother Bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    is_clone = config['bot_info'].get('is_clone', False)
    
    if not is_clone:
        # This is Mother Bot - check for Mother Bot admin
        if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
            await mother_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only Mother Bot administrators can access this panel.")
    else:
        # This is a Clone Bot - check for Clone admin
        clone_admin_id = config['bot_info'].get('admin_id')
        if user_id == clone_admin_id:
            await clone_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only the clone administrator can access this panel.")

async def mother_admin_panel(client: Client, message: Message):
    """Mother Bot Admin Panel"""
    user_id = message.from_user.id
    
    # Validate Mother Bot admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied. Only Mother Bot administrators can access this panel.")
    
    # Store admin session
    admin_sessions[user_id] = {'type': 'mother', 'timestamp': datetime.now()}
    
    # Get statistics
    try:
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())
    except Exception as e:
        total_clones = active_clones = running_clones = total_subscriptions = 0
        print(f"Error getting stats: {e}")
    
    panel_text = f"🎛️ **Mother Bot Admin Panel**\n\n"
    panel_text += f"📊 **System Overview:**\n"
    panel_text += f"• Total Clones: {total_clones}\n"
    panel_text += f"• Active Clones: {active_clones}\n"
    panel_text += f"• Running Clones: {running_clones}\n"
    panel_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
    panel_text += f"🕐 **Panel Access Time:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ Pending Clone Requests", callback_data="mother_pending_requests")],
        [InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone")],
        [InlineKeyboardButton("💰 Manage Subscriptions", callback_data="mother_manage_subscriptions")],
        [InlineKeyboardButton("📢 Manage Global Force Channels", callback_data="mother_global_force_channels")],
        [InlineKeyboardButton("📄 Edit About Page", callback_data="mother_edit_about")],
        [InlineKeyboardButton("📋 View All Clones", callback_data="mother_view_all_clones")],
        [InlineKeyboardButton("🗑️ Disable/Delete Clone", callback_data="mother_disable_clone")],
        [InlineKeyboardButton("📊 System Statistics", callback_data="mother_statistics")]
    ])
    
    await message.reply_text(panel_text, reply_markup=buttons)

async def clone_admin_panel(client: Client, message: Message):
    """Clone Bot Admin Panel"""
    user_id = message.from_user.id
    
    # Get bot configuration
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    # Validate clone admin permissions
    if not config['bot_info'].get('is_clone', False):
        return await message.reply_text("❌ This command is only available in clone bots.")
    
    if user_id != config['bot_info'].get('admin_id'):
        return await message.reply_text("❌ Only the clone administrator can access this panel.")
    
    # Store admin session
    admin_sessions[user_id] = {'type': 'clone', 'timestamp': datetime.now(), 'bot_token': bot_token}
    
    me = await client.get_me()
    subscription = config.get('subscription', {})
    
    panel_text = f"⚙️ **Clone Admin Panel**\n"
    panel_text += f"🤖 **Bot:** @{me.username}\n\n"
    
    panel_text += f"📊 **Status Information:**\n"
    panel_text += f"• Subscription: {subscription.get('tier', 'Unknown')}\n"
    panel_text += f"• Status: {subscription.get('status', 'Unknown')}\n"
    if subscription.get('expiry'):
        days_remaining = (subscription['expiry'] - datetime.now()).days
        panel_text += f"• Days Remaining: {days_remaining}\n"
    
    panel_text += f"\n✨ **Quick Settings Access:**\n"
    features = config.get('features', {})
    enabled_count = sum(1 for enabled in features.values() if enabled)
    panel_text += f"• Enabled Features: {enabled_count}/{len(features)}\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Manage Local Force Channels", callback_data="clone_local_force_channels")],
        [InlineKeyboardButton("🔔 Manage Request Channels", callback_data="clone_request_channels")],
        [InlineKeyboardButton("🎫 Configure Token/Command Limit", callback_data="clone_token_command_config")],
        [InlineKeyboardButton("💰 Set Token/Command Pricing", callback_data="clone_token_pricing")],
        [InlineKeyboardButton("⚙️ Enable/Disable Bot Features", callback_data="clone_bot_features")],
        [InlineKeyboardButton("📊 View Subscription Status", callback_data="clone_subscription_status")]
    ])
    
    await message.reply_text(panel_text, reply_markup=buttons)

# Mother Bot Callback Handlers
@Client.on_callback_query(filters.regex("^mother_"))
async def mother_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Mother Bot admin panel callbacks"""
    user_id = query.from_user.id
    
    # Validate session and permissions
    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'mother' or user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Session expired or unauthorized access!", show_alert=True)
    
    callback_data = query.data
    
    if callback_data == "mother_pending_requests":
        await handle_mother_pending_requests(client, query)
    elif callback_data == "mother_create_clone":
        await handle_mother_create_clone(client, query)
    elif callback_data == "mother_manage_subscriptions":
        await handle_mother_manage_subscriptions(client, query)
    elif callback_data == "mother_global_force_channels":
        await handle_mother_global_force_channels(client, query)
    elif callback_data == "mother_edit_about":
        await handle_mother_edit_about(client, query)
    elif callback_data == "mother_view_all_clones":
        await handle_mother_view_all_clones(client, query)
    elif callback_data == "mother_disable_clone":
        await handle_mother_disable_clone(client, query)
    elif callback_data == "mother_statistics":
        await handle_mother_statistics(client, query)
    elif callback_data == "back_to_mother_panel":
        await mother_admin_panel(client, query.message)
    else:
        await query.answer("⚠️ Unknown action", show_alert=True)

# Clone Bot Callback Handlers
@Client.on_callback_query(filters.regex("^clone_"))
async def clone_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Clone Bot admin panel callbacks"""
    user_id = query.from_user.id
    
    # Validate session and permissions
    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        return await query.answer("❌ Session expired or unauthorized access!", show_alert=True)
    
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if user_id != config['bot_info'].get('admin_id'):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    callback_data = query.data
    
    if callback_data == "clone_local_force_channels":
        await handle_clone_local_force_channels(client, query)
    elif callback_data == "clone_request_channels":
        await handle_clone_request_channels(client, query)
    elif callback_data == "clone_token_command_config":
        await handle_clone_token_command_config(client, query)
    elif callback_data == "clone_token_pricing":
        await handle_clone_token_pricing(client, query)
    elif callback_data == "clone_bot_features":
        await handle_clone_bot_features(client, query)
    elif callback_data == "clone_subscription_status":
        await handle_clone_subscription_status(client, query)
    elif callback_data == "back_to_clone_panel":
        await clone_admin_panel(client, query.message)
    else:
        await query.answer("⚠️ Unknown action", show_alert=True)

# Mother Bot Handler Functions
async def handle_mother_create_clone(client: Client, query: CallbackQuery):
    """Handle clone creation interface"""
    text = "🤖 **Create New Clone Bot**\n\n"
    text += "To create a new clone, provide the following information:\n\n"
    text += "**Format:** `/createclone <bot_token> <admin_id> <db_url> [tier]`\n\n"
    text += "**Example:**\n"
    text += "`/createclone 123456:ABC-DEF... 123456789 mongodb://user:pass@host/db monthly`\n\n"
    text += "**Available Tiers:**\n"
    text += "• `monthly` - $3/month\n"
    text += "• `quarterly` - $8/3 months\n"
    text += "• `semi_annual` - $15/6 months\n"
    text += "• `yearly` - $26/year"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_manage_subscriptions(client: Client, query: CallbackQuery):
    """Handle subscription management"""
    subscriptions = await get_all_subscriptions()
    
    if not subscriptions:
        text = "💰 **Subscription Management**\n\n❌ No subscriptions found."
    else:
        active_subs = len([s for s in subscriptions if s['status'] == 'active'])
        pending_subs = len([s for s in subscriptions if s['status'] == 'pending'])
        expired_subs = len([s for s in subscriptions if s['status'] == 'expired'])
        total_revenue = sum(s['price'] for s in subscriptions if s.get('payment_verified', False))
        
        text = f"💰 **Subscription Management**\n\n"
        text += f"📊 **Statistics:**\n"
        text += f"• Total Revenue: ${total_revenue}\n"
        text += f"• Active: {active_subs}\n"
        text += f"• Pending: {pending_subs}\n"
        text += f"• Expired: {expired_subs}\n\n"
        text += "**Recent Subscriptions:**\n"
        
        for sub in sorted(subscriptions, key=lambda x: x.get('created_at', datetime.now()), reverse=True)[:5]:
            clone = await get_clone(sub['_id'])
            username = clone.get('username', 'Unknown') if clone else 'Unknown'
            text += f"• @{username} - {sub['tier']} (${sub['price']}) - {sub['status']}\n"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Full Report", callback_data="mother_subscription_report")],
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_global_force_channels(client: Client, query: CallbackQuery):
    """Handle global force channels management"""
    try:
        global_channels = await get_global_force_channels()
    except:
        global_channels = []
    
    text = f"📢 **Global Force Channels Management**\n\n"
    
    if global_channels:
        text += "**Current Global Force Channels:**\n"
        for i, channel in enumerate(global_channels, 1):
            text += f"{i}. {channel}\n"
    else:
        text += "❌ No global force channels set.\n"
    
    text += f"\n**Commands:**\n"
    text += f"• `/setglobalchannels <channel1> <channel2> ...` - Set channels\n"
    text += f"• `/addglobalchannel <channel>` - Add single channel\n"
    text += f"• `/removeglobalchannel <channel>` - Remove channel\n"
    text += f"• `/clearglobalchannels` - Remove all channels"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_edit_about(client: Client, query: CallbackQuery):
    """Handle about page editing"""
    try:
        global_about = await get_global_about()
    except:
        global_about = None
    
    text = f"📄 **Edit Global About Page**\n\n"
    
    if global_about:
        text += f"**Current About Page:**\n{global_about[:200]}{'...' if len(global_about) > 200 else ''}\n\n"
    else:
        text += "❌ No global about page set.\n\n"
    
    text += f"**Commands:**\n"
    text += f"• `/setglobalabout <text>` - Set about page\n"
    text += f"• `/clearglobalabout` - Clear about page\n\n"
    text += f"**Note:** The about page will be displayed in all clone bots."
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_view_all_clones(client: Client, query: CallbackQuery):
    """Handle viewing all clones"""
    clones = await get_all_clones()
    running_clones = clone_manager.get_running_clones()
    
    if not clones:
        text = "📋 **All Clones**\n\n❌ No clones found."
    else:
        text = f"📋 **All Clones ({len(clones)} total)**\n\n"
        
        for i, clone in enumerate(clones[:10], 1):  # Show first 10
            status_emoji = "🟢" if clone['_id'] in running_clones else "🔴"
            subscription = await get_subscription(clone['_id'])
            
            text += f"**{i}. @{clone.get('username', 'Unknown')}**\n"
            text += f"   {status_emoji} Status: {clone['status']}\n"
            text += f"   👤 Admin: {clone['admin_id']}\n"
            
            if subscription:
                text += f"   💳 Subscription: {subscription['tier']} ({subscription['status']})\n"
                if subscription.get('expiry_date'):
                    text += f"   📅 Expires: {subscription['expiry_date'].strftime('%Y-%m-%d')}\n"
            else:
                text += f"   💳 Subscription: None\n"
            text += "\n"
        
        if len(clones) > 10:
            text += f"... and {len(clones) - 10} more clones"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="mother_view_all_clones")],
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_disable_clone(client: Client, query: CallbackQuery):
    """Handle clone disabling/deletion"""
    clones = await get_all_clones()
    
    if not clones:
        text = "🗑️ **Disable/Delete Clone**\n\n❌ No clones available to manage."
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])
    else:
        text = f"🗑️ **Disable/Delete Clone**\n\n"
        text += f"**Commands:**\n"
        text += f"• `/disableclone <bot_id>` - Disable clone\n"
        text += f"• `/enableclone <bot_id>` - Enable clone\n"
        text += f"• `/deleteclone <bot_id>` - Permanently delete clone\n\n"
        text += f"**Available Clones:**\n"
        
        for clone in clones[:5]:  # Show first 5
            text += f"• @{clone.get('username', 'Unknown')} (ID: {clone['_id'][:8]}...)\n"
        
        if len(clones) > 5:
            text += f"... and {len(clones) - 5} more\n"
        
        text += f"\n⚠️ **Warning:** Deletion is permanent and cannot be undone!"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 View All Clones", callback_data="mother_view_all_clones")],
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_mother_statistics(client: Client, query: CallbackQuery):
    """Handle system statistics"""
    try:
        clones = await get_all_clones()
        subscriptions = await get_all_subscriptions()
        running_clones = clone_manager.get_running_clones()
        
        total_clones = len(clones)
        active_clones = len([c for c in clones if c['status'] == 'active'])
        total_revenue = sum(s['price'] for s in subscriptions if s.get('payment_verified', False))
        monthly_revenue = sum(s['price'] for s in subscriptions 
                             if s.get('payment_verified', False) and 
                             s.get('created_at', datetime.now()) > datetime.now() - timedelta(days=30))
        
        text = f"📊 **System Statistics**\n\n"
        text += f"🤖 **Clones:**\n"
        text += f"• Total Created: {total_clones}\n"
        text += f"• Currently Running: {len(running_clones)}\n"
        text += f"• Active: {active_clones}\n"
        text += f"• Inactive: {total_clones - active_clones}\n\n"
        
        text += f"💰 **Financial:**\n"
        text += f"• Total Revenue: ${total_revenue}\n"
        text += f"• This Month: ${monthly_revenue}\n"
        text += f"• Active Subscriptions: {len([s for s in subscriptions if s['status'] == 'active'])}\n\n"
        
        text += f"⏱️ **System:**\n"
        text += f"• Mother Bot: Running\n"
        text += f"• Clone Manager: Active\n"
        text += f"• Database: Connected\n"
        text += f"• Last Updated: {datetime.now().strftime('%H:%M:%S UTC')}"
        
    except Exception as e:
        text = f"📊 **System Statistics**\n\n❌ Error loading statistics: {str(e)}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="mother_statistics")],
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

# Clone Bot Handler Functions
async def handle_clone_local_force_channels(client: Client, query: CallbackQuery):
    """Handle local force channels management"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    channels = config.get('channels', {})
    local_force = channels.get('force_channels', [])
    global_force = channels.get('global_force_channels', [])
    
    text = f"📢 **Local Force Channels Management**\n\n"
    
    if global_force:
        text += f"🌐 **Global Force Channels** (Set by Mother Bot):\n"
        for channel in global_force:
            text += f"• {channel}\n"
        text += "\n"
    
    text += f"🏠 **Your Local Force Channels:**\n"
    if local_force:
        for i, channel in enumerate(local_force, 1):
            text += f"{i}. {channel}\n"
    else:
        text += "❌ No local force channels set.\n"
    
    text += f"\n**Commands:**\n"
    text += f"• `/addforce <channel>` - Add force channel\n"
    text += f"• `/removeforce <channel>` - Remove force channel\n"
    text += f"• `/listforce` - List all force channels"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_clone_request_channels(client: Client, query: CallbackQuery):
    """Handle request channels management"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    channels = config.get('channels', {})
    request_channels = channels.get('request_channels', [])
    
    text = f"🔔 **Request Channels Management**\n\n"
    text += f"**Current Request Channels:**\n"
    


async def handle_mother_pending_requests(client: Client, query: CallbackQuery):
    """Handle pending clone requests management"""
    from bot.plugins.clone_request import get_all_pending_requests
    
    try:
        pending_requests = await get_all_pending_requests()
        
        if not pending_requests:
            text = "⏳ **Pending Clone Requests**\n\n❌ No pending requests found."
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="mother_pending_requests")],
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        else:
            text = f"⏳ **Pending Clone Requests ({len(pending_requests)})**\n\n"
            
            buttons = []
            for i, request in enumerate(pending_requests[:10], 1):  # Show first 10
                requester_name = request['requester_info']['first_name']
                if request['requester_info']['username']:
                    requester_name += f" (@{request['requester_info']['username']})"
                
                text += f"**{i}. @{request['bot_username']}**\n"
                text += f"   👤 {requester_name}\n"
                text += f"   💰 {request['plan_details']['name']} (${request['plan_details']['price']})\n"
                text += f"   📅 {request['created_at'].strftime('%m-%d %H:%M')}\n"
                
                buttons.append([InlineKeyboardButton(
                    f"📋 {request['bot_username'][:15]}... - Review",
                    callback_data=f"view_request:{request['request_id']}"
                )])
            
            if len(pending_requests) > 10:
                text += f"\n... and {len(pending_requests) - 10} more requests"
                buttons.append([InlineKeyboardButton("📄 View All", callback_data="mother_all_pending_requests")])
            
            buttons.extend([
                [InlineKeyboardButton("🔄 Refresh", callback_data="mother_pending_requests")],
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        text = f"⏳ **Pending Clone Requests**\n\n❌ Error loading requests: {str(e)}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])
        await query.edit_message_text(text, reply_markup=buttons)

    if request_channels:
        for i, channel in enumerate(request_channels, 1):
            text += f"{i}. {channel}\n"
    else:
        text += "❌ No request channels set.\n"
    
    text += f"\n**Commands:**\n"
    text += f"• `/addrequest <channel>` - Add request channel\n"
    text += f"• `/removerequest <channel>` - Remove request channel\n"
    text += f"• `/listrequest` - List all request channels\n\n"
    text += f"**Note:** Request channels are where users can request files."
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_clone_token_command_config(client: Client, query: CallbackQuery):
    """Handle token/command configuration"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    token_settings = config.get('token_settings', {})
    
    text = f"🎫 **Token/Command Configuration**\n\n"
    text += f"**Current Settings:**\n"
    text += f"• Status: {'Enabled' if token_settings.get('enabled', True) else 'Disabled'}\n"
    text += f"• Mode: {token_settings.get('mode', 'one_time').replace('_', ' ').title()}\n"
    text += f"• Command Limit: {token_settings.get('command_limit', 100)}\n"
    text += f"• Token Validity: {token_settings.get('validity_hours', 24)} hours\n\n"
    
    text += f"**Commands:**\n"
    text += f"• `/settokenmode <one_time|command_limit>` - Set token mode\n"
    text += f"• `/setcommandlimit <number>` - Set command limit\n"
    text += f"• `/settokenvalidity <hours>` - Set token validity\n"
    text += f"• `/toggletoken` - Enable/disable token system"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Toggle Token System", callback_data="clone_toggle_token_system")],
        [InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_clone_token_pricing(client: Client, query: CallbackQuery):
    """Handle token pricing configuration"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    token_settings = config.get('token_settings', {})
    
    text = f"💰 **Token/Command Pricing**\n\n"
    text += f"**Current Pricing:**\n"
    text += f"• Token Price: ${token_settings.get('pricing', 1.0)}\n"
    text += f"• Currency: USD\n"
    text += f"• Payment Method: Manual Verification\n\n"
    
    text += f"**Commands:**\n"
    text += f"• `/settokenprice <price>` - Set token price\n"
    text += f"• `/setcurrency <currency>` - Set currency (USD, EUR, etc.)\n\n"
    
    text += f"**Pricing Guidelines:**\n"
    text += f"• Minimum: $0.10\n"
    text += f"• Maximum: $10.00\n"
    text += f"• Recommended: $1.00 - $3.00"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def handle_clone_bot_features(client: Client, query: CallbackQuery):
    """Handle bot features management"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    features = config.get('features', {})
    
    text = f"⚙️ **Bot Features Management**\n\n"
    text += f"Toggle features on/off for your clone bot:\n\n"
    
    buttons = []
    for feature, enabled in features.items():
        if feature not in ['clone_creation', 'admin_panel']:  # Restricted features
            emoji = "✅" if enabled else "❌"
            feature_name = feature.replace('_', ' ').title()
            text += f"{emoji} **{feature_name}**: {'Enabled' if enabled else 'Disabled'}\n"
            
            button_text = f"{'🔴 Disable' if enabled else '🟢 Enable'} {feature_name}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"toggle_feature#{feature}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def handle_clone_subscription_status(client: Client, query: CallbackQuery):
    """Handle subscription status viewing"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    subscription = config.get('subscription', {})
    me = await client.get_me()
    
    text = f"📊 **Subscription Status**\n\n"
    text += f"🤖 **Bot:** @{me.username}\n"
    text += f"👤 **Admin:** {config['bot_info'].get('admin_id')}\n\n"
    
    if subscription:
        text += f"💳 **Subscription Details:**\n"
        text += f"• Plan: {subscription.get('tier', 'Unknown')}\n"
        text += f"• Status: {subscription.get('status', 'Unknown')}\n"
        text += f"• Price: ${subscription.get('price', 0)}\n"
        
        if subscription.get('expiry'):
            days_remaining = (subscription['expiry'] - datetime.now()).days
            text += f"• Expires: {subscription['expiry'].strftime('%Y-%m-%d %H:%M UTC')}\n"
            text += f"• Days Remaining: {days_remaining}\n"
            
            if days_remaining <= 7:
                text += f"\n⚠️ **Warning:** Subscription expires soon! Contact Mother Bot admin to renew."
            elif days_remaining <= 0:
                text += f"\n❌ **Expired:** Subscription has expired! Contact Mother Bot admin to renew."
        
        if subscription.get('created_at'):
            text += f"• Created: {subscription['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n"
    else:
        text += f"❌ **No Subscription Found**\n"
        text += f"Contact the Mother Bot administrator to set up your subscription."
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="clone_subscription_status")],
        [InlineKeyboardButton("🔙 Back to Clone Panel", callback_data="back_to_clone_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

# Feature toggle handler for clone bots
@Client.on_callback_query(filters.regex("^toggle_feature#"))
async def toggle_feature_handler(client: Client, query: CallbackQuery):
    """Handle feature toggling for clone bots"""
    user_id = query.from_user.id
    session = admin_sessions.get(user_id)
    
    if not session or session['type'] != 'clone':
        return await query.answer("❌ Session expired!", show_alert=True)
    
    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if user_id != config['bot_info'].get('admin_id'):
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
    await handle_clone_bot_features(client, query)

# Session cleanup task
async def cleanup_expired_sessions():
    """Clean up expired admin sessions"""
    current_time = datetime.now()
    expired_sessions = []
    
    for user_id, session in admin_sessions.items():
        if (current_time - session['timestamp']).seconds > 3600:  # 1 hour expiry
            expired_sessions.append(user_id)
    
    for user_id in expired_sessions:
        del admin_sessions[user_id]

# Schedule session cleanup every hour
import asyncio
asyncio.create_task(cleanup_expired_sessions())
