# Cleaned & Refactored by @Mak0912 (TG)

import asyncio
from pyrogram import filters, Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelInvalid
import logging

from info import Config
from bot.utils import encode
from bot.database import add_to_index

logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.user(Config.ADMINS) & ~filters.command([]) & (filters.photo | filters.video | filters.document) & ~filters.text)
async def auto_index_files(client: Client, message: Message):
    """Automatically index media files (videos, documents, photos) sent by admins"""
    reply_text = await message.reply_text("Indexing file...!", quote=True)

    try:
        # Copy to DB channel for storage
        post_message = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went wrong while storing file!")
        return

    # Determine media type and file info (exclude text, zip, rar etc.)
    media_type = "unknown"
    file_size = 0
    file_name = message.caption or f"File_{post_message.id}"

    if message.video:
        media_type = "video"
        file_size = message.video.file_size or 0
        if message.video.file_name:
            file_name = message.video.file_name
    elif message.photo:
        media_type = "photo"
        file_size = getattr(message.photo, 'file_size', 0)
    elif message.document:
        # Skip zip, rar and other compressed files
        if message.document.file_name:
            file_ext = message.document.file_name.lower().split('.')[-1]
            if file_ext in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
                await reply_text.edit_text("❌ Compressed files (zip, rar, etc.) are not indexed automatically.")
                return
        media_type = "document"
        file_size = message.document.file_size or 0
        if message.document.file_name:
            file_name = message.document.file_name

    try:
        # Use unique message ID combining channel and message ID
        unique_file_id = f"{client.db_channel.id}_{post_message.id}"

        # Add to search index
        await add_to_index(
            file_id=unique_file_id,
            file_name=file_name,
            file_type=media_type,
            file_size=file_size,
            caption=message.caption or '',
            user_id=message.from_user.id
        )

        await reply_text.edit_text(f"✅ File indexed successfully!\n\n📁 **File**: {file_name}\n📊 **Type**: {media_type}\n💾 **Size**: {file_size} bytes")
        print(f"✅ Indexed file {post_message.id} to database")

    except Exception as e:
        await reply_text.edit_text(f"❌ Error indexing file: {str(e)}")
        print(f"❌ Error indexing file: {e}")

@Client.on_message(filters.private & filters.command("link"))
async def create_link(client: Client, message: Message):
    # Check if user is admin
    if message.from_user.id not in list(Config.ADMINS) and message.from_user.id != Config.OWNER_ID:
        return await message.reply_text("❌ This command is only available to administrators.")
    """Create shareable link for files - requires /link command"""
    await message.reply_text("📎 Send the file you want to create a shareable link for:", quote=True)

    try:
        # Wait for the file from admin
        file_message = await client.ask(
            chat_id=message.chat.id,
            text="📎 Send the file you want to create a shareable link for:",
            filters=(filters.photo | filters.video | filters.document | filters.audio | filters.text),
            timeout=60
        )
    except Exception:
        return await message.reply_text("⏰ Timeout! Please try again.")

    reply_text = await file_message.reply_text("Creating shareable link...!", quote=True)

    try:
        post_message = await file_message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await file_message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went Wrong..!")
        return

    converted_id = post_message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>🔗 Shareable Link Created</b>\n\n{link}", reply_markup=reply_markup, disable_web_page_preview=True)

    if not Config.DISABLE_CHANNEL_BUTTON:
        try:
            await post_message.edit_reply_markup(reply_markup)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await post_message.edit_reply_markup(reply_markup)
        except Exception:
            pass

@Client.on_message(filters.channel & filters.incoming & filters.chat(Config.INDEX_CHANNEL_ID))
async def auto_index_media(client: Client, message: Message):
    """Auto index videos and media files from the designated indexing channel"""
    # Only index videos and media files (not text or audio)
    if message.video or message.document or message.photo:
        try:
            # Determine media type and file info
            media_type = "unknown"
            file_size = 0
            file_name = message.caption or f"File_{message.id}"

            if message.video:
                media_type = "video"
                file_size = message.video.file_size or 0
                if message.video.file_name:
                    file_name = message.video.file_name
            elif message.photo:
                media_type = "photo"
                file_size = getattr(message.photo, 'file_size', 0)
            elif message.document:
                media_type = "document"
                file_size = message.document.file_size or 0
                if message.document.file_name:
                    file_name = message.document.file_name

            # Use unique message ID for indexing
            unique_file_id = f"{Config.INDEX_CHANNEL_ID}_{message.id}"
            # Add to index
            await add_to_index(
                file_id=unique_file_id,
                file_name=file_name,
                file_type=media_type,
                file_size=file_size,
                caption=message.caption or '',
                user_id=message.from_user.id if message.from_user else 0
            )

            print(f"✅ Auto-indexed {media_type} file {message.id} from indexing channel")

        except Exception as e:
            print(f"❌ Error auto-indexing from indexing channel: {e}")

