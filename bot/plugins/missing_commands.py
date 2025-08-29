
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.users import add_user
from bot.database.premium_db import is_premium_user
from bot.database.balance_db import get_user_balance
from bot.utils import handle_force_sub
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("profile") & filters.private)
async def profile_command(client: Client, message: Message):
    """Handle /profile command"""
    user = message.from_user
    user_id = user.id

    print(f"🚀 DEBUG COMMAND: /profile command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    # Check user data
    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)
    is_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)

    # Enhanced profile information
    text = f"👤 **Your Detailed Profile**\n\n"
    text += f"🆔 **User ID:** `{user.id}`\n"
    text += f"👤 **Full Name:** {user.first_name}"
    if user.last_name:
        text += f" {user.last_name}"

    if user.username:
        text += f"\n📱 **Username:** @{user.username}"
    else:
        text += f"\n📱 **Username:** Not set"

    text += f"\n💰 **Current Balance:** ${balance:.2f}\n"

    if user_premium:
        text += f"💎 **Account Type:** Premium Member ⭐\n"
    else:
        text += f"👤 **Account Type:** Free User\n"

    if is_admin:
        text += f"🔧 **Access Level:** Administrator\n"

    text += f"\n🎯 **Profile Actions:**\n"
    text += f"Manage your account settings and view detailed information below."

    # Profile action buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance_user"),
            InlineKeyboardButton("📊 Transaction History", callback_data="transaction_history")
        ],
        [
            InlineKeyboardButton("🤖 My Clone Bots", callback_data="manage_my_clone"),
            InlineKeyboardButton("⚙️ Account Settings", callback_data="account_settings")
        ],
        [
            InlineKeyboardButton("📈 Usage Stats", callback_data="detailed_stats"),
            InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium_info")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("balance") & filters.private)
async def balance_command(client: Client, message: Message):
    """Handle /balance command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /balance command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    # Get user balance
    balance = await get_user_balance(user_id)
    user_premium = await is_premium_user(user_id)

    text = f"💰 **Your Account Balance**\n\n"
    text += f"👤 **User:** {message.from_user.first_name}\n"
    text += f"💵 **Current Balance:** ${balance:.2f}\n"
    text += f"⭐ **Account Type:** {'Premium' if user_premium else 'Free User'}\n\n"
    text += f"💡 **Use your balance to:**\n"
    text += f"• 🤖 Create clone bots\n"
    text += f"• 💎 Purchase premium features\n"
    text += f"• ⚡ Access premium tools\n"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Add Balance", callback_data="add_balance_user"),
            InlineKeyboardButton("📊 Transaction History", callback_data="transaction_history")
        ],
        [
            InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
            InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client: Client, message: Message):
    """Handle /premium command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /premium command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    user_premium = await is_premium_user(user_id)

    if user_premium:
        text = f"💎 **Premium Membership Active**\n\n"
        text += f"🎉 **Congratulations!** You're a premium member!\n\n"
        text += f"✨ **Your Premium Benefits:**\n"
        text += f"• 🤖 **Unlimited Clone Bots**\n"
        text += f"• ⚡ **Priority Processing**\n"
        text += f"• 🔒 **Advanced Security**\n"
        text += f"• 📊 **Detailed Analytics**\n"
        text += f"• 🎯 **Premium Support**\n"
        text += f"• 💾 **Increased Storage**\n"
        text += f"• 🎨 **Custom Branding**\n\n"
        text += f"🔥 **Status:** Active Premium Member"
    else:
        text = f"💎 **Premium Membership Benefits**\n\n"
        text += f"🚀 **Unlock the full potential of your file storage bot!**\n\n"
        text += f"✨ **Exclusive Premium Features:**\n"
        text += f"• 🤖 **Unlimited Clone Bots** - Create as many as you need\n"
        text += f"• ⚡ **Priority Processing** - Faster file operations\n"
        text += f"• 🔒 **Advanced Security** - Enhanced protection\n"
        text += f"• 📊 **Detailed Analytics** - Complete usage insights\n"
        text += f"• 🎯 **Premium Support** - Direct access to our team\n"
        text += f"• 🔥 **No Ads** - Clean, uninterrupted experience\n"
        text += f"• 💾 **Increased Storage** - More file capacity\n"
        text += f"• 🎨 **Custom Branding** - Personalize your clones\n\n"
        text += f"💰 **Pricing Plans:**\n"
        text += f"• 📱 **Monthly:** $9.99/month\n"
        text += f"• 💎 **Yearly:** $99.99/year *(Save 17%!)*\n"
        text += f"• ⚡ **Lifetime:** $299.99 *(Best Value!)*"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Upgrade Now", callback_data="buy_premium"),
            InlineKeyboardButton("🎁 Free Trial", callback_data="premium_trial")
        ],
        [
            InlineKeyboardButton("📋 Compare Plans", callback_data="compare_plans"),
            InlineKeyboardButton("💬 Contact Sales", url=f"https://t.me/{Config.ADMIN_USERNAME}")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("myclones") & filters.private)
