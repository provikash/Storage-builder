
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database import add_user, present_user
from bot.database.clone_db import get_global_about
from bot.utils.clone_config_loader import clone_config_loader
from bot.utils import helper
from datetime import datetime

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    """Dynamic start handler for Mother Bot and Clone Bots"""
    user_id = message.from_user.id
    
    # Add user to database
    if not await present_user(user_id):
        await add_user(user_id)
    
    # Get bot configuration
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    # Check if user can access the bot
    if config['bot_info'].get('is_clone', False):
        access_result = await clone_config_loader.can_user_access(bot_token, user_id)
        if isinstance(access_result, tuple) and not access_result[0]:
            return await message.reply_text(access_result[1])
    
    # Handle file sharing links
    if len(message.command) > 1:
        await handle_file_request(client, message, config)
        return
    
    # Show appropriate start message
    if config['bot_info'].get('is_mother_bot', False):
        await show_mother_bot_start(client, message, config)
    else:
        await show_clone_bot_start(client, message, config)

async def handle_file_request(client: Client, message: Message, config: dict):
    """Handle file sharing request from start parameter"""
    try:
        from bot.utils.encoder import decode
        base64_string = message.command[1]
        decoded_data = decode(base64_string)
        
        if decoded_data.startswith("get-"):
            # Handle file sharing
            converted_id = int(decoded_data.split("-", 1)[1])
            
            # Check force channels
            force_channels = await clone_config_loader.get_force_channels(
                getattr(client, 'bot_token', Config.BOT_TOKEN)
            )
            
            if force_channels:
                # Check if user is member of force channels
                from bot.utils.helper import is_subscribed
                is_member = await is_subscribed(client, message.from_user.id, force_channels)
                if not is_member:
                    await show_force_subscribe_message(client, message, force_channels)
                    return
            
            # Send the file
            await send_file_from_id(client, message, converted_id)
            
    except Exception as e:
        await message.reply_text("❌ Invalid or expired link!")

