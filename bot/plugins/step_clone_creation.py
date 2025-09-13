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

# Mocking get_context_logger for now as it's not provided in the original code snippet
# In a real scenario, this would be imported from bot.logging
def get_context_logger(name):
    return LOGGER(name)

logger = get_context_logger(__name__)

# Initialize session manager
session_manager = SessionManager()

# Global session storage for clone creation
creation_sessions = {}

def get_creation_sessions():
    """Get the global creation sessions dictionary"""
    global creation_sessions
    return creation_sessions

def clear_creation_session(user_id):
    """Clear a specific user's creation session"""
    global creation_sessions
    if user_id in creation_sessions:
        del creation_sessions[user_id]
        logger.info(f"🧹 Cleared creation session for user {user_id}")


async def notify_mother_bot_admins(user_id: int, clone_data: dict, plan_details: dict):
    """Notify mother bot admins about a new clone creation."""
    try:
        if not Config.OWNER_ID: # Assuming OWNER_ID is a list or single ID of mother bot admins
            logger.warning("No OWNER_ID configured, cannot notify admins about new clone.")
            return

        # Assuming 'client' is accessible or passed as an argument.
        # For this example, we'll assume it's a global client instance or passed in.
        # If not, this part would need adjustment.
        # For now, let's simulate 'client' access.
        # Replace this with actual client access if available.
        async def get_mock_user(user_id):
            class MockUser:
                def __init__(self, id, username=None, first_name='TestUser'):
                    self.id = id
                    self.username = username
                    self.first_name = first_name
            return MockUser(user_id, username='mock_user')

        user_info = await get_mock_user(user_id) # Replace with actual client.get_users(user_id)
        user_name = f"@{user_info.username}" if user_info.username else f"{user_info.first_name} {user_id}"

        message_text = (
            f"📣 **New Clone Bot Created!**\n\n"
            f"👤 **User:** {user_name} (ID: `{user_id}`)\n"
            f"🤖 **Clone Bot:** @{clone_data['bot_username']} (ID: `{clone_data['bot_id']}`)\n"
            f"💰 **Plan:** {plan_details['name']} (${plan_details['price']})\n"
            f"📅 **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🔗 **Bot Link:** https://t.me/{clone_data['bot_username']}"
        )

        # Ensure Config.OWNER_ID is iterable
        admin_ids = [Config.OWNER_ID] if isinstance(Config.OWNER_ID, int) else Config.OWNER_ID

        # Mocking client.send_message for demonstration if client is not globally available
        async def mock_send_message(chat_id, text):
            print(f"--- Sending to {chat_id} ---")
            print(text)
            print("-------------------------")
            return True

        for admin_id in admin_ids:
            try:
                # Replace with actual client.send_message(admin_id, message_text)
                await mock_send_message(admin_id, message_text)
                logger.info(f"Notified admin {admin_id} about new clone creation by user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")

    except Exception as e:
        logger.error(f"Error in notify_mother_bot_admins for user {user_id}: {e}")

async def create_clone_directly(user_id: int, data: dict):
    """Create clone directly without the removed clone_request module"""
    try:
        plan_details = data['plan_details']
        required_amount = plan_details['price']

        print(f"💰 DEBUG CLONE: Processing payment of ${required_amount} for user {user_id}")

        # Check and deduct balance
        current_balance = await get_user_balance(user_id)
        if current_balance < required_amount:
            return False, f"Insufficient balance. Required: ${required_amount}, Available: ${current_balance}"

        # Deduct balance
        await deduct_balance(user_id, required_amount, f"Clone creation - {plan_details['name']}")
        print(f"💰 DEBUG CLONE: Balance deducted successfully for user {user_id}")

        # Create clone record
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
        print(f"🤖 DEBUG CLONE: Clone record created for bot {data['bot_id']}")

        # Create subscription
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
        print(f"📅 DEBUG CLONE: Subscription created for bot {data['bot_id']}")

        # Start the clone
        from clone_manager import clone_manager
        success, message = await clone_manager.start_clone(str(data['bot_id']))

        if success:
            print(f"🎉 DEBUG CLONE: Clone started successfully for user {user_id}")

            # Send notification to mother bot admins
            await notify_mother_bot_admins(user_id, data, plan_details)

            return True, {
                'bot_id': data['bot_id'],
                'bot_username': data['bot_username'],
                'plan': plan_details['name'],
                'expires_at': subscription_data['expires_at'],
                'clone_started': True
            }
        else:
            print(f"❌ DEBUG CLONE: Failed to start clone: {message}")
            return False, f"Clone created but failed to start: {message}"

    except Exception as e:
        logger.error(f"❌ Error in create_clone_directly for user {user_id}: {e}")
        return False, str(e)

