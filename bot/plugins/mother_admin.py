import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from clone_manager import clone_manager

# Update pricing plans with new structure
PREMIUM_PLANS = {
            "monthly": {
                "name": "Monthly Plan",
                "price": "$2.99",
                "duration": "1 Month",
                "per_month": "$2.99",
                "discount": "0%",
                "description": "Simple, accessible entry point"
            },
            "quarterly": {
                "name": "3-Month Plan", 
                "price": "$7.99",
                "duration": "3 Months",
                "per_month": "$2.66",
                "discount": "11%",
                "description": "Slight discount for commitment"
            },
            "biannual": {
                "name": "6-Month Plan",
                "price": "$14.99", 
                "duration": "6 Months",
                "per_month": "$2.50",
                "discount": "16%",
                "description": "Moderate discount for longer commitment"
            },
            "annual": {
                "name": "12-Month Plan",
                "price": "$26.99",
                "duration": "12 Months", 
                "per_month": "$2.25",
                "discount": "25%",
                "description": "Best value with maximum savings"
            }
        }

@Client.on_message(filters.command("motheradmin") & filters.private)
async def mother_admin_panel(client: Client, message: Message):
    """Mother Bot Admin Panel"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied. Only Mother Bot admins can access this panel.")

    # Get current stats for dashboard display
    try:
        running_clones = len(clone_manager.get_running_clones())
        total_clones = len(await get_all_clones())
    except:
        running_clones = 0
        total_clones = 0

    buttons = InlineKeyboardMarkup([
        # Row 1: Main Management
        [
            InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone"),
            InlineKeyboardButton("📋 Manage Clones", callback_data="mother_manage_clones")
        ],
        # Row 2: Financial & Settings
        [
            InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions"),
            InlineKeyboardButton("🌐 Global Settings", callback_data="mother_global_settings")
        ],
        # Row 3: Analytics & System
        [
            InlineKeyboardButton("📊 Statistics", callback_data="mother_statistics"),
            InlineKeyboardButton("🔧 System Info", callback_data="mother_system_info")
        ],
        # Row 4: User & Database Management
        [
            InlineKeyboardButton("👥 User Management", callback_data="mother_users"),
            InlineKeyboardButton("📢 Broadcast", callback_data="mother_broadcast")
        ]
    ])

    await message.reply_text(
        f"🎛️ **Mother Bot Admin Panel**\n\n"
        f"📊 **Quick Stats:**\n"
        f"• Running Clones: {running_clones}/{total_clones}\n"
        f"• System Status: ✅ Online\n\n"
        f"**Welcome to the administration center.**\n"
        f"Choose an option below to manage your bot network:",
        reply_markup=buttons)

@Client.on_callback_query(filters.regex("^mother_create_clone$"))
async def create_clone_callback(client: Client, query: CallbackQuery):
    """Handle clone creation"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    await query.edit_message_text(
        "🤖 **Create New Clone Bot**\n\n"
        "To create a new clone, provide the following information:\n\n"
        "**Format:** `/createclone <bot_token> <admin_id> <db_url> [tier]`\n\n"
        "**Example:**\n"
        "`/createclone 123456:ABC-DEF... 123456789 mongodb://user:pass@host/db monthly`\n\n"
        "**Available Tiers:**\n"
        "• `monthly` - $2.99/month\n"
        "• `quarterly` - $7.99/3 months\n"
        "• `biannual` - $14.99/6 months\n"
        "• `annual` - $26.99/year\n\n"
        "If tier is not specified, `monthly` will be used by default.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