# Temporary storage for indexing state
class IndexTemp:
    CURRENT = 0
    CANCEL = False

temp = IndexTemp()

@Client.on_message(filters.private & filters.user(Config.ADMINS) & filters.command("debug"))
async def debug_message(client: Client, message: Message):
    """Debug command to check message properties"""
    if message.reply_to_message:
        msg = message.reply_to_message
        debug_info = f"**Message Debug Info:**\n\n"
        debug_info += f"Is Forwarded: {bool(msg.forward_from_chat)}\n"
        if msg.forward_from_chat:
            debug_info += f"Forward From: {msg.forward_from_chat.title or msg.forward_from_chat.username}\n"
            debug_info += f"Forward From ID: {msg.forward_from_chat.id}\n"
            debug_info += f"Forward From Type: {msg.forward_from_chat.type}\n"
        debug_info += f"Has Media: {bool(msg.media)}\n"
        debug_info += f"Media Type: {msg.media if msg.media else 'None'}\n"
        await message.reply_text(debug_info)
    else:
        await message.reply_text("❌ Reply to a message to debug it!")

@Client.on_message(filters.forwarded & filters.private & filters.user(Config.ADMINS))
async def handle_forwarded_files(client: Client, message: Message):
    """Handle forwarded messages and auto-index channel if bot is admin"""

    # Check if message is forwarded from a channel
    if not message.forward_from_chat:
        return

    if message.forward_from_chat.type != enums.ChatType.CHANNEL:
        return

    forward_chat = message.forward_from_chat
    channel_id = forward_chat.id
    channel_title = forward_chat.title or forward_chat.username or "Unknown Channel"

    # Check if bot is admin in the forwarded channel
    try:
        bot_member = await client.get_chat_member(channel_id, client.me.id)
        if bot_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            await message.reply_text(
                f"❌ I'm not an admin in **{channel_title}**\n"
                f"Please make me an admin with message reading permissions to index files from this channel."
            )
            return
    except (ChatAdminRequired, ChannelInvalid):
        await message.reply_text(
            f"❌ Cannot access **{channel_title}**\n"
            f"Please make me an admin with message reading permissions to index files from this channel."
        )
        return
    except Exception as e:
        await message.reply_text(f"❌ Error checking admin status: {str(e)}")
        return

    # Confirm indexing with admin
    confirm_msg = await message.reply_text(
        f"✅ I'm an admin in **{channel_title}**!\n\n"
        f"Do you want me to start indexing all media files from this channel?\n"
        f"This will only index new files (no duplicates).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Indexing", callback_data=f"start_index#{channel_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_index")]
        ])
    )

@Client.on_callback_query(filters.regex(r"^(start_index|cancel_index)"))
async def handle_index_callback(client: Client, query):
    """Handle indexing confirmation callbacks"""
    
    # Security check: Only admins can perform indexing
    if query.from_user.id not in Config.ADMINS:
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    if query.data == "cancel_index":
        await query.message.edit_text("❌ Indexing cancelled.")
        return

    # Extract channel ID from callback data
    _, channel_id = query.data.split("#")
    channel_id = int(channel_id)

    await query.message.edit_text("🔍 Starting to index channel files... Please wait.")

    # Start indexing process
    await index_channel_files(client, query.message, channel_id)