@Client.on_callback_query(filters.regex("^start_clone_creation$"), group=1)
async def start_clone_creation_callback(client: Client, query: CallbackQuery):
    """Start the clone creation process"""
    user_id = query.from_user.id
    print(f"🚀 DEBUG CLONE: start_clone_creation_callback triggered by user {user_id}")
    print(f"📋 DEBUG CLONE: Query data: '{query.data}'")
    await query.answer()

    # Check if user already has an active clone
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

    # Check user balance first
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
            [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])

        return await query.edit_message_text(text, reply_markup=buttons)

    # Show simplified creation process
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
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("🚀 Start Creating", callback_data="begin_step1_plan")],
        [InlineKeyboardButton("« Back", callback_data="start_clone_creation")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^begin_step1_plan$"), group=1)
async def begin_step1_plan_callback(client: Client, query: CallbackQuery):
    """Handle begin step 1 - plan selection"""
    await query.answer()

    user_id = query.from_user.id
    print(f"💎 DEBUG CLONE: begin_step1_plan_callback triggered by user {user_id}")

    # Get clone pricing tiers (excluding token verification plans)
    from bot.database.subscription_db import get_pricing_tiers, PRICING_TIERS
    pricing_tiers = await get_pricing_tiers()

    # Use PRICING_TIERS if get_pricing_tiers returns empty list or None
    if not pricing_tiers:
        pricing_tiers = PRICING_TIERS
        print(f"💎 DEBUG CLONE: Using default pricing tiers: {list(pricing_tiers.keys())}")
    else:
        print(f"💎 DEBUG CLONE: Got pricing tiers from DB: {pricing_tiers}")
        # If it's a list, convert to dict format
        if isinstance(pricing_tiers, list):
            pricing_tiers = PRICING_TIERS
            print(f"💎 DEBUG CLONE: Converting list to default pricing tiers")

    for tier_name, tier_data in pricing_tiers.items():
        print(f"💎 DEBUG CLONE: Plan {tier_name}: {tier_data['name']} - ${tier_data['price']}")

    # Create or get session
    session = await session_manager.get_session(user_id)
    if not session:
        # Create new session
        session_data = {
            'step': 'plan_selection',
            'data': {},
            'started_at': datetime.now(),
            'type': 'clone_creation' # Mark session type
        }
        await session_manager.create_session(user_id, 'clone_creation', session_data)
        session = await session_manager.get_session(user_id)

    # Get clone pricing tiers (excluding token verification plans)
    from bot.database.subscription_db import get_pricing_tiers, PRICING_TIERS
    pricing_tiers = await get_pricing_tiers()

    # Use PRICING_TIERS if get_pricing_tiers returns empty list or None
    if not pricing_tiers or isinstance(pricing_tiers, list):
        pricing_tiers = PRICING_TIERS

    text = f"💎 **Step 1/3: Choose Your Clone Plan**\n\n"
    text += f"Select the subscription plan for your clone bot:\n\n"

    # Display available plans with better formatting
    for tier_name, tier_data in pricing_tiers.items():
        text += f"**{tier_data['name']}** - ${tier_data['price']:.2f}\n"
        text += f"• Duration: {tier_data['duration_days']} days\n"
        text += f"• Features: {', '.join(tier_data['features'])}\n\n"

    buttons = []
    for tier_name, tier_data in pricing_tiers.items():
        plan_text = f"{tier_data['name']} - ${tier_data['price']:.2f}"
        buttons.append([InlineKeyboardButton(plan_text, callback_data=f"select_plan:{tier_name}")])

    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^select_plan:"), group=1)
async def select_plan_callback(client: Client, query: CallbackQuery):
    """Handle plan selection in clone creation"""
    await query.answer()
    user_id = query.from_user.id
    plan_id = query.data.split(':')[1] if ':' in query.data else 'unknown'
    print(f"💰 DEBUG CLONE: select_plan_callback triggered by user {user_id}")
    print(f"📋 DEBUG CLONE: Plan selection: '{plan_id}'")

    session = await session_manager.get_session(user_id)

    if not session:
        return await query.edit_message_text(
            "❌ Session expired! Please start again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]
            ])
        )

    # Get plan details - ensure we're only using clone plans
    from bot.database.subscription_db import get_pricing_tiers, PRICING_TIERS
    pricing_tiers = await get_pricing_tiers()

    # Use PRICING_TIERS if get_pricing_tiers returns empty list or None
    if not pricing_tiers or isinstance(pricing_tiers, list):
        pricing_tiers = PRICING_TIERS

    plan_details = pricing_tiers.get(plan_id)

    if not plan_details:
        print(f"❌ DEBUG CLONE: Invalid plan selected: '{plan_id}'. Available plans: {list(pricing_tiers.keys())}")
        return await query.answer("❌ Invalid plan selected!", show_alert=True)

    # Validate that it's a valid clone plan (not a token plan)
    valid_clone_plans = ["monthly", "quarterly", "semi_annual", "yearly"]
    if plan_id not in valid_clone_plans:
        print(f"❌ DEBUG CLONE: Plan '{plan_id}' is not a valid clone plan")
        return await query.answer("❌ Invalid clone plan selected!", show_alert=True)

    # Check if user has sufficient balance
    from bot.database.balance_db import get_user_balance
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

    # Update session with selected plan
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

