import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from bot.logging import LOGGER
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

logger = LOGGER(__name__)

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

async def get_trending_files(clone_id: str, limit: int = 10):
    """Get trending files based on recent downloads and engagement"""
    try:
        from bot.database.index_db import get_trending_files as get_index_trending_files
        files = await get_index_trending_files(limit=limit, clone_id=clone_id)
        return files
    except ImportError:
        try:
            from bot.database.mongo_db import get_trending_files as get_mongo_trending_files
            files = await get_mongo_trending_files(limit=limit, clone_id=clone_id)
            return files
        except ImportError:
            # Fallback to popular files
            return await get_popular_files(limit=limit, clone_id=clone_id)

async def get_file_stats(file_id: str, clone_id: str = None):
    """Get detailed file statistics"""
    try:
        from bot.database.mongo_db import get_file_stats as get_mongo_file_stats
        return await get_mongo_file_stats(file_id, clone_id)
    except ImportError:
        return {
            'views': 0,
            'downloads': 0,
            'shares': 0,
            'recent_activity': 0
        }

def format_file_text(file_data, include_stats=True):
    """Format file information for display with enhanced details"""
    try:
        file_name = file_data.get('file_name', 'Unknown File')
        file_size = get_readable_file_size(file_data.get('file_size', 0))
        file_type = file_data.get('file_type', 'unknown').upper()
        download_count = file_data.get('download_count', 0)

        # Get file extension for emoji
        ext = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
        emoji_map = {
            'mp4': '🎬', 'mkv': '🎬', 'avi': '🎬', 'mov': '🎬',
            'mp3': '🎵', 'flac': '🎵', 'wav': '🎵', 'm4a': '🎵',
            'pdf': '📄', 'doc': '📄', 'docx': '📄', 'txt': '📄',
            'jpg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'jpeg': '🖼️',
            'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦',
            'apk': '📱', 'exe': '💻', 'dmg': '💻', 'deb': '💻'
        }
        file_emoji = emoji_map.get(ext, '📁')

        text = f"{file_emoji} **{file_name}**\n"
        text += f"📊 **Type:** {file_type}\n"
        text += f"💾 **Size:** {file_size}\n"

        if include_stats:
            text += f"⬇️ **Downloads:** {download_count:,}\n"

            # Add popularity indicators
            if download_count > 1000:
                text += f"🔥 **Hot File** - Very Popular!\n"
            elif download_count > 100:
                text += f"⭐ **Popular** - Trending!\n"
            elif download_count > 10:
                text += f"👍 **Good** - Well Received!\n"

            # Add upload date if available
            upload_date = file_data.get('upload_date')
            if upload_date:
                from datetime import datetime
                if isinstance(upload_date, str):
                    upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                days_ago = (datetime.now() - upload_date.replace(tzinfo=None)).days
                if days_ago == 0:
                    text += f"🆕 **Uploaded:** Today\n"
                elif days_ago == 1:
                    text += f"📅 **Uploaded:** Yesterday\n"
                elif days_ago < 7:
                    text += f"📅 **Uploaded:** {days_ago} days ago\n"
                elif days_ago < 30:
                    weeks = days_ago // 7
                    text += f"📅 **Uploaded:** {weeks} week{'s' if weeks > 1 else ''} ago\n"

        return text
    except Exception as e:
        logger.error(f"Error formatting file text: {e}")
        return "❌ Error formatting file information"