@Client.on_message(filters.private & filters.user(Config.ADMINS) & filters.command("indexchannel"))
async def manual_index_channel(client: Client, message: Message):
    """Manual command to index a channel by ID or username"""
    try:
        # Get channel ID from command
        if len(message.command) < 2:
            return await message.reply_text(
                "❌ Please provide channel ID or username!\n\n"
                "Usage: `/indexchannel @channelname` or `/indexchannel -1001234567890`"
            )

        channel_input = message.command[1]

        # Try to get channel info
        try:
            channel = await client.get_chat(channel_input)
            channel_id = channel.id
            channel_title = channel.title or channel.username or "Unknown Channel"
        except Exception as e:
            return await message.reply_text(f"❌ Cannot find channel: {str(e)}")

        # Check if bot is admin
        try:
            bot_member = await client.get_chat_member(channel_id, client.me.id)
            if bot_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                return await message.reply_text(
                    f"❌ I'm not an admin in **{channel_title}**\n"
                    f"Please make me an admin with message reading permissions."
                )
        except Exception as e:
            return await message.reply_text(f"❌ Error checking admin status: {str(e)}")

        # Start indexing
        confirm_msg = await message.reply_text(
            f"✅ Found channel **{channel_title}**!\n\n"
            f"Starting indexing process...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_index")]
            ])
        )

        # Start the indexing process
        await index_channel_files(client, confirm_msg, channel_id)

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.private & filters.user(Config.ADMINS) & filters.command("setskip"))
async def set_skip_number(client: Client, message: Message):
    """Set skip number for indexing"""
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply_text("Skip number should be an integer.")
        await message.reply_text(f"Successfully set SKIP number to {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply_text("Give me a skip number")

async def index_channel_files(client: Client, message: Message, channel_id: int):
    """Index all media files from a channel using get_messages (bot-compatible)"""

    total_files = 0
    duplicate_files = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    try:
        # Get channel info
        channel = await client.get_chat(channel_id)
        
        # Start indexing from latest messages
        current = 0
        async for msg in client.get_chat_history(channel_id):
            if temp.CANCEL:
                await message.edit_text(
                    f"❌ Indexing cancelled!\n\n"
                    f"📊 **Statistics:**\n"
                    f"• Files indexed: {total_files}\n"
                    f"• Duplicates skipped: {duplicate_files}\n"
                    f"• Deleted messages: {deleted}\n"
                    f"• Non-media messages: {no_media}\n"
                    f"• Errors: {errors}"
                )
                break

            current += 1

            # Update progress every 50 messages
            if current % 50 == 0:
                await message.edit_text(
                    f"🔍 **Indexing in progress...**\n\n"
                    f"📊 **Current Statistics:**\n"
                    f"• Messages processed: {current}\n"
                    f"• Files indexed: {total_files}\n"
                    f"• Duplicates skipped: {duplicate_files}\n"
                    f"• Non-media messages: {no_media}\n"
                    f"• Errors: {errors}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Cancel", callback_data="index_cancel")]
                    ])
                )

            if msg.empty:
                deleted += 1
                continue

            if not msg.media:
                no_media += 1
                continue

            # Only index video, document, photo, audio
            if not (msg.video or msg.document or msg.photo or msg.audio):
                unsupported += 1
                continue

            try:
                # Determine file info
                media_type = "unknown"
                file_size = 0
                file_name = msg.caption or f"File_{msg.id}"

                if msg.video:
                    media_type = "video"
                    file_size = msg.video.file_size or 0
                    if msg.video.file_name:
                        file_name = msg.video.file_name
                elif msg.document:
                    media_type = "document"
                    file_size = msg.document.file_size or 0
                    if msg.document.file_name:
                        file_name = msg.document.file_name
                elif msg.photo:
                    media_type = "photo"
                    file_size = getattr(msg.photo, 'file_size', 0)
                elif msg.audio:
                    media_type = "audio"
                    file_size = msg.audio.file_size or 0
                    if msg.audio.file_name:
                        file_name = msg.audio.file_name

                # Create unique file ID
                unique_file_id = f"{channel_id}_{msg.id}"

                # Add to index
                await add_to_index(
                    file_id=unique_file_id,
                    file_name=file_name,
                    file_type=media_type,
                    file_size=file_size,
                    caption=msg.caption or '',
                    user_id=msg.from_user.id if msg.from_user else 0
                )

                total_files += 1

            except Exception as e:
                print(f"Error indexing message {msg.id}: {e}")
                errors += 1

        # Final status
        await message.edit_text(
            f"✅ **Indexing completed!**\n\n"
            f"📊 **Final Statistics:**\n"
            f"• Messages processed: {current}\n"
            f"• Files indexed: {total_files}\n"
            f"• Duplicates skipped: {duplicate_files}\n"
            f"• Deleted messages: {deleted}\n"
            f"• Non-media messages: {no_media + unsupported}\n"
            f"• Errors: {errors}"
        )

    except Exception as e:
        logger.exception(f"Error during channel indexing: {e}")
        await message.edit_text(f"❌ Error during indexing: {str(e)}")

