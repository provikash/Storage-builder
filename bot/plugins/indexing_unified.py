"""
Unified Indexing Module
Consolidates all indexing functionality:
- Mother bot manual indexing
- Clone bot indexing
- Bulk/batch indexing
- Auto-indexing from channels
- Forwarded message indexing
"""
import logging
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_by_bot_token
from bot.database.index_db import add_to_index
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Global state for indexing
indexing_state = {}
bulk_indexing_state = {}

# Temporary storage for indexing configuration
class IndexConfig:
    CURRENT_SKIP = 0
    CANCEL = False

index_config = IndexConfig()


def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None


async def verify_clone_admin(client: Client, user_id: int) -> tuple[bool, dict]:
    """Verify if user is clone admin"""
    try:
        bot_token = getattr(client, 'bot_token', None)
        
        # If bot_token is None or matches mother bot, this is not a clone
        if not bot_token or bot_token == Config.BOT_TOKEN:
            logger.info(f"This is mother bot, not a clone")
            return False, None

        # Get clone data
        clone_data = await get_clone_by_bot_token(bot_token)
        logger.info(f"Clone data retrieved for token {bot_token[:10]}...: {clone_data is not None}")
        
        if not clone_data:
            logger.warning(f"No clone data found for bot token: {bot_token[:10]}...")
            return False, None

        # Check admin ID - support both admin_id and owner_id fields
        admin_id = clone_data.get('admin_id') or clone_data.get('owner_id')
        logger.info(f"Checking admin: user_id={user_id}, admin_id={admin_id}")
        
        is_admin = user_id == admin_id
        logger.info(f"Admin verification result: {is_admin}")
        
        return is_admin, clone_data
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}", exc_info=True)
        return False, None


# ===================== MOTHER BOT INDEXING =====================

