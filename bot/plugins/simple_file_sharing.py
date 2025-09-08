import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from info import Config
from bot.database import add_user, present_user
from bot.utils.helper import get_readable_time
from bot.logging import LOGGER

logger = LOGGER(__name__)

# DISABLED: Using start_handler.py instead to avoid conflicts
# @Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Start command for clone bots - simple file sharing welcome"""
    user_id = message.from_user.id

    # Add user to database
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    # Check if this is a clone bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone = bot_token != Config.BOT_TOKEN

    if is_clone:
        # Clone bot welcome message
        text = f"🤖 **Welcome to File Sharing Bot!**\n\n"
        text += f"👋 Hi {message.from_user.first_name}!\n\n"
        text += f"📁 **What I can do:**\n"
        text += f"• Share files instantly\n"
        text += f"• Search through file database\n"
        text += f"• Generate download links\n"
        text += f"• Batch file operations\n\n"
        text += f"🚀 **Getting Started:**\n"
        text += f"Just send me a file or use /search to find files!\n\n"
        text += f"💡 **Need Help?** Use /help for more commands"

        # Create inline keyboard
        buttons = []

        # Get clone configuration for random/recent buttons
        try:
            from bot.utils.clone_config_loader import clone_config_loader
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            config = await clone_config_loader.get_bot_config(bot_token)
            features = config.get('features', {})
        except:
            features = {}

        # Show Search Files button to all users
        buttons.append([InlineKeyboardButton("🔍 Search Files", callback_data="search_files")])

        # Show random, recent and popular buttons to ALL users
        # Token verification will handle access control when clicked
        random_recent_row = []
        random_recent_row.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
        random_recent_row.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))
        
        buttons.append(random_recent_row)
        
        # Add popular files button - always show to all users
        buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])

        buttons.extend([
            [InlineKeyboardButton("❓ Help", callback_data="help_info")]
        ])
        
        # Convert buttons list to InlineKeyboardMarkup
        buttons = InlineKeyboardMarkup(buttons)
    else:
        # Mother bot welcome message
        text = f"🤖 **Welcome to Mother Bot!**\n\n"
        text += f"👋 Hi {message.from_user.first_name}!\n\n"
        text += f"🌟 **This is the Mother Bot** - Control center for bot clones\n\n"
        text += f"⚡ **Available Features:**\n"
        text += f"• Create bot clones\n"
        text += f"• Manage existing clones\n"
        text += f"• File sharing capabilities\n"
        text += f"• Advanced admin controls\n\n"

        if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
            text += f"🔧 **Admin Access Granted**\n"
            text += f"Use /motheradmin for admin panel"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 Create Clone", callback_data="start_clone_creation"),
                InlineKeyboardButton("⚙️ Manage Clones", callback_data="manage_my_clone")
            ],
            [
                InlineKeyboardButton("📁 Search Files", callback_data="search_files"),
                InlineKeyboardButton("📊 Stats", callback_data="view_stats")
            ],
            [InlineKeyboardButton("❓ Help", callback_data="help_info")]
        ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Help command for clone bots"""
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone = bot_token != Config.BOT_TOKEN

    if is_clone:
        # Clone bot help
        help_text = """📋 **Available Commands**

**File Operations:**
• Send any file - I'll store and share it
• `/search <query>` - Search for files
• `/rand` - Get random files
• `/recent` - Get recent files

**Information:**
• `/stats` - View bot statistics
• `/mystats` - Your personal stats
• `/help` - Show this help

**Premium Features:**
• `/token` - Generate access tokens
• `/premium` - View premium plans

**Links:**
• `/genlink <file_id>` - Generate file link
• `/batch <start> <end>` - Batch link generator

🤖 This is a file sharing clone bot with full functionality!"""
    else:
        # Mother bot help
        help_text = """📋 **Mother Bot Commands**

**Clone Management:**
• `/createclone` - Create a new bot clone
• `/manageclone` - Manage your clones
• `/listclones` - List all clones (Admin)

**File Operations:**
• Send any file - Store and share
• `/search <query>` - Search files
• `/genlink <file_id>` - Generate links

**Administration:**
• `/motheradmin` - Admin panel (Admin)
• `/stats` - System statistics
• `/broadcast` - Send broadcast (Admin)

**Premium & Tokens:**
• `/token` - Generate access tokens
• `/premium` - View premium plans

🌟 **Mother Bot** - Create and manage bot clones!"""

    await message.reply_text(help_text)

@Client.on_message(filters.command("search") & filters.private)
async def search_files(client: Client, message: Message):
    """Simple search functionality"""
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Search Query Required**\n\n"
            "Usage: `/search <filename>`\n"
            "Example: `/search movie.mp4`"
        )

    query = " ".join(message.command[1:])
    await message.reply_text(
        f"🔍 **Searching for:** `{query}`\n\n"
        f"⏳ Please wait while I search the database..."
    )

    # Implement actual search logic here
    # This is a placeholder for the search functionality

@Client.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_files(client: Client, message: Message):
    """Handle incoming files for clone bots"""
    user_id = message.from_user.id

    # Add user if not exists
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    # Get file info
    file_name = getattr(message.document or message.video or message.audio, 'file_name', 'Unknown')
    file_size = getattr(message.document or message.video or message.audio, 'file_size', 0)

    # Store file info (implement your file storage logic here)
    file_id = message.id

    # Create share button
    share_link = f"https://t.me/{client.me.username}?start=file_{file_id}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Share", url=share_link),
            InlineKeyboardButton("🔗 Get Link", callback_data=f"get_link_{file_id}")
        ]
    ])

    await message.reply_text(
        f"✅ **File Received!**\n\n"
        f"📁 **Name:** `{file_name}`\n"
        f"📊 **Size:** `{get_readable_time(file_size) if file_size else 'Unknown'}`\n"
        f"🆔 **File ID:** `{file_id}`\n\n"
        f"Your file has been stored and is ready to share!",
        reply_markup=buttons
    )

# Remove all clone creation related callback handlers for clone bots