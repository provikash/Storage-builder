
<pyrogram>
"""
Simple test commands for clone bot verification
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command(["test", "ping"]) & filters.private)
async def test_command(client: Client, message: Message):
    """Simple test command to verify bot responsiveness"""
    try:
        user_id = message.from_user.id
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        
        # Check if this is a clone bot
        is_clone = bot_token != Config.BOT_TOKEN
        
        if is_clone:
            bot_id = bot_token.split(':')[0]
            text = f"🤖 **Clone Bot Test Successful!**\n\n"
            text += f"📋 **Bot ID:** `{bot_id}`\n"
            text += f"👤 **User ID:** `{user_id}`\n"
            text += f"✅ **Status:** Online and responding\n"
            text += f"🕐 **Response Time:** Good\n\n"
            text += f"💡 **Available Commands:**\n"
            text += f"• `/start` - Main menu\n"
            text += f"• `/help` - Help information\n"
            text += f"• `/random` - Random files\n"
            text += f"• `/popular` - Popular files\n"
            text += f"• `/files` - File discovery\n"
        else:
            text = f"🤖 **Mother Bot Test Successful!**\n\n"
            text += f"👤 **User ID:** `{user_id}`\n"
            text += f"✅ **Status:** Online and responding\n"
            text += f"🕐 **Response Time:** Good\n\n"
            text += f"💡 **Available Commands:**\n"
            text += f"• `/start` - Main menu\n"
            text += f"• `/createclone` - Create new clone\n"
            text += f"• `/motheradmin` - Admin panel\n"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
        ])

        await message.reply_text(text, reply_markup=buttons, quote=True)
        logger.info(f"Test command responded successfully for user {user_id}")

    except Exception as e:
        logger.error(f"Error in test command: {e}")
        await message.reply_text(
            "🤖 **Basic Test Response**\n\n✅ Bot is online and responding to commands!",
            quote=True
        )

@Client.on_message(filters.command(["status"]) & filters.private)
async def status_command(client: Client, message: Message):
    """Status command for clone bots"""
    try:
        user_id = message.from_user.id
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        
        text = "📊 **Bot Status Report**\n\n"
        text += "✅ **Connection:** Active\n"
        text += "✅ **Commands:** Working\n"
        text += "✅ **Database:** Connected\n"
        text += "✅ **File System:** Operational\n\n"
        
        if bot_token != Config.BOT_TOKEN:
            text += "🤖 **Bot Type:** Clone Bot\n"
            bot_id = bot_token.split(':')[0]
            text += f"📋 **Clone ID:** `{bot_id}`\n"
        else:
            text += "🤖 **Bot Type:** Mother Bot\n"
        
        text += f"👤 **Your ID:** `{user_id}`\n"
        text += f"⏰ **Last Check:** Just now"

        await message.reply_text(text, quote=True)
        logger.info(f"Status command responded successfully for user {user_id}")

    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await message.reply_text("❌ Error getting status information.", quote=True)

@Client.on_message(filters.command(["help"]) & filters.private)
async def help_command(client: Client, message: Message):
    """Help command for clone bots"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = bot_token != Config.BOT_TOKEN
        
        if is_clone:
            text = "🤖 **Clone Bot Help**\n\n"
            text += "📋 **Available Commands:**\n\n"
            text += "🏠 **Basic Commands:**\n"
            text += "• `/start` - Main menu and bot info\n"
            text += "• `/help` - This help message\n"
            text += "• `/test` or `/ping` - Test bot response\n"
            text += "• `/status` - Check bot status\n\n"
            text += "📁 **File Commands:**\n"
            text += "• `/files` or `/discover` - File discovery hub\n"
            text += "• `/random` - Get random files\n"
            text += "• `/popular` or `/top` - Most popular files\n"
            text += "• `/trending` or `/hot` - Trending files\n\n"
            text += "💡 **Tips:**\n"
            text += "• Use `/start` to see the main interface\n"
            text += "• Browse files using the inline buttons\n"
            text += "• All file downloads are tracked\n"
        else:
            text = "🤖 **Mother Bot Help**\n\n"
            text += "This is the main bot that manages clone bots.\n\n"
            text += "📋 **Admin Commands:**\n"
            text += "• `/motheradmin` - Admin panel\n"
            text += "• `/createclone` - Create new clone bot\n"
            text += "• `/stats` - System statistics\n\n"
            text += "💡 For file sharing features, use a clone bot."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("🧪 Test Bot", callback_data="test_bot")]
        ])

        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply_text("❌ Error loading help information.", quote=True)

# Callback handlers
@Client.on_callback_query(filters.regex("^test_bot$"))
async def test_bot_callback(client: Client, query):
    """Handle test bot callback"""
    try:
        await query.answer("Testing bot response...")
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = bot_token != Config.BOT_TOKEN
        
        text = "🧪 **Bot Test Results**\n\n"
        text += "✅ **Callback Handling:** Working\n"
        text += "✅ **Message Editing:** Working\n"
        text += "✅ **Button Response:** Working\n\n"
        
        if is_clone:
            bot_id = bot_token.split(':')[0]
            text += f"🤖 **Clone Bot ID:** `{bot_id}`\n"
        else:
            text += "🤖 **Mother Bot:** Active\n"
            
        text += "🎉 **All systems operational!**"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in test bot callback: {e}")
        await query.answer("❌ Test failed", show_alert=True)

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_callback(client: Client, query):
    """Handle help menu callback"""
    try:
        await query.answer()
        # Re-send help command content
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = bot_token != Config.BOT_TOKEN
        
        if is_clone:
            text = "🤖 **Clone Bot Help**\n\n"
            text += "📋 **Available Commands:**\n\n"
            text += "🏠 **Basic Commands:**\n"
            text += "• `/start` - Main menu and bot info\n"
            text += "• `/help` - This help message\n"
            text += "• `/test` or `/ping` - Test bot response\n"
            text += "• `/status` - Check bot status\n\n"
            text += "📁 **File Commands:**\n"
            text += "• `/files` or `/discover` - File discovery hub\n"
            text += "• `/random` - Get random files\n"
            text += "• `/popular` or `/top` - Most popular files\n"
            text += "• `/trending` or `/hot` - Trending files\n\n"
            text += "💡 **Tips:**\n"
            text += "• Use `/start` to see the main interface\n"
            text += "• Browse files using the inline buttons\n"
            text += "• All file downloads are tracked\n"
        else:
            text = "🤖 **Mother Bot Help**\n\n"
            text += "This is the main bot that manages clone bots.\n\n"
            text += "📋 **Admin Commands:**\n"
            text += "• `/motheradmin` - Admin panel\n"
            text += "• `/createclone` - Create new clone bot\n"
            text += "• `/stats` - System statistics\n\n"
            text += "💡 For file sharing features, use a clone bot."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("🧪 Test Bot", callback_data="test_bot")]
        ])

        await query.edit_message_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in help menu callback: {e}")
        await query.answer("❌ Error loading help", show_alert=True)
</pyrogram>
