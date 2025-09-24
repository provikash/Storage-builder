import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
try:
    from bot.database.mongo_db import get_random_files, get_recent_files, get_popular_files, get_file_by_id, increment_download_count
except ImportError:
    logger.warning("Failed to import from mongo_db, trying index_db")
    try:
        from bot.database.index_db import get_random_files, get_recent_files, get_popular_files
        from bot.database.mongo_db import get_file_by_id, increment_download_count
    except ImportError:
        logger.error("Failed to import database functions")
        async def get_random_files(*args, **kwargs): return []
        async def get_recent_files(*args, **kwargs): return []
        async def get_popular_files(*args, **kwargs): return []
        async def get_file_by_id(*args, **kwargs): return None
        async def increment_download_count(*args, **kwargs): pass
from bot.database.clone_db import get_clone_by_bot_token
from bot.utils.helper import get_readable_file_size
from info import Config
import bot.utils.clone_config_loader as clone_config_loader

logger = logging.getLogger(__name__)

async def check_clone_feature_enabled(client: Client, feature_name: str):
    """Check if a feature is enabled for the current clone"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # If this is the mother bot, features are controlled differently
        if bot_token == Config.BOT_TOKEN:
            return False  # Mother bot doesn't use random features

        # Get clone data from database
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            logger.error(f"No clone data found for bot token {bot_token}")
            return False

        # Map feature names to database fields
        feature_mapping = {
            'random_button': 'random_mode',
            'recent_button': 'recent_mode', 
            'popular_button': 'popular_mode'
        }
        
        db_field = feature_mapping.get(feature_name, feature_name)
        is_enabled = clone_data.get(db_field, True)  # Default to True
        
        logger.info(f"Feature check for {feature_name} (db_field: {db_field}): {is_enabled}")
        return is_enabled

    except Exception as e:
        logger.error(f"Error checking clone feature {feature_name}: {e}")
        return False

async def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        if bot_token == Config.BOT_TOKEN:
            return None  # This is mother bot

        # Extract bot ID from token
        bot_id = bot_token.split(':')[0]
        return bot_id

    except Exception as e:
        logger.error(f"Error getting clone ID: {e}")
        return None

def format_file_text(file_data):
    """Format file information for display"""
    try:
        file_name = file_data.get('file_name', 'Unknown File')
        file_size = get_readable_file_size(file_data.get('file_size', 0))
        file_type = file_data.get('file_type', 'unknown').upper()
        download_count = file_data.get('download_count', 0)

        text = f"📁 **{file_name}**\n"
        text += f"📊 **Type:** {file_type}\n"
        text += f"💾 **Size:** {file_size}\n"
        text += f"⬇️ **Downloads:** {download_count}\n"

        return text
    except Exception as e:
        logger.error(f"Error formatting file text: {e}")
        return "❌ Error formatting file information"

def create_file_buttons(files):
    """Create inline keyboard buttons for files"""
    try:
        buttons = []

        for i, file_data in enumerate(files, 1):
            file_name = file_data.get('file_name', f'File {i}')[:30] + ('...' if len(file_data.get('file_name', '')) > 30 else '')
            file_id = str(file_data.get('_id', file_data.get('file_id')))

            buttons.append([
                InlineKeyboardButton(f"📁 {file_name}", callback_data=f"get_file:{file_id}")
            ])

        # Add navigation buttons
        nav_buttons = [
            InlineKeyboardButton("🎲 Random", callback_data="clone_random_files"),
            InlineKeyboardButton("🕒 Recent", callback_data="clone_recent_files"),
            InlineKeyboardButton("🔥 Popular", callback_data="clone_popular_files")
        ]
        buttons.append(nav_buttons)

        return InlineKeyboardMarkup(buttons)

    except Exception as e:
        logger.error(f"Error creating file buttons: {e}")
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Error", callback_data="error")]])

@Client.on_message(filters.command("random") & filters.private)
async def random_files_command(client: Client, message: Message):
    """Handle /random command for clone bots"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'random_button'):
            await message.reply_text("❌ Random files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This feature is only available in clone bots.")
            return

        # Get random files from clone database
        try:
            from bot.database.index_db import get_random_files as get_index_random_files
            files = await get_index_random_files(limit=10, clone_id=clone_id)
        except ImportError:
            # Fallback to mongo_db if index_db is not available
            files = await get_random_files(limit=10, clone_id=clone_id)

        if not files:
            await message.reply_text("❌ No files found in database. Index some files first.")
            return

        text = "🎲 **Random Files**\n\n"
        text += f"Found {len(files)} random files:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0])

        buttons = create_file_buttons(files)

        await message.reply_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in random files command: {e}")
        await message.reply_text("❌ Error retrieving random files. Please try again.")

