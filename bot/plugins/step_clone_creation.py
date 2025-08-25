
import asyncio
import uuid
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.database.balance_db import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store user creation sessions
creation_sessions = {}

@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client, query):
    """Handle create clone button with step-by-step process"""
    await query.answer()
    
    user_id = query.from_user.id
    
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
    
    # Check user balance
    current_balance = await get_user_balance(user_id)
    
    text = f"🤖 **Create Your Clone Bot**\n\n"
    text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"
    
    if current_balance < 3.00:
        text += f"❌ **Insufficient Balance**\n\n"
        text += f"You need at least $3.00 to create a clone.\n"
        text += f"Please add balance to your account first.\n\n"
        text += f"💡 **Clone Plans:**\n"
        text += f"• Monthly: $3.00\n"
        text += f"• Quarterly: $8.00\n"
        text += f"• Semi-Annual: $15.00\n"
        text += f"• Yearly: $26.00"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
            [InlineKeyboardButton("« Back", callback_data="back_to_start")]
        ])
        
        return await query.edit_message_text(text, reply_markup=buttons)
    
    # Start the creation process
    text += f"✅ **You can create a clone!**\n\n"
    text += f"🎯 **What you'll need:**\n"
    text += f"1. Bot token from @BotFather\n"
    text += f"2. MongoDB database URL\n"
    text += f"3. Choose subscription plan\n\n"
    text += f"📝 **Process:**\n"
    text += f"• Step 1: Provide bot token\n"
    text += f"• Step 2: Provide database URL\n"
    text += f"• Step 3: Select plan\n"
    text += f"• Step 4: Confirm & create\n\n"
    text += f"Ready to begin?"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Creation", callback_data="begin_creation")],
        [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
        [InlineKeyboardButton("« Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^begin_creation$"))
async def begin_creation_callback(client, query):
    """Begin the step-by-step creation process"""
    await query.answer()
    
    user_id = query.from_user.id
    
    # Initialize session
    creation_sessions[user_id] = {
        'step': 'bot_token',
        'data': {},
        'started_at': datetime.now()
    }
    
    text = f"🤖 **Step 1/4: Bot Token**\n\n"
    text += f"Please provide your bot token from @BotFather.\n\n"
    text += f"📋 **How to get a bot token:**\n"
    text += f"1. Go to @BotFather on Telegram\n"
    text += f"2. Send `/newbot` command\n"
    text += f"3. Follow the instructions\n"
    text += f"4. Copy the bot token\n\n"
    text += f"📝 **Format:** `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`\n\n"
    text += f"⚠️ **Important:** Keep your token secure!\n\n"
    text += f"Please send your bot token now:"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_message(filters.private & ~filters.command(["start", "help", "about", "admin"]))
async def handle_creation_input(client: Client, message: Message):
    """Handle user input during creation process"""
    user_id = message.from_user.id
    session = creation_sessions.get(user_id)
    
    if not session:
        return
    
    # Check session timeout (30 minutes)
    if (datetime.now() - session['started_at']).seconds > 1800:
        del creation_sessions[user_id]
        return await message.reply_text(
            "⏰ **Session Expired!**\n\n"
            "Your creation session has timed out.\n"
            "Please start again with the create clone button.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")]
            ])
        )
    
    step = session['step']
    user_input = message.text.strip()
    
    if step == 'bot_token':
        await handle_bot_token_input(client, message, user_input, session)
    elif step == 'mongodb_url':
        await handle_mongodb_input(client, message, user_input, session)

