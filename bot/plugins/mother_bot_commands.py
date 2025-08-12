
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Show help for mother bot"""
    user_id = message.from_user.id
    
    if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
        help_text = """🤖 **Mother Bot Commands**

**Clone Management:**
• `/createclone` - Create a new bot clone
• `/settoken <token>` - Set bot token for clone
• `/listclones` - List all your clones
• `/stopclone <bot_id>` - Stop a clone
• `/startclone <bot_id>` - Start a clone

**Regular Commands:**
• `/start` - Start the bot
• `/stats` - View bot statistics
• `/users` - Get user count
• `/broadcast` - Broadcast message
• `/genlink` - Generate file link
• `/batch` - Batch link generator

**Premium & Token:**
• `/token` - Generate access token
• `/premium` - View premium plans
• `/mystats` - View your stats"""
    else:
        help_text = """🤖 **Available Commands**

• `/start` - Start the bot
• `/token` - Generate access token
• `/rand` - Get random files
• `/premium` - View premium plans
• `/mystats` - View your stats
• `/help` - Show this help"""
    
    await message.reply_text(help_text)

@Client.on_message(filters.command("motherbot") & filters.private)
async def mother_bot_info(client: Client, message: Message):
    """Show mother bot information"""
    info_text = """🤖 **Mother Bot System**

This is a mother bot that can create multiple clones of itself!

**Features:**
✅ Create unlimited bot clones
✅ Each clone operates independently
✅ Same features as the main bot
✅ Easy token-based setup
✅ Full admin control

**For Admins:**
Use `/createclone` to start creating your bot network!

**For Users:**
Enjoy the same great file sharing experience across all bot instances!"""

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Create Clone", callback_data="create_new_clone")],
        [InlineKeyboardButton("📋 View Clones", callback_data="manage_clones")],
        [InlineKeyboardButton("❓ Help", callback_data="show_help")]
    ])

    await message.reply_text(info_text, reply_markup=buttons)