@Client.on_message(filters.command("createclone") & filters.private)
async def create_clone_command(client: Client, message: Message):
    """Create a new clone bot"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot admins can create clones.")

    if len(message.command) < 4:
        return await message.reply_text(
            "❌ **Invalid format!**\n\n"
            "Usage: `/createclone <bot_token> <admin_id> <db_url> [tier]`\n\n"
            "Example:\n"
            "`/createclone 123456:ABC-DEF... 123456789 mongodb://user:pass@host/db monthly`"
        )

    bot_token = message.command[1]
    try:
        admin_id = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ Admin ID must be a valid number!")

    db_url = message.command[3]
    tier = message.command[4] if len(message.command) > 4 else "monthly"

    # Validate tier
    if tier not in PREMIUM_PLANS:
        return await message.reply_text(
            f"❌ Invalid tier! Available tiers: {', '.join(PREMIUM_PLANS.keys())}"
        )

    processing_msg = await message.reply_text("🔄 Creating clone bot... Please wait.")

    try:
        success, result = await clone_manager.create_clone(bot_token, admin_id, db_url, tier)

        if success:
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Start Clone", callback_data=f"start_clone#{result['bot_id']}")],
                [InlineKeyboardButton("💳 Verify Payment", callback_data=f"verify_payment#{result['bot_id']}")],
                [InlineKeyboardButton("📋 Manage Clones", callback_data="mother_manage_clones")]
            ])

            await processing_msg.edit_text(
                f"🎉 **Clone Created Successfully!**\n\n"
                f"🤖 **Bot Username:** @{result['username']}\n"
                f"🆔 **Bot ID:** {result['bot_id']}\n"
                f"👤 **Admin ID:** {result['admin_id']}\n"
                f"💰 **Tier:** {tier}\n"
                f"📊 **Status:** Pending Payment\n\n"
                f"⚠️ **Note:** The clone will start after payment verification.",
                reply_markup=buttons
            )
        else:
            await processing_msg.edit_text(f"❌ **Failed to create clone:**\n{result}")

    except Exception as e:
        await processing_msg.edit_text(f"❌ **Error creating clone:**\n{str(e)}")

@Client.on_callback_query(filters.regex("^mother_manage_clones$"))
async def manage_clones_callback(client: Client, query: CallbackQuery):
    """Show clone management interface"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get all clones
    clones = await get_all_clones()
    running_clones = clone_manager.get_running_clones()

    if not clones:
        await query.edit_message_text(
            "📝 **No Clones Found**\n\n"
            "You haven't created any clone bots yet.\n"
            "Use the 'Create Clone' option to get started!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone")],
                [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
            ])
        )
        return

    clone_list = "🤖 **Clone Management**\n\n"
    buttons = []

    for i, clone in enumerate(clones[:10], 1):  # Show max 10 clones
        status_emoji = "🟢" if clone['_id'] in running_clones else "🔴"
        subscription = await get_subscription(clone['_id'])
        sub_status = subscription['status'] if subscription else "No Subscription"

        clone_list += f"**{i}.** @{clone.get('username', 'Unknown')}\n"
        clone_list += f"   {status_emoji} Status: {clone['status']}\n"
        clone_list += f"   💳 Subscription: {sub_status}\n"
        if subscription:
            clone_list += f"   📅 Expires: {subscription['expiry_date'].strftime('%Y-%m-%d')}\n"
        clone_list += "\n"

        # Add management buttons for each clone
        buttons.append([
            InlineKeyboardButton(f"🛠️ Manage {clone.get('username', clone['_id'][:8])}", 
                               callback_data=f"manage_clone#{clone['_id']}")
        ])

    buttons.extend([
        [InlineKeyboardButton("🤖 Create New Clone", callback_data="mother_create_clone")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(
        clone_list,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^manage_clone#"))
async def manage_specific_clone(client: Client, query: CallbackQuery):
    """Manage a specific clone"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_id = query.data.split("#")[1]
    clone = await get_clone(clone_id)
    subscription = await get_subscription(clone_id)

    if not clone:
        return await query.answer("❌ Clone not found!", show_alert=True)

    running_clones = clone_manager.get_running_clones()
    is_running = clone_id in running_clones

    status_text = f"🛠️ **Managing Clone: @{clone.get('username', 'Unknown')}**\n\n"
    status_text += f"🆔 **Bot ID:** {clone_id}\n"
    status_text += f"👤 **Admin ID:** {clone['admin_id']}\n"
    status_text += f"📊 **Status:** {clone['status']}\n"
    status_text += f"🔄 **Running:** {'Yes' if is_running else 'No'}\n"

    if subscription:
        status_text += f"💳 **Subscription:** {subscription['tier']}\n"
        status_text += f"💰 **Price:** ${subscription['price']}\n"
        status_text += f"📅 **Expires:** {subscription['expiry_date'].strftime('%Y-%m-%d %H:%M')}\n"
        status_text += f"✅ **Payment Status:** {subscription['status']}\n"
    else:
        status_text += f"💳 **Subscription:** No active subscription\n"

    buttons = []

    if is_running:
        buttons.append([InlineKeyboardButton("🛑 Stop Clone", callback_data=f"stop_clone#{clone_id}")])
    else:
        buttons.append([InlineKeyboardButton("▶️ Start Clone", callback_data=f"start_clone#{clone_id}")])

    if subscription and subscription['status'] != 'active':
        buttons.append([InlineKeyboardButton("💳 Verify Payment", callback_data=f"verify_payment#{clone_id}")])

    buttons.extend([
        [InlineKeyboardButton("⏰ Extend Subscription", callback_data=f"extend_sub#{clone_id}")],
        [InlineKeyboardButton("🗑️ Deactivate Clone", callback_data=f"deactivate_clone#{clone_id}")],
        [InlineKeyboardButton("« Back to Clones", callback_data="mother_manage_clones")]
    ])

    await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^(start_clone|stop_clone|verify_payment|deactivate_clone|extend_sub)#"))
async def clone_actions(client: Client, query: CallbackQuery):
    """Handle clone actions"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    action, clone_id = query.data.split("#")

    if action == "start_clone":
        # Check subscription before starting
        subscription = await get_subscription(clone_id)
        if not subscription or subscription['status'] != 'active':
            return await query.answer("❌ Cannot start clone: No active subscription!", show_alert=True)
        
        # Check if features are enabled in settings (placeholder for actual settings check)
        # For now, assuming features are always enabled if subscription is active
        # You'll need to integrate with your settings logic here.
        # Example: if not await is_feature_enabled(clone_id, "random"): return await query.answer("Random feature disabled.", show_alert=True)

        success, message = await clone_manager.start_clone(clone_id)
        await query.answer(f"✅ {message}" if success else f"❌ {message}", show_alert=True)

    elif action == "stop_clone":
        success, message = await clone_manager.stop_clone(clone_id)
        await query.answer(f"✅ {message}" if success else f"❌ {message}", show_alert=True)

    elif action == "verify_payment":
        # Activate subscription
        await activate_subscription(clone_id)
        await activate_clone(clone_id)
        await query.answer("✅ Payment verified! Subscription activated. Clone can now be started.", show_alert=True)

    elif action == "deactivate_clone":
        await deactivate_clone(clone_id)
        await clone_manager.stop_clone(clone_id)
        await query.answer("✅ Clone deactivated and stopped.", show_alert=True)

    elif action == "extend_sub":
        # Show extension options
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 1 Month (+$2.99)", callback_data="extend_1m#"+clone_id)],
            [InlineKeyboardButton("📅 3 Months (+$7.99)", callback_data="extend_3m#"+clone_id)],
            [InlineKeyboardButton("📅 6 Months (+$14.99)", callback_data="extend_6m#"+clone_id)],
            [InlineKeyboardButton("📅 1 Year (+$26.99)", callback_data="extend_1y#"+clone_id)],
            [InlineKeyboardButton("« Back", callback_data=f"manage_clone#{clone_id}")]
        ])

        await query.edit_message_text(
            "⏰ **Extend Subscription**\n\n"
            "Choose extension period:",
            reply_markup=buttons
        )
        return

    # Refresh the management page
    await manage_specific_clone(client, query)

@Client.on_callback_query(filters.regex("^mother_subscriptions$"))
async def subscriptions_panel(client: Client, query: CallbackQuery):
    """Show subscriptions management"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    subscriptions_data = await get_all_subscriptions()

    if not subscriptions_data:
        await query.edit_message_text(
            "💳 **No Subscriptions Found**\n\n"
            "No clone subscriptions have been created yet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
            ])
        )
        return

    # Calculate statistics
    total_revenue = sum(float(sub['price'].replace('$', '')) for sub in subscriptions_data if sub['payment_verified'])
    active_subs = len([sub for sub in subscriptions_data if sub['status'] == 'active'])
    pending_subs = len([sub for sub in subscriptions_data if sub['status'] == 'pending'])
    expired_subs = len([sub for sub in subscriptions_data if sub['status'] == 'expired'])

    subs_text = f"💰 **Subscription Management**\n\n"
    subs_text += f"📊 **Statistics:**\n"
    subs_text += f"💵 Total Revenue: ${total_revenue:.2f}\n"
    subs_text += f"✅ Active: {active_subs}\n"
    subs_text += f"⏳ Pending: {pending_subs}\n"
    subs_text += f"❌ Expired: {expired_subs}\n\n"

    subs_text += f"**Recent Subscriptions:**\n"
    for sub in sorted(subscriptions_data, key=lambda x: x['created_at'], reverse=True)[:5]:
        clone = await get_clone(sub['_id'])
        username = clone.get('username', 'Unknown') if clone else 'Unknown'
        subs_text += f"• @{username} - {sub['tier']} (${sub['price']}) - {sub['status']}\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Full Report", callback_data="full_subscription_report")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(subs_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^mother_global_settings$"))
async def global_settings_panel(client: Client, query: CallbackQuery):
    """Show global settings management"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    global_force_channels = await get_global_force_channels()
    global_about = await get_global_about()

    settings_text = f"🌐 **Global Settings**\n\n"
    settings_text += f"**Global Force Channels:**\n"
    if global_force_channels:
        for channel in global_force_channels:
            settings_text += f"• {channel}\n"
    else:
        settings_text += "No global force channels set\n"

    settings_text += f"\n**Global About Page:**\n"
    settings_text += f"{'Set' if global_about else 'Not set'}\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Manage Force Channels", callback_data="manage_global_channels")],
        [InlineKeyboardButton("📄 Edit About Page", callback_data="edit_global_about")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(settings_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^mother_statistics$"))
async def statistics_panel(client: Client, query: CallbackQuery):
    """Show system statistics"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clones = await get_all_clones()
    subscriptions_data = await get_all_subscriptions()
    running_clones = clone_manager.get_running_clones()

    stats_text = f"📊 **Mother Bot Statistics**\n\n"
    stats_text += f"🤖 **Clones:**\n"
    stats_text += f"• Total Created: {len(clones)}\n"
    stats_text += f"• Currently Running: {len(running_clones)}\n"
    stats_text += f"• Active: {len([c for c in clones if c['status'] == 'active'])}\n"
    stats_text += f"• Deactivated: {len([c for c in clones if c['status'] == 'deactivated'])}\n\n"

    stats_text += f"💰 **Financial:**\n"
    total_revenue = sum(float(sub['price'].replace('$', '')) for sub in subscriptions_data if sub['payment_verified'])
    monthly_revenue = sum(float(sub['price'].replace('$', '')) for sub in subscriptions_data 
                         if sub['payment_verified'] and sub['created_at'] > datetime.now() - timedelta(days=30))
    stats_text += f"• Total Revenue: ${total_revenue:.2f}\n"
    stats_text += f"• This Month: ${monthly_revenue:.2f}\n"
    stats_text += f"• Active Subscriptions: {len([s for s in subscriptions_data if s['status'] == 'active'])}\n\n"

    stats_text += f"⏱️ **System Uptime:**\n"
    stats_text += f"• Mother Bot: Running\n"
    stats_text += f"• Clone Manager: Active\n"
    stats_text += f"• Database: Connected\n"

    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="mother_statistics")],
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

# Back to main panel handler
@Client.on_callback_query(filters.regex("^back_to_mother_panel$"))
async def back_to_panel(client: Client, query: CallbackQuery):
    """Go back to main admin panel"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get current stats for dashboard display
    try:
        running_clones = len(clone_manager.get_running_clones())
        total_clones = len(await get_all_clones())
    except:
        running_clones = 0
        total_clones = 0

    buttons = InlineKeyboardMarkup([
        # Row 1: Main Management
        [
            InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone"),
            InlineKeyboardButton("📋 Manage Clones", callback_data="mother_manage_clones")
        ],
        # Row 2: Financial & Settings
        [
            InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions"),
            InlineKeyboardButton("🌐 Global Settings", callback_data="mother_global_settings")
        ],
        # Row 3: Analytics & System
        [
            InlineKeyboardButton("📊 Statistics", callback_data="mother_statistics"),
            InlineKeyboardButton("🔧 System Info", callback_data="mother_system_info")
        ],
        # Row 4: User & Database Management
        [
            InlineKeyboardButton("👥 User Management", callback_data="mother_users"),
            InlineKeyboardButton("📢 Broadcast", callback_data="mother_broadcast")
        ]
    ])

    await query.edit_message_text(
        f"🎛️ **Mother Bot Admin Panel**\n\n"
        f"📊 **Quick Stats:**\n"
        f"• Running Clones: {running_clones}/{total_clones}\n"
        f"• System Status: ✅ Online\n\n"
        f"**Welcome to the administration center.**\n"
        f"Choose an option below to manage your bot network:",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("^mother_create_clone$"))
async def create_clone_callback(client: Client, query: CallbackQuery):
    """Handle create clone callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    await query.edit_message_text(
        "🤖 **Create New Clone Bot**\n\n"
        "To create a new clone bot, you need a bot token from BotFather.\n\n"
        "📋 **Steps:**\n"
        "1. Go to @BotFather on Telegram\n"
        "2. Create a new bot with /newbot\n"
        "3. Copy the bot token\n"
        "4. Use /createclone command with the token\n\n"
        "**Usage:** /createclone <bot_token>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 How to Get Token", url="https://t.me/BotFather")],
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

@Client.on_callback_query(filters.regex("^mother_manage_clones$"))
async def manage_clones_callback(client: Client, query: CallbackQuery):
    """Handle manage clones callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get all clones from database
    all_clones = await get_all_clones()

    if not all_clones:
        await query.edit_message_text(
            "📋 **Clone Management**\n\n"
            "❌ No clones found.\n\n"
            "Create your first clone with /createclone command.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone")],
                [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
            ])
        )
        return

    clone_text = "📋 **Active Clone Bots**\n\n"
    buttons = []

    for clone in all_clones[:10]:  # Show first 10 clones
        status = "🟢 Active" if clone.get('status') == 'active' else "🔴 Inactive"
        clone_text += f"🤖 **@{clone.get('username', 'Unknown')}**\n"
        clone_text += f"   📊 Status: {status}\n"
        clone_text += f"   👤 Owner: {clone.get('admin_id')}\n\n"

        buttons.append([
            InlineKeyboardButton(f"⚙️ {clone.get('username', 'Bot')}", 
                               callback_data=f"manage_clone_{clone.get('_id', clone.get('bot_id', 'unknown'))}")
        ])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="mother_manage_clones")])
    buttons.append([InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")])

    await query.edit_message_text(clone_text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^mother_subscriptions$"))
async def subscriptions_callback(client: Client, query: CallbackQuery):
    """Handle subscriptions callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get subscription statistics
    total_subs = await get_total_subscriptions()
    active_subs = await get_active_subscriptions()
    expired_subs = total_subs - active_subs

    subs_text = f"💰 **Subscription Management**\n\n"
    subs_text += f"📊 **Statistics:**\n"
    subs_text += f"• Total Subscriptions: {total_subs}\n"
    subs_text += f"• Active: {active_subs}\n"
    subs_text += f"• Expired: {expired_subs}\n\n"
    subs_text += f"💡 Use /premium command to manage individual subscriptions."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Detailed Report", callback_data="subscription_report")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="mother_subscriptions")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(subs_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^mother_global_settings$"))
async def global_settings_callback(client: Client, query: CallbackQuery):
    """Handle global settings callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    try:
        global_force_channels = await get_global_force_channels()
        global_about = await get_global_about()
    except Exception as e:
        global_force_channels = []
        global_about = None
        print(f"Error getting global settings: {e}")

    settings_text = f"🌐 **Global Settings**\n\n"
    settings_text += f"**Global Force Channels:**\n"
    if global_force_channels:
        for channel in global_force_channels:
            settings_text += f"• {channel}\n"
    else:
        settings_text += "No global force channels set\n"

    settings_text += f"\n**Global About Page:**\n"
    settings_text += f"{'Set' if global_about else 'Not set'}\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Manage Force Channels", callback_data="manage_global_channels")],
        [InlineKeyboardButton("📄 Edit About Page", callback_data="edit_global_about")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(settings_text, reply_markup=buttons)

# Add handlers for new dashboard buttons
@Client.on_callback_query(filters.regex("^mother_system_info$"))
async def system_info_callback(client: Client, query: CallbackQuery):
    """Handle system info callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    import psutil
    import platform
    from datetime import datetime

    system_info = f"🔧 **System Information**\n\n"
    system_info += f"💻 **Server Details:**\n"
    system_info += f"• OS: {platform.system()} {platform.release()}\n"
    system_info += f"• CPU Usage: {psutil.cpu_percent():.1f}%\n"
    system_info += f"• Memory Usage: {psutil.virtual_memory().percent:.1f}%\n"
    system_info += f"• Disk Usage: {psutil.disk_usage('/').percent:.1f}%\n\n"

    system_info += f"🤖 **Bot Network:**\n"
    system_info += f"• Mother Bot: ✅ Running\n"
    system_info += f"• Active Clones: {len(clone_manager.get_running_clones())}\n"
    system_info += f"• Database: ✅ Connected\n\n"

    system_info += f"⏱️ **Uptime:**\n"
    system_info += f"• Since: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    await query.edit_message_text(
        system_info,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="mother_system_info")],
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

@Client.on_callback_query(filters.regex("^mother_users$"))
async def users_callback(client: Client, query: CallbackQuery):
    """Handle user management callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    from bot.database.users import get_users_count

    try:
        total_users = await get_users_count()
    except:
        total_users = 0

    users_text = f"👥 **User Management**\n\n"
    users_text += f"📊 **Statistics:**\n"
    users_text += f"• Total Users: {total_users}\n\n"
    users_text += f"🛠️ **Available Tools:**\n"
    users_text += f"• View user statistics\n"
    users_text += f"• Broadcast messages to users\n"
    users_text += f"• Manage user access\n"

    await query.edit_message_text(
        users_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View Stats", callback_data="user_detailed_stats")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="mother_users")],
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

@Client.on_callback_query(filters.regex("^mother_broadcast$"))
async def broadcast_callback(client: Client, query: CallbackQuery):
    """Handle broadcast callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    broadcast_text = f"📢 **Broadcast Message**\n\n"
    broadcast_text += f"📝 **How to Use:**\n"
    broadcast_text += f"Send a message to all bot users using:\n\n"
    broadcast_text += f"**Command:** `/broadcast <message>`\n\n"
    broadcast_text += f"⚠️ **Note:** This will send the message to all registered users across all clones."

    await query.edit_message_text(
        broadcast_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
        ])
    )

@Client.on_callback_query(filters.regex("^mother_statistics$"))
async def statistics_callback(client: Client, query: CallbackQuery):
    """Handle statistics callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    try:
        # Get statistics
        total_clones = await get_total_clones_count()
        active_clones = await get_active_clones_count()
        total_users = await get_total_users_count()
        total_files = await get_total_files_count()
    except Exception as e:
        print(f"Error getting statistics: {e}")
        total_clones = active_clones = total_users = total_files = 0

    stats_text = f"📊 **System Statistics**\n\n"
    stats_text += f"🤖 **Bot Network:**\n"
    stats_text += f"• Total Clones: {total_clones}\n"
    stats_text += f"• Active Clones: {active_clones}\n"
    stats_text += f"• Inactive Clones: {total_clones - active_clones}\n\n"
    stats_text += f"👥 **Users:**\n"
    stats_text += f"• Total Users: {total_users}\n\n"
    stats_text += f"📁 **Files:**\n"
    stats_text += f"• Total Indexed: {total_files}\n\n"
    stats_text += f"⏰ **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"

    # Check if message content would be different
    if query.message.text != stats_text:
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="mother_statistics")],
                [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
            ])
        )
    else:
        await query.answer("Statistics are already up to date!", show_alert=False)

