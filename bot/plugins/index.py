
import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from info import Config
from bot.database import add_to_index
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

# Temporary storage for indexing state
class IndexTemp:
    CURRENT = 0
    CANCEL = False

temp = IndexTemp()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    # Security check: Only admins can perform indexing
    if query.from_user.id not in Config.ADMINS:
        return await query.answer("❌ Unauthorized access!", show_alert=True)
        
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    
    _, action, chat, lst_msg_id, from_user = query.data.split("#")
    
    if action == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user),
                               f'Your submission for indexing {chat} has been declined by moderators.',
                               reply_to_message_id=int(lst_msg_id))
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    
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

    if message.from_user.id in Config.ADMINS:
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

    if isinstance(chat_id, int):
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure I am an admin in the chat with invite permissions.')
    else:
        link = f"@{message.forward_from_chat.username}"
    
    buttons = [
        [InlineKeyboardButton('✅ Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')],
        [InlineKeyboardButton('❌ Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # Send to log channel (using owner as fallback if no log channel configured)
    log_chat = getattr(Config, 'LOG_CHANNEL', Config.OWNER_ID)
    await bot.send_message(log_chat,
                           f'#IndexRequest\n\n'
                           f'By: {message.from_user.mention} (<code>{message.from_user.id}</code>)\n'
                           f'Chat ID/Username: <code>{chat_id}</code>\n'
                           f'Last Message ID: <code>{last_msg_id}</code>\n'
                           f'Invite Link: {link}',
                           reply_markup=reply_markup)
    
    await message.reply('Thank you for the contribution! Wait for moderators to verify the files.')

@Client.on_message(filters.command('setskip') & filters.private & filters.user(Config.ADMINS))
async def set_skip_number(bot, message):
    """Set skip number for indexing"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/setskip <number>`\nExample: `/setskip 100`")
    
    try:
        skip_num = int(message.command[1])
        if skip_num < 0:
            return await message.reply_text("❌ Skip number must be a positive integer.")
        
        temp.CURRENT = skip_num
        await message.reply_text(f"✅ Successfully set SKIP number to **{skip_num}**\n\nThis means indexing will start from message {skip_num} from the latest message.")
        
    except ValueError:
        await message.reply_text("❌ Invalid number. Please provide a valid integer.")
    except Exception as e:
        await message.reply_text(f"❌ Error setting skip number: {str(e)}")

async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
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
                
                # Extract file information
                file_name = getattr(media, 'file_name', None) or message.caption or f"File_{message.id}"
                file_size = getattr(media, 'file_size', 0)
                file_type = message.media.value
                caption = message.caption or ''
                
                try:
                    # Check if this is being indexed for a clone
                    clone_id = None
                    if hasattr(bot, 'bot_token') and bot.bot_token != Config.BOT_TOKEN:
                        clone_id = bot.bot_token.split(':')[0]
                    
                    # Add to our index database
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
                except Exception as e:
                    logger.exception(f"Error indexing file {message.id}: {e}")
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
