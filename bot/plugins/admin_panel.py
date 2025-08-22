import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import enums
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

# Store admin sessions to prevent unauthorized access
admin_sessions = {}

# Helper function to check Mother Bot admin permissions
def is_mother_admin(user_id):
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    debug_print(f"is_mother_admin check: user_id={user_id}, owner_id={owner_id}, admins={admins}")
    
    # Convert to list if it's a tuple
    if isinstance(admins, tuple):
        admin_list = list(admins)
    else:
        admin_list = admins if isinstance(admins, list) else []
    
    is_owner = user_id == owner_id
    is_admin = user_id in admin_list
    result = is_owner or is_admin
    
    debug_print(f"is_mother_admin result: {result} (is_owner: {is_owner}, is_admin: {is_admin})")
    return result

# Helper function to check Clone Bot admin permissions
def is_clone_admin(user_id, config):
    admin_id = config['bot_info'].get('admin_id')
    result = user_id == admin_id
    debug_print(f"is_clone_admin check: user_id={user_id}, expected_admin_id={admin_id}, result={result}")
    return result

# Helper function for debug printing with a common prefix
def debug_print(message):
    print(f"DEBUG: {message}")
    # Also log to actual logger
    from bot.logging import LOGGER
    logger = LOGGER(__name__)
    logger.info(f"ADMIN_DEBUG: {message}")

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command_handler(client: Client, message: Message):
    """Main admin command handler - routes to appropriate panel"""
    user_id = message.from_user.id
    debug_print(f"Received /admin command from user {user_id}")

    # Check if this is Mother Bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    debug_print(f"Bot token: {bot_token}, Config loaded: {config is not None}")

    is_clone = config['bot_info'].get('is_clone', False)
    debug_print(f"is_clone: {is_clone}")

    if not is_clone:
        # This is Mother Bot - check for Mother Bot admin
        debug_print(f"Checking Mother Bot admin permissions for user {user_id}. Owner: {Config.OWNER_ID}, Admins: {Config.ADMINS}")
        if is_mother_admin(user_id):
            await mother_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only Mother Bot administrators can access this panel.")
            debug_print(f"Access denied for user {user_id} to Mother Bot panel.")
    else:
        # This is a Clone Bot - check for Clone admin
        clone_admin_id = config['bot_info'].get('admin_id')
        debug_print(f"Checking Clone Bot admin permissions for user {user_id}. Clone Admin ID: {clone_admin_id}")
        if is_clone_admin(user_id, config):
            await clone_admin_panel(client, message)
        else:
            await message.reply_text("❌ Access denied. Only the clone administrator can access this panel.")
            debug_print(f"Access denied for user {user_id} to Clone Bot panel.")