@Client.on_callback_query(filters.regex("^back_to_mother_panel$"))
async def back_to_panel(client: Client, query: CallbackQuery):
    """Return to main mother bot panel"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Create Clone", callback_data="mother_create_clone")],
        [InlineKeyboardButton("📋 Manage Clones", callback_data="mother_manage_clones")],
        [InlineKeyboardButton("💰 Subscriptions", callback_data="mother_subscriptions")],
        [InlineKeyboardButton("🌐 Global Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("📊 Statistics", callback_data="mother_statistics")]
    ])

    await query.edit_message_text(
        "🎛️ **Mother Bot Admin Panel**\n\n"
        "Welcome to the Mother Bot administration center.\n"
        "Choose an option below to manage your bot network:",
        reply_markup=buttons
    )

# Add more callback handlers for detailed management
@Client.on_callback_query(filters.regex("^extend_(1m|3m|6m|1y)#"))
async def extend_subscription_handler(client: Client, query: CallbackQuery):
    """Handle subscription extension"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    period, clone_id = query.data.split("#")
    period = period.replace("extend_", "")

    # Define extension periods and prices from PREMIUM_PLANS
    extensions = {
        "1m": PREMIUM_PLANS["monthly"],
        "3m": PREMIUM_PLANS["quarterly"],
        "6m": PREMIUM_PLANS["biannual"],
        "1y": PREMIUM_PLANS["annual"]
    }

    ext_data = extensions[period]

    try:
        await extend_subscription(clone_id, ext_data["duration"], ext_data["price"])
        await query.answer(f"✅ Subscription extended by {ext_data['name']} ({ext_data['duration']})", show_alert=True)

        # Go back to clone management
        await manage_specific_clone(client, query)

    except Exception as e:
        await query.answer(f"❌ Error extending subscription: {str(e)}", show_alert=True)

