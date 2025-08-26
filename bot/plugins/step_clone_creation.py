
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
    """Start simplified clone creation process"""
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
    
    # Check user balance first
    current_balance = await get_user_balance(user_id)
    
    text = f"🤖 **Create Your Clone Bot**\n\n"
    text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"
    
    if current_balance < 3.00:
        text += f"❌ **Insufficient Balance**\n\n"
        text += f"You need at least $3.00 to create a clone.\n"
        text += f"Please add balance to your account first.\n\n"
        text += f"💡 **Clone Plans:**\n"
        text += f"• Monthly: $3.00 (30 days)\n"
        text += f"• Quarterly: $8.00 (90 days) - Best Value!\n"
        text += f"• Semi-Annual: $15.00 (180 days)\n"
        text += f"• Yearly: $26.00 (365 days)"
        
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
    text += f"💡 **Available Plans:**\n"
    text += f"• Monthly: $3.00 - Perfect for testing\n"
    text += f"• Quarterly: $8.00 - Most popular!\n"
    text += f"• Semi-Annual: $15.00 - Better value\n"
    text += f"• Yearly: $26.00 - Best savings\n\n"
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

@Client.on_callback_query(filters.regex("^begin_step1_plan$"))
async def step1_choose_plan(client, query):
    """Step 1: Choose subscription plan"""
    await query.answer()
    
    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)
    
    # Initialize session with timestamp for uniqueness
    current_time = datetime.now()
    creation_sessions[user_id] = {
        'step': 'plan_selection',
        'data': {},
        'started_at': current_time
    }
    
    text = f"📋 **Step 1/3: Choose Your Plan**\n\n"
    text += f"💰 **Your Balance:** ${current_balance:.2f}\n\n"
    text += f"Select a subscription plan for your clone:\n\n"
    
    from bot.database.subscription_db import PRICING_TIERS
    
    buttons = []
    
    for plan_id, plan_data in PRICING_TIERS.items():
        price = plan_data['price']
        can_afford = current_balance >= price
        
        if can_afford:
            emoji = "✅"
            callback_data = f"select_plan:{plan_id}"
        else:
            emoji = "❌"
            callback_data = "insufficient_balance"
        
        text += f"{emoji} **{plan_data['name']}** - ${price}\n"
        text += f"   Duration: {plan_data['duration_days']} days\n"
        
        if plan_data.get('savings'):
            text += f"   💡 Save: {plan_data['savings']}\n"
        text += "\n"
        
        if can_afford:
            buttons.append([InlineKeyboardButton(
                f"{plan_data['name']} - ${price}",
                callback_data=callback_data
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
    
    # Add timestamp to make content unique
    text += f"\n🕐 **Session started:** {current_time.strftime('%H:%M:%S')}"
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            await query.answer("ℹ️ Plan selection is already displayed above.", show_alert=False)
        else:
            await query.answer("❌ Error loading plans. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^select_plan:"))
async def step2_bot_token(client, query):
    """Step 2: Get bot token"""
    await query.answer()
    
    user_id = query.from_user.id
    session = creation_sessions.get(user_id)
    
    if not session:
        return await query.answer("❌ Session expired! Please start over.", show_alert=True)
    
    plan_id = query.data.split(':')[1]
    from bot.database.subscription_db import PRICING_TIERS
    selected_plan = PRICING_TIERS.get(plan_id)
    
    if not selected_plan:
        return await query.answer("❌ Invalid plan selected!", show_alert=True)
    
    # Store plan selection
    session['data']['plan_id'] = plan_id
    session['data']['plan_details'] = selected_plan
    session['step'] = 'bot_token'
    
    text = f"🤖 **Step 2/3: Bot Token**\n\n"
    text += f"✅ **Selected Plan:** {selected_plan['name']} (${selected_plan['price']})\n\n"
    text += f"Now, provide your bot token from @BotFather.\n\n"
    text += f"**📋 Quick Guide:**\n"
    text += f"1. Go to @BotFather\n"
    text += f"2. Send `/newbot`\n"
    text += f"3. Choose bot name: `My File Bot`\n"
    text += f"4. Choose username: `myfilebot` (must end with 'bot')\n"
    text += f"5. Copy the token and send it here\n\n"
    text += f"**📝 Token Format:**\n"
    text += f"`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
    text += f"⚠️ **Keep your token secure!**\n\n"
    text += f"Please send your bot token now:"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Open BotFather", url="https://t.me/BotFather")],
        [InlineKeyboardButton("❓ Need Help?", callback_data="token_help")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_creation")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^token_help$"))
async def token_help_callback(client, query):
    """Show token help"""
    await query.answer()
    
    user_id = query.from_user.id
    session = creation_sessions.get(user_id, {})
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
    session = creation_sessions.get(user_id)
    
    if not session:
        return
    
    # Check session timeout (30 minutes)
    if (datetime.now() - session['started_at']).seconds > 1800:
        del creation_sessions[user_id]
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
    
    if step == 'bot_token':
        await handle_bot_token_input(client, message, user_input, session)
    elif step == 'mongodb_url':
        await handle_mongodb_input(client, message, user_input, session)

async def handle_bot_token_input(client: Client, message: Message, bot_token: str, session: dict):
    """Handle and validate bot token"""
    user_id = message.from_user.id
    
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
        await test_client.stop()
        
        # Store validated data
        session['data']['bot_token'] = bot_token
        session['data']['bot_username'] = me.username or f"bot_{me.id}"
        session['data']['bot_id'] = me.id
        session['step'] = 'mongodb_url'
        
        plan = session['data']['plan_details']
        
        text = f"✅ **Step 2 Complete!**\n\n"
        text += f"🤖 **Bot Verified:** @{me.username or f'bot_{me.id}'}\n"
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

async def handle_mongodb_input(client: Client, message: Message, mongodb_url: str, session: dict):
    """Handle and validate MongoDB URL"""
    user_id = message.from_user.id
    
    # Validate URL format
    if not mongodb_url.startswith(('mongodb://', 'mongodb+srv://')):
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
        
        # Show final confirmation
        await show_final_confirmation(client, processing_msg, user_id)
        
    except Exception as e:
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
    session = creation_sessions[user_id]
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
    session = creation_sessions.get(user_id)
    
    if not session or session['step'] != 'confirmation':
        return await query.answer("❌ Session expired!", show_alert=True)
    
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
        
        # Import the auto-approval function
        from bot.plugins.clone_request import process_clone_auto_approval
        
        success, result = await process_clone_auto_approval(user_id, data)
        
        if success:
            # Clean up session
            del creation_sessions[user_id]
            
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
            del creation_sessions[user_id]
            
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
        logger.error(f"Error in final confirmation: {e}")
        
        if user_id in creation_sessions:
            del creation_sessions[user_id]
        
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
    
    if user_id in creation_sessions:
        step = creation_sessions[user_id].get('step', 'unknown')
        del creation_sessions[user_id]
    else:
        step = 'unknown'
    
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
async def session_cleanup_task():
    """Background task to clean up sessions"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        await cleanup_creation_sessions()

# Start cleanup task
asyncio.create_task(session_cleanup_task())