@Client.on_callback_query(filters.regex("^token_help$"))
async def token_help_callback(client, query):
    """Show token help"""
    await query.answer()

    user_id = query.from_user.id
    session = await session_manager.get_session(user_id)
    plan_id = session.get('data', {}).get('plan_id', 'monthly')

    text = f"🤖 **How to Get Bot Token**\n\n"
    text += f"**Step-by-step guide:**\n\n"
    text += f"1. **Open @BotFather**\n"
    text += f"   Click the link below or search for @BotFather\n\n"
    text += f"2. **Create Bot**\n"
    text += f"   Send: `/newbot`\n\n"
    text += f"3. **Choose Name**\n"
    text += f"   Example: `My File Sharing Bot`\n\n"
    text += f"4. **Choose Username**\n"
    text += f"   Must end with 'bot'\n"
    text += f"   Example: `myfilesharebot` or `my_file_bot`\n\n"
    text += f"5. **Copy Token**\n"
    text += f"   BotFather will give you a token like:\n"
    text += f"   `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
    text += f"6. **Send Token**\n"
    text += f"   Paste the token in this chat\n\n"
    text += f"⚠️ **Important:**\n"
    text += f"• Never share your token publicly\n"
    text += f"• Token gives full control of your bot\n"
    text += f"• If compromised, regenerate in @BotFather\n\n"
    text += f"💡 **Tip:** After getting your token, come back here and send it!"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Open BotFather", url="https://t.me/BotFather")],
        [InlineKeyboardButton("« Back to Step 2", callback_data=f"select_plan:{plan_id}")]
    ])

    try:
        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            await query.answer("ℹ️ Help information is already displayed above.", show_alert=False)
        else:
            await query.answer("❌ Error loading help. Please try again.", show_alert=True)