async def mother_admin_panel(client: Client, query_or_message):
    """Display Mother Bot admin panel with comprehensive options"""
    user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id
    debug_print(f"Displaying Mother Bot admin panel for user {user_id}")

    # Check admin permissions
    if not is_mother_admin(user_id):
        debug_print(f"Invalid permission to access Mother Bot panel for user {user_id}")
        if hasattr(query_or_message, 'answer'):
            await query_or_message.answer("❌ Unauthorized access!", show_alert=True)
            return
        else:
            await query_or_message.reply_text("❌ You don't have permission to access this panel.")
            return

    # Get statistics
    try:
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())
        debug_print(f"Stats - Total Clones: {total_clones}, Active Clones: {active_clones}, Running Clones: {running_clones}, Total Subscriptions: {total_subscriptions}")
    except Exception as e:
        total_clones = active_clones = running_clones = total_subscriptions = 0
        debug_print(f"ERROR: Error getting Mother Bot stats: {e}")

    panel_text = f"🎛️ **Mother Bot Admin Panel**\n\n"
    panel_text += f"📊 **System Overview:**\n"
    panel_text += f"• Total Clones: {total_clones}\n"
    panel_text += f"• Active Clones: {active_clones}\n"
    panel_text += f"• Running Clones: {running_clones}\n"
    panel_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
    panel_text += f"🕐 **Panel Access Time:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ Pending Clone Requests", callback_data="mother_pending_requests")],
        [InlineKeyboardButton("🤖 Manage Clones", callback_data="mother_manage_clones")],
        [InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions")],
        [InlineKeyboardButton("⚙️ Global Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("📊 System Statistics", callback_data="mother_statistics")]
    ])

    debug_print("Sending Mother Bot admin panel message.")

    # Store admin session
    admin_sessions[user_id] = {
        'type': 'mother_admin',
        'timestamp': datetime.now(),
        'last_content': panel_text  # Store content to prevent duplicate edits
    }
    debug_print(f"Stored Mother Bot admin session for user {user_id}")

    if hasattr(query_or_message, 'edit_message_text'):
        try:
            # Check if content is different from last message
            last_session = admin_sessions.get(user_id, {})
            if last_session.get('last_content') != panel_text:
                await query_or_message.edit_message_text(panel_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
                admin_sessions[user_id]['last_content'] = panel_text
                debug_print(f"Successfully updated Mother Bot panel for user {user_id}")
            else:
                debug_print(f"Message content unchanged for user {user_id}, skipping edit")
                await query_or_message.answer("Panel refreshed!", show_alert=False)
        except Exception as e:
            debug_print(f"Error editing message: {e}")
            await query_or_message.answer("Panel updated!", show_alert=False)
    else:
        await query_or_message.reply_text(panel_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)

async def clone_admin_panel(client: Client, message: Message):
    """Clone Bot Admin Panel"""
    user_id = message.from_user.id
    debug_print(f"Displaying Clone Bot admin panel for user {user_id}")

    # Get bot configuration
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    debug_print(f"Bot token: {bot_token}, Config loaded: {config is not None}")


    # Validate clone admin permissions
    if not config['bot_info'].get('is_clone', False):
        debug_print(f"Command used on non-clone bot for user {user_id}")
        return await message.reply_text("❌ This command is only available in clone bots.")

    if not is_clone_admin(user_id, config):
        debug_print(f"Unauthorized access to Clone Bot panel for user {user_id}. Expected admin ID: {config['bot_info'].get('admin_id')}")
        return await message.reply_text("❌ Only the clone administrator can access this panel.")

    # Store admin session
    admin_sessions[user_id] = {'type': 'clone', 'timestamp': datetime.now(), 'bot_token': bot_token}
    debug_print(f"Stored Clone Bot admin session for user {user_id}, bot_token: {bot_token}")


    me = await client.get_me()
    subscription = config.get('subscription', {})
    debug_print(f"Bot username: {me.username}, Subscription: {subscription}")

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
    debug_print(f"Sending Clone Bot admin panel message.")
    await message.reply_text(panel_text, reply_markup=buttons)

# Handle approval/rejection callbacks
@Client.on_callback_query(filters.regex("^(approve_request|reject_request):"))
async def handle_clone_approval_callbacks(client: Client, query: CallbackQuery):
    """Handle clone request approval/rejection"""
    user_id = query.from_user.id
    debug_print(f"Clone approval callback received from user {user_id}, data: {query.data}")

    # Validate Mother Bot admin permissions
    if not is_mother_admin(user_id):
        debug_print(f"Unauthorized approval attempt from user {user_id}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    try:
        action, request_id = query.data.split(":", 1)
        debug_print(f"Processing {action} for request {request_id}")

        if action == "approve_request":
            from bot.plugins.clone_approval import approve_clone_request
            await approve_clone_request(client, query, request_id)
        elif action == "reject_request":
            from bot.plugins.clone_approval import reject_clone_request
            await reject_clone_request(client, query, request_id)

    except Exception as e:
        debug_print(f"ERROR: Error in clone approval callback: {e}")
        await query.answer("❌ Error processing request!", show_alert=True)

# Mother Bot Callback Handlers
@Client.on_callback_query(filters.regex("^mother_"))
async def mother_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Mother Bot admin panel callbacks"""
    user_id = query.from_user.id
    debug_print(f"Mother Bot callback received from user {user_id}, data: {query.data}")

    # Check admin permissions first
    if not is_mother_admin(user_id):
        debug_print(f"Permission denied for Mother Bot callback from user {user_id}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Validate or create session
    session = admin_sessions.get(user_id)
    debug_print(f"Current session for user {user_id}: {session}")
    
    if not session or session['type'] != 'mother_admin':
        debug_print(f"Creating new mother admin session for user {user_id}")
        admin_sessions[user_id] = {
            'type': 'mother_admin',
            'timestamp': datetime.now(),
            'last_content': None
        }
        session = admin_sessions[user_id]
    else:
        # Update timestamp
        session['timestamp'] = datetime.now()
        debug_print(f"Updated existing session timestamp for user {user_id}")

    callback_data = query.data
    debug_print(f"Processing callback_data: {callback_data}")

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
    elif callback_data == "mother_subscription_report":
        await handle_mother_subscription_report(client, query)
    elif callback_data == "view_all_pending":
        await handle_view_all_pending_requests(client, query)
    elif callback_data == "mother_manage_clones":
        await handle_mother_manage_clones(client, query)
    elif callback_data == "mother_subscriptions":
        await handle_mother_manage_subscriptions(client, query)
    elif callback_data == "mother_global_settings":
        await handle_mother_global_settings(client, query)
    elif callback_data == "back_to_mother_panel":
        debug_print(f"Navigating back to Mother Bot panel for user {user_id}")
        await mother_admin_panel(client, query)
    else:
        debug_print(f"Unknown Mother Bot callback action: {callback_data}")
        await query.answer("⚠️ Unknown action", show_alert=True)

# Clone Bot Callback Handlers
@Client.on_callback_query(filters.regex("^clone_"))
async def clone_admin_callbacks(client: Client, query: CallbackQuery):
    """Handle Clone Bot admin panel callbacks"""
    user_id = query.from_user.id
    debug_print(f"Clone Bot callback received from user {user_id}, data: {query.data}")

    # Get bot configuration first
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    debug_print(f"Bot token for clone callback: {bot_token}")
    
    try:
        config = await clone_config_loader.get_bot_config(bot_token)
        debug_print(f"Config loaded successfully for clone callback")
    except Exception as e:
        debug_print(f"Error loading config for clone callback: {e}")
        return await query.answer("❌ Error loading bot configuration!", show_alert=True)

    # Check clone admin permissions
    if not is_clone_admin(user_id, config):
        debug_print(f"Unauthorized access to Clone Bot panel for user {user_id}. Expected admin ID: {config['bot_info'].get('admin_id')}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Validate or create session
    session = admin_sessions.get(user_id)
    debug_print(f"Current clone session for user {user_id}: {session}")
    
    if not session or session['type'] != 'clone':
        debug_print(f"Creating new clone admin session for user {user_id}")
        admin_sessions[user_id] = {
            'type': 'clone',
            'timestamp': datetime.now(),
            'bot_token': bot_token,
            'last_content': None
        }
        session = admin_sessions[user_id]
    else:
        # Update timestamp and bot_token
        session['timestamp'] = datetime.now()
        session['bot_token'] = bot_token
        debug_print(f"Updated existing clone session for user {user_id}")

    callback_data = query.data
    debug_print(f"Processing callback_data: {callback_data}")

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
    elif callback_data == "clone_toggle_token_system":
        await handle_clone_toggle_token_system(client, query)
    elif callback_data == "back_to_clone_panel":
        debug_print(f"Navigating back to Clone Bot panel for user {user_id}")
        await clone_admin_panel(client, query.message) # Pass message to clone_admin_panel
    else:
        debug_print(f"Unknown Clone Bot callback action: {callback_data}")
        await query.answer("⚠️ Unknown action", show_alert=True)

# Mother Bot Handler Functions
async def handle_mother_pending_requests(client: Client, query: CallbackQuery):
    """Handle pending clone requests interface"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_pending_requests called by user {user_id}")

    try:
        from bot.database.clone_db import get_all_clone_requests
        pending_requests = await get_all_clone_requests("pending")
        debug_print(f"Found {len(pending_requests)} pending requests")

        text = f"⏳ **Pending Clone Requests ({len(pending_requests)})**\n\n"

        if not pending_requests:
            text += "✅ No pending requests found.\n\n"
            text += "**Commands:**\n"
            text += "• Users can request clones with `/requestclone`\n"
            text += "• Requests will appear here for approval"
        else:
            text += "**Recent Requests:**\n"
            for i, req in enumerate(pending_requests[:5], 1):
                masked_token = f"{req['bot_token'][:8]}...{req['bot_token'][-4:]}"
                text += f"**{i}. Request #{req['request_id'][:8]}...**\n"
                text += f"👤 User: {req['user_id']}\n"
                text += f"🤖 Bot: @{req['bot_username']}\n"
                text += f"🔑 Token: `{masked_token}`\n"
                text += f"💰 Plan: {req['plan_details']['name']} (${req['plan_details']['price']})\n"
                text += f"📅 Date: {req['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"

            if len(pending_requests) > 5:
                text += f"... and {len(pending_requests) - 5} more requests\n\n"

            text += "**Quick Actions:**\n"
            text += "• Click on buttons below to approve/reject\n"
            text += "• Or use commands: `/approveclone <request_id>` | `/rejectclone <request_id>`"

        buttons = []
        if pending_requests:
            # Show approve/reject buttons for first few requests
            for req in pending_requests[:3]:
                req_short = req['request_id'][:8]
                buttons.append([
                    InlineKeyboardButton(f"✅ Approve {req_short}", callback_data=f"approve_request:{req['request_id']}"),
                    InlineKeyboardButton(f"❌ Reject {req_short}", callback_data=f"reject_request:{req['request_id']}")
                ])

            if len(pending_requests) > 3:
                buttons.append([InlineKeyboardButton("📋 View All Requests", callback_data="view_all_pending")])

        buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="mother_pending_requests")])
        buttons.append([InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        debug_print(f"Successfully displayed pending requests for user {user_id}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_mother_pending_requests for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error loading pending requests**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or check the logs.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        )


async def handle_mother_create_clone(client: Client, query: CallbackQuery):
    """Handle clone creation interface"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_create_clone called by user {user_id}")
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
    debug_print(f"Displayed create clone interface for user {user_id}")

async def handle_mother_manage_subscriptions(client: Client, query: CallbackQuery):
    """Handle subscription management"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_manage_subscriptions called by user {user_id}")

    try:
        subscriptions = await get_all_subscriptions()
        debug_print(f"Fetched {len(subscriptions)} subscriptions.")

        if not subscriptions:
            subscriptions_text = "💰 **Subscription Management**\n\n❌ No subscriptions found."
        else:
            active_subs = len([s for s in subscriptions if s['status'] == 'active'])
            pending_subs = len([s for s in subscriptions if s['status'] == 'pending'])
            expired_subs = len([s for s in subscriptions if s['status'] == 'expired'])
            total_revenue = sum(s['price'] for s in subscriptions if s.get('payment_verified', False))

            subscriptions_text = f"💰 **Subscription Management**\n\n"
            subscriptions_text += f"📊 **Statistics:**\n"
            subscriptions_text += f"• Total Revenue: ${total_revenue}\n"
            subscriptions_text += f"• Active: {active_subs}\n"
            subscriptions_text += f"• Pending: {pending_subs}\n"
            subscriptions_text += f"• Expired: {expired_subs}\n\n"
            subscriptions_text += "**Recent Subscriptions:**\n"

            for sub in sorted(subscriptions, key=lambda x: x.get('created_at', datetime.now()), reverse=True)[:5]:
                clone = await get_clone(sub['_id'])
                username = clone.get('username', 'Unknown') if clone else 'Unknown'
                subscriptions_text += f"• @{username} - {sub['tier']} (${sub['price']}) - {sub['status']}\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Full Report", callback_data="mother_subscription_report")],
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])

        try:
            # Check if content changed to prevent MESSAGE_NOT_MODIFIED
            last_session = admin_sessions.get(user_id, {})
            if last_session.get('last_content') != subscriptions_text:
                await query.edit_message_text(subscriptions_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
                admin_sessions[user_id]['last_content'] = subscriptions_text
                debug_print(f"Displayed subscription management for user {user_id}")
            else:
                debug_print(f"Message content unchanged for subscription management for user {user_id}")
        except Exception as e:
            debug_print(f"Error in subscription management for user {user_id}: {e}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_mother_manage_subscriptions for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error managing subscriptions**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or check the logs.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        )

async def handle_mother_global_force_channels(client: Client, query: CallbackQuery):
    """Handle global force channels management"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_global_force_channels called by user {user_id}")

    try:
        global_channels = await get_global_force_channels()
        debug_print(f"Fetched {len(global_channels)} global force channels.")
    except Exception as e:
        global_channels = []
        debug_print(f"ERROR: Error fetching global force channels: {e}")

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
    debug_print(f"Displayed global force channels management for user {user_id}")


async def handle_mother_edit_about(client: Client, query: CallbackQuery):
    """Handle about page editing"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_edit_about called by user {user_id}")

    try:
        global_about = await get_global_about()
        debug_print(f"Fetched global about page: {'Exists' if global_about else 'None'}")
    except Exception as e:
        global_about = None
        debug_print(f"ERROR: Error fetching global about page: {e}")

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
    debug_print(f"Displayed edit about page interface for user {user_id}")


async def handle_mother_view_all_clones(client: Client, query: CallbackQuery):
    """Handle viewing all clones"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_view_all_clones called by user {user_id}")

    clones = await get_all_clones()
    debug_print(f"Fetched {len(clones)} clones.")
    running_clones = clone_manager.get_running_clones()
    debug_print(f"Found {len(running_clones)} running clones.")


    if not clones:
        clones_text = "📋 **All Clones**\n\n❌ No clones found."
    else:
        clones_text = f"📋 **All Clones ({len(clones)} total)**\n\n"

        for i, clone in enumerate(clones[:10], 1):  # Show first 10
            status_emoji = "🟢" if clone['_id'] in running_clones else "🔴"
            subscription = await get_subscription(clone['_id'])
            debug_print(f"Processing clone {i}: {clone.get('username', 'Unknown')}, Status: {clone['status']}, Subscription: {subscription}")


            clones_text += f"**{i}. @{clone.get('username', 'Unknown')}**\n"
            clones_text += f"   {status_emoji} Status: {clone['status']}\n"
            clones_text += f"   👤 Admin: {clone['admin_id']}\n"

            if subscription:
                clones_text += f"   💳 Subscription: {subscription['tier']} (${subscription['price']})\n"
                if subscription.get('expiry_date'):
                    clones_text += f"   📅 Expires: {subscription['expiry_date'].strftime('%Y-%m-%d')}\n"
            else:
                clones_text += f"   💳 Subscription: None\n"
            clones_text += "\n"

        if len(clones) > 10:
            clones_text += f"... and {len(clones) - 10} more clones"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="mother_view_all_clones")],
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])

    try:
        # Check if content changed to prevent MESSAGE_NOT_MODIFIED
        last_session = admin_sessions.get(user_id, {})
        if last_session.get('last_content') != clones_text:
            await query.edit_message_text(clones_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
            admin_sessions[user_id]['last_content'] = clones_text
            debug_print(f"Displayed all clones list for user {user_id}")
        else:
            debug_print(f"Message content unchanged for clones list for user {user_id}")
    except Exception as e:
        debug_print(f"Error displaying clones list for user {user_id}: {e}")


async def handle_mother_disable_clone(client: Client, query: CallbackQuery):
    """Handle clone disabling/deletion"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_disable_clone called by user {user_id}")

    clones = await get_all_clones()
    debug_print(f"Fetched {len(clones)} clones.")


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
    debug_print(f"Displayed disable/delete clone interface for user {user_id}")


