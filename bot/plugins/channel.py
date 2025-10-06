# Cleaned & Refactored by @Mak0912 (TG)
# Link Generation Module - Indexing functions moved to bot/plugins/indexing_unified.py

import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import logging

from info import Config
from bot.utils import encode

logger = logging.getLogger(__name__)

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



@Client.on_message(filters.channel & filters.incoming & filters.chat(Config.CHANNEL_ID))
async def new_post(client: Client, message: Message):
    """Handle new posts in the main storage channel - add share button"""
    
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