@Client.on_message(filters.private & ~filters.command(["start", "help", "about", "admin"]))
async def handle_creation_input(client: Client, message: Message):
    """Handle user input during creation process"""
    user_id = message.from_user.id
    session = await session_manager.get_session(user_id)

    if not session:
        return

    # Check session timeout (30 minutes)
    if (datetime.now() - session['started_at']).seconds > 1800:
        await session_manager.delete_session(user_id)
        return await message.reply_text(
            "⏰ **Session Expired!**\n\n"
            "Your creation session has timed out.\n"
            "Please start again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]
            ])
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
    print(f"👤 DEBUG CLONE: handle_bot_username_input for user {user_id}")
    print(f"💬 DEBUG CLONE: Received bot username: '{bot_username}'")

    # Validate username format
    if not bot_username or not bot_username.endswith('bot') or len(bot_username) < 5:
        return await message.reply_text(
            "❌ **Invalid Bot Username!**\n\n"
            "Please provide a valid bot username from @BotFather.\n\n"
            "**Rules:**\n"
            "- Must end with `bot` (e.g., `MyAwesomeBot`)\n"
            "- Must be at least 5 characters long\n\n"
            "Try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ How to create bot?", url="https://core.telegram.org/bots#6-botfather")],
                [InlineKeyboardButton("🔙 Back to Plans", callback_data="begin_step1_plan")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    # Check if username is already in use by the user
    user_clones = await get_user_clones(user_id)
    if any(clone['username'] == bot_username for clone in user_clones):
        return await message.reply_text(
            f"❌ **Username '{bot_username}' already in use!**\n\n"
            "You already have a clone with this username.\n"
            "Please choose a different username.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ How to create bot?", url="https://core.telegram.org/bots#6-botfather")],
                [InlineKeyboardButton("🔙 Back to Plans", callback_data="begin_step1_plan")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    # Store bot username and proceed to token step
    session['data']['bot_username'] = bot_username
    session['step'] = 'bot_token'
    await session_manager.update_session(user_id, session)

    text = f"✅ **Bot Username Set: @{bot_username}**\n\n"
    text += f"🤖 **Step 2/3: Bot Token**\n\n"
    text += f"Now, please send your bot's API token.\n"
    text += f"You can get this from @BotFather.\n\n"
    text += f"**Format:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
    text += f"⚠️ **Keep your token secure!**"

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Open BotFather", url="https://t.me/BotFather")],
            [InlineKeyboardButton("❓ Get Token Help", callback_data="token_help")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
        ])
    )