def create_file_buttons(files, current_mode="random", page=1, total_pages=1):
    """Create inline keyboard buttons for files with enhanced navigation"""
    try:
        buttons = []

        # File buttons (max 5 per page for better UX)
        files_per_page = min(5, len(files))
        for i, file_data in enumerate(files[:files_per_page], 1):
            file_name = file_data.get('file_name', f'File {i}')
            file_size = get_readable_file_size(file_data.get('file_size', 0))
            download_count = file_data.get('download_count', 0)

            # Truncate filename and add file info
            if len(file_name) > 25:
                display_name = file_name[:22] + "..."
            else:
                display_name = file_name

            # Add popularity indicator
            if current_mode == "popular" and download_count > 100:
                popularity = "🔥" if download_count > 1000 else "⭐"
                button_text = f"{popularity} {display_name} [{file_size}]"
            else:
                button_text = f"📁 {display_name} [{file_size}]"

            file_id = str(file_data.get('_id', file_data.get('file_id')))
            buttons.append([
                InlineKeyboardButton(button_text, callback_data=f"get_file:{file_id}")
            ])

        # Add spacing
        if buttons:
            buttons.append([InlineKeyboardButton("─────────────────", callback_data="separator")])

        # Enhanced navigation buttons
        mode_buttons = []

        # Mode selection buttons with current mode indicator
        random_text = "🎲 Random ✓" if current_mode == "random" else "🎲 Random"
        recent_text = "🕒 Recent ✓" if current_mode == "recent" else "🕒 Recent"
        popular_text = "🔥 Popular ✓" if current_mode == "popular" else "🔥 Popular"

        mode_buttons.append([
            InlineKeyboardButton(random_text, callback_data="clone_random_files"),
            InlineKeyboardButton(recent_text, callback_data="clone_recent_files")
        ])
        mode_buttons.append([
            InlineKeyboardButton(popular_text, callback_data="clone_popular_files"),
            InlineKeyboardButton("📊 Trending", callback_data="clone_trending_files")
        ])

        buttons.extend(mode_buttons)

        # Pagination if needed
        if total_pages > 1:
            nav_row = []
            if page > 1:
                nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{current_mode}_{page-1}"))

            nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="page_info"))

            if page < total_pages:
                nav_row.append(InlineKeyboardButton("➡️ Next", callback_data=f"page_{current_mode}_{page+1}"))

            buttons.append(nav_row)

        # Action buttons
        action_buttons = [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{current_mode}"),
            InlineKeyboardButton("🏠 Home", callback_data="back_to_start")
        ]
        buttons.append(action_buttons)

        return InlineKeyboardMarkup(buttons)

    except Exception as e:
        logger.error(f"Error creating file buttons: {e}")
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Error", callback_data="error")]])

@Client.on_message(filters.command(["files", "discover"]) & filters.private)
async def files_discovery_command(client: Client, message: Message):
    """Handle /files and /discover commands - main file discovery interface"""
    try:
        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ File discovery is only available in clone bots.")
            return

        text = "🎯 **File Discovery Hub**\n\n"
        text += "🚀 **Discover amazing files in multiple ways:**\n\n"

        text += "🎲 **Random** - `/random`\n"
        text += "   • Discover unexpected gems\n"
        text += "   • Perfect for exploration\n\n"

        text += "🔥 **Popular** - `/popular` or `/top`\n"
        text += "   • Most downloaded files\n"
        text += "   • Community favorites\n\n"

        text += "📊 **Trending** - `/trending` or `/hot`\n"
        text += "   • What's hot right now\n"
        text += "   • Based on recent activity\n\n"

        text += "🕒 **Recent** - Browse latest uploads\n\n"

        text += "💡 **Pro Tips:**\n"
        text += "• Like files to help others discover them\n"
        text += "• Share files to boost their popularity\n"
        text += "• Check trending for the hottest content"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎲 Random", callback_data="clone_random_files"),
                InlineKeyboardButton("🔥 Popular", callback_data="clone_popular_files")
            ],
            [
                InlineKeyboardButton("📊 Trending", callback_data="clone_trending_files"),
                InlineKeyboardButton("🕒 Recent", callback_data="clone_recent_files")
            ],
            [InlineKeyboardButton("🎯 Quick Random", callback_data="get_random_file")]
        ])

        await message.reply_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in files discovery command: {e}")
        await message.reply_text("❌ Error loading file discovery. Please try again.")


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

        text = "🎲 **Random Files Discovery**\n\n"
        text += f"🎯 Picked {len(files)} random files for you:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="random")

        await message.reply_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in random files command: {e}")
        await message.reply_text("❌ Error retrieving random files. Please try again.")

