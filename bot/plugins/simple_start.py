
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("start") & filters.private, group=0)
async def simple_start_command(client: Client, message: Message):
    """Simple fallback start command"""
    try:
        user = message.from_user
        user_id = user.id
        
        print(f"🔥 SIMPLE START: Command from user {user_id}")
        logger.info(f"Simple start command from user {user_id}")
        
        text = f"🤖 **Welcome {user.first_name}!**\n\n"
        text += f"I'm your personal bot assistant.\n\n"
        text += f"🎯 **Available Options:**"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Help", callback_data="help_menu")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
        logger.info(f"Simple start response sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in simple start command: {e}")
        try:
            await message.reply_text("✅ Bot is working! Try again.")
        except:
            pass