async def handle_bot_token_input(client: Client, message: Message, bot_token: str, session: dict):
    """Handle and validate bot token"""
    user_id = message.from_user.id
    print(f"🔑 DEBUG CLONE: handle_bot_token_input for user {user_id}")
    print(f"💬 DEBUG CLONE: Received bot token (masked): '{bot_token[:8]}...'")

    # Validate token format
    if not bot_token or ':' not in bot_token or len(bot_token) < 20:
        return await message.reply_text(
            "❌ **Invalid Token Format!**\n\n"
            "Please provide a valid bot token from @BotFather.\n\n"
            "**Correct format:** `bot_id:token_string`\n"
            "**Example:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
            "Try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Get Help", callback_data="token_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    # Test the bot token
    processing_msg = await message.reply_text(
        "🔄 **Validating Bot Token...**\n\n"
        "Please wait while we verify your token..."
    )

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

        # Ensure the username matches the one provided by the user
        if me.username.lower() != session['data']['bot_username'].lower():
            await test_client.stop()
            return await processing_msg.edit_text(
                f"❌ **Username Mismatch!**\n\n"
                f"The token you provided is for bot @{me.username}, "
                f"but you entered @{session['data']['bot_username']}.\n\n"
                "Please ensure the token matches the username or restart.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Plans", callback_data="begin_step1_plan")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
                ])
            )

        await test_client.stop()

        # Store validated data
        session['data']['bot_token'] = bot_token
        session['data']['bot_id'] = me.id
        session['step'] = 'mongodb_url'
        await session_manager.update_session(user_id, session)

        plan = session['data']['plan_details']

        text = f"✅ **Step 2 Complete!**\n\n"
        text += f"🤖 **Bot Verified:** @{me.username}\n"
        text += f"🆔 **Bot ID:** `{me.id}`\n"
        text += f"💰 **Plan:** {plan['name']} (${plan['price']})\n\n"
        text += f"🗄️ **Step 3/3: Database URL**\n\n"
        text += f"Now provide your MongoDB connection URL.\n\n"
        text += f"**📋 Quick Options:**\n\n"
        text += f"**Option 1: Free MongoDB Atlas**\n"
        text += f"• Sign up at mongodb.com/atlas\n"
        text += f"• Create free cluster\n"
        text += f"• Get connection string\n\n"
        text += f"**Option 2: Contact Admin**\n"
        text += f"• Get shared database access\n"
        text += f"• Ready-to-use connection\n\n"
        text += f"**📝 URL Format:**\n"
        text += f"`mongodb+srv://user:pass@cluster.mongodb.net/dbname`\n\n"
        text += f"Please send your MongoDB URL now:"

        await processing_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Get MongoDB Atlas", url="https://www.mongodb.com/atlas")],
                [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
                [InlineKeyboardButton("❓ Database Help", callback_data="database_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    except asyncio.TimeoutError:
        await processing_msg.edit_text(
            "❌ **Token Validation Timeout!**\n\n"
            "The bot token verification took too long.\n"
            "Please check your token and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Get Help", callback_data="token_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )
    except Exception as e:
        logger.error(f"Token validation error for user {user_id}: {e}")
        await processing_msg.edit_text(
            f"❌ **Token Validation Failed!**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"**Common issues:**\n"
            f"• Invalid token format\n"
            f"• Token already in use\n"
            f"• Bot deleted from @BotFather\n\n"
            f"Please check your token and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Get Help", callback_data="token_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

@Client.on_callback_query(filters.regex("^database_help$"))
async def database_help_callback(client, query):
    """Show database help"""
    await query.answer()

    text = f"🗄️ **Database Setup Guide**\n\n"
    text += f"**🌟 Recommended: MongoDB Atlas (Free)**\n\n"
    text += f"**Step 1:** Visit mongodb.com/atlas\n"
    text += f"**Step 2:** Create free account\n"
    text += f"**Step 3:** Build a database\n"
    text += f"   • Choose FREE shared cluster\n"
    text += f"   • Select any cloud provider\n"
    text += f"   • Name your cluster\n\n"
    text += f"**Step 4:** Create database user\n"
    text += f"   • Username: yourname\n"
    text += f"   • Password: strong_password\n\n"
    text += f"**Step 5:** Network access\n"
    text += f"   • Add IP: 0.0.0.0/0 (allow all)\n\n"
    text += f"**Step 6:** Get connection string\n"
    text += f"   • Click 'Connect'\n"
    text += f"   • Choose 'Connect your application'\n"
    text += f"   • Copy the connection string\n"
    text += f"   • Replace <password> with your password\n\n"
    text += f"**📝 Final URL looks like:**\n"
    text += f"`mongodb+srv://user:pass@cluster0.xyz.mongodb.net/mybot`\n\n"
    text += f"**🔒 Alternative:** Contact admin for shared database"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 MongoDB Atlas", url="https://www.mongodb.com/atlas")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("« Back to Step 3", callback_data="back_to_step3")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

# Helper to go back to Step 3
@Client.on_callback_query(filters.regex("^back_to_step3$"))
async def back_to_step3_callback(client: Client, query: CallbackQuery):
    """Go back to database URL input step"""
    await query.answer()
    user_id = query.from_user.id
    session = await session_manager.get_session(user_id)

    if not session or session['step'] != 'mongodb_url':
        await session_manager.delete_session(user_id)
        return await query.edit_message_text(
            "❌ Session expired or not at the correct step. Please start over.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")]
            ])
        )

    # Re-display the database URL input prompt
    text = f"🗄️ **Step 3/3: Database URL**\n\n"
    text += f"Please provide your MongoDB connection URL.\n\n"
    text += f"**Quick Options:**\n\n"
    text += f"**Option 1: Free MongoDB Atlas**\n"
    text += f"• Sign up at mongodb.com/atlas\n"
    text += f"• Create free cluster\n"
    text += f"• Get connection string\n\n"
    text += f"**Option 2: Contact Admin**\n"
    text += f"• Get shared database access\n"
    text += f"• Ready-to-use connection\n\n"
    text += f"**📝 URL Format:**\n"
    text += f"`mongodb+srv://user:pass@cluster.mongodb.net/dbname`\n\n"
    text += f"Please send your MongoDB URL now:"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Get MongoDB Atlas", url="https://www.mongodb.com/atlas")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
        [InlineKeyboardButton("❓ Database Help", callback_data="database_help")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])

    await query.edit_text(
        text,
        reply_markup=buttons
    )


