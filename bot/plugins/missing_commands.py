from pyrogram import Client, filters
from pyrogram.types import Message
from bot.logging import LOGGER
from info import Config

logger = LOGGER(__name__)

@Client.on_message(filters.command("profile") & filters.private)
async def profile_command(client: Client, message: Message):
    """Handle /profile command"""
    try:
        # Route to start_handler profile callback
        from bot.plugins.start_handler import profile_callback
        from pyrogram.types import CallbackQuery, InlineKeyboardButton

        # Create a fake callback query to reuse existing handler
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await profile_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await message.reply_text("❌ Error loading profile. Please try /start")

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

@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client: Client, message: Message):
    """Handle /premium command"""
    try:
        from bot.plugins.premium import premium_callback

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda text="", show_alert=False: None,
            'edit_message_text': lambda text, reply_markup=None: message.reply_text(text, reply_markup=reply_markup)
        })()

        await premium_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in premium command: {e}")
        await message.reply_text("❌ Error loading premium info. Please try /start")

@Client.on_message(filters.command("myclones") & filters.private)
async def myclones_command(client: Client, message: Message):
    """Handle /myclones command"""
    try:
        from bot.plugins.clone_management import my_clones_callback

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await my_clones_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in myclones command: {e}")
        await message.reply_text("❌ Error loading clones. Please try /start")

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle /stats command"""
    try:
        from bot.plugins.stats import my_stats_callback

        # Create fake callback query  
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda text="", show_alert=False: None,
            'edit_message_text': lambda text, reply_markup=None: message.reply_text(text, reply_markup=reply_markup)
        })()

        await my_stats_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error loading stats. Please try /start")

@Client.on_message(filters.command("createclone") & filters.private)
async def createclone_command(client: Client, message: Message):
    """Handle /createclone command"""
    try:
        from bot.plugins.step_clone_creation import start_clone_creation_callback

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await start_clone_creation_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in createclone command: {e}")
        await message.reply_text("❌ Error starting clone creation. Please try /start")

@Client.on_message(filters.command("deleteclone") & filters.private)
async def deleteclone_command(client: Client, message: Message):
    """Handle /deleteclone command"""
    try:
        from bot.plugins.clone_management import delete_clone_callback

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await delete_clone_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in deleteclone command: {e}")
        await message.reply_text("❌ Error deleting clone. Please try /start")

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

# Removed duplicate help command handler - handled in start_handler.pydler
        from bot.plugins.start_handler import help_callback

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await help_callback(client, fake_query)

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply_text("❌ Error loading help. Please try /start")

# Admin commands
@Client.on_message(filters.command("admin") & filters.private)
async def admin_command(client: Client, message: Message):
    """Handle /admin command"""
    try:
        user_id = message.from_user.id
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            await message.reply_text("❌ Unauthorized access!")
            return

        from bot.plugins.admin_panel import mother_admin_panel

        # Create fake callback query
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda: None,
            'edit_message_text': message.reply_text
        })()

        await mother_admin_panel(client, fake_query)

    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        await message.reply_text("❌ Error loading admin panel. Please try /start")

@Client.on_message(filters.command("addbalance") & filters.private)
async def addbalance_command(client: Client, message: Message):
    """Handle /addbalance command"""
    try:
        user_id = message.from_user.id
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            await message.reply_text("❌ Unauthorized access!")
            return

        await message.reply_text(
            "💰 **Add Balance Command**\n\n"
            "**Usage:** `/addbalance <user_id> <amount>`\n"
            "**Example:** `/addbalance 123456789 50.00`\n\n"
            "This will add the specified amount to the user's balance."
        )

    except Exception as e:
        logger.error(f"Error in addbalance command: {e}")
        await message.reply_text("❌ Error in addbalance command.")

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle /broadcast command"""
    try:
        user_id = message.from_user.id
        if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
            await message.reply_text("❌ Unauthorized access!")
            return

        await message.reply_text(
            "📢 **Broadcast Command**\n\n"
            "**Usage:** Reply to a message with `/broadcast` to send it to all users.\n\n"
            "⚠️ **Note:** This will send the message to all registered users."
        )

    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await message.reply_text("❌ Error in broadcast command.")

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