async def handle_mother_statistics(client: Client, query: CallbackQuery):
    """Handle system statistics"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_statistics called by user {user_id}")

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

        debug_print(f"Stats - Total Clones: {total_clones}, Active Clones: {active_clones}, Running Clones: {len(running_clones)}, Total Subscriptions: {len(subscriptions)}")
        debug_print(f"Financials - Total Revenue: ${total_revenue}, Monthly Revenue: ${monthly_revenue}")

        panel_text = f"📊 **System Statistics**\n\n"
        panel_text += f"🤖 **Clones:**\n"
        panel_text += f"• Total Created: {total_clones}\n"
        panel_text += f"• Currently Running: {len(running_clones)}\n"
        panel_text += f"• Active: {active_clones}\n"
        panel_text += f"• Inactive: {total_clones - active_clones}\n\n"

        panel_text += f"💰 **Financial:**\n"
        panel_text += f"• Total Revenue: ${total_revenue}\n"
        panel_text += f"• This Month: ${monthly_revenue}\n"
        panel_text += f"• Active Subscriptions: {len([s for s in subscriptions if s['status'] == 'active'])}\n\n"

        panel_text += f"⏱️ **System:**\n"
        panel_text += f"• Mother Bot: Running\n"
        panel_text += f"• Clone Manager: Active\n"
        panel_text += f"• Database: Connected\n"
        panel_text += f"• Last Updated: {datetime.now().strftime('%H:%M:%S UTC')}"

    except Exception as e:
        panel_text = f"📊 **System Statistics**\n\n❌ Error loading statistics: {str(e)}"
        debug_print(f"ERROR: Error in handle_mother_statistics for user {user_id}: {e}")

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="mother_statistics")],
        [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
    ])

    try:
        # Always try to edit message for statistics (data changes frequently)
        await query.edit_message_text(panel_text, reply_markup=buttons, parse_mode=enums.ParseMode.MARKDOWN)
        admin_sessions[user_id]['last_content'] = panel_text
        debug_print(f"Displayed system statistics for user {user_id}")
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            debug_print(f"Statistics content unchanged for user {user_id}")
            await query.answer("Statistics refreshed!", show_alert=False)
        else:
            debug_print(f"Error displaying system statistics for user {user_id}: {e}")
            await query.answer("Error loading statistics!", show_alert=True)


async def handle_mother_subscription_report(client: Client, query: CallbackQuery):
    """Handle detailed subscription report"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_subscription_report called by user {user_id}")

    try:
        subscriptions = await get_all_subscriptions()

        text = f"📊 **Detailed Subscription Report**\n\n"

        if not subscriptions:
            text += "❌ No subscriptions found."
        else:
            for sub in subscriptions:
                clone = await get_clone(sub['_id'])
                username = clone.get('username', 'Unknown') if clone else 'Unknown'

                text += f"**@{username}**\n"
                text += f"• Plan: {sub['tier']} (${sub['price']})\n"
                text += f"• Status: {sub['status']}\n"
                text += f"• Payment Verified: {'✅' if sub.get('payment_verified', False) else '❌'}\n"
                text += f"• Created: {sub.get('created_at', 'Unknown')}\n"
                if sub.get('expiry_date'):
                    text += f"• Expires: {sub['expiry_date'].strftime('%Y-%m-%d')}\n"
                text += "\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Subscriptions", callback_data="mother_manage_subscriptions")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
        debug_print(f"Displayed subscription report for user {user_id}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_mother_subscription_report for user {user_id}: {e}")
        await query.answer("❌ Error loading report!", show_alert=True)