async def show_mother_bot_start(client: Client, message: Message, config: dict):
    """Show Mother Bot start message"""
    me = await client.get_me()
    user_id = message.from_user.id
    
    # Get user balance
    from bot.database.balance_db import create_user_profile, get_user_balance
    await create_user_profile(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    current_balance = await get_user_balance(user_id)
    
    # Check if user is admin
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
    
    start_text = f"🤖 **Welcome to {me.first_name}**\n\n"
    start_text += "🎛️ **Mother Bot System**\n"
    start_text += "The ultimate file-sharing bot with clone creation capabilities!\n\n"
    
    # Add balance information
    start_text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"
    
    if is_admin:
        start_text += "👑 **Admin Features:**\n"
        start_text += "• Create unlimited bot clones\n"
        start_text += "• Manage subscriptions\n"
        start_text += "• Global settings control\n"
        start_text += "• Full system access\n\n"
    
    start_text += "✨ **Features:**\n"
    start_text += "• 📁 File sharing & storage\n"
    start_text += "• 🔗 Short link generation\n"
    start_text += "• 🔍 Advanced search\n"
    start_text += "• 🎯 Token verification\n"
    start_text += "• 💎 Premium subscriptions\n"
    start_text += "• 🤖 Clone bot creation\n\n"
    
    start_text += f"👤 **Your Info:**\n"
    start_text += f"• User ID: `{user_id}`\n"
    start_text += f"• Status: {'Admin' if is_admin else 'User'}\n"
    
    buttons = []
    
    # Add create clone and balance buttons for all users
    # First row - Profile and Create Clone
    buttons.extend([
        [
            InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")
        ]
    ])
    
    # Second row - Balance management
    buttons.extend([
        [
            InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")
        ]
    ])
    
    # Admin panel if admin
    if is_admin:
        buttons.append([InlineKeyboardButton("🎛️ Admin Panel", callback_data="mother_admin_panel")])
    
    # Feature buttons
    buttons.extend([
        [
            InlineKeyboardButton("🔍 Search Files", callback_data="search_files"),
            InlineKeyboardButton("🎲 Random Files", callback_data="random_files")
        ],
        [
            InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            InlineKeyboardButton("❓ Help", callback_data="help_menu")
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
        ]
    ])
    
    await message.reply_text(
        start_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_clone_bot_start(client: Client, message: Message, config: dict):
    """Show Clone Bot start message"""
    me = await client.get_me()
    user_id = message.from_user.id
    
    # Get user balance
    from bot.database.balance_db import create_user_profile, get_user_balance
    await create_user_profile(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    current_balance = await get_user_balance(user_id)
    
    # Get custom messages or use defaults
    custom_messages = config.get('custom_messages', {})
    global_about = await get_global_about()
    
    # Check if user is clone admin
    is_admin = user_id == config['bot_info'].get('admin_id')
    
    start_text = custom_messages.get('start_message', '')
    
    if not start_text:
        start_text = f"🤖 **Welcome to {me.first_name}**\n\n"
        start_text += "📁 **Professional File Sharing Bot**\n"
        start_text += "Fast, reliable, and secure file sharing service.\n\n"
        
        # Add balance information
        start_text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"
        
        start_text += "✨ **Features:**\n"
        if config['features'].get('search', True):
            start_text += "• 🔍 Advanced file search\n"
        if config['features'].get('upload', True):
            start_text += "• 📤 File upload & sharing\n"
        if config['features'].get('token_verification', True):
            start_text += "• 🎯 Token verification system\n"
        if config['features'].get('premium', True):
            start_text += "• 💎 Premium subscriptions\n"
        if config['features'].get('batch_links', True):
            start_text += "• 🔗 Batch link generation\n"
        
        start_text += f"\n👤 **Your Info:**\n"
        start_text += f"• User ID: `{user_id}`\n"
        start_text += f"• Status: {'Clone Admin' if is_admin else 'User'}\n"
        
        # Add subscription info
        subscription = config.get('subscription', {})
        if subscription.get('active'):
            start_text += f"• Plan: {subscription.get('tier', 'Unknown')}\n"
            if subscription.get('expiry'):
                start_text += f"• Expires: {subscription['expiry'].strftime('%Y-%m-%d')}\n"
    
    # Add global about information
    if global_about:
        start_text += f"\n{global_about}\n"
    
    start_text += "\n🤖 **Made by Mother Bot System**\n"
    start_text += "Want your own bot? Create a clone now!"
    
    buttons = []
    
    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Clone Settings", callback_data="clone_admin_panel")])
    
    # First row - Profile and Create Clone
    buttons.extend([
        [
            InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")
        ]
    ])
    
    # Feature buttons based on enabled features
    feature_row = []
    if config['features'].get('search', True):
        feature_row.append(InlineKeyboardButton("🔍 Search", callback_data="search_files"))
    if config['features'].get('upload', True):
        feature_row.append(InlineKeyboardButton("📤 Upload", callback_data="upload_files"))
    
    if feature_row:
        buttons.append(feature_row)
    
    # Additional features
    additional_features = []
    if config['features'].get('token_verification', True):
        additional_features.append(InlineKeyboardButton("🎯 Get Token", callback_data="get_token"))
    if config['features'].get('premium', True):
        additional_features.append(InlineKeyboardButton("💎 Premium", callback_data="premium_info"))
    
    if additional_features:
        # Split into rows of 2
        for i in range(0, len(additional_features), 2):
            buttons.append(additional_features[i:i+2])
    
    # Random files and balance
    buttons.extend([
        [InlineKeyboardButton("🎲 Random Files", callback_data="random_files")],
        [
            InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help_menu"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
        ],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")]
    ])
    
    await message.reply_text(
        start_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_force_subscribe_message(client: Client, message: Message, force_channels: list):
    """Show force subscription message"""
    text = "🔒 **Access Restricted**\n\n"
    text += "To use this bot, you must join the following channel(s):\n\n"
    
    buttons = []
    for i, channel in enumerate(force_channels[:5], 1):  # Max 5 channels
        try:
            chat = await client.get_chat(channel)
            channel_name = chat.title or f"Channel {i}"
            invite_link = chat.invite_link or f"https://t.me/{chat.username}" if chat.username else None
            
            if invite_link:
                buttons.append([InlineKeyboardButton(f"📢 Join {channel_name}", url=invite_link)])
            
            text += f"• {channel_name}\n"
        except:
            buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=f"https://t.me/{channel.replace('@', '')}")])
    
    buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="check_subscription")])
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def get_user_clones(user_id: int):
    """Get user's clones"""
    try:
        from bot.database.clone_db import get_user_clones as db_get_user_clones
        return await db_get_user_clones(user_id)
    except Exception as e:
        print(f"Error getting user clones: {e}")
        return []