@Client.on_message(filters.command("setglobalchannels") & filters.private)
async def set_global_channels(client: Client, message: Message):
    """Set global force channels"""
    if message.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Access denied.")

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setglobalchannels channel1 channel2 ...`\n\n"
            "Example: `/setglobalchannels @channel1 @channel2 -1001234567890`"
        )

    channels = message.command[1:]
    await set_global_force_channels(channels)

    await message.reply_text(
        f"✅ **Global force channels updated!**\n\n"
        f"**Channels set:**\n" + 
        "\n".join(f"• {channel}" for channel in channels)
    )

@Client.on_callback_query(filters.regex("^manage_global_channels$"))
async def manage_force_channels_callback(client: Client, query: CallbackQuery):
    """Handle manage force channels callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    global_force_channels = await get_global_force_channels()

    channels_text = f"📢 **Manage Global Force Channels**\n\n"

    if global_force_channels:
        channels_text += f"**Current Force Channels:**\n"
        for i, channel in enumerate(global_force_channels, 1):
            try:
                # Try to get channel info
                chat = await client.get_chat(channel)
                title = chat.title or f"Channel {channel}"
                channels_text += f"{i}. **{title}** (`{channel}`)\n"
            except:
                channels_text += f"{i}. `{channel}` (Invalid/Inaccessible)\n"
        channels_text += f"\n"
    else:
        channels_text += f"**No force channels configured.**\n\n"

    channels_text += f"**📋 Commands:**\n"
    channels_text += f"• `/addglobalchannel <channel_id>` - Add force channel\n"
    channels_text += f"• `/removeglobalchannel <channel_id>` - Remove force channel\n"
    channels_text += f"• `/clearglobalchannels` - Remove all channels\n"
    channels_text += f"• `/globalchannels` - List all channels\n\n"

    channels_text += f"**💡 Tips:**\n"
    channels_text += f"• Channel ID format: -1001234567890\n"
    channels_text += f"• Make sure bot is admin in the channel\n"
    channels_text += f"• Users must join ALL channels to access content"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="manage_global_channels")],
        [InlineKeyboardButton("🌐 Back to Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(channels_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^edit_global_about$"))
async def edit_global_about_callback(client: Client, query: CallbackQuery):
    """Handle edit global about callback"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    global_about = await get_global_about()

    about_text = f"📄 **Edit Global About Page**\n\n"

    if global_about:
        about_preview = global_about[:200] + "..." if len(global_about) > 200 else global_about
        about_text += f"**Current About Message:**\n"
        about_text += f"```\n{about_preview}\n```\n\n"
    else:
        about_text += f"**No global about message set.**\n\n"

    about_text += f"**📋 Commands:**\n"
    about_text += f"• `/setglobalabout <message>` - Set about message\n"
    about_text += f"• `/clearglobalabout` - Clear about message\n\n"

    about_text += f"**💡 Tips:**\n"
    about_text += f"• Supports Markdown formatting\n"
    about_text += f"• Will be shown in all clone bots\n"
    about_text += f"• Keep it under 4000 characters"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="edit_global_about")],
        [InlineKeyboardButton("🌐 Back to Settings", callback_data="mother_global_settings")],
        [InlineKeyboardButton("« Back to Panel", callback_data="back_to_mother_panel")]
    ])

    await query.edit_message_text(about_text, reply_markup=buttons)