async def index_channel_files_alt(client: Client, message: Message, channel_id: int):
    """Alternative indexing method with proper error handling"""
    total_files = 0
    duplicate_files = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    message_count = 0
    processed_files = set()

    try:
        # Get channel info
        channel = await client.get_chat(channel_id)
        channel_title = channel.title or "Unknown Channel"

        status_msg = await message.edit_text(
            f"📊 **Indexing Progress for {channel_title}**\n\n"
            f"🔍 Scanning messages...\n"
            f"📁 Files indexed: {total_files}\n"
            f"⚠️ Duplicates skipped: {duplicate_files}\n"
            f"❌ Errors: {errors}"
        )

        temp.CANCEL = False

        # Use get_messages with batch processing for bot compatibility
        current_id = temp.CURRENT
        batch_size = 50  # Reduced from 100 to prevent rate limiting

        while not temp.CANCEL:
            try:
                # Add delay between batches to prevent rate limiting
                if current_id > temp.CURRENT:
                    await asyncio.sleep(1)  # 1 second delay between batches
                
                # Get a batch of messages starting from current_id
                message_ids = list(range(current_id + 1, current_id + batch_size + 1))
                messages = await client.get_messages(channel_id, message_ids=message_ids)

                # If no messages returned, we've reached the end
                if not messages or all(msg is None for msg in messages):
                    break

                for msg in messages:
                    if temp.CANCEL:
                        await status_msg.edit_text(
                            f"⚠️ **Indexing Cancelled for {channel_title}**\n\n"
                            f"🔍 Messages scanned: {message_count}\n"
                            f"📁 Files indexed: {total_files}\n"
                            f"⚠️ Duplicates skipped: {duplicate_files}\n"
                            f"❌ Errors: {errors}"
                        )
                        break

                    # Skip None messages (deleted or not found)
                    if msg is None:
                        deleted += 1
                        continue

                    message_count += 1

                    # Update progress every 200 messages to reduce API calls
                    if message_count % 200 == 0:
                        await status_msg.edit_text(
                            f"📊 **Indexing Progress for {channel_title}**\n\n"
                            f"🔍 Messages scanned: {message_count}\n"
                            f"📁 Files indexed: {total_files}\n"
                            f"⚠️ Duplicates skipped: {duplicate_files}\n"
                            f"❌ Errors: {errors}"
                        )


                    # Skip if message has no media
                    if not msg.media:
                        no_media += 1
                        continue

                    # Only process videos, documents, and photos (skip audio, stickers, etc.)
                    if msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
                        unsupported += 1
                        continue

                    # Use Telegram's unique message ID as the file identifier
                    # Each message has a unique ID within a channel
                    unique_file_id = f"{channel_id}_{msg.id}"

                    if unique_file_id in processed_files:
                        duplicate_files += 1
                        continue

                    try:
                        # Check if file already exists in database using unique message ID
                        from bot.database.index_db import collection
                        existing_file = await collection.find_one({"_id": unique_file_id})
                        if existing_file:
                            duplicate_files += 1
                            processed_files.add(unique_file_id)
                            continue

                        # Extract file information
                        media_type = "unknown"
                        file_size = 0
                        file_name = msg.caption or f"File_{msg.id}"

                        if msg.video:
                            media_type = "video"
                            file_size = msg.video.file_size or 0
                            if msg.video.file_name:
                                file_name = msg.video.file_name
                        elif msg.photo:
                            media_type = "photo"
                            file_size = getattr(msg.photo, 'file_size', 0)
                        elif msg.document:
                            # Skip compressed files
                            if msg.document.file_name:
                                file_ext = msg.document.file_name.lower().split('.')[-1]
                                if file_ext in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
                                    continue
                            media_type = "document"
                            file_size = msg.document.file_size or 0
                            if msg.document.file_name:
                                file_name = msg.document.file_name

                        # Add to index using unique message ID
                        await add_to_index(
                            file_id=unique_file_id,
                            file_name=file_name,
                            file_type=media_type,
                            file_size=file_size,
                            caption=msg.caption or '',
                            user_id=msg.from_user.id if msg.from_user else 0
                        )

                        total_files += 1
                        processed_files.add(unique_file_id)

                    except Exception as e:
                        logger.exception(f"Error indexing file {msg.id}: {e}")
                        errors += 1

                # Update current_id for the next batch
                current_id += batch_size

            except Exception as e:
                logger.exception(f"Error during batch processing: {e}")
                errors += 1
                break


        # Final status update
        await status_msg.edit_text(
            f"✅ **Indexing Complete for {channel_title}**\n\n"
            f"🔍 Total messages scanned: {message_count}\n"
            f"📁 Files successfully indexed: {total_files}\n"
            f"⚠️ Duplicate files skipped: {duplicate_files}\n"
            f"🗑️ Deleted messages skipped: {deleted}\n"
            f"📄 Non-media messages skipped: {no_media + unsupported}\n"
            f"❌ Errors encountered: {errors}\n\n"
            f"All media files from the channel have been indexed!"
        )

        logger.info(f"✅ Completed indexing channel {channel_title}: {total_files} files indexed")

    except Exception as e:
        logger.exception(f"Error during channel indexing: {e}")
        await message.edit_text(f"❌ Error during indexing: {str(e)}")