async def myclones_command(client: Client, message: Message):
    """Handle /myclones command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /myclones command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    # Route to clone management
    from bot.plugins.clone_management import manage_user_clone
    
    # Create a fake query object for callback compatibility
    class FakeQuery:
        def __init__(self, message):
            self.from_user = message.from_user
            self.message = message
            self.data = "manage_my_clone"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None):
            await message.reply_text(text, reply_markup=reply_markup)

    fake_query = FakeQuery(message)
    await manage_user_clone(client, fake_query)

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle /stats command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /stats command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    user_premium = await is_premium_user(user_id)
    balance = await get_user_balance(user_id)

    text = f"📊 **Your Bot Usage Statistics**\n\n"
    text += f"👤 **Account Summary:**\n"
    text += f"• User ID: `{user_id}`\n"
    text += f"• Status: {'🌟 Premium' if user_premium else '🆓 Free User'}\n"
    text += f"• Current Balance: ${balance:.2f}\n\n"

    text += f"📈 **Usage Analytics:**\n"
    text += f"• Total Commands Used: Loading...\n"
    text += f"• Files Accessed: Loading...\n"
    text += f"• Clone Bots Created: Loading...\n"
    text += f"• Premium Features Used: Loading...\n\n"

    text += f"🎯 **Activity Summary:**\n"
    text += f"• Last Login: Just now\n"
    text += f"• Total Sessions: Loading...\n"
    text += f"• Average Session Time: Loading..."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Stats", callback_data="user_stats"),
            InlineKeyboardButton("📱 Detailed Report", callback_data="detailed_stats")
        ],
        [
            InlineKeyboardButton("🤖 My Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("💎 Premium Plans", callback_data="premium_info")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("createclone") & filters.private)
async def createclone_command(client: Client, message: Message):
    """Handle /createclone command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /createclone command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Add user to database
    await add_user(user_id)

    # Route to clone creation
    from bot.plugins.step_clone_creation import start_clone_creation
    
    # Create a fake query object for callback compatibility
    class FakeQuery:
        def __init__(self, message):
            self.from_user = message.from_user
            self.message = message
            self.data = "start_clone_creation"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None):
            await message.reply_text(text, reply_markup=reply_markup)

    fake_query = FakeQuery(message)
    await start_clone_creation(client, fake_query)

@Client.on_message(filters.command("deleteclone") & filters.private)
async def deleteclone_command(client: Client, message: Message):
    """Handle /deleteclone command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /deleteclone command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    text = f"🗑️ **Delete Clone Bot**\n\n"
    text += f"⚠️ **Warning:** This action is permanent!\n\n"
    text += f"To delete a clone bot:\n"
    text += f"1. Go to **Manage My Clones**\n"
    text += f"2. Select the clone you want to delete\n"
    text += f"3. Choose **Delete Clone** option\n\n"
    text += f"🔒 **Security:** Only you can delete your own clones."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Manage My Clones", callback_data="manage_my_clone"),
            InlineKeyboardButton("🤖 Create New Clone", callback_data="start_clone_creation")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("clonestatus") & filters.private)
async def clonestatus_command(client: Client, message: Message):
    """Handle /clonestatus command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /clonestatus command from user {user_id}")

    # Handle force subscription first
    if not await handle_force_sub(client, message):
        return

    # Route to clone management for status
    from bot.plugins.clone_management import manage_user_clone
    
    # Create a fake query object for callback compatibility
    class FakeQuery:
        def __init__(self, message):
            self.from_user = message.from_user
            self.message = message
            self.data = "manage_my_clone"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None):
            await message.reply_text(text, reply_markup=reply_markup)

    fake_query = FakeQuery(message)
    await manage_user_clone(client, fake_query)

# Admin commands
def admin_only(func):
    async def wrapper(client, message):
        user_id = message.from_user.id
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            return await message.reply_text("❌ This command is only available to administrators.")
        return await func(client, message)
    return wrapper

@Client.on_message(filters.command("admin") & filters.private)
@admin_only
async def admin_command(client: Client, message: Message):
    """Handle /admin command"""
    user_id = message.from_user.id

    print(f"🚀 DEBUG COMMAND: /admin command from user {user_id}")

    # Route to admin panel
    from bot.plugins.admin_panel import mother_admin_panel
    
    # Create a fake query object for callback compatibility
    class FakeQuery:
        def __init__(self, message):
            self.from_user = message.from_user
            self.message = message
            self.data = "admin_panel"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None):
            await message.reply_text(text, reply_markup=reply_markup)

    fake_query = FakeQuery(message)
    await mother_admin_panel(client, fake_query)

@Client.on_message(filters.command("addbalance") & filters.private)
@admin_only
async def addbalance_command(client: Client, message: Message):
    """Handle /addbalance command"""
    try:
        args = message.text.split()
        if len(args) != 3:
            return await message.reply_text("❌ Usage: `/addbalance <user_id> <amount>`")
        
        target_user_id = int(args[1])
        amount = float(args[2])
        
        from bot.database.balance_db import add_balance
        success = await add_balance(target_user_id, amount)
        
        if success:
            await message.reply_text(f"✅ Successfully added ${amount:.2f} to user {target_user_id}")
        else:
            await message.reply_text(f"❌ Failed to add balance to user {target_user_id}")
            
    except (ValueError, IndexError):
        await message.reply_text("❌ Invalid format. Usage: `/addbalance <user_id> <amount>`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("users") & filters.private)
@admin_only
async def users_command(client: Client, message: Message):
    """Handle /users command"""
    try:
        from bot.database import full_userbase
        users = await full_userbase()
        
        text = f"👥 **Bot Statistics**\n\n"
        text += f"📊 **Total Users:** {len(users)}\n"
        text += f"🆔 **User Count:** {len(users)} registered users\n"
        text += f"📈 **Growth:** Active and growing!\n\n"
        text += f"🎯 **Bot Status:** Fully operational"
        
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error retrieving user stats: {str(e)}")
