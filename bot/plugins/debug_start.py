
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("debug") & filters.private)
async def debug_command(client: Client, message: Message):
    """Debug command to test bot responsiveness"""
    try:
        user_id = message.from_user.id
        text = f"🔧 **Debug Response**\n\n"
        text += f"✅ Bot is responsive and working!\n"
        text += f"👤 User ID: `{user_id}`\n"
        text += f"🕐 Time: {message.date}\n"
        text += f"📨 Message ID: {message.id}"
        
        await message.reply_text(text)
        logger.info(f"Debug command successful for user {user_id}")
    except Exception as e:
        logger.error(f"Debug command failed: {e}")
        try:
            await message.reply_text("⚠️ Debug response with error")
        except Exception:
            pass:
            pass

@Client.on_message(filters.text & filters.private, group=99)
async def catch_all_handler(client: Client, message: Message):
    """Catch-all handler to log unhandled messages"""
    try:
        if message.text and message.text.startswith('/'):
            logger.warning(f"Unhandled command: {message.text} from user {message.from_user.id}")
            if message.text.lower().startswith("/start"):
                await message.reply_text(
                    "🤖 **Bot Response**\n\n"
                    "✅ I received your start command!\n"
                    "Try /debug for system status."
                )
        else:
            # Handle non-command text
            if message.text and len(message.text) < 50:
                await message.reply_text(
                    f"📝 You sent: `{message.text}`\n\n"
                    f"Use /start to begin or /debug to test."
                )
    except Exception as e:
        logger.error(f"Error in catch-all handler: {e}")
