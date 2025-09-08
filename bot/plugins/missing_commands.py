from pyrogram import Client, filters
from pyrogram.types import Message
from bot.logging import LOGGER
from info import Config

logger = LOGGER(__name__)

@Client.on_message(filters.command("balance") & filters.private)
async def balance_command(client: Client, message: Message):
    """Handle /balance command"""
    try:
        from bot.database.balance_db import get_user_balance

        user_id = message.from_user.id
        balance = await get_user_balance(user_id)

        text = f"💰 **Your Account Balance**\n\n"
        text += f"👤 **User:** {message.from_user.first_name}\n"
        text += f"🆔 **ID:** `{user_id}`\n"
        text += f"💵 **Current Balance:** ${balance:.2f}\n\n"
        text += f"💡 **Use your balance to:**\n"
        text += f"• 🤖 Create clone bots\n"
        text += f"• 💎 Upgrade to premium\n"
        text += f"• 🔓 Unlock advanced features"

        await message.reply_text(text)

    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await message.reply_text("❌ Error loading balance. Please try /start")

@Client.on_message(filters.command("clonestatus") & filters.private)
async def clonestatus_command(client: Client, message: Message):
    """Handle /clonestatus command"""
    try:
        from bot.database.clone_db import get_user_clones

        user_id = message.from_user.id
        clones = await get_user_clones(user_id)

        if not clones:
            await message.reply_text("🤖 **No Clone Bots Found**\n\nYou haven't created any clone bots yet. Use /createclone to get started!")
            return

        text = f"🤖 **Your Clone Bots Status**\n\n"
        for i, clone in enumerate(clones, 1):
            status = "🟢 Active" if clone.get('status') == 'active' else "🔴 Inactive"
            text += f"**{i}. Clone Bot {clone.get('bot_id')}**\n"
            text += f"📊 Status: {status}\n"
            text += f"📅 Created: {clone.get('created_at', 'Unknown')}\n\n"

        await message.reply_text(text)

    except Exception as e:
        logger.error(f"Error in clonestatus command: {e}")
        await message.reply_text("❌ Error loading clone status. Please try /start")

# Admin commands
@Client.on_message(filters.command("users") & filters.private)
async def users_command(client: Client, message: Message):
    """Handle /users command"""
    try:
        user_id = message.from_user.id
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            await message.reply_text("❌ Unauthorized access!")
            return

        from bot.database.users import get_users_count

        total_users = await get_users_count()

        text = f"👥 **Total Users Statistics**\n\n"
        text += f"📊 **Total Registered Users:** {total_users}\n"
        text += f"📅 **As of:** {message.date.strftime('%Y-%m-%d %H:%M')}"

        await message.reply_text(text)

    except Exception as e:
        logger.error(f"Error in users command: {e}")
        await message.reply_text("❌ Error loading user statistics.")