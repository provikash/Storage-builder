from bot.utils.command_verification import check_command_limit, use_command
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config

@Client.on_callback_query(filters.regex("^(premium_trial|buy_premium_trial|execute_rand)$"), group=98)
async def handle_specific_callbacks(client: Client, query: CallbackQuery):
    """Handle specific callbacks that might be missed"""
    callback_data = query.data

    if callback_data in ["premium_trial", "buy_premium_trial"]:
        await query.answer("💎 Premium features coming soon! Stay tuned.", show_alert=True)
    elif callback_data == "execute_rand":
        await query.answer("🔄 This feature is being updated. Try again later.", show_alert=True)
    else:
        await query.answer("🔄 Processing...", show_alert=False)

@Client.on_callback_query(filters.regex("^close_message$"), group=97)
async def handle_close_message(client: Client, query: CallbackQuery):
    """Handle close message callback"""
    try:
        await query.message.delete()
    except:
        await query.edit_message_text("✅ Session closed.")