async def handle_mongodb_input(client: Client, message: Message, mongodb_url: str, session: dict):
    """Handle and validate MongoDB URL"""
    user_id = message.from_user.id
    print(f"🗄️ DEBUG CLONE: handle_mongodb_input for user {user_id}")
    print(f"💬 DEBUG CLONE: Received MongoDB URL: '{mongodb_url}'")

    # Validate URL format
    if not mongodb_url.startswith(('mongodb://', 'mongodb+srv://')):
        await session_manager.delete_session(user_id)
        return await message.reply_text(
            "❌ **Invalid MongoDB URL!**\n\n"
            "**URL must start with:**\n"
            "• `mongodb://` or\n"
            "• `mongodb+srv://`\n\n"
            "**Example:**\n"
            "`mongodb+srv://user:pass@cluster.mongodb.net/dbname`\n\n"
            "Try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Get Help", callback_data="database_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

    # Test MongoDB connection
    processing_msg = await message.reply_text(
        "🔄 **Testing Database Connection...**\n\n"
        "Please wait while we verify your database..."
    )

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        test_client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=10000)
        test_db = test_client.test_connection_db

        await asyncio.wait_for(test_db.command("ping"), timeout=15.0)
        test_client.close()

        # Store validated data
        session['data']['mongodb_url'] = mongodb_url
        session['step'] = 'confirmation'
        await session_manager.update_session(user_id, session)

        # Show final confirmation
        await show_final_confirmation(client, processing_msg, user_id)

    except Exception as e:
        logger.error(f"MongoDB connection error for user {user_id}: {e}")
        await session_manager.delete_session(user_id)
        await processing_msg.edit_text(
            f"❌ **Database Connection Failed!**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"**Common issues:**\n"
            f"• Wrong credentials\n"
            f"• Network restrictions\n"
            f"• Invalid URL format\n\n"
            f"Please check your URL and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Get Help", callback_data="database_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

async def show_final_confirmation(client: Client, message: Message, user_id: int):
    """Show final confirmation before creating clone"""
    session = await session_manager.get_session(user_id)
    data = session['data']
    plan = data['plan_details']

    current_balance = await get_user_balance(user_id)
    remaining_balance = current_balance - plan['price']

    # Mask sensitive data for display
    masked_token = f"{data['bot_token'][:8]}...{data['bot_token'][-4:]}"
    masked_db = f"{data['mongodb_url'][:25]}...{data['mongodb_url'][-10:]}"

    text = f"🎉 **Ready to Create Your Clone!**\n\n"
    text += f"**📋 Final Review:**\n\n"
    text += f"🤖 **Bot:** @{data['bot_username']}\n"
    text += f"🆔 **Bot ID:** `{data['bot_id']}`\n"
    text += f"🔑 **Token:** `{masked_token}`\n"
    text += f"🗄️ **Database:** `{masked_db}`\n"
    text += f"💰 **Plan:** {plan['name']}\n"
    text += f"⏱️ **Duration:** {plan['duration_days']} days\n\n"
    text += f"**💳 Payment Summary:**\n"
    text += f"• Current Balance: ${current_balance:.2f}\n"
    text += f"• Plan Cost: ${plan['price']:.2f}\n"
    text += f"• Remaining Balance: ${remaining_balance:.2f}\n\n"
    text += f"**✅ What happens next:**\n"
    text += f"• Payment deducted automatically\n"
    text += f"• Clone created instantly\n"
    text += f"• Bot starts immediately\n"
    text += f"• Ready to use in minutes!\n\n"
    text += f"**Ready to proceed?**"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Create My Clone!", callback_data="confirm_final_creation")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])

    await message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^confirm_final_creation$"))
async def handle_final_confirmation(client: Client, query: CallbackQuery):
    """Handle final creation confirmation and create the clone"""
    user_id = query.from_user.id
    session = await session_manager.get_session(user_id)

    if not session or session['step'] != 'confirmation':
        await session_manager.delete_session(user_id)
        return await query.answer("❌ Session expired!", show_alert=True)

    print(f"🎉 DEBUG CLONE: confirm_final_creation triggered by user {user_id}")

    try:
        data = session['data']
        plan_details = data['plan_details']
        required_amount = plan_details['price']

        # Show processing message
        processing_msg = await query.edit_message_text(
            f"🚀 **Creating Your Clone...**\n\n"
            f"⚙️ **Step 1:** Deducting ${required_amount:.2f} from balance...\n"
            f"⚙️ **Step 2:** Setting up @{data['bot_username']}...\n"
            f"⚙️ **Step 3:** Configuring database...\n"
            f"⚙️ **Step 4:** Starting bot services...\n\n"
            f"🕐 **Please wait, this usually takes 1-2 minutes...**"
        )

        # Process clone creation directly (since clone_request module was removed)
        success, result = await create_clone_directly(user_id, data)

        if success:
            # Clean up session
            await session_manager.delete_session(user_id)

            remaining_balance = await get_user_balance(user_id)

            text = f"🎉 **Clone Created Successfully!**\n\n"
            text += f"🤖 **Your Bot:** @{data['bot_username']}\n"
            text += f"🆔 **Bot ID:** `{data['bot_id']}`\n"
            text += f"💰 **Plan:** {plan_details['name']} ({plan_details['duration_days']} days)\n"
            text += f"💵 **Amount Paid:** ${required_amount:.2f}\n"
            text += f"💰 **Remaining Balance:** ${remaining_balance:.2f}\n\n"

            if isinstance(result, dict) and result.get('clone_started'):
                text += f"✅ **Status:** Your bot is running and ready!\n\n"
                text += f"🔗 **Bot Link:** https://t.me/{data['bot_username']}\n\n"
                text += f"🎯 **What's next?**\n"
                text += f"• Click 'Open Bot' to start using it\n"
                text += f"• Your clone has all the features of this bot\n"
                text += f"• Manage settings anytime\n"
                text += f"• Monitor usage and statistics"
            else:
                text += f"🔄 **Status:** Starting up (may take a few more minutes)\n\n"
                text += f"Your clone is being deployed and will be ready shortly!"

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Open My Bot", url=f"https://t.me/{data['bot_username']}")],
                [InlineKeyboardButton("📋 Manage Clone", callback_data="manage_my_clone")],
                [InlineKeyboardButton("🎯 Create Another", callback_data="start_clone_creation")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])

            await processing_msg.edit_text(text, reply_markup=buttons)
        else:
            # Clean up session
            await session_manager.delete_session(user_id)

            text = f"❌ **Clone Creation Failed!**\n\n"
            text += f"**Error:** {result}\n\n"
            text += f"**Don't worry:**\n"
            text += f"• Your balance has NOT been deducted\n"
            text += f"• You can try again immediately\n"
            text += f"• Contact admin if problem persists\n\n"
            text += f"**Common solutions:**\n"
            text += f"• Check your bot token is correct\n"
            text += f"• Verify database URL works\n"
            text += f"• Ensure bot is not already in use"

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_clone_creation")],
                [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])

            await processing_msg.edit_text(text, reply_markup=buttons)

    except Exception as e:
        logger.error(f"Error in final confirmation for user {user_id}: {e}")

        await session_manager.delete_session(user_id)

        await query.edit_message_text(
            "❌ **Unexpected Error!**\n\n"
            "Something went wrong during clone creation.\n"
            "Your balance has not been affected.\n\n"
            "Please try again or contact support.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_clone_creation")],
                [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])
        )