async def handle_mother_global_settings(client: Client, query: CallbackQuery):
    """Handle global settings management"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_global_settings called by user {user_id}")

    try:
        global_channels = await get_global_force_channels()
        global_about = await get_global_about()
        
        text = f"⚙️ **Global Settings Management**\n\n"
        
        text += f"📢 **Global Force Channels ({len(global_channels)}):**\n"
        if global_channels:
            for i, channel in enumerate(global_channels[:3], 1):
                text += f"{i}. {channel}\n"
            if len(global_channels) > 3:
                text += f"... and {len(global_channels) - 3} more\n"
        else:
            text += "❌ No global force channels set\n"
            
        text += f"\n📄 **Global About Page:**\n"
        if global_about:
            text += f"✅ About page configured ({len(global_about)} characters)\n"
        else:
            text += "❌ No global about page set\n"
            
        text += f"\n**Quick Actions:**\n"
        text += f"• Use buttons below for management\n"
        text += f"• Or use commands for detailed control"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Manage Force Channels", callback_data="mother_global_force_channels")],
            [InlineKeyboardButton("📄 Edit About Page", callback_data="mother_edit_about")],
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
        debug_print(f"Displayed global settings for user {user_id}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_mother_global_settings for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error loading global settings**\n\nError: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        )

async def handle_mother_manage_clones(client: Client, query: CallbackQuery):
    """Handle clone management interface"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_manage_clones called by user {user_id}")

    try:
        clones = await get_all_clones()
        running_clones = clone_manager.get_running_clones()
        
        text = f"🤖 **Clone Management ({len(clones)} total)**\n\n"
        
        if not clones:
            text += "❌ No clones found."
        else:
            text += "**Clone Status Overview:**\n"
            for clone in clones[:5]:
                status_emoji = "🟢" if clone['_id'] in running_clones else "🔴"
                text += f"{status_emoji} @{clone.get('username', 'Unknown')} - {clone['status']}\n"
            
            if len(clones) > 5:
                text += f"... and {len(clones) - 5} more clones\n"
            
            text += f"\n**Commands:**\n"
            text += f"• `/startclone <bot_id>` - Start a clone\n"
            text += f"• `/stopclone <bot_id>` - Stop a clone\n"
            text += f"• `/restartclone <bot_id>` - Restart a clone\n"
            text += f"• `/deleteclone <bot_id>` - Delete a clone"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 View All Clones", callback_data="mother_view_all_clones")],
            [InlineKeyboardButton("🗑️ Delete Clone", callback_data="mother_disable_clone")],
            [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)
        debug_print(f"Displayed clone management for user {user_id}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_mother_manage_clones for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error managing clones**\n\nError: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Panel", callback_data="back_to_mother_panel")]
            ])
        )