async def handle_bot_token_input(client: Client, message: Message, bot_token: str, session: dict):
    """Handle bot token validation"""
    user_id = message.from_user.id
    
    # Validate token format
    if not bot_token or ':' not in bot_token or len(bot_token) < 20:
        return await message.reply_text(
            "❌ **Invalid Token Format!**\n\n"
            "Please provide a valid bot token from @BotFather.\n"
            "Format: `bot_id:token_string`\n\n"
            "Try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )
    
    # Test the bot token
    processing_msg = await message.reply_text("🔄 **Validating bot token...** Please wait.")
    
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
        await test_client.stop()
        
        # Store validated data
        session['data']['bot_token'] = bot_token
        session['data']['bot_username'] = me.username or f"bot_{me.id}"
        session['data']['bot_id'] = me.id
        session['step'] = 'mongodb_url'
        
        text = f"✅ **Step 1 Complete!**\n\n"
        text += f"🤖 **Bot:** @{me.username or f'bot_{me.id}'}\n"
        text += f"🆔 **Bot ID:** `{me.id}`\n\n"
        text += f"📝 **Step 2/4: Database URL**\n\n"
        text += f"Please provide your MongoDB connection URL.\n\n"
        text += f"📋 **Examples:**\n"
        text += f"• `mongodb://username:password@host:port/database`\n"
        text += f"• `mongodb+srv://username:password@cluster.mongodb.net/database`\n\n"
        text += f"⚠️ **Note:** This will be your clone's private database.\n\n"
        text += f"Please send your MongoDB URL now:"
        
        await processing_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )
        
    except asyncio.TimeoutError:
        await processing_msg.edit_text(
            "❌ **Token Validation Timeout!**\n\n"
            "Please check your token and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ **Token Validation Failed!**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please check your token and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

async def handle_mongodb_input(client: Client, message: Message, mongodb_url: str, session: dict):
    """Handle MongoDB URL validation"""
    user_id = message.from_user.id
    
    # Validate URL format
    if not mongodb_url.startswith(('mongodb://', 'mongodb+srv://')):
        return await message.reply_text(
            "❌ **Invalid MongoDB URL!**\n\n"
            "URL must start with `mongodb://` or `mongodb+srv://`\n\n"
            "Try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )
    
    # Test MongoDB connection
    processing_msg = await message.reply_text("🔄 **Testing database connection...** Please wait.")
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        test_client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=10000)
        test_db = test_client.test_connection_db
        
        await asyncio.wait_for(test_db.command("ping"), timeout=15.0)
        test_client.close()
        
        # Store validated data
        session['data']['mongodb_url'] = mongodb_url
        session['step'] = 'plan_selection'
        
        # Show subscription plans
        await show_subscription_plans(client, processing_msg, user_id)
        
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ **Database Connection Failed!**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please check your URL and try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
            ])
        )

async def show_subscription_plans(client: Client, message: Message, user_id: int):
    """Show available subscription plans"""
    from bot.database.subscription_db import PRICING_TIERS
    
    current_balance = await get_user_balance(user_id)
    
    text = f"💰 **Step 3/4: Choose Plan**\n\n"
    text += f"💵 **Your Balance:** ${current_balance:.2f}\n\n"
    text += f"📋 **Available Plans:**\n\n"
    
    buttons = []
    
    for plan_id, plan_data in PRICING_TIERS.items():
        price = plan_data['price']
        can_afford = current_balance >= price
        status = "✅" if can_afford else "❌"
        
        text += f"{status} **{plan_data['name']}** - ${price}\n"
        text += f"   Duration: {plan_data['duration_days']} days\n"
        if plan_data.get('features'):
            text += f"   Features: {', '.join(plan_data['features'])}\n"
        text += "\n"
        
        if can_afford:
            buttons.append([InlineKeyboardButton(
                f"{plan_data['name']} - ${price}",
                callback_data=f"select_plan:{plan_id}"
            )])
    
    if not buttons:
        text += "❌ **Insufficient balance for any plan**\n"
        text += "Please add balance to continue."
        buttons = [
            [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
        ]
    else:
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")])
    
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^select_plan:"))
async def handle_plan_selection(client: Client, query: CallbackQuery):
    """Handle subscription plan selection"""
    user_id = query.from_user.id
    session = creation_sessions.get(user_id)
    
    if not session or session['step'] != 'plan_selection':
        return await query.answer("❌ Session expired! Please start over.", show_alert=True)
    
    plan_id = query.data.split(':')[1]
    from bot.database.subscription_db import PRICING_TIERS
    selected_plan = PRICING_TIERS.get(plan_id)
    
    if not selected_plan:
        return await query.answer("❌ Invalid plan selected!", show_alert=True)
    
    session['data']['subscription_plan'] = plan_id
    session['data']['plan_details'] = selected_plan
    session['step'] = 'confirmation'
    
    # Show confirmation
    await show_creation_confirmation(client, query, user_id)

async def show_creation_confirmation(client: Client, query: CallbackQuery, user_id: int):
    """Show creation confirmation"""
    session = creation_sessions[user_id]
    data = session['data']
    plan = data['plan_details']
    
    current_balance = await get_user_balance(user_id)
    remaining_balance = current_balance - plan['price']
    
    # Mask sensitive data
    masked_token = f"{data['bot_token'][:8]}...{data['bot_token'][-4:]}"
    masked_db = f"{data['mongodb_url'][:20]}...{data['mongodb_url'][-10:]}"
    
    text = f"📋 **Step 4/4: Final Confirmation**\n\n"
    text += f"🔍 **Review Your Clone:**\n\n"
    text += f"🤖 **Bot:** @{data['bot_username']}\n"
    text += f"🆔 **Bot ID:** `{data['bot_id']}`\n"
    text += f"🔑 **Token:** `{masked_token}`\n"
    text += f"🗄️ **Database:** `{masked_db}`\n"
    text += f"💰 **Plan:** {plan['name']} (${plan['price']})\n"
    text += f"⏱️ **Duration:** {plan['duration_days']} days\n\n"
    text += f"💵 **Payment:**\n"
    text += f"• Current Balance: ${current_balance:.2f}\n"
    text += f"• Plan Cost: ${plan['price']:.2f}\n"
    text += f"• Remaining Balance: ${remaining_balance:.2f}\n\n"
    text += f"✅ **What happens next:**\n"
    text += f"• Payment will be deducted automatically\n"
    text += f"• Your clone will be created instantly\n"
    text += f"• Bot will start automatically\n\n"
    text += f"Confirm creation?"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Create Clone", callback_data="confirm_creation")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^confirm_creation$"))