@Client.on_callback_query(filters.regex("^cancel_creation$"))
async def handle_creation_cancellation(client: Client, query: CallbackQuery):
    """Handle creation cancellation"""
    user_id = query.from_user.id

    session = await session_manager.get_session(user_id)
    step = session.get('step', 'unknown') if session else 'unknown'
    await session_manager.delete_session(user_id)

    print(f"❌ DEBUG CLONE: cancel_creation triggered by user {user_id}, session was at step: {step}")

    text = f"❌ **Clone Creation Cancelled**\n\n"
    text += f"No charges were made to your account.\n"
    text += f"You can start creating a clone anytime!\n\n"
    text += f"💡 **Remember:** You need:\n"
    text += f"• Bot token from @BotFather\n"
    text += f"• MongoDB database URL\n"
    text += f"• Sufficient balance for your plan\n\n"
    text += f"🔄 **Session was at step:** {step}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Again", callback_data="start_clone_creation")],
        [InlineKeyboardButton("❓ Get Help", callback_data="creation_help")],
        [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
    ])

    try:
        await query.edit_message_text(text, reply_markup=buttons)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            await query.answer("✅ Creation already cancelled. You can start again anytime.", show_alert=False)
        else:
            await query.answer("❌ Error cancelling. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^insufficient_balance$"))