@Client.on_message(filters.command(["popular", "top"]) & filters.private)
async def popular_files_command(client: Client, message: Message):
    """Handle /popular and /top commands for clone bots"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'popular_button'):
            await message.reply_text("❌ Popular files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This feature is only available in clone bots.")
            return

        # Get popular files from database
        try:
            from bot.database.index_db import get_popular_files as get_index_popular_files
            files = await get_index_popular_files(limit=10, clone_id=clone_id)
        except ImportError:
            files = await get_popular_files(limit=10, clone_id=clone_id)

        if not files:
            await message.reply_text("❌ No popular files found. Files need downloads to become popular!")
            return

        # Sort by download count
        files = sorted(files, key=lambda x: x.get('download_count', 0), reverse=True)
        top_downloads = files[0].get('download_count', 0) if files else 0

        text = "🔥 **Most Popular Files**\n\n"
        text += f"👑 **Hall of Fame** - Top {len(files)} downloads\n"
        text += f"🏆 **Champion:** {top_downloads:,} downloads\n\n"

        # Show top file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="popular")

        await message.reply_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in popular files command: {e}")
        await message.reply_text("❌ Error retrieving popular files. Please try again.")

@Client.on_message(filters.command(["trending", "hot"]) & filters.private)
async def trending_files_command(client: Client, message: Message):
    """Handle /trending and /hot commands for clone bots"""
    try:
        # Check if this is a clone and feature is enabled
        if not await check_clone_feature_enabled(client, 'popular_button'):
            await message.reply_text("❌ Trending files feature is not available or disabled.")
            return

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This feature is only available in clone bots.")
            return

        # Get trending files
        files = await get_trending_files(clone_id, limit=10)

        if not files:
            await message.reply_text("❌ No trending files found. Upload and share some files to see trends!")
            return

        text = "📊 **Trending Files**\n\n"
        text += f"🚀 **What's Hot Right Now**\n"
        text += f"⚡ Based on recent activity and engagement\n\n"

        # Show trending file details
        if files:
            trending_file = files[0]
            recent_activity = trending_file.get('recent_downloads', 0)
            text += format_file_text(trending_file, include_stats=True)
            if recent_activity > 0:
                text += f"\n🔥 **Blazing hot** with recent activity!"

        buttons = create_file_buttons(files, current_mode="trending")

        await message.reply_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in trending files command: {e}")
        await message.reply_text("❌ Error retrieving trending files. Please try again.")

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
    """Handle file download request with enhanced tracking and UI"""
    try:
        await query.answer()

        file_id = query.data.split(":", 1)[1]
        clone_id = await get_clone_id_from_client(client)
        user_id = query.from_user.id

        # Get file from appropriate database
        from bot.database.mongo_db import get_file_by_id, increment_download_count
        file_data = await get_file_by_id(file_id, clone_id)

        if not file_data:
            await query.answer("❌ File not found or removed.", show_alert=True)
            return

        # Increment download count and track user activity
        await increment_download_count(file_id, clone_id)

        # Track view (even if not downloaded)
        try:
            await track_file_view(file_id, user_id, clone_id)
        except:
            pass  # Non-critical

        # Get updated stats
        file_stats = await get_file_stats(file_id, clone_id)

        # Enhanced file display
        file_name = file_data.get('file_name', 'Unknown File')
        file_size = get_readable_file_size(file_data.get('file_size', 0))
        file_type = file_data.get('file_type', 'File').upper()
        downloads = file_stats.get('downloads', 0)
        views = file_stats.get('views', 0)

        # Get file extension for better emoji
        ext = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
        emoji_map = {
            'mp4': '🎬', 'mkv': '🎬', 'avi': '🎬', 'mov': '🎬',
            'mp3': '🎵', 'flac': '🎵', 'wav': '🎵', 'm4a': '🎵',
            'pdf': '📄', 'doc': '📄', 'docx': '📄', 'txt': '📄',
            'jpg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'jpeg': '🖼️',
            'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦',
            'apk': '📱', 'exe': '💻', 'dmg': '💻', 'deb': '💻'
        }
        file_emoji = emoji_map.get(ext, '📁')

        text = f"{file_emoji} **{file_name}**\n\n"
        text += f"📊 **Type:** {file_type}\n"
        text += f"💾 **Size:** {file_size}\n"
        text += f"⬇️ **Downloads:** {downloads:,}\n"
        text += f"👀 **Views:** {views:,}\n\n"

        # Add popularity indicators
        if downloads > 1000:
            text += f"🔥 **Viral File** - Extremely Popular!\n"
        elif downloads > 100:
            text += f"⭐ **Popular Choice** - Highly Downloaded!\n"
        elif downloads > 10:
            text += f"👍 **Community Favorite** - Well Received!\n"

        text += f"\n💫 **Ready to download?** Click below!"

        # Generate download link
        try:
            # Try to use existing link generation
            from bot.utils.helper import encode
            download_link = f"https://t.me/{client.me.username}?start=file_{encode(file_id)}"
        except:
            # Fallback
            download_link = f"https://t.me/{client.me.username}?start=file_{file_id}"

        # Enhanced button layout
        buttons = [
            [InlineKeyboardButton("⬇️ Download Now", url=download_link)],
            [
                InlineKeyboardButton("📤 Share", callback_data=f"share_file:{file_id}"),
                InlineKeyboardButton("❤️ Like", callback_data=f"like_file:{file_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to List", callback_data="clone_random_files"),
                InlineKeyboardButton("🎲 Get Another", callback_data="get_random_file")
            ]
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error handling file download: {e}")
        await query.answer("❌ Error processing file request.", show_alert=True)

# Helper function to track file views
async def track_file_view(file_id, user_id, clone_id=None):
    """Track file views for analytics"""
    try:
        from bot.database.mongo_db import files_collection, clone_files_collection
        from datetime import datetime

        collection = clone_files_collection if clone_id else files_collection

        # Update view count
        await collection.update_one(
            {"_id": file_id} if not clone_id else {"_id": file_id, "clone_id": clone_id},
            {
                "$inc": {"view_count": 1},
                "$set": {"last_viewed": datetime.now()},
                "$addToSet": {"viewers": user_id}
            }
        )
    except Exception as e:
        logger.error(f"Error tracking file view: {e}")

@Client.on_callback_query(filters.regex("^share_file:"))
async def handle_share_file(client: Client, query):
    """Handle file sharing"""
    try:
        await query.answer("📤 File sharing link copied to clipboard!", show_alert=True)

        file_id = query.data.split(":", 1)[1]
        clone_id = await get_clone_id_from_client(client)

        # Track share
        try:
            from bot.database.mongo_db import files_collection, clone_files_collection
            collection = clone_files_collection if clone_id else files_collection
            await collection.update_one(
                {"_id": file_id},
                {"$inc": {"share_count": 1}}
            )
        except:
            pass

    except Exception as e:
        logger.error(f"Error handling file share: {e}")

@Client.on_callback_query(filters.regex("^like_file:"))
async def handle_like_file(client: Client, query):
    """Handle file likes"""
    try:
        await query.answer("❤️ Thanks for liking this file!", show_alert=True)

        file_id = query.data.split(":", 1)[1]
        clone_id = await get_clone_id_from_client(client)
        user_id = query.from_user.id

        # Track like
        try:
            from bot.database.mongo_db import files_collection, clone_files_collection
            collection = clone_files_collection if clone_id else files_collection
            await collection.update_one(
                {"_id": file_id},
                {
                    "$inc": {"like_count": 1},
                    "$addToSet": {"liked_by": user_id}
                }
            )
        except:
            pass

    except Exception as e:
        logger.error(f"Error handling file like: {e}")

@Client.on_callback_query(filters.regex("^get_random_file$"))
async def handle_get_random_file(client: Client, query):
    """Get a single random file quickly"""
    try:
        await query.answer()

        clone_id = await get_clone_id_from_client(client)

        # Get one random file
        try:
            from bot.database.index_db import get_random_files as get_index_random_files
            files = await get_index_random_files(limit=1, clone_id=clone_id)
        except ImportError:
            files = await get_random_files(limit=1, clone_id=clone_id)

        if files:
            # Simulate clicking on the file
            file_id = str(files[0].get('_id', files[0].get('file_id')))
            query.data = f"get_file:{file_id}"
            await handle_get_file(client, query)
        else:
            await query.answer("❌ No files available.", show_alert=True)

    except Exception as e:
        logger.error(f"Error getting random file: {e}")
        await query.answer("❌ Error getting random file.", show_alert=True)

# Callback handlers for clone bot file browsing
@Client.on_callback_query(filters.regex("^clone_random_files$"))
async def handle_clone_random_files_callback(client: Client, query: CallbackQuery):
    """Handle random files callback for clone bot"""
    try:
        await query.answer()

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Check if feature is enabled
        if not await check_clone_feature_enabled(client, 'random_button'):
            await query.edit_message_text("❌ Random files feature is not available or disabled.")
            return

        # Get random files
        try:
            from bot.database.index_db import get_random_files as get_index_random_files
            files = await get_index_random_files(limit=10, clone_id=clone_id)
        except ImportError:
            files = await get_random_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No files found in database. Index some files first.")
            return

        text = "🎲 **Random Files Discovery**\n\n"
        text += f"🎯 Picked {len(files)} random files for you:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="random")
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in random files callback: {e}")
        await query.edit_message_text("❌ Error loading random files. Please try again.")

@Client.on_callback_query(filters.regex("^clone_popular_files$"))
async def handle_clone_popular_files_callback(client: Client, query: CallbackQuery):
    """Handle popular files callback for clone bot"""
    try:
        await query.answer()

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Check if feature is enabled
        if not await check_clone_feature_enabled(client, 'popular_button'):
            await query.edit_message_text("❌ Popular files feature is not available or disabled.")
            return

        # Get popular files
        try:
            from bot.database.index_db import get_popular_files as get_index_popular_files
            files = await get_index_popular_files(limit=10, clone_id=clone_id)
        except ImportError:
            files = await get_popular_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No popular files found. Files need downloads to become popular!")
            return

        # Sort by download count
        files = sorted(files, key=lambda x: x.get('download_count', 0), reverse=True)
        top_downloads = files[0].get('download_count', 0) if files else 0

        text = "🔥 **Most Popular Files**\n\n"
        text += f"👑 **Hall of Fame** - Top {len(files)} downloads\n"
        text += f"🏆 **Champion:** {top_downloads:,} downloads\n\n"

        # Show top file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="popular")
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in popular files callback: {e}")
        await query.edit_message_text("❌ Error loading popular files. Please try again.")

@Client.on_callback_query(filters.regex("^clone_recent_files$"))
async def handle_clone_recent_files_callback(client: Client, query: CallbackQuery):
    """Handle recent files callback for clone bot"""
    try:
        await query.answer()

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Check if feature is enabled
        if not await check_clone_feature_enabled(client, 'recent_button'):
            await query.edit_message_text("❌ Recent files feature is not available or disabled.")
            return

        # Get recent files
        try:
            from bot.database.index_db import get_recent_files as get_index_recent_files
            files = await get_index_recent_files(limit=10, clone_id=clone_id)
        except ImportError:
            files = await get_recent_files(limit=10, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No recent files found. Index some files first.")
            return

        text = "🆕 **Recent Files**\n\n"
        text += f"⏰ Latest {len(files)} files uploaded:\n\n"

        # Show first file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="recent")
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in recent files callback: {e}")
        await query.edit_message_text("❌ Error loading recent files. Please try again.")

@Client.on_callback_query(filters.regex("^clone_trending_files$"))
async def handle_clone_trending_files_callback(client: Client, query: CallbackQuery):
    """Handle trending files callback for clone bot"""
    try:
        await query.answer()

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Get trending files
        files = await get_trending_files(clone_id, limit=10)

        if not files:
            await query.edit_message_text("❌ No trending files found right now. Check back later!")
            return

        text = "📊 **Trending Files**\n\n"
        text += f"🔥 What's hot right now - {len(files)} files:\n\n"

        # Show top trending file details
        if files:
            text += format_file_text(files[0], include_stats=True)

        buttons = create_file_buttons(files, current_mode="trending")
        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in trending files callback: {e}")
        await query.edit_message_text("❌ Error loading trending files. Please try again.")

@Client.on_callback_query(filters.regex("^get_file:"))
async def handle_get_file_callback(client: Client, query: CallbackQuery):
    """Handle file download callback"""
    try:
        await query.answer("Processing your request...")

        file_id = query.data.split(":", 1)[1]
        clone_id = await get_clone_id_from_client(client)

        # Get file details
        file_data = await get_file_by_id(file_id, clone_id)
        if not file_data:
            await query.edit_message_text("❌ File not found or has been removed.")
            return

        # Increment download count
        await increment_download_count(file_id, clone_id)

        # Format file info
        text = format_file_text(file_data, include_stats=True)
        text += "\n📥 **Download starting...**"

        # Create download button or link
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Files", callback_data="clone_random_files")],
            [InlineKeyboardButton("🔄 More Random", callback_data="clone_random_files")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

        # Send the actual file if available
        try:
            if 'file_id' in file_data and file_data['file_id']:
                await client.send_document(
                    chat_id=query.from_user.id,
                    document=file_data['file_id'],
                    caption=f"📁 **{file_data.get('file_name', 'File')}**\n💾 Size: {get_readable_file_size(file_data.get('file_size', 0))}"
                )
        except Exception as send_error:
            logger.error(f"Error sending file: {send_error}")
            await query.message.reply_text("❌ Error sending file. The file might be unavailable.")

    except Exception as e:
        logger.error(f"Error in get file callback: {e}")
        await query.edit_message_text("❌ Error processing file request. Please try again.")

@Client.on_callback_query(filters.regex("^get_random_file$"))
async def handle_quick_random_file_callback(client: Client, query: CallbackQuery):
    """Handle quick random file callback"""
    try:
        await query.answer("Getting random file...")

        clone_id = await get_clone_id_from_client(client)
        if not clone_id:
            await query.edit_message_text("❌ This feature is only available in clone bots.")
            return

        # Get one random file
        try:
            from bot.database.index_db import get_random_files as get_index_random_files
            files = await get_index_random_files(limit=1, clone_id=clone_id)
        except ImportError:
            files = await get_random_files(limit=1, clone_id=clone_id)

        if not files:
            await query.edit_message_text("❌ No files found in database.")
            return

        file_data = files[0]
        file_id = str(file_data.get('_id', file_data.get('file_id')))

        # Increment download count
        await increment_download_count(file_id, clone_id)

        # Send file details and file
        text = "🎲 **Quick Random Pick!**\n\n"
        text += format_file_text(file_data, include_stats=True)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Another Random", callback_data="get_random_file")],
            [InlineKeyboardButton("📋 Browse All", callback_data="clone_random_files")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

        # Send the actual file
        try:
            if 'file_id' in file_data and file_data['file_id']:
                await client.send_document(
                    chat_id=query.from_user.id,
                    document=file_data['file_id'],
                    caption=f"🎲 **Random Pick:** {file_data.get('file_name', 'File')}"
                )
        except Exception as send_error:
            logger.error(f"Error sending random file: {send_error}")

    except Exception as e:
        logger.error(f"Error in quick random file callback: {e}")
        await query.edit_message_text("❌ Error getting random file. Please try again.")