async def send_file_from_id(client: Client, message: Message, converted_id: int):
    """Send file from converted ID"""
    try:
        # Get the original message from DB channel
        channel_id = getattr(client, 'db_channel', Config.CHANNEL_ID)
        if hasattr(client, 'db_channel'):
            channel_id = client.db_channel.id
        else:
            channel_id = Config.CHANNEL_ID
            
        message_id = converted_id // abs(channel_id)
        
        # Get the message
        file_message = await client.get_messages(channel_id, message_id)
        
        if not file_message or not file_message.media:
            await message.reply_text("❌ File not found or expired!")
            return
        
        # Forward the file
        await file_message.copy(message.chat.id)
        
    except Exception as e:
        await message.reply_text("❌ Error retrieving file. The link may be expired.")

@Client.on_callback_query(filters.regex("^mother_admin_panel$"))
async def mother_admin_panel_callback(client, query):
    """Redirect to mother admin panel"""
    from bot.plugins.mother_admin import mother_admin_panel
    await mother_admin_panel(client, query.message)

@Client.on_callback_query(filters.regex("^check_subscription$"))
async def check_subscription_callback(client, query):
    """Check if user joined force channels"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    force_channels = await clone_config_loader.get_force_channels(bot_token)
    
    from bot.utils.helper import is_subscribed
    is_member = await is_subscribed(client, query.from_user.id, force_channels)
    
    if is_member:
        await query.answer("✅ Access granted! You can now use the bot.", show_alert=True)
        # Show start message again
        config = await clone_config_loader.get_bot_config(bot_token)
        if config['bot_info'].get('is_mother_bot', False):
            await show_mother_bot_start(client, query.message, config)
        else:
            await show_clone_bot_start(client, query.message, config)
    else:
        await query.answer("❌ Please join all required channels first!", show_alert=True)

# Clone creation handler - simplified version
@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client, query):
    """Start simplified clone creation process"""
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check balance first
    from bot.database.balance_db import get_user_balance
    current_balance = await get_user_balance(user_id)
    
    if current_balance < 3.00:
        text = f"❌ **Insufficient Balance**\n\n"
        text += f"💰 **Current Balance:** ${current_balance:.2f}\n"
        text += f"💵 **Required:** $3.00 (minimum)\n\n"
        text += f"You need at least $3.00 to create a clone.\n"
        text += f"Please add balance to your account first.\n\n"
        text += f"**💡 Clone Plans:**\n"
        text += f"• Monthly: $3.00\n"
        text += f"• Quarterly: $8.00\n"
        text += f"• Semi-Annual: $15.00\n"
        text += f"• Yearly: $26.00"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
            [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        return
    
    # Show clone creation options
    text = f"🤖 **Create Your Clone Bot**\n\n"
    text += f"✅ **Balance Check:** ${current_balance:.2f} available\n\n"
    text += f"**📋 What you need:**\n"
    text += f"1. **Bot Token** - Get from @BotFather\n"
    text += f"2. **MongoDB URL** - Database connection\n"
    text += f"3. **Choose Plan** - Select subscription duration\n\n"
    text += f"**💰 Available Plans:**\n"
    text += f"• **Monthly:** $3.00 - 30 days\n"
    text += f"• **Quarterly:** $8.00 - 90 days (Best Value!)\n"
    text += f"• **Semi-Annual:** $15.00 - 180 days\n"
    text += f"• **Yearly:** $26.00 - 365 days\n\n"
    text += f"**🚀 Process:**\n"
    text += f"1. Select your plan\n"
    text += f"2. Provide bot token & database\n"
    text += f"3. Instant deployment\n"
    text += f"4. Start using your clone!\n\n"
    text += f"**✨ Your clone will have all features of this bot!**"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Monthly ($3)", callback_data="create_clone_monthly"),
            InlineKeyboardButton("📅 Quarterly ($8)", callback_data="create_clone_quarterly")
        ],
        [
            InlineKeyboardButton("📅 Semi-Annual ($15)", callback_data="create_clone_semi"),
            InlineKeyboardButton("📅 Yearly ($26)", callback_data="create_clone_yearly")
        ],
        [InlineKeyboardButton("❓ How to get Bot Token?", callback_data="how_to_get_token")],
        [InlineKeyboardButton("❓ How to get MongoDB?", callback_data="how_to_get_mongodb")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^how_to_get_token$"))
async def how_to_get_token_callback(client, query):
    """Show how to get bot token"""
    await query.answer()
    
    text = f"🤖 **How to Get Bot Token**\n\n"
    text += f"**Step 1:** Go to @BotFather on Telegram\n"
    text += f"**Step 2:** Send `/newbot` command\n"
    text += f"**Step 3:** Choose a name for your bot\n"
    text += f"**Step 4:** Choose a username (must end with 'bot')\n"
    text += f"**Step 5:** Copy the token provided\n\n"
    text += f"**📝 Example:**\n"
    text += f"• Bot Name: `My File Bot`\n"
    text += f"• Username: `myfilebot` or `my_file_bot`\n"
    text += f"• Token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
    text += f"**⚠️ Important:**\n"
    text += f"• Keep your token secret\n"
    text += f"• Don't share with others\n"
    text += f"• Token format: numbers:letters\n\n"
    text += f"**🔗 Quick Link:** @BotFather"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Open BotFather", url="https://t.me/BotFather")],
        [InlineKeyboardButton("« Back to Clone Creation", callback_data="start_clone_creation")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^how_to_get_mongodb$"))
async def how_to_get_mongodb_callback(client, query):
    """Show how to get MongoDB"""
    await query.answer()
    
    text = f"🗄️ **How to Get MongoDB URL**\n\n"
    text += f"**Option 1: MongoDB Atlas (Recommended)**\n"
    text += f"1. Go to mongodb.com/atlas\n"
    text += f"2. Create free account\n"
    text += f"3. Create new cluster (free tier)\n"
    text += f"4. Create database user\n"
    text += f"5. Get connection string\n\n"
    text += f"**Option 2: Use same as Mother Bot**\n"
    text += f"Contact admin to get shared database access\n\n"
    text += f"**📝 URL Format:**\n"
    text += f"`mongodb+srv://username:password@cluster.mongodb.net/dbname`\n\n"
    text += f"**⚠️ Important:**\n"
    text += f"• Keep credentials secure\n"
    text += f"• Use strong passwords\n"
    text += f"• Free tier has 512MB limit\n\n"
    text += f"**💡 Need Help?**\n"
    text += f"Contact admin for assistance with setup"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 MongoDB Atlas", url="https://www.mongodb.com/atlas")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("« Back to Clone Creation", callback_data="start_clone_creation")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^manage_my_clone$"))
async def manage_my_clone_callback(client, query):
    """Handle manage my clone button"""
    await query.answer()
    
    user_id = query.from_user.id
    user_clones = await get_user_clones(user_id)
    active_clones = [clone for clone in user_clones if clone.get('status') == 'active']
    
    if not active_clones:
        text = f"❌ **No Active Clone Found**\n\n"
        text += f"You don't have any active clones.\n"
        text += f"Would you like to create one?"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])
        
        return await query.edit_message_text(text, reply_markup=buttons)
    
    clone = active_clones[0]  # Get the first active clone
    
    # Get subscription info
    from bot.database.subscription_db import get_subscription_by_bot_id
    subscription = await get_subscription_by_bot_id(clone['_id'])
    
    text = f"📋 **Your Clone Management**\n\n"
    text += f"🤖 **Bot:** @{clone.get('username', 'Unknown')}\n"
    text += f"🆔 **Bot ID:** `{clone['_id']}`\n"
    text += f"📊 **Status:** {clone['status'].title()}\n"
    text += f"📅 **Created:** {clone.get('created_at', datetime.now()).strftime('%Y-%m-%d')}\n"
    
    if subscription:
        text += f"💰 **Plan:** {subscription.get('tier', 'Unknown').title()}\n"
        if subscription.get('expiry'):
            text += f"⏰ **Expires:** {subscription['expiry'].strftime('%Y-%m-%d')}\n"
        text += f"🔄 **Auto Renew:** {'Yes' if subscription.get('auto_renew', False) else 'No'}\n"
    
    text += f"\n🔗 **Bot Link:** https://t.me/{clone.get('username', 'unknown')}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{clone.get('username', 'unknown')}")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data=f"clone_settings:{clone['_id']}")],
        [InlineKeyboardButton("📊 Statistics", callback_data=f"clone_stats:{clone['_id']}")],
        [InlineKeyboardButton("💰 Subscription", callback_data=f"clone_subscription:{clone['_id']}")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^add_balance$"))
async def add_balance_callback(client, query):
    """Handle add balance button"""
    await query.answer()
    
    from bot.database.balance_db import get_user_balance, get_user_transactions
    
    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)
    recent_transactions = await get_user_transactions(user_id, limit=5)
    
    text = f"💰 **Balance Management**\n\n"
    text += f"💵 **Current Balance:** ${current_balance:.2f}\n\n"
    
    if recent_transactions:
        text += "📊 **Recent Transactions:**\n"
        for trans in recent_transactions[:3]:
            emoji = "➕" if trans['type'] == 'credit' else "➖"
            text += f"{emoji} ${trans['amount']:.2f} - {trans['description']}\n"
        text += "\n"
    
    text += "💳 **Payment Methods:**\n"
    text += "• PayPal: Contact admin\n"
    text += "• Cryptocurrency: Contact admin\n"
    text += "• Bank Transfer: Contact admin\n\n"
    text += "📞 **Contact admin to add balance to your account**"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("🔄 Refresh Balance", callback_data="add_balance")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^check_balance$"))
async def check_balance_callback(client, query):
    """Handle check balance button"""
    await query.answer()
    
    from bot.database.balance_db import get_user_balance, get_user_transactions
    
    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)
    recent_transactions = await get_user_transactions(user_id, limit=5)
    
    text = f"💰 **Your Balance Information**\n\n"
    text += f"💵 **Current Balance:** ${current_balance:.2f}\n\n"
    
    if recent_transactions:
        text += "📊 **Recent Transactions:**\n"
        for trans in recent_transactions[:3]:
            emoji = "➕" if trans['type'] == 'credit' else "➖"
            date_str = trans['timestamp'].strftime('%m-%d %H:%M')
            text += f"{emoji} ${trans['amount']:.2f} - {trans['description']} ({date_str})\n"
        text += "\n"
    else:
        text += "📊 **Recent Transactions:** No transactions yet\n\n"
    
    text += "💡 **Clone Creation Costs:**\n"
    text += "• Monthly Plan: $3.00\n"
    text += "• Quarterly Plan: $8.00\n"
    text += "• Semi-Annual Plan: $15.00\n"
    text += "• Yearly Plan: $26.00\n\n"
    
    # Check if user can afford any plan
    if current_balance >= 3.00:
        text += "✅ **You can create a clone!**"
    else:
        text += f"❌ **Insufficient balance for clone creation**\n"
        text += f"You need at least $3.00 to create a clone."
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")
        ],
        [InlineKeyboardButton("🔄 Refresh", callback_data="check_balance")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client, query):
    """Handle back to start button"""
    await query.answer()
    
    # Show start message again
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    if config['bot_info'].get('is_mother_bot', False):
        await show_mother_bot_start(client, query.message, config)
    else:
        await show_clone_bot_start(client, query.message, config)

@Client.on_callback_query(filters.regex("^user_profile$"))
async def user_profile_callback(client, query):
    """Handle user profile button"""
    await query.answer()
    
    from bot.database.balance_db import get_user_balance, get_user_transactions
    from bot.database.clone_db import get_user_clones
    
    user_id = query.from_user.id
    user = query.from_user
    current_balance = await get_user_balance(user_id)
    recent_transactions = await get_user_transactions(user_id, limit=3)
    user_clones = await get_user_clones(user_id)
    active_clones = [clone for clone in user_clones if clone.get('status') == 'active']
    
    # Check if user is admin
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
    
    text = f"👤 **User Profile**\n\n"
    text += f"🆔 **User ID:** `{user_id}`\n"
    text += f"👤 **Name:** {user.first_name}"
    if user.last_name:
        text += f" {user.last_name}"
    text += "\n"
    if user.username:
        text += f"🏷️ **Username:** @{user.username}\n"
    text += f"👑 **Status:** {'Admin' if is_admin else 'User'}\n"
    text += f"💰 **Current Balance:** ${current_balance:.2f}\n"
    text += f"🤖 **Active Clones:** {len(active_clones)}\n\n"
    
    if recent_transactions:
        text += "📊 **Recent Transactions:**\n"
        for trans in recent_transactions:
            emoji = "➕" if trans['type'] == 'credit' else "➖"
            date_str = trans['timestamp'].strftime('%m-%d')
            text += f"{emoji} ${trans['amount']:.2f} - {trans['description']} ({date_str})\n"
    else:
        text += "📊 **Recent Transactions:** No transactions yet\n"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Add Balance", callback_data="add_balance"),
            InlineKeyboardButton("📊 Full History", callback_data="transaction_history")
        ],
        [InlineKeyboardButton("🤖 My Clones", callback_data="manage_my_clone")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_callback(client, query):
    """Handle help menu button"""
    await query.answer()
    
    user_id = query.from_user.id
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
    
    text = f"❓ **Help & Commands**\n\n"
    
    text += "**🔧 Basic Commands:**\n"
    text += "• `/start` - Start the bot\n"
    text += "• `/help` - Show help menu\n"
    text += "• `/mystats` - View your statistics\n"
    text += "• `/token` - Generate access token\n"
    text += "• `/rand` - Get random files\n\n"
    
    text += "**🔍 Search & Files:**\n"
    text += "• `/search <query>` - Search for files\n"
    text += "• Send any file to get a shareable link\n"
    text += "• Use generated links to access files\n\n"
    
    text += "**🤖 Clone Management:**\n"
    text += "• `/createclone` - Create a new bot clone\n"
    text += "• `/myclones` - View your clones\n"
    text += "• Clones operate independently\n"
    text += "• Each clone costs $3-26 based on plan\n\n"
    
    text += "**💰 Balance & Premium:**\n"
    text += "• `/premium` - View premium plans\n"
    text += "• Contact admin to add balance\n"
    text += "• Premium features available\n\n"
    
    if is_admin:
        text += "**👑 Admin Commands:**\n"
        text += "• `/admin` - Admin panel\n"
        text += "• `/broadcast` - Send broadcast\n"
        text += "• `/stats` - Global statistics\n"
        text += "• `/users` - User management\n\n"
    
    text += "**📞 Support:**\n"
    text += "• Contact admin for issues\n"
    text += "• Report bugs or suggestions\n"
    text += "• Get help with clone setup\n\n"
    
    text += "**💡 Tips:**\n"
    text += "• Keep your tokens secure\n"
    text += "• Join force channels if required\n"
    text += "• Use premium for better features"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("💎 Premium", callback_data="premium_info")
        ],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_bot_callback(client, query):
    """Handle about bot button"""
    await query.answer()
    
    me = await client.get_me()
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)
    
    text = f"ℹ️ **About {me.first_name}**\n\n"
    
    if config['bot_info'].get('is_mother_bot', False):
        text += "🤖 **Mother Bot System**\n"
        text += "The ultimate file-sharing bot with advanced clone management!\n\n"
        
        text += "**🌟 Key Features:**\n"
        text += "• 📁 Unlimited file sharing\n"
        text += "• 🤖 Create bot clones\n"
        text += "• 🔍 Advanced search system\n"
        text += "• 💎 Premium subscriptions\n"
        text += "• 🔗 Short link generation\n"
        text += "• 🎯 Token verification\n"
        text += "• 📊 Analytics & statistics\n"
        text += "• 👥 Multi-user support\n\n"
        
        text += "**💰 Clone Pricing:**\n"
        text += "• Monthly: $3.00\n"
        text += "• Quarterly: $8.00\n"
        text += "• Semi-Annual: $15.00\n"
        text += "• Yearly: $26.00\n\n"
    else:
        text += "📁 **Professional File Sharing Bot**\n"
        text += "Fast, reliable, and secure file sharing service.\n\n"
        
        text += "**✨ Features:**\n"
        text += "• 📤 File upload & sharing\n"
        text += "• 🔍 Smart file search\n"
        text += "• 🔗 Instant link generation\n"
        text += "• 🎯 Token verification\n"
        text += "• 💎 Premium options\n"
        text += "• 🎲 Random file discovery\n\n"
    
    text += "**🛠️ Technical Info:**\n"
    text += f"• Bot ID: `{me.id}`\n"
    text += f"• Username: @{me.username}\n"
    text += "• Platform: Telegram\n"
    text += "• Language: Python\n"
    text += "• Database: MongoDB\n\n"
    
    text += "**👨‍💻 Developer:**\n"
    text += "• Created with ❤️\n"
    text += "• Powered by Mother Bot System\n"
    text += "• Open source project\n\n"
    
    text += "**🔗 Links:**\n"
    text += f"• Bot: @{me.username}\n"
    if hasattr(Config, 'SUPPORT_CHAT'):
        text += f"• Support: {Config.SUPPORT_CHAT}\n"
    if hasattr(Config, 'UPDATES_CHANNEL'):
        text += f"• Updates: {Config.UPDATES_CHANNEL}\n"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Create Your Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")
        ],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^transaction_history$"))
async def transaction_history_callback(client, query):
    """Handle transaction history button"""
    await query.answer()
    
    from bot.database.balance_db import get_user_transactions
    
    user_id = query.from_user.id
    transactions = await get_user_transactions(user_id, limit=10)
    
    text = f"📊 **Transaction History**\n\n"
    
    if transactions:
        for trans in transactions:
            emoji = "➕" if trans['type'] == 'credit' else "➖"
            date_str = trans['timestamp'].strftime('%Y-%m-%d %H:%M')
            text += f"{emoji} **${trans['amount']:.2f}**\n"
            text += f"   {trans['description']}\n"
            text += f"   📅 {date_str}\n\n"
    else:
        text += "No transactions found.\n\n"
        text += "💡 **Get Started:**\n"
        text += "• Create a clone to start earning\n"
        text += "• Contact admin to add balance\n"
        text += "• Use premium features"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance"),
            InlineKeyboardButton("👤 Profile", callback_data="user_profile")
        ],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
