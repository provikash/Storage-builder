"""
Simple test commands for clone bot verification
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("test") & filters.private)
async def test_command(client: Client, message: Message):
    """Test command to verify clone bot is working"""
    try:
        await message.reply_text(
            "✅ **Clone Bot Test**\n\n"
            "This clone bot is working perfectly!\n"
            "All systems operational.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Test Again", callback_data="test_again")],
                [InlineKeyboardButton("🏠 Back to Home", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in test command: {e}")
        await message.reply_text("❌ Test failed. Please try again.")

@Client.on_callback_query(filters.regex("^test_again$"))
async def test_again_callback(client: Client, callback_query):
    """Handle test again callback"""
    try:
        await callback_query.answer("✅ Test successful!", show_alert=True)
        await callback_query.edit_message_text(
            "✅ **Clone Bot Test - Repeated**\n\n"
            "This clone bot is still working perfectly!\n"
            "All systems remain operational.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Test Again", callback_data="test_again")],
                [InlineKeyboardButton("🏠 Back to Home", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in test again callback: {e}")
        await callback_query.answer("❌ Test failed", show_alert=True)