async def handle_view_all_pending_requests(client: Client, query: CallbackQuery):
    """Handle viewing all pending requests with pagination"""
    user_id = query.from_user.id
    debug_print(f"handle_view_all_pending_requests called by user {user_id}")

    try:
        from bot.database.clone_db import get_all_clone_requests
        pending_requests = await get_all_clone_requests("pending")

        text = f"📋 **All Pending Clone Requests ({len(pending_requests)})**\n\n"

        if not pending_requests:
            text += "✅ No pending requests found."
        else:
            for i, req in enumerate(pending_requests, 1):
                masked_token = f"{req['bot_token'][:8]}...{req['bot_token'][-4:]}"
                text += f"**{i}. Request #{req['request_id'][:8]}...**\n"
                text += f"👤 User: {req['user_id']}\n"
                text += f"🤖 Bot: @{req['bot_username']}\n"
                text += f"🔑 Token: `{masked_token}`\n"
                text += f"💰 Plan: {req['plan_details']['name']}\n"
                text += f"📅 Date: {req['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"

        buttons = []

        # Add approve/reject buttons for first 3 requests
        for req in pending_requests[:3]:
            req_short = req['request_id'][:8]
            buttons.append([
                InlineKeyboardButton(f"✅ Approve {req_short}", callback_data=f"approve_request:{req['request_id']}"),
                InlineKeyboardButton(f"❌ Reject {req_short}", callback_data=f"reject_request:{req['request_id']}")
            ])

        buttons.append([InlineKeyboardButton("🔙 Back to Pending Requests", callback_data="mother_pending_requests")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        debug_print(f"Displayed all pending requests for user {user_id}")

    except Exception as e:
        debug_print(f"ERROR: Error in handle_view_all_pending_requests for user {user_id}: {e}")
        await query.answer("❌ Error loading requests!", show_alert=True)

async def handle_clone_toggle_token_system(client: Client, query: CallbackQuery):
    """Handle toggling token system for clone bot"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_toggle_token_system called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for token toggle from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    if not is_clone_admin(user_id, config):
        debug_print(f"Unauthorized token toggle attempt from user {user_id}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    try:
        bot_id = bot_token.split(':')[0]
        current_config = await get_clone_config(bot_id)
        token_settings = current_config.get('token_settings', {})

        current_status = token_settings.get('enabled', True)
        new_status = not current_status
        token_settings['enabled'] = new_status

        await update_clone_config(bot_id, {'token_settings': token_settings})
        clone_config_loader.clear_cache(bot_token)

        status_text = "enabled" if new_status else "disabled"
        await query.answer(f"✅ Token system {status_text}!", show_alert=True)
        debug_print(f"Token system toggled to {status_text} for bot {bot_id}")

        # Refresh the token config panel
        await handle_clone_token_command_config(client, query)

    except Exception as e:
        debug_print(f"ERROR: Error toggling token system for user {user_id}: {e}")
        await query.answer("❌ Error toggling token system!", show_alert=True)


# Clone Bot Handler Functions
async def handle_clone_local_force_channels(client: Client, query: CallbackQuery):
    """Handle local force channels management"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_local_force_channels called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_local_force_channels from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    channels = config.get('channels', {})
    local_force = channels.get('force_channels', [])
    global_force = channels.get('global_force_channels', [])
    debug_print(f"Local force channels: {local_force}, Global force channels: {global_force}")


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
    debug_print(f"Displayed local force channels management for user {user_id}")


async def handle_clone_request_channels(client: Client, query: CallbackQuery):
    """Handle request channels management"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_request_channels called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_request_channels from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    channels = config.get('channels', {})
    request_channels = channels.get('request_channels', [])
    debug_print(f"Request channels: {request_channels}")


    text = f"🔔 **Request Channels Management**\n\n"
    text += f"**Current Request Channels:**\n"

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
    debug_print(f"Displayed request channels management for user {user_id}")


async def handle_clone_token_command_config(client: Client, query: CallbackQuery):
    """Handle token/command configuration"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_token_command_config called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_token_command_config from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    token_settings = config.get('token_settings', {})
    debug_print(f"Token settings: {token_settings}")


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
    debug_print(f"Displayed token/command configuration for user {user_id}")


async def handle_clone_token_pricing(client: Client, query: CallbackQuery):
    """Handle token pricing configuration"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_token_pricing called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_token_pricing from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    token_settings = config.get('token_settings', {})
    debug_print(f"Token settings for pricing: {token_settings}")


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
    debug_print(f"Displayed token pricing configuration for user {user_id}")


async def handle_clone_bot_features(client: Client, query: CallbackQuery):
    """Handle bot features management"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_bot_features called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_bot_features from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    features = config.get('features', {})
    debug_print(f"Current features: {features}")


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
    debug_print(f"Displayed bot features management for user {user_id}")


async def handle_clone_subscription_status(client: Client, query: CallbackQuery):
    """Handle subscription status viewing"""
    user_id = query.from_user.id
    debug_print(f"handle_clone_subscription_status called by user {user_id}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for handle_clone_subscription_status from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    subscription = config.get('subscription', {})
    me = await client.get_me()
    debug_print(f"Bot username: {me.username}, Subscription details: {subscription}")


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
    debug_print(f"Displayed subscription status for user {user_id}")


# Feature toggle handler for clone bots
@Client.on_callback_query(filters.regex("^toggle_feature#"))
async def toggle_feature_handler(client: Client, query: CallbackQuery):
    """Handle feature toggling for clone bots"""
    user_id = query.from_user.id
    debug_print(f"toggle_feature_handler called by user {user_id}, data: {query.data}")

    session = admin_sessions.get(user_id)
    if not session or session['type'] != 'clone':
        debug_print(f"Invalid session for toggle_feature_handler from user {user_id}")
        return await query.answer("❌ Session expired!", show_alert=True)

    bot_token = session.get('bot_token', getattr(client, 'bot_token', Config.BOT_TOKEN))
    config = await clone_config_loader.get_bot_config(bot_token)

    if not is_clone_admin(user_id, config):
        debug_print(f"Unauthorized access to toggle feature for user {user_id}. Expected admin ID: {config['bot_info'].get('admin_id')}")
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    feature = query.data.split("#")[1]
    bot_id = bot_token.split(':')[0]
    debug_print(f"Toggling feature '{feature}' for bot ID '{bot_id}'")


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
    debug_print(f"Feature '{feature}' toggled to {status} for bot ID '{bot_id}'")


    # Refresh the features panel
    await handle_clone_bot_features(client, query)

# Session cleanup task
async def cleanup_expired_sessions():
    """Clean up expired admin sessions"""
    debug_print("Running cleanup_expired_sessions task...")
    current_time = datetime.now()
    expired_sessions = []

    for user_id, session in admin_sessions.items():
        if (current_time - session['timestamp']).total_seconds() > 3600:  # 1 hour expiry
            expired_sessions.append(user_id)
            debug_print(f"Session expired for user {user_id}")

    for user_id in expired_sessions:
        del admin_sessions[user_id]
        debug_print(f"Removed expired session for user {user_id}")
    debug_print(f"cleanup_expired_sessions finished. Removed {len(expired_sessions)} sessions.")

# Schedule session cleanup every hour
# Ensure this runs only once by scheduling it outside of any handler that might be called multiple times.
# A common pattern is to schedule it when the bot starts.
# asyncio.create_task(cleanup_expired_sessions()) # This line is commented out to prevent multiple task creations if this file is imported multiple times.
# The actual scheduling should be handled by the main bot startup logic.