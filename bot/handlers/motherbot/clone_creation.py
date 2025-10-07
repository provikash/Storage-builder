
"""
Mother Bot Clone Creation Handler
Handles step-by-step clone creation process
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.database.balance_db import *
from bot.logging import LOGGER
from bot.utils.session_manager import SessionManager

logger = LOGGER(__name__)
session_manager = SessionManager()

async def notify_mother_bot_admins(user_id: int, clone_data: dict, plan_details: dict):
    """Notify mother bot admins about a new clone creation."""
    try:
        if not Config.OWNER_ID:
            logger.warning("No OWNER_ID configured, cannot notify admins about new clone.")
            return

        from pyrogram import Client as TelegramClient
        
        user_name = f"User {user_id}"
        
        message_text = (
            f"📣 **New Clone Bot Created!**\n\n"
            f"👤 **User:** {user_name} (ID: `{user_id}`)\n"
            f"🤖 **Clone Bot:** @{clone_data['bot_username']} (ID: `{clone_data['bot_id']}`)\n"
            f"💰 **Plan:** {plan_details['name']} (${plan_details['price']})\n"
            f"📅 **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🔗 **Bot Link:** https://t.me/{clone_data['bot_username']}"
        )

        admin_ids = [Config.OWNER_ID] if isinstance(Config.OWNER_ID, int) else Config.OWNER_ID

        for admin_id in admin_ids:
            try:
                logger.info(f"Would notify admin {admin_id} about new clone creation by user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")

    except Exception as e:
        logger.error(f"Error in notify_mother_bot_admins for user {user_id}: {e}")

async def create_clone_directly(user_id: int, data: dict):
    """Create clone directly"""
    try:
        plan_details = data['plan_details']
        required_amount = plan_details['price']

        logger.info(f"💰 Processing payment of ${required_amount} for user {user_id}")

        current_balance = await get_user_balance(user_id)
        if current_balance < required_amount:
            return False, f"Insufficient balance. Required: ${required_amount}, Available: ${current_balance}"

        await deduct_balance(user_id, required_amount, f"Clone creation - {plan_details['name']}")
        logger.info(f"💰 Balance deducted successfully for user {user_id}")

        clone_data = {
            '_id': str(data['bot_id']),
            'admin_id': user_id,
            'username': data['bot_username'],
            'bot_token': data['bot_token'],
            'mongodb_url': data['mongodb_url'],
            'status': 'active',
            'created_at': datetime.now(),
            'last_seen': datetime.now()
        }

        await create_clone(clone_data)
        logger.info(f"🤖 Clone record created for bot {data['bot_id']}")

        subscription_data = {
            '_id': str(data['bot_id']),
            'bot_id': str(data['bot_id']),
            'user_id': user_id,
            'tier': data['plan_id'],
            'plan_data': plan_details,
            'price': required_amount,
            'status': 'active',
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(days=plan_details['duration_days']),
            'payment_verified': True
        }

        await create_subscription(str(data['bot_id']), user_id, data['plan_id'], True)
        logger.info(f"📅 Subscription created for bot {data['bot_id']}")

        from clone_manager import clone_manager
        success, message = await clone_manager.start_clone(str(data['bot_id']))

        if success:
            logger.info(f"🎉 Clone started successfully for user {user_id}")
            await notify_mother_bot_admins(user_id, data, plan_details)

            return True, {
                'bot_id': data['bot_id'],
                'bot_username': data['bot_username'],
                'plan': plan_details['name'],
                'expires_at': subscription_data['expires_at'],
                'clone_started': True
            }
        else:
            logger.error(f"❌ Failed to start clone: {message}")
            return False, f"Clone created but failed to start: {message}"

    except Exception as e:
        logger.error(f"❌ Error in create_clone_directly for user {user_id}: {e}")
        return False, str(e)

@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client: Client, query: CallbackQuery):
    """Start the clone creation process"""
    user_id = query.from_user.id
    logger.info(f"🚀 start_clone_creation_callback triggered by user {user_id}")
    await query.answer()

    user_clones = await get_user_clones(user_id)
    active_clones = [clone for clone in user_clones if clone.get('status') == 'active']

    if active_clones:
        text = f"⚠️ **You already have an active clone!**\n\n"
        text += f"🤖 **Active Clone:** @{active_clones[0].get('username', 'Unknown')}\n"
        text += f"🆔 **Bot ID:** `{active_clones[0]['_id']}`\n"
        text += f"📊 **Status:** {active_clones[0]['status'].title()}\n\n"
        text += f"You can only have one active clone at a time."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Manage My Clone", callback_data="manage_my_clone")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])

        return await query.edit_message_text(text, reply_markup=buttons)

    current_balance = await get_user_balance(user_id)

    text = f"🤖 **Create Your Clone Bot**\n\n"
    text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"

    if current_balance < 3.00:
        text += f"❌ **Insufficient Balance**\n\n"
        text += f"You need at least $3.00 to create a clone.\n"
        text += f"Please add balance to your account first.\n\n"
        text += f"💡 **Clone Plans:**\n"
        text += f"• Monthly Plan: $3.00 (30 days)\n"
        text += f"• 3 Months Plan: $8.00 (90 days) - Best Value!\n"
        text += f"• 6 Months Plan: $15.00 (180 days)\n"
        text += f"• Yearly Plan: $26.00 (365 days)"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
            [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{getattr(Config, 'OWNER_USERNAME', 'admin')}")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])

        return await query.edit_message_text(text, reply_markup=buttons)

    text += f"✅ **You can create a clone!**\n\n"
    text += f"🎯 **Simple 3-Step Process:**\n\n"
    text += f"**Step 1:** Choose your plan\n"
    text += f"**Step 2:** Provide bot token (from @BotFather)\n"
    text += f"**Step 3:** Provide database URL\n\n"
    text += f"💡 **Available Clone Plans:**\n"
    text += f"• Monthly Plan: $3.00 (30 days) - Perfect for testing\n"
    text += f"• 3 Months Plan: $8.00 (90 days) - Most popular!\n"
    text += f"• 6 Months Plan: $15.00 (180 days) - Better value\n"
    text += f"• Yearly Plan: $26.00 (365 days) - Best savings\n\n"
    text += f"Your clone will be ready in minutes!"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Creating", callback_data="begin_step1_plan")],
        [InlineKeyboardButton("❓ Need Help?", callback_data="creation_help")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^creation_help$"))
async def creation_help_callback(client, query):
    """Show creation help"""
    await query.answer()

    text = f"❓ **Clone Creation Help**\n\n"
    text += f"**🤖 What is a Clone?**\n"
    text += f"A clone is your personal copy of this bot with all the same features!\n\n"
    text += f"**📋 What you need:**\n"
    text += f"1. **Bot Token** - Get free from @BotFather\n"
    text += f"2. **Database** - MongoDB connection URL\n"
    text += f"3. **Plan** - Choose subscription duration\n\n"
    text += f"**🔧 Getting Bot Token:**\n"
    text += f"• Go to @BotFather\n"
    text += f"• Send `/newbot`\n"
    text += f"• Choose name and username\n"
    text += f"• Copy the token provided\n\n"
    text += f"**🗄️ Getting Database:**\n"
    text += f"• Use MongoDB Atlas (free tier)\n"
    text += f"• Or contact admin for shared database\n\n"
    text += f"**💰 Payment:**\n"
    text += f"Payment is deducted from your balance automatically after successful setup."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Get Bot Token", url="https://t.me/BotFather")],
        [InlineKeyboardButton("🗄️ Get MongoDB", url="https://www.mongodb.com/atlas")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{getattr(Config, 'OWNER_USERNAME', 'admin')}")],
        [InlineKeyboardButton("🚀 Start Creating", callback_data="begin_step1_plan")],
        [InlineKeyboardButton("« Back", callback_data="start_clone_creation")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^begin_step1_plan$"))
async def begin_step1_plan_callback(client: Client, query: CallbackQuery):
    """Handle begin step 1 - plan selection"""
    await query.answer()

    user_id = query.from_user.id
    logger.info(f"💎 begin_step1_plan_callback triggered by user {user_id}")

    from bot.database.subscription_db import PRICING_TIERS
    
    session_data = {
        'step': 'plan_selection',
        'data': {},
        'started_at': datetime.now(),
        'type': 'clone_creation'
    }
    await session_manager.create_session(user_id, 'clone_creation', session_data)

    text = f"💎 **Step 1/3: Choose Your Clone Plan**\n\n"
    text += f"Select the subscription plan for your clone bot:\n\n"

    for tier_name, tier_data in PRICING_TIERS.items():
        text += f"**{tier_data['name']}** - ${tier_data['price']:.2f}\n"
        text += f"• Duration: {tier_data['duration_days']} days\n"
        text += f"• Features: {', '.join(tier_data['features'])}\n\n"

    buttons = []
    for tier_name, tier_data in PRICING_TIERS.items():
        plan_text = f"{tier_data['name']} - ${tier_data['price']:.2f}"
        buttons.append([InlineKeyboardButton(plan_text, callback_data=f"select_plan:{tier_name}")])

    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^select_plan:"))
async def select_plan_callback(client: Client, query: CallbackQuery):
    """Handle plan selection"""
    await query.answer()
    user_id = query.from_user.id
    plan_id = query.data.split(':')[1]
    
    session = await session_manager.get_session(user_id)
    if not session:
        return await query.edit_message_text(
            "❌ Session expired! Please start again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]])
        )

    from bot.database.subscription_db import PRICING_TIERS
    plan_details = PRICING_TIERS.get(plan_id)

    if not plan_details:
        return await query.answer("❌ Invalid plan selected!", show_alert=True)

    balance = await get_user_balance(user_id)
    if balance < plan_details['price']:
        return await query.edit_message_text(
            f"❌ **Insufficient Balance!**\n\n"
            f"💰 Your Balance: ${balance}\n"
            f"💸 Plan Cost: ${plan_details['price']}\n"
            f"💵 Required: ${plan_details['price'] - balance}\n\n"
            "Please add balance to continue.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
                [InlineKeyboardButton("🔙 Back to Plans", callback_data="begin_step1_plan")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    session['data']['plan_id'] = plan_id
    session['data']['plan_details'] = plan_details
    session['step'] = 'bot_username'
    await session_manager.update_session(user_id, session)

    text = f"✅ **Plan Selected: {plan_details['name']}**\n\n"
    text += f"💰 **Cost:** ${plan_details['price']}\n"
    text += f"⏰ **Duration:** {plan_details['duration_days']} days\n\n"
    text += f"🤖 **Step 2/3: Bot Username**\n\n"
    text += f"Now, please send me your bot's username (without @).\n"
    text += f"Example: `MyAwesomeBot`\n\n"
    text += f"Make sure your bot is created via @BotFather first!"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ How to create bot?", url="https://core.telegram.org/bots#6-botfather")],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data="begin_step1_plan")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
        ])
    )

@Client.on_message(filters.private & ~filters.command(["start", "help", "about", "admin"]))
async def handle_creation_input(client: Client, message: Message):
    """Handle user input during creation process"""
    user_id = message.from_user.id
    session = await session_manager.get_session(user_id)

    if not session:
        return

    if (datetime.now() - session['started_at']).seconds > 1800:
        await session_manager.delete_session(user_id)
        return await message.reply_text(
            "⏰ **Session Expired!**\n\nYour creation session has timed out.\nPlease start again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]])
        )

    step = session['step']
    user_input = message.text.strip()

    if step == 'bot_username':
        await handle_bot_username_input(client, message, user_input, session)
    elif step == 'bot_token':
        await handle_bot_token_input(client, message, user_input, session)
    elif step == 'mongodb_url':
        await handle_mongodb_input(client, message, user_input, session)

async def handle_bot_username_input(client: Client, message: Message, bot_username: str, session: dict):
    """Handle and validate bot username"""
    user_id = message.from_user.id

    if not bot_username or not bot_username.endswith('bot') or len(bot_username) < 5:
        return await message.reply_text("❌ **Invalid Bot Username!**\n\nMust end with `bot` and be at least 5 characters long.")

    user_clones = await get_user_clones(user_id)
    if any(clone['username'] == bot_username for clone in user_clones):
        return await message.reply_text(f"❌ **Username '{bot_username}' already in use!**")

    session['data']['bot_username'] = bot_username
    session['step'] = 'bot_token'
    await session_manager.update_session(user_id, session)

    text = f"✅ **Bot Username Set: @{bot_username}**\n\n"
    text += f"🤖 **Step 2/3: Bot Token**\n\n"
    text += f"Now, please send your bot's API token.\n"
    text += f"Get this from @BotFather.\n\n"
    text += f"**Format:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`"

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]]))

async def handle_bot_token_input(client: Client, message: Message, bot_token: str, session: dict):
    """Handle and validate bot token"""
    user_id = message.from_user.id

    if not bot_token or ':' not in bot_token or len(bot_token) < 20:
        return await message.reply_text("❌ **Invalid Token Format!**")

    processing_msg = await message.reply_text("🔄 **Validating Bot Token...**")

    try:
        from pyrogram import Client as TestClient

        test_client = TestClient(
            name=f"test_{bot_token[:10]}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=bot_token,
            in_memory=True
        )

        await asyncio.wait_for(test_client.start(), timeout=30.0)
        me = await test_client.get_me()

        if me.username.lower() != session['data']['bot_username'].lower():
            await test_client.stop()
            return await processing_msg.edit_text(f"❌ **Username Mismatch!**\n\nToken is for @{me.username}, but you entered @{session['data']['bot_username']}.")

        await test_client.stop()

        session['data']['bot_token'] = bot_token
        session['data']['bot_id'] = me.id
        session['step'] = 'mongodb_url'
        await session_manager.update_session(user_id, session)

        plan = session['data']['plan_details']

        text = f"✅ **Step 2 Complete!**\n\n"
        text += f"🤖 **Bot Verified:** @{me.username}\n"
        text += f"🆔 **Bot ID:** `{me.id}`\n\n"
        text += f"🗄️ **Step 3/3: Database URL**\n\n"
        text += f"Provide your MongoDB connection URL.\n\n"
        text += f"**Format:** `mongodb+srv://user:pass@cluster.mongodb.net/dbname`"

        await processing_msg.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]]))

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        await processing_msg.edit_text(f"❌ **Token Validation Failed!**\n\n{str(e)}")

async def handle_mongodb_input(client: Client, message: Message, mongodb_url: str, session: dict):
    """Handle and validate MongoDB URL"""
    user_id = message.from_user.id

    if not mongodb_url.startswith(('mongodb://', 'mongodb+srv://')):
        await session_manager.delete_session(user_id)
        return await message.reply_text("❌ **Invalid MongoDB URL!**")

    processing_msg = await message.reply_text("🔄 **Testing Database Connection...**")

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        test_client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=10000)
        test_db = test_client.test_connection_db
        await asyncio.wait_for(test_db.command("ping"), timeout=15.0)
        test_client.close()

        session['data']['mongodb_url'] = mongodb_url
        session['step'] = 'confirmation'
        await session_manager.update_session(user_id, session)

        await show_final_confirmation(client, processing_msg, user_id)

    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        await session_manager.delete_session(user_id)
        await processing_msg.edit_text(f"❌ **Database Connection Failed!**\n\n{str(e)}")

async def show_final_confirmation(client: Client, message: Message, user_id: int):
    """Show final confirmation"""
    session = await session_manager.get_session(user_id)
    data = session['data']
    plan = data['plan_details']

    current_balance = await get_user_balance(user_id)
    remaining_balance = current_balance - plan['price']

    text = f"🎉 **Ready to Create Your Clone!**\n\n"
    text += f"**📋 Final Review:**\n\n"
    text += f"🤖 **Bot:** @{data['bot_username']}\n"
    text += f"💰 **Plan:** {plan['name']}\n"
    text += f"⏱️ **Duration:** {plan['duration_days']} days\n\n"
    text += f"**💳 Payment:**\n"
    text += f"• Current: ${current_balance:.2f}\n"
    text += f"• Cost: ${plan['price']:.2f}\n"
    text += f"• After: ${remaining_balance:.2f}\n\n"
    text += f"**Ready to proceed?**"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Create My Clone!", callback_data="confirm_final_creation")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])

    await message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^confirm_final_creation$"))
async def handle_final_confirmation(client: Client, query: CallbackQuery):
    """Handle final creation confirmation"""
    user_id = query.from_user.id
    session = await session_manager.get_session(user_id)

    if not session or session['step'] != 'confirmation':
        await session_manager.delete_session(user_id)
        return await query.answer("❌ Session expired!", show_alert=True)

    try:
        data = session['data']
        plan_details = data['plan_details']

        processing_msg = await query.edit_message_text(f"🚀 **Creating Your Clone...**\n\nPlease wait...")

        success, result = await create_clone_directly(user_id, data)

        if success:
            await session_manager.delete_session(user_id)
            remaining_balance = await get_user_balance(user_id)

            text = f"🎉 **Clone Created Successfully!**\n\n"
            text += f"🤖 **Your Bot:** @{data['bot_username']}\n"
            text += f"💰 **Plan:** {plan_details['name']}\n"
            text += f"💵 **Paid:** ${plan_details['price']:.2f}\n"
            text += f"💰 **Balance:** ${remaining_balance:.2f}\n\n"
            text += f"✅ Your bot is running and ready!"

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Open My Bot", url=f"https://t.me/{data['bot_username']}")],
                [InlineKeyboardButton("📋 Manage Clone", callback_data="manage_my_clone")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])

            await processing_msg.edit_text(text, reply_markup=buttons)
        else:
            await session_manager.delete_session(user_id)
            text = f"❌ **Clone Creation Failed!**\n\n{result}"
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_clone_creation")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])
            await processing_msg.edit_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in final confirmation: {e}")
        await session_manager.delete_session(user_id)
        await query.edit_message_text("❌ **Unexpected Error!**\n\nPlease try again.")

@Client.on_callback_query(filters.regex("^cancel_creation$"))
async def handle_creation_cancellation(client: Client, query: CallbackQuery):
    """Handle creation cancellation"""
    user_id = query.from_user.id
    await session_manager.delete_session(user_id)

    text = f"❌ **Clone Creation Cancelled**\n\nNo charges were made to your account."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")],
        [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)