@Client.on_callback_query(filters.regex(r"^index_cancel"))
async def cancel_indexing(client: Client, query):
    """Cancel ongoing indexing process"""
    temp.CANCEL = True
    await query.answer("Indexing process cancelled!", show_alert=True)

@Client.on_message(filters.channel & filters.incoming & filters.chat(Config.CHANNEL_ID))
async def new_post(client: Client, message: Message):
    """Handle new posts in the main storage channel"""
    
    # Auto-index media files from the main storage channel
    if message.video or message.document or message.photo or message.audio:
        try:
            # Determine media type and file info
            media_type = "unknown"
            file_size = 0
            file_name = message.caption or f"File_{message.id}"

            if message.video:
                media_type = "video"
                file_size = message.video.file_size or 0
                if message.video.file_name:
                    file_name = message.video.file_name
            elif message.document:
                media_type = "document"
                file_size = message.document.file_size or 0
                if message.document.file_name:
                    file_name = message.document.file_name
            elif message.photo:
                media_type = "photo"
                file_size = getattr(message.photo, 'file_size', 0)
            elif message.audio:
                media_type = "audio"
                file_size = message.audio.file_size or 0
                if message.audio.file_name:
                    file_name = message.audio.file_name

            # Use unique message ID for indexing
            unique_file_id = f"{Config.CHANNEL_ID}_{message.id}"

            # Add to index
            await add_to_index(
                file_id=unique_file_id,
                file_name=file_name,
                file_type=media_type,
                file_size=file_size,
                caption=message.caption or '',
                user_id=message.from_user.id if message.from_user else 0
            )

            print(f"✅ Auto-indexed {media_type} file {message.id} from main storage channel")

        except Exception as e:
            print(f"❌ Error auto-indexing from main channel: {e}")
    
    # Add share button if not disabled
    if not Config.DISABLE_CHANNEL_BUTTON:
        converted_id = message.id * abs(client.db_channel.id)
        string = f"get-{converted_id}"
        base64_string = encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
        try:
            await message.edit_reply_markup(reply_markup)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.edit_reply_markup(reply_markup)
        except Exception:
            pass
"""
Channel management plugin for file indexing and storage
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config
from bot.database.index_db import save_file, get_search_results

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & filters.media)
async def index_files(client: Client, message: Message):
    """Index files from channels"""
    try:
        # Only index from configured channels
        if message.chat.id not in Config.FORCE_SUB_CHANNEL:
            return
            
        # Extract file info
        media = message.document or message.video or message.audio or message.photo
        if not media:
            return
            
        file_name = getattr(media, 'file_name', '') or message.caption or 'Unknown'
        file_size = getattr(media, 'file_size', 0)
        file_type = message.media.value if message.media else 'unknown'
        
        # Save to database
        await save_file(
            file_id=media.file_id,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            message_id=message.id,
            chat_id=message.chat.id,
            caption=message.caption or ''
        )
        
        logger.info(f"Indexed file: {file_name} from channel {message.chat.id}")
        
    except Exception as e:
        logger.error(f"Error indexing file: {e}")

@Client.on_message(filters.command("search") & filters.private)
async def search_files(client: Client, message: Message):
    """Search indexed files"""
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ Please provide a search query.\n\nUsage: `/search filename`")
            return
            
        query = " ".join(message.command[1:])
        results = await get_search_results(query, limit=50)
        
        if not results:
            await message.reply_text("❌ No files found matching your search.")
            return
            
        text = f"🔍 **Search Results for:** `{query}`\n\n"
        for i, result in enumerate(results[:10], 1):
            text += f"{i}. **{result['file_name']}**\n"
            text += f"   📁 Size: {result['file_size']} bytes\n"
            text += f"   🔗 `/get_{result['file_id']}`\n\n"
            
        if len(results) > 10:
            text += f"... and {len(results) - 10} more results.\n"
            
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await message.reply_text("❌ An error occurred while searching.")
