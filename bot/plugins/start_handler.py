
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
    buttons.extend([
        [InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")],
        [InlineKeyboardButton("💰 Add Balance", callback_data="add_balance")]
    ])
    
    if is_admin:
        buttons.append([InlineKeyboardButton("🎛️ Admin Panel", callback_data="mother_admin_panel")])
    
    buttons.extend([
        [InlineKeyboardButton("🔍 Search Files", callback_data="search_files")],
        [InlineKeyboardButton("🎲 Random Files", callback_data="random_files")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium_info")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
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
    
    # Add feature buttons based on enabled features
    feature_buttons = []
    if config['features'].get('search', True):
        feature_buttons.append(InlineKeyboardButton("🔍 Search", callback_data="search_files"))
    if config['features'].get('upload', True):
        feature_buttons.append(InlineKeyboardButton("📤 Upload", callback_data="upload_files"))
    
    if feature_buttons:
        # Split into rows of 2
        for i in range(0, len(feature_buttons), 2):
            buttons.append(feature_buttons[i:i+2])
    
    if config['features'].get('token_verification', True):
        buttons.append([InlineKeyboardButton("🎯 Get Token", callback_data="get_token")])
    
    if config['features'].get('premium', True):
        buttons.append([InlineKeyboardButton("💎 Premium", callback_data="premium_info")])
    
    buttons.extend([
        [InlineKeyboardButton("🎲 Random Files", callback_data="random_files")],
        [InlineKeyboardButton("🤖 Create Your Clone", callback_data="start_clone_creation")],
        [InlineKeyboardButton("💰 Add Balance", callback_data="add_balance")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
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

@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client, query):
    """Handle create clone button"""
    await query.answer()
    
    # Import the clone creation function
    from bot.plugins.clone_request import create_clone_command
    
    # Create a fake message object to trigger the command
    class FakeMessage:
        def __init__(self, user):
            self.from_user = user
            self.chat = user
            self.command = ["createclone"]
        
        async def reply_text(self, text, reply_markup=None):
            return await query.edit_message_text(text, reply_markup=reply_markup)
    
    fake_message = FakeMessage(query.from_user)
    await create_clone_command(client, fake_message)

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