async def handle_insufficient_balance(client, query):
    """Handle insufficient balance selection"""
    await query.answer("❌ Insufficient balance for this plan. Please add balance first.", show_alert=True)

# Helper for back to start
@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Go back to start menu from clone creation"""
    user_id = query.from_user.id
    print(f"⬅️ DEBUG CLONE: back_to_start_callback triggered by user {user_id}")

    await query.answer()

    # Clear any active creation session
    await session_manager.delete_session(user_id) # Use session manager to clear

    # Redirecting to a hypothetical main start handler.
    # In a real application, you'd import and call the appropriate handler.
    print(f"Redirecting user {user_id} to main start handler.")
    # Example of how you might call it if imported:
    # from bot.plugins.start_handler import start_handler as main_start_handler
    # await main_start_handler(client, query.message) # Assuming start_handler takes message

# Session cleanup task
async def cleanup_creation_sessions():
    """Clean up expired clone creation sessions"""
    try:
        # Use session_manager to get all sessions of type 'clone_creation'
        all_clone_sessions = await session_manager.get_sessions_by_type('clone_creation')
        current_time = datetime.now()

        for user_id, session in all_clone_sessions.items():
            session_time = session.get('started_at', current_time)
            if (current_time - session_time).total_seconds() > 1800:  # 30 minutes
                await session_manager.delete_session(user_id)
                logger.info(f"🧹 Cleaned up expired clone creation session for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error in session cleanup: {e}")

# Schedule cleanup every 10 minutes
async def session_cleanup_task():
    """Background task to clean up sessions"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        await cleanup_creation_sessions()

# Start cleanup task
asyncio.create_task(session_cleanup_task())

async def start_clone_creation(client: Client, message: Message):
    """Start the clone creation process - wrapper function for external calls"""
    user_id = message.from_user.id
    print(f"🚀 DEBUG CLONE: start_clone_creation function called for user {user_id}")

    # Create a fake callback query to reuse existing callback handler
    from pyrogram.types import CallbackQuery

    # Create minimal callback query structure
    class FakeCallbackQuery:
        def __init__(self, user, message):
            self.from_user = user
            self.message = message
            self.data = "start_clone_creation"

        async def answer(self):
            pass

        async def edit_message_text(self, text, reply_markup=None):
            return await self.message.edit_text(text, reply_markup=reply_markup)

    fake_query = FakeCallbackQuery(message.from_user, message)
    await start_clone_creation_callback(client, fake_query)