@Client.on_callback_query(filters.regex(r'^index'))
async def index_callback_handler(bot, query):
    """Handle indexing callbacks for mother bot"""
    if query.from_user.id not in Config.ADMINS:
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    if query.data.startswith('index_cancel'):
        index_config.CANCEL = True
        return await query.answer("Cancelling Indexing")

    _, action, chat, lst_msg_id, from_user = query.data.split("#")

    if action == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user),
                               f'Your submission for indexing {chat} has been declined by moderators.',
                               reply_to_message_id=int(lst_msg_id))
        return

    msg = query.message
    await query.answer('Processing...⏳', show_alert=True)

    if int(from_user) not in Config.ADMINS:
        await bot.send_message(int(from_user),
                               f'Your submission for indexing {chat} has been accepted and will be added soon.',
                               reply_to_message_id=int(lst_msg_id))

    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )

    try:
        chat = int(chat)
    except:
        chat = chat

    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message((filters.forwarded | (filters.regex(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text) & filters.private & filters.incoming & filters.user(Config.ADMINS))
async def send_for_index(bot, message):
    """Handle forwarded messages or links for indexing (Mother bot)"""
    if message.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
    elif message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return

    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply('This may be a private channel/group. Make me an admin to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid link specified.')
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'Error - {e}')

    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make sure I am an admin in the channel, if channel is private')

    if k.empty:
        return await message.reply('This may be a group and I am not an admin.')

    buttons = [
        [InlineKeyboardButton('✅ Yes', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')],
        [InlineKeyboardButton('❌ Close', callback_data='close')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    return await message.reply(
        f'Do you want to index this channel/group?\n\n'
        f'Chat ID/Username: <code>{chat_id}</code>\n'
        f'Last Message ID: <code>{last_msg_id}</code>\n\n'
        f'Use /setskip to set skip number',
        reply_markup=reply_markup)


@Client.on_message(filters.command('setskip') & filters.private & filters.user(Config.ADMINS))
async def set_skip_number(bot, message):
    """Set skip number for indexing"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/setskip <number>`\nExample: `/setskip 100`")

    try:
        skip_num = int(message.command[1])
        if skip_num < 0:
            return await message.reply_text("❌ Skip number must be a positive integer.")

        index_config.CURRENT_SKIP = skip_num
        await message.reply_text(f"✅ Successfully set SKIP number to **{skip_num}**\n\nIndexing will start from message {skip_num} from the latest message.")

    except ValueError:
        await message.reply_text("❌ Invalid number. Please provide a valid integer.")


async def index_files_to_db(lst_msg_id, chat, msg, bot, clone_id=None, clone_data=None):
    """Unified file indexing logic for both mother and clone bots"""
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    clone_client = None  # Initialize outside try block
    try:
        current = index_config.CURRENT_SKIP
        index_config.CANCEL = False

        # Get database connection
        if clone_id and clone_data:
            # Use mongodb_url or db_url field from clone_data
            mongodb_url = clone_data.get('mongodb_url') or clone_data.get('db_url')
            if not mongodb_url:
                await msg.edit("❌ Clone database URL not configured.\n\nPlease ensure your clone has a valid MongoDB URL.")
                logger.error(f"No MongoDB URL found for clone {clone_id}")
                return
            
            logger.info(f"📊 Using MongoDB URL for clone {clone_id}: {mongodb_url[:20]}...")
            clone_client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=30000)
            db_name = clone_data.get('db_name', f"clone_{clone_id}")
            clone_db = clone_client[db_name]
            files_collection = clone_db.files
            logger.info(f"📊 Connected to database: {db_name}, collection: files")
        else:
            files_collection = None

        async for message in bot.iter_messages(chat, lst_msg_id, index_config.CURRENT_SKIP):
            if index_config.CANCEL:
                await msg.edit(f"Successfully Cancelled!\n\n"
                               f"Saved <code>{total_files}</code> files to database!\n"
                               f"Duplicate Files Skipped: <code>{duplicate}</code>\n"
                               f"Deleted Messages Skipped: <code>{deleted}</code>\n"
                               f"Non-Media messages skipped: <code>{no_media + unsupported}</code>\n"
                               f"Errors Occurred: <code>{errors}</code>")
                break

            current += 1

            if current % 80 == 0:
                can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                reply = InlineKeyboardMarkup(can)
                await msg.edit_text(
                    text=f"Total messages fetched: <code>{current}</code>\n"
                         f"Total messages saved: <code>{total_files}</code>\n"
                         f"Duplicate Files Skipped: <code>{duplicate}</code>\n"
                         f"Deleted Messages Skipped: <code>{deleted}</code>\n"
                         f"Non-Media messages skipped: <code>{no_media + unsupported}</code>\n"
                         f"Errors Occurred: <code>{errors}</code>",
                    reply_markup=reply)

            if message.empty:
                deleted += 1
                continue
            elif not message.media:
                no_media += 1
                continue
            elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                unsupported += 1
                continue

            media = getattr(message, message.media.value, None)
            if not media:
                unsupported += 1
                continue

            file_name = getattr(media, 'file_name', None) or message.caption or f"File_{message.id}"
            file_size = getattr(media, 'file_size', 0)
            file_type = message.media.value
            caption = message.caption or ''

            try:
                if files_collection:
                    # Clone bot - use MongoDB directly
                    unique_file_id = f"{chat}_{message.id}"
                    file_doc = {
                        "_id": unique_file_id,
                        "file_id": getattr(media, 'file_id', str(message.id)),
                        "message_id": message.id,
                        "chat_id": chat,
                        "file_name": file_name,
                        "file_type": file_type,
                        "file_size": file_size,
                        "caption": caption,
                        "user_id": message.from_user.id if message.from_user else 0,
                        "date": message.date,
                        "clone_id": clone_id,
                        "indexed_at": datetime.utcnow()
                    }
                    # Check if document already exists
                    existing = await files_collection.find_one({"_id": unique_file_id})
                    if existing:
                        duplicate += 1
                    else:
                        result = await files_collection.insert_one(file_doc)
                        if result.inserted_id:
                            total_files += 1
                        else:
                            errors += 1
                else:
                    # Mother bot - use index_db
                    try:
                        await add_to_index(
                            file_id=str(message.id),
                            file_name=file_name,
                            file_type=file_type,
                            file_size=file_size,
                            caption=caption,
                            user_id=message.from_user.id if message.from_user else 0,
                            clone_id=clone_id
                        )
                        total_files += 1
                    except Exception as add_error:
                        # Check if it's a duplicate error
                        if "duplicate" in str(add_error).lower():
                            duplicate += 1
                        else:
                            raise
            except Exception as e:
                logger.error(f"❌ Error indexing file {message.id} in chat {chat}: {e}")
                errors += 1

    except Exception as e:
        logger.exception(e)
        await msg.edit(f'Error: {e}')
    else:
        await msg.edit(f'Successfully saved <code>{total_files}</code> files to database!\n'
                       f'Duplicate Files Skipped: <code>{duplicate}</code>\n'
                       f'Deleted Messages Skipped: <code>{deleted}</code>\n'
                       f'Non-Media messages skipped: <code>{no_media + unsupported}</code>\n'
                       f'Errors Occurred: <code>{errors}</code>')
    finally:
        if clone_client is not None:
            clone_client.close()


# ===================== CLONE BOT INDEXING =====================

@Client.on_message(filters.command(['index', 'indexing', 'cloneindex']) & filters.private)
async def clone_index_command(client: Client, message: Message):
    """Unified indexing command for clone bots"""
    try:
        logger.info(f"📥 Index command received from user {message.from_user.id}")
        logger.info(f"📥 Command text: {message.text}")
        logger.info(f"📥 Command args: {message.command}")
        
        # Get bot token
        bot_token = getattr(client, 'bot_token', None)
        
        # Check if this is a clone bot
        if not bot_token or bot_token == Config.BOT_TOKEN:
            # This is the mother bot, ignore the command or show error
            logger.info(f"Index command received on mother bot, ignoring")
            return await message.reply_text(
                "❌ **This command is not available on the mother bot.**\n\n"
                "Indexing commands are only available on clone bots."
            )
        
        logger.info(f"🔑 Clone bot token (first 10 chars): {bot_token[:10]}...")

        # Verify admin
        is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
        logger.info(f"✅ Admin verification result: is_admin={is_admin}, clone_data={'present' if clone_data else 'None'}")

        if not is_admin:
            logger.warning(f"⛔ User {message.from_user.id} is not authorized for clone indexing")
            
            # Provide detailed error message
            if clone_data:
                admin_id = clone_data.get('admin_id') or clone_data.get('owner_id')
                error_msg = f"❌ **Access Denied**\n\n"
                error_msg += f"This command is only available to the clone bot administrator.\n\n"
                error_msg += f"👤 Your ID: `{message.from_user.id}`\n"
                error_msg += f"👑 Admin ID: `{admin_id}`\n\n"
                error_msg += f"Please contact the bot owner if you believe this is an error."
            else:
                error_msg = "❌ **Access Denied**\n\nThis command is only available to clone administrators."
            
            return await message.reply_text(error_msg)

        clone_id = get_clone_id_from_client(client)
        logger.info(f"🆔 Clone ID extracted: {clone_id}")
    except Exception as e:
        logger.error(f"❌ Error in clone_index_command initial setup: {e}", exc_info=True)
        return await message.reply_text(f"❌ Error: {str(e)}")

    if len(message.command) < 2:
        db_name = clone_data.get('db_name', f'clone_{clone_id}')
        mongodb_url = clone_data.get('mongodb_url') or clone_data.get('db_url', 'Not configured')
        
        help_text = (
            "📚 **Clone Bot Indexing System**\n\n"
            "**Available Commands:**\n"
            "• `/index <channel_link>` - Index from channel link\n"
            "• `/index <username>` - Index from channel username\n"
            "• `/index <channel_id>` - Index from channel ID\n\n"

            "**Supported Formats:**\n"
            "• `https://t.me/channel/123`\n"
            "• `https://t.me/c/1234567890/1`\n"
            "• `@channelname`\n"
            "• Channel ID: `-1001234567890`\n\n"

            "**Features:**\n"
            "✅ Auto-duplicate detection\n"
            "✅ Progress tracking\n"
            "✅ Error recovery\n"
            "✅ Uses clone's own database\n\n"

            f"**Clone Database:** `{db_name}`\n"
            f"**MongoDB URL:** `{mongodb_url[:30]}...`\n\n"
            "**Note:** Only the clone administrator can use indexing commands."
        )
        return await message.reply_text(help_text)

    input_text = " ".join(message.command[1:]).strip()
    await process_clone_index_request(client, message, input_text, clone_id, clone_data)


async def process_clone_index_request(client: Client, message: Message, input_text: str, clone_id: str, clone_data: dict):
    """Process clone indexing request"""
    try:
        logger.info(f"Processing clone index request for input: {input_text}")
        channel_id = None

        # Parse input format
        if input_text.startswith('@'):
            username = input_text[1:]
            logger.info(f"Parsing username: @{username}")
            chat = await client.get_chat(username)
            channel_id = chat.id
            logger.info(f"Resolved channel ID: {channel_id}")
        elif input_text.startswith('https://t.me/'):
            if '/c/' in input_text:
                regex = re.compile(r"https://t\.me/c/(\d+)/(\d+)")
                match = regex.match(input_text)
                if match:
                    channel_id = int(f"-100{match.group(1)}")
                    logger.info(f"Parsed private channel ID: {channel_id}")
            else:
                regex = re.compile(r"https://t\.me/([^/]+)/?(\d+)?")
                match = regex.match(input_text)
                if match:
                    username = match.group(1)
                    chat = await client.get_chat(username)
                    channel_id = chat.id
                    logger.info(f"Resolved public channel ID: {channel_id}")
        elif input_text.startswith('-100') or input_text.lstrip('-').isdigit():
            channel_id = int(input_text)
            logger.info(f"Using direct channel ID: {channel_id}")

        if not channel_id:
            logger.error(f"Failed to parse channel ID from input: {input_text}")
            return await message.reply_text(
                "❌ **Invalid Channel Format**\n\n"
                "Please use one of these formats:\n"
                "• `@channelname`\n"
                "• `https://t.me/channelname`\n"
                "• `-1001234567890` (Channel ID)\n"
                "• `https://t.me/c/1234567890/123` (Private channel)\n\n"
                f"**Your input:** `{input_text}`"
            )

        # Verify bot has access to channel
        try:
            chat_info = await client.get_chat(channel_id)
            logger.info(f"✅ Verified access to channel: {chat_info.title} ({channel_id})")
        except Exception as e:
            logger.error(f"❌ Cannot access channel {channel_id}: {e}")
            error_msg = str(e)

            if "CHANNEL_PRIVATE" in error_msg or "CHANNEL_INVALID" in error_msg:
                return await message.reply_text(
                    f"❌ **Cannot Access Channel**\n\n"
                    f"The channel `{channel_id}` is private or doesn't exist.\n\n"
                    "**Required Steps:**\n"
                    "1. Add the bot to the channel\n"
                    "2. Make the bot an admin\n"
                    "3. Grant 'Read Messages' permission\n"
                    "4. Try the command again"
                )
            elif "CHAT_ADMIN_REQUIRED" in error_msg:
                return await message.reply_text(
                    f"❌ **Admin Rights Required**\n\n"
                    f"The bot needs admin rights in `{channel_id}`.\n\n"
                    "**Required Steps:**\n"
                    "1. Go to channel settings\n"
                    "2. Add bot as administrator\n"
                    "3. Enable these permissions:\n"
                    "   • Read Messages\n"
                    "   • Access Message History"
                )
            else:
                return await message.reply_text(
                    f"❌ **Error Accessing Channel**\n\n"
                    f"Error: `{error_msg}`\n\n"
                    "Make sure:\n"
                    "• The bot is added to the channel\n"
                    "• The bot has admin rights\n"
                    "• For private channels, bot must be an admin"
                )

        try:
            async for latest_msg in client.iter_messages(channel_id, limit=1):
                last_msg_id = latest_msg.id
                break
            else:
                return await message.reply_text("❌ Channel appears to be empty.")
            logger.info(f"Found last message ID: {last_msg_id}")
        except Exception as e:
            logger.error(f"Failed to read messages from channel: {e}")
            return await message.reply_text(
                f"❌ **Cannot Read Messages**\n\n"
                f"Error: {str(e)}\n\n"
                f"The bot needs admin rights with 'Read Messages' permission."
            )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Indexing", callback_data=f"start_clone_index:{clone_id}:{channel_id}:{last_msg_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])

        await message.reply_text(
            f"🔍 **Indexing Confirmation**\n\n"
            f"**Channel:** {chat_info.title}\n"
            f"**Total Messages:** ~{last_msg_id:,}\n"
            f"**Database:** `{clone_data.get('db_name')}`\n\n"
            f"Ready to start indexing?",
            reply_markup=buttons
        )

    except Exception as e:
        logger.error(f"Error processing clone index request: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


@Client.on_callback_query(filters.regex("^start_clone_index:"))
async def start_clone_index_callback(client: Client, query: CallbackQuery):
    """Handle start clone indexing callback"""
    try:
        _, clone_id, channel_id, last_msg_id = query.data.split(":")
        channel_id = int(channel_id)
        last_msg_id = int(last_msg_id)

        is_admin, clone_data = await verify_clone_admin(client, query.from_user.id)
        if not is_admin:
            return await query.answer("❌ Unauthorized!", show_alert=True)

        await query.answer("Starting indexing...", show_alert=False)

        # Get latest message ID for indexing
        try:
            # Try to get the latest message from the channel
            async for msg in client.get_chat_history(channel_id, limit=1):
                last_message_id = msg.id
                break
            else:
                last_message_id = 0
        except Exception as e:
            logger.warning(f"Could not get latest message ID: {e}")
            last_message_id = 0

        # Start indexing
        status_msg = await query.message.edit_text(
            f"🔄 **Starting Indexing**\n\n"
            f"📢 **Channel:** `{await (await client.get_chat(channel_id)).title}`\n"
            f"🆔 **Channel ID:** `{channel_id}`\n"
            f"💾 **Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`\n"
            f"📊 **Last Message ID:** `{last_message_id if last_message_id > 0 else 'All messages'}`\n\n"
            "⏳ Indexing in progress...\n"
            "_This may take a while depending on channel size_"
        )

        await index_files_to_db(
            lst_msg_id=last_message_id,
            chat=channel_id,
            msg=status_msg,
            bot=client,
            clone_id=clone_id,
            clone_data=clone_data
        )

    except Exception as e:
        logger.error(f"❌ Error in start_clone_index_callback: {e}")
        await query.message.edit_text(
            f"❌ **Indexing Failed**\n\n"
            f"Error: `{str(e)}`\n\n"
            "Please check:\n"
            "• Bot has admin access to the channel\n"
            "• Database connection is working\n"
            "• Channel ID/link is correct"
        )


@Client.on_callback_query(filters.regex("^index_cancel$"))
async def cancel_clone_index_callback(client: Client, query: CallbackQuery):
    """Handle cancel indexing callback"""
    try:
        index_config.CANCEL = True
        await query.answer("⏹️ Cancelling indexing...", show_alert=True)

    except Exception as e:
        logger.error(f"Error in cancel_clone_index_callback: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


# ===================== BULK INDEXING =====================

@Client.on_message(filters.command(['bulkindex', 'batchindex']) & filters.private)
async def bulk_index_command(client: Client, message: Message):
    """Bulk indexing for multiple channels"""
    is_admin, clone_data = await verify_clone_admin(client, message.from_user.id)
    if not is_admin and message.from_user.id not in Config.ADMINS:
        return await message.reply_text("❌ Bulk indexing is only available to administrators.")

    clone_id = get_clone_id_from_client(client)

    if len(message.command) < 2:
        help_text = (
            "📚 **Bulk Indexing System**\n\n"
            "**Usage:**\n"
            "`/bulkindex <channel1> <channel2> <channel3>...`\n\n"

            "**Supported Formats:**\n"
            "• Channel usernames: `@channel1 @channel2`\n"
            "• Channel IDs: `-1001234 -1005678`\n"
            "• Mixed format: `@channel1 -1001234`\n\n"

            "**Example:**\n"
            "`/bulkindex @movies @series @documentaries`\n\n"

            "**Features:**\n"
            "✅ Parallel processing\n"
            "✅ Individual channel progress\n"
            "✅ Error recovery per channel\n"
        )
        return await message.reply_text(help_text)

    channels = message.command[1:]
    channel_info = []

    for channel in channels:
        try:
            if channel.startswith('@'):
                username = channel[1:]
                chat = await client.get_chat(username)
                channel_id = chat.id
            elif channel.lstrip('-').isdigit():
                channel_id = int(channel)
                chat = await client.get_chat(channel_id)
            else:
                continue

            async for latest_msg in client.iter_messages(channel_id, limit=1):
                last_msg_id = latest_msg.id
                break
            else:
                continue

            channel_info.append({
                "id": channel_id,
                "title": chat.title,
                "last_msg_id": last_msg_id
            })
        except:
            continue

    if not channel_info:
        return await message.reply_text("❌ No valid channels found.")

    total_messages = sum(ch['last_msg_id'] for ch in channel_info)

    text = f"📋 **Bulk Indexing Confirmation**\n\n"
    text += f"**Valid Channels ({len(channel_info)}):**\n"
    for i, ch in enumerate(channel_info[:10], 1):
        text += f"{i}. {ch['title']} (~{ch['last_msg_id']:,} messages)\n"

    text += f"\n**Total Estimated Messages:** {total_messages:,}\n"

    # Start indexing immediately
    status_msg = await message.reply_text(text + "\n\n🔄 **Starting bulk indexing...**")

    for ch in channel_info:
        try:
            await status_msg.edit_text(f"📚 Indexing: **{ch['title']}**\n\nPlease wait...")
            await index_files_to_db(ch['last_msg_id'], ch['id'], status_msg, client, clone_id, clone_data)
        except Exception as e:
            logger.error(f"Error bulk indexing {ch['title']}: {e}")

    await status_msg.edit_text("✅ **Bulk indexing completed!**")


# ===================== AUTO-INDEXING =====================

@Client.on_message(filters.channel & filters.incoming & filters.chat(Config.INDEX_CHANNEL_ID if hasattr(Config, 'INDEX_CHANNEL_ID') else 0))
async def auto_index_channel_media(client: Client, message: Message):
    """Auto-index media from designated channel"""
    if message.video or message.document or message.photo:
        try:
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

            unique_file_id = f"{Config.INDEX_CHANNEL_ID}_{message.id}"
            await add_to_index(
                file_id=unique_file_id,
                file_name=file_name,
                file_type=media_type,
                file_size=file_size,
                caption=message.caption or '',
                user_id=message.from_user.id if message.from_user else 0
            )

            logger.info(f"✅ Auto-indexed {media_type} file {message.id} from indexing channel")

        except Exception as e:
            logger.error(f"❌ Error auto-indexing: {e}")