async def handle_creation_confirmation(client: Client, query: CallbackQuery):
    """Handle final creation confirmation"""
    user_id = query.from_user.id
    session = creation_sessions.get(user_id)
    
    if not session or session['step'] != 'confirmation':
        return await query.answer("❌ Session expired!", show_alert=True)
    
    try:
        data = session['data']
        plan_details = data['plan_details']
        required_amount = plan_details['price']
        
        # Process creation
        processing_msg = await query.edit_message_text(
            f"⚙️ **Creating Your Clone...**\n\n"
            f"💰 **Deducting ${required_amount:.2f}...**\n"
            f"🤖 **Setting up @{data['bot_username']}...**\n\n"
            f"Please wait, this may take a moment..."
        )
        
        # Import the auto-approval function
        from bot.plugins.clone_request import process_clone_auto_approval
        
        success, result = await process_clone_auto_approval(user_id, data)
        
        if success:
            # Clean up session
            del creation_sessions[user_id]
            
            if isinstance(result, dict):
                text = f"🎉 **Clone Created Successfully!**\n\n"
                text += f"🤖 **Bot:** @{result['bot_username']}\n"
                text += f"💰 **Plan:** {result['plan']}\n"
                text += f"💵 **Amount Deducted:** ${result['amount_deducted']:.2f}\n"
                
                if result['clone_started']:
                    text += f"\n✅ **Status:** Your bot is running and ready!\n"
                    text += f"🔗 **Bot Link:** https://t.me/{result['bot_username']}"
                else:
                    text += f"\n⚠️ **Status:** Starting up (may take a few minutes)"
                
                remaining_balance = await get_user_balance(user_id)
                text += f"\n💰 **Remaining Balance:** ${remaining_balance:.2f}"
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{result['bot_username']}")],
                    [InlineKeyboardButton("📋 Manage Clone", callback_data="manage_my_clone")],
                    [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
                ])
                
            else:
                text = f"🎉 **Clone Created Successfully!**\n\n"
                text += f"🤖 **Bot:** @{data['bot_username']}\n"
                text += f"💰 **Plan:** {plan_details['name']}\n"
                text += f"💵 **Amount Deducted:** ${required_amount:.2f}\n\n"
                text += f"✅ Your clone is being set up and will be ready shortly!"
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{data['bot_username']}")],
                    [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
                ])
            
            await processing_msg.edit_text(text, reply_markup=buttons)
        else:
            # Clean up session
            del creation_sessions[user_id]
            
            await processing_msg.edit_text(
                f"❌ **Clone Creation Failed!**\n\n"
                f"Error: {result}\n\n"
                f"Your balance has not been deducted.\n"
                f"Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="start_clone_creation")],
                    [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error in creation confirmation: {e}")
        
        if user_id in creation_sessions:
            del creation_sessions[user_id]
        
        await query.edit_message_text(
            "❌ **Error creating clone!**\n\n"
            "Please try again later or contact support.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_clone_creation")],
                [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
            ])
        )

@Client.on_callback_query(filters.regex("^cancel_creation$"))
async def handle_creation_cancellation(client: Client, query: CallbackQuery):
    """Handle creation cancellation"""
    user_id = query.from_user.id
    
    if user_id in creation_sessions:
        del creation_sessions[user_id]
    
    text = f"❌ **Clone Creation Cancelled**\n\n"
    text += f"No charges were made to your account.\n"
    text += f"You can start creating a clone anytime!"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation")],
        [InlineKeyboardButton("🏠 Back Home", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

# Session cleanup task
async def cleanup_creation_sessions():
    """Clean up expired creation sessions"""
    current_time = datetime.now()
    expired_sessions = []
    
    for user_id, session in creation_sessions.items():
        if (current_time - session['started_at']).seconds > 1800:  # 30 minutes
            expired_sessions.append(user_id)
    
    for user_id in expired_sessions:
        del creation_sessions[user_id]
        logger.info(f"Cleaned up expired session for user {user_id}")

# Schedule cleanup every 10 minutes
import asyncio
async def session_cleanup_task():
    """Background task to clean up sessions"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        await cleanup_creation_sessions()

# Start cleanup task
asyncio.create_task(session_cleanup_task())
