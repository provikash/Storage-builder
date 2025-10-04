
"""
Unified Commands Handler System
Consolidates all command handlers from the entire project
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database import add_user, present_user, is_premium_user
from bot.utils import handle_force_sub
from bot.logging import LOGGER

logger = LOGGER(__name__)

# =====================================================
# HELP COMMAND
# =====================================================
@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle help command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    help_text = """
📚 **Help & Commands**

🤖 **Basic Commands:**
/start - Start the bot
/help - Show this help message
/about - About this bot

💎 **Premium Commands:**
/premium - View premium plans
/balance - Check your balance
/profile - View your profile

🔍 **Search & Files:**
Use the search feature to find files

👨‍💼 **Admin Commands:**
/admin - Admin panel (Admins only)
/broadcast - Broadcast message (Admins only)
/stats - Bot statistics (Admins only)

Need more help? Contact support!
"""
    
    await message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )

# =====================================================
# PROFILE COMMAND
# =====================================================
@Client.on_message(filters.command("profile") & filters.private)
async def profile_command(client: Client, message: Message):
    """Handle profile command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    try:
        from bot.database.users import get_user_stats
        stats = await get_user_stats(user_id)
        is_premium = await is_premium_user(user_id)
        
        profile_text = f"""
👤 **Your Profile**

🆔 User ID: `{user_id}`
👤 Name: {message.from_user.first_name}
"""
        if message.from_user.username:
            profile_text += f"📝 Username: @{message.from_user.username}\n"
        
        profile_text += f"""
💎 Status: {'Premium ⭐' if is_premium else 'Free User'}
📊 Commands Used: {stats.get('command_count', 0)}
🤖 Clone Bots: {stats.get('clone_count', 0)}
"""
        
        await message.reply_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium", callback_data="show_premium_plans")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await message.reply_text("❌ Error loading profile. Please try again.")

# =====================================================
# BALANCE COMMAND
# =====================================================
@Client.on_message(filters.command("balance") & filters.private)
async def balance_command(client: Client, message: Message):
    """Handle balance command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    try:
        from bot.database.balance_db import get_user_balance
        balance = await get_user_balance(user_id)
        
        balance_text = f"""
💰 **Your Balance**

Current Balance: **{balance} tokens**

Use tokens to:
• Create clone bots
• Access premium features
• Remove command limits
"""
        
        await message.reply_text(
            balance_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Balance", callback_data="show_balance_options")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await message.reply_text("❌ Error loading balance. Please try again.")

# =====================================================
# PREMIUM COMMAND
# =====================================================
@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client: Client, message: Message):
    """Handle premium command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    is_premium = await is_premium_user(user_id)
    
    if is_premium:
        await message.reply_text(
            "✨ **You're already a Premium Member!**\n\n"
            "Enjoy unlimited access to all features.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
        return
    
    premium_text = """
💎 **Premium Membership**

✨ Premium Benefits:
• Unlimited commands
• No verification required
• Priority support
• Exclusive features
• Ad-free experience

📦 Choose Your Plan:
"""
    
    await message.reply_text(
        premium_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 View Plans", callback_data="show_premium_plans")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

# =====================================================
# MY CLONES COMMAND
# =====================================================
@Client.on_message(filters.command("myclones") & filters.private)
async def myclones_command(client: Client, message: Message):
    """Handle myclones command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    try:
        from bot.database.clone_db import get_user_clones
        clones = await get_user_clones(user_id)
        
        if not clones:
            await message.reply_text(
                "🤖 **You don't have any clone bots yet!**\n\n"
                "Create your first clone bot using /createclone",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Create Clone", callback_data="start_clone_creation")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
            return
        
        clones_text = f"🤖 **Your Clone Bots** ({len(clones)})\n\n"
        
        buttons = []
        for clone in clones[:10]:  # Limit to 10
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'unknown')
            status_emoji = "✅" if status == "active" else "❌"
            
            clones_text += f"{status_emoji} @{username} - {status}\n"
            buttons.append([InlineKeyboardButton(f"⚙️ {username}", callback_data=f"manage_clone_{clone.get('_id')}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
        
        await message.reply_text(
            clones_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Error in myclones command: {e}")
        await message.reply_text("❌ Error loading clones. Please try again.")

# =====================================================
# CREATE CLONE COMMAND
# =====================================================
@Client.on_message(filters.command("createclone") & filters.private)
async def createclone_command(client: Client, message: Message):
    """Handle createclone command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    await message.reply_text(
        "🤖 **Create Your Clone Bot**\n\n"
        "To create a clone bot:\n"
        "1. Talk to @BotFather on Telegram\n"
        "2. Create a new bot and get the bot token\n"
        "3. Send the bot token to me\n\n"
        "⚠️ Make sure you have sufficient balance!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Check Balance", callback_data="show_balance_options")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

# =====================================================
# STATS COMMAND
# =====================================================
@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle stats command"""
    user_id = message.from_user.id
    
    if await handle_force_sub(client, message):
        return
    
    # Check if user is admin
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        await message.reply_text("❌ This command is only for admins.")
        return
    
    try:
        from bot.database.users import get_total_users
        from bot.database.clone_db import get_all_clones
        
        total_users = await get_total_users()
        all_clones = await get_all_clones()
        active_clones = len([c for c in all_clones if c.get('status') == 'active'])
        
        stats_text = f"""
📊 **Bot Statistics**

👥 Total Users: {total_users}
🤖 Total Clones: {len(all_clones)}
✅ Active Clones: {active_clones}
❌ Inactive Clones: {len(all_clones) - active_clones}
"""
        
        await message.reply_text(stats_text)
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error loading statistics.")

# =====================================================
# BROADCAST COMMAND
# =====================================================
@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle broadcast command"""
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        await message.reply_text("❌ This command is only for admins.")
        return
    
    await message.reply_text(
        "📢 **Broadcast Message**\n\n"
        "Reply to any message with /broadcast to send it to all users.\n\n"
        "Usage: Reply to a message and use /broadcast"
    )

logger.info("✅ Unified commands module loaded successfully")
