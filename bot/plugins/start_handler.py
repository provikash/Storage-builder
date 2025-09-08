
import asyncio
from datetime import datetime
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.logging import LOGGER

# Import with error handling
try:
    from bot.utils.session_manager import get_session, clear_session, session_expired
except ImportError:
    async def session_expired(user_id): return False
    async def clear_session(user_id): pass
    async def get_session(user_id): return None

try:
    from bot.database.users import add_user, present_user
except ImportError:
    async def add_user(user_id): pass
    async def present_user(user_id): return True

try:
    from bot.database.premium_db import is_premium_user
except ImportError:
    async def is_premium_user(user_id): return False

try:
    from bot.database.balance_db import get_user_balance
except ImportError:
    async def get_user_balance(user_id): return 0.0

try:
    from bot.database.clone_db import get_clone_by_bot_token
except ImportError:
    async def get_clone_by_bot_token(token): return None

try:
    from bot.utils import helper as utils
except ImportError:
    class utils:
        @staticmethod
        async def handle_force_sub(client, message):
            return True

logger = LOGGER(__name__)

async def is_clone_bot_instance_async(client):
    """Detect if this is a clone bot instance"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = bot_token != Config.BOT_TOKEN
        return is_clone, bot_token
    except:
        return False, Config.BOT_TOKEN

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

@Client.on_message(filters.command("start") & filters.private, group=0)
async def start_command(client: Client, message: Message):
    """Unified start command handler for both mother and clone bots"""
    user = message.from_user
    user_id = user.id

    try:
        logger.info(f"Start command received from user {user_id}")

        # Handle force subscription first
        if not await utils.handle_force_sub(client, message):
            logger.info(f"User {user_id} blocked by force subscription")
            return

        # Check session and clear if expired
        if await session_expired(user.id):
            await clear_session(user.id)

        # Add user to database
        await add_user(user.id)

        # Get user data
        user_premium = await is_premium_user(user.id)
        balance = await get_user_balance(user.id)

        # Detect bot type
        is_clone_bot, bot_token = await is_clone_bot_instance_async(client)
        is_admin_user = await is_clone_admin(client, user_id)

        if is_clone_bot:
            # Clone bot start message
            text = f"🤖 **Welcome {user.first_name}!**\n\n"
            text += f"📁 **Your Personal File Bot** - Browse, search, and download files instantly.\n\n"
            text += f"🌟 **Features Available:**\n"
            text += f"• 🎲 Random file discovery\n"
            text += f"• 🆕 Latest uploaded content\n"
            text += f"• 🔥 Most popular downloads\n"
            text += f"• 🔍 Advanced search functionality\n\n"
            text += f"💎 Status: {'Premium' if user_premium else 'Free'}\n\n"
            text += f"🎯 **Choose an option below:**"

            buttons = []
            
            if is_admin_user:
                # Clone admin buttons
                buttons.append([InlineKeyboardButton("⚙️ Clone Settings", callback_data="clone_settings")])

            # Get clone settings for feature visibility
            try:
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    show_random = clone_data.get('random_mode', True)
                    show_recent = clone_data.get('recent_mode', True)
                    show_popular = clone_data.get('popular_mode', True)

                    # File browsing buttons based on settings
                    file_buttons_row = []
                    if show_random:
                        file_buttons_row.append(InlineKeyboardButton("🎲 Random Files", callback_data="random_files"))
                    if show_recent:
                        file_buttons_row.append(InlineKeyboardButton("🆕 Recent Files", callback_data="recent_files"))

                    if file_buttons_row:
                        buttons.append(file_buttons_row)

                    if show_popular:
                        buttons.append([InlineKeyboardButton("🔥 Most Popular", callback_data="popular_files")])
            except Exception as e:
                logger.error(f"Error getting clone settings: {e}")

            # Always show user action buttons
            buttons.append([
                InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ])
            buttons.append([
                InlineKeyboardButton("💎 Plans", callback_data="premium_info"),
                InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
            ])

        else:
            # Mother bot start message
            text = f"🚀 **Welcome to Advanced Bot Creator, {user.first_name}!**\n\n"
            text += f"🤖 **Create & Manage Personal Clone Bots**\n"
            text += f"Build your own file-sharing bot network with advanced features.\n\n"
            text += f"🌟 **What You Can Do:**\n"
            text += f"• 🤖 Create unlimited clone bots\n"
            text += f"• 📁 Advanced file management system\n"
            text += f"• 👥 User management & analytics\n"
            text += f"• 💎 Premium features & monetization\n"
            text += f"• 🔧 Complete customization control\n\n"
            text += f"💎 Status: {'Premium' if user_premium else 'Free'} | Balance: ${balance:.2f}\n\n"
            text += f"🎯 **Get Started:**"

            buttons = []

            # Main features
            buttons.append([
                InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
                InlineKeyboardButton("📋 My Clones", callback_data="manage_my_clone")
            ])
            buttons.append([
                InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
                InlineKeyboardButton("💎 Plans", callback_data="premium_info")
            ])
            buttons.append([
                InlineKeyboardButton("❓ Help", callback_data="help_menu"),
                InlineKeyboardButton("ℹ️ About", callback_data="about_water")
            ])

            # Admin panel for mother bot admins
            is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
            if is_mother_admin:
                buttons.append([
                    InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
                    InlineKeyboardButton("🔧 Bot Management", callback_data="bot_management")
                ])

        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        logger.info(f"Start message sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        await message.reply_text("❌ An error occurred. Please try again later.")

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Return to main start menu"""
    await query.answer()
    
    # Create a fake message to reuse start_command logic
    fake_message = type('obj', (object,), {
        'from_user': query.from_user,
        'reply_text': lambda text, reply_markup=None: query.edit_message_text(text, reply_markup=reply_markup)
    })()
    
    await start_command(client, fake_message)

# Settings handlers for clone bots
@Client.on_callback_query(filters.regex("^clone_settings$"))
async def clone_settings_callback(client: Client, query: CallbackQuery):
    """Handle clone settings callback"""
    await query.answer()
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        await query.edit_message_text("❌ Only clone admin can access settings.")
        return

    try:
        from bot.plugins.clone_admin_settings import clone_settings_command
        await clone_settings_command(client, query.message)
    except ImportError:
        await query.edit_message_text("❌ Settings module not available.")

# Profile callback
@Client.on_callback_query(filters.regex("^user_profile$"))
async def profile_callback(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        user_premium = await is_premium_user(user_id)
        balance = await get_user_balance(user_id)
        
        text = f"👤 **Your Profile**\n\n"
        text += f"🆔 **User ID:** `{user_id}`\n"
        text += f"📛 **Name:** {query.from_user.first_name}\n"
        text += f"💎 **Status:** {'Premium' if user_premium else 'Free'}\n"
        text += f"💰 **Balance:** ${balance:.2f}\n"
        
        buttons = [[InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Error in profile callback: {e}")
        await query.edit_message_text("❌ Error loading profile.")

# Help callback
@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_callback(client: Client, query: CallbackQuery):
    """Handle help callback"""
    await query.answer()
    
    text = f"❓ **Help & Support**\n\n"
    text += f"🤖 **Available Commands:**\n"
    text += f"• `/start` - Main menu\n"
    text += f"• `/help` - Show this help\n\n"
    text += f"💡 **Need Help?**\n"
    text += f"Contact our support team for assistance.\n\n"
    text += f"📚 **Documentation:**\n"
    text += f"Visit our help center for detailed guides."
    
    buttons = [[InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