async def handle_clone_random_files(client: Client, query):
    """Handle random files callback for clones"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'random_button'):
            await query.edit_message_text("❌ Random files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Get random files from clone database
        try:
            from bot.database.index_db import get_random_files as get_index_random_files
            files = await get_index_random_files(limit=10, clone_id=clone_id)
        except ImportError:
            # Fallback to mongo_db if index_db is not available
            files = await get_random_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No files found in database. Index some files first.")
            return

        text = "🎲 **Random Files**\n\n"
        text += f"Found {len(files)} random files:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0])

        buttons = create_file_buttons(files)

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in clone random files callback: {e}")
        await query.answer("❌ Error retrieving random files.", show_alert=True)

async def handle_clone_recent_files(client: Client, query):
    """Handle recent files callback for clones"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'recent_button'):
            await query.edit_message_text("❌ Recent files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Get recent files from clone database
        try:
            from bot.database.index_db import get_recent_files as get_index_recent_files
            files = await get_index_recent_files(limit=10, clone_id=clone_id)
        except ImportError:
            # Fallback to mongo_db if index_db is not available
            files = await get_recent_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No files found in database. Index some files first.")
            return

        text = "🕒 **Recent Files**\n\n"
        text += f"Found {len(files)} recent files:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0])

        buttons = create_file_buttons(files)

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in clone recent files callback: {e}")
        await query.answer("❌ Error retrieving recent files.", show_alert=True)

async def handle_clone_popular_files(client: Client, query):
    """Handle popular files callback for clones"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'popular_button'):
            await query.edit_message_text("❌ Popular files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Get popular files from clone database
        try:
            from bot.database.index_db import get_popular_files as get_index_popular_files
            files = await get_index_popular_files(limit=10, clone_id=clone_id)
        except ImportError:
            # Fallback to mongo_db if index_db is not available
            files = await get_popular_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No files found in database. Index some files first.")
            return

        text = "🔥 **Popular Files**\n\n"
        text += f"Found {len(files)} popular files:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0])

        buttons = create_file_buttons(files)

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in clone popular files callback: {e}")
        await query.answer("❌ Error retrieving popular files.", show_alert=True)

@Client.on_callback_query(filters.regex("^get_file:"))
async def handle_get_file(client: Client, query):
    """Handle file download request"""
    try:
        await query.answer()

        file_id = query.data.split(":", 1)[1]
        clone_id = await get_clone_id_from_client(client)

        # Get file from appropriate database
        from bot.database.mongo_db import get_file_by_id, increment_download_count
        file_data = await get_file_by_id(file_id, clone_id)

        if not file_data:
            await query.answer("❌ File not found.", show_alert=True)
            return

        # Increment download count
        await increment_download_count(file_id, clone_id)

        # Create download link (implement according to your link generation logic)
        file_name = file_data.get('file_name', 'Unknown File')
        file_size = get_readable_file_size(file_data.get('file_size', 0))

        text = f"📁 **{file_name}**\n\n"
        text += f"💾 **Size:** {file_size}\n"
        text += f"⬇️ **Downloads:** {file_data.get('download_count', 0) + 1}\n\n"
        text += "Click the link below to download:"

        # You'll need to implement your link generation logic here
        download_link = f"https://t.me/{client.me.username}?start=file_{file_id}"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download", url=download_link)],
            [InlineKeyboardButton("🔙 Back", callback_data="clone_random_files")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error handling file download: {e}")
        await query.answer("❌ Error processing file request.", show_alert=True)