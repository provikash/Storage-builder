import asyncio
import uuid
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store user request sessions
request_sessions = {}

@Client.on_message(filters.command("requestclone") & filters.private)
async def request_clone_command(client: Client, message: Message):
    """Handle clone request initiation"""
    user_id = message.from_user.id

    # Check if user already has a pending request
    existing_request = await get_pending_clone_request(user_id)
    if existing_request:
        return await message.reply_text(
            "⏳ **You already have a pending clone request!**\n\n"
            f"Request ID: `{existing_request['request_id'][:8]}...`\n"
            f"Status: {existing_request['status'].title()}\n"
            f"Submitted: {existing_request['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "Please wait for admin approval or contact support."
        )

    # Start request session
    request_sessions[user_id] = {
        'step': 'bot_token',
        'data': {},
        'started_at': datetime.now()
    }

    await message.reply_text(
        "🤖 **Clone Bot Request Process**\n\n"
        "Welcome! Let's set up your clone bot. I'll need some information from you.\n\n"
        "**Step 1/4: Bot Token**\n\n"
        "Please provide your bot token from @BotFather:\n\n"
        "Example: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`\n\n"
        "⚠️ **Important:** Keep your token secure and never share it publicly!"
    )

@Client.on_message(filters.private & ~filters.command(["start", "help", "about", "admin", "requestclone"]))
async def handle_clone_request_input(client: Client, message: Message):
    """Handle user input during clone request process"""
    user_id = message.from_user.id
    session = request_sessions.get(user_id)

    if not session:
        return
    
    # Check if session is expired (30 minutes)
    if (datetime.now() - session['started_at']).seconds > 1800:
        del request_sessions[user_id]
        await message.reply_text(
            "⏰ **Session expired!**\n\n"
            "Your clone request session has timed out. Please start again with /requestclone"
        )
        return

    step = session['step']
    user_input = message.text.strip()

    if step == 'bot_token':
        # Validate bot token format
        if not user_input or ':' not in user_input or len(user_input) < 20:
            return await message.reply_text(
                "❌ **Invalid bot token format!**\n\n"
                "Please provide a valid bot token from @BotFather.\n"
                "Format: `bot_id:token_string`"
            )

        # Test bot token
        try:
            logger.info(f"Testing bot token for user {user_id}")
            from pyrogram import Client as TestClient
            import asyncio
            
            test_client = TestClient(
                name=f"test_{user_input[:10]}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=user_input,
                in_memory=True
            )
            
            # Add timeout for token validation
            try:
                await asyncio.wait_for(test_client.start(), timeout=30.0)
                me = await test_client.get_me()
                await test_client.stop()
            except asyncio.TimeoutError:
                raise Exception("Token validation timed out")

            session['data']['bot_token'] = user_input
            session['data']['bot_username'] = me.username or f"bot_{me.id}"
            session['data']['bot_id'] = me.id
            session['step'] = 'mongodb_url'

            logger.info(f"Bot token validated for user {user_id}: @{me.username}")

            await message.reply_text(
                f"✅ **Bot Token Validated!**\n\n"
                f"🤖 Bot: @{me.username or f'bot_{me.id}'}\n"
                f"🆔 Bot ID: `{me.id}`\n\n"
                f"**Step 2/4: Database URL**\n\n"
                f"Please provide your MongoDB connection URL:\n\n"
                f"Example: `mongodb://username:password@host:port/database`\n"
                f"Or: `mongodb+srv://username:password@cluster.mongodb.net/database`\n\n"
                f"⚠️ **Note:** This will be your clone's private database."
            )

        except Exception as e:
            logger.error(f"Bot token validation failed for user {user_id}: {e}")
            await message.reply_text(
                f"❌ **Bot token validation failed!**\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check your token and try again.\n\n"
                f"Make sure:\n"
                f"• Token is from @BotFather\n"
                f"• Token format is correct (number:letters)\n"
                f"• Bot is not deleted or restricted"
            )

    elif step == 'mongodb_url':
        # Validate MongoDB URL format
        if not user_input.startswith(('mongodb://', 'mongodb+srv://')):
            return await message.reply_text(
                "❌ **Invalid MongoDB URL format!**\n\n"
                "URL must start with `mongodb://` or `mongodb+srv://`\n"
                "Please provide a valid MongoDB connection string."
            )

        # Test MongoDB connection
        try:
            logger.info(f"Testing MongoDB connection for user {user_id}")
            from motor.motor_asyncio import AsyncIOMotorClient
            import asyncio
            
            test_client = AsyncIOMotorClient(user_input, serverSelectionTimeoutMS=10000)
            test_db = test_client.test_connection_db
            
            # Add timeout for MongoDB connection test
            await asyncio.wait_for(test_db.command("ping"), timeout=15.0)
            test_client.close()

            session['data']['mongodb_url'] = user_input
            session['step'] = 'subscription_plan'

            logger.info(f"MongoDB connection validated for user {user_id}")

            # Show subscription plans
            await show_subscription_plans(client, message, user_id)

        except Exception as e:
            logger.error(f"MongoDB connection failed for user {user_id}: {e}")
            await message.reply_text(
                f"❌ **Database connection failed!**\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check your MongoDB URL and try again.\n\n"
                f"Make sure:\n"
                f"• URL starts with mongodb:// or mongodb+srv://\n"
                f"• Credentials are correct\n"
                f"• Database server is accessible\n"
                f"• Network allows connections"
            )

async def show_subscription_plans(client: Client, message: Message, user_id: int):
    """Show available subscription plans"""
    plans = await get_pricing_tiers()

    text = "💰 **Step 3/4: Subscription Plan**\n\n"
    text += "Choose your subscription plan:\n\n"

    buttons = []
    for plan_id, plan_data in plans.items():
        text += f"**{plan_data['name']}** - ${plan_data['price']}\n"
        text += f"Duration: {plan_data['duration_days']} days\n"
        if plan_data.get('features'):
            text += f"Features: {', '.join(plan_data['features'])}\n"
        text += "\n"

        buttons.append([InlineKeyboardButton(
            f"{plan_data['name']} - ${plan_data['price']}", 
            callback_data=f"select_plan:{plan_id}"
        )])

    text += "Select a plan to continue:"

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^select_plan:"))
async def handle_plan_selection(client: Client, query: CallbackQuery):
    """Handle subscription plan selection"""
    user_id = query.from_user.id
    session = request_sessions.get(user_id)

    if not session or session['step'] != 'subscription_plan':
        return await query.answer("❌ Session expired! Please start over with /requestclone", show_alert=True)

    plan_id = query.data.split(':')[1]
    plans = await get_pricing_tiers()
    selected_plan = plans.get(plan_id)

    if not selected_plan:
        return await query.answer("❌ Invalid plan selected!", show_alert=True)

    session['data']['subscription_plan'] = plan_id
    session['data']['plan_details'] = selected_plan
    session['step'] = 'confirmation'

    # Show confirmation
    await show_request_confirmation(client, query, user_id)

async def show_request_confirmation(client: Client, query: CallbackQuery, user_id: int):
    """Show request confirmation"""
    session = request_sessions[user_id]
    data = session['data']
    plan = data['plan_details']

    # Mask sensitive data
    masked_token = f"{data['bot_token'][:8]}...{data['bot_token'][-4:]}"
    masked_db = f"{data['mongodb_url'][:20]}...{data['mongodb_url'][-10:]}"

    text = "📋 **Step 4/4: Confirmation**\n\n"
    text += "Please review your clone request:\n\n"
    text += f"🤖 **Bot:** @{data['bot_username']}\n"
    text += f"🆔 **Bot ID:** `{data['bot_id']}`\n"
    text += f"🔑 **Token:** `{masked_token}`\n"
    text += f"🗄️ **Database:** `{masked_db}`\n"
    text += f"💰 **Plan:** {plan['name']} (${plan['price']})\n"
    text += f"⏱️ **Duration:** {plan['duration_days']} days\n\n"
    text += "⚠️ **Important Notes:**\n"
    text += "• Your request will be reviewed by administrators\n"
    text += "• You'll be notified once approved/rejected\n"
    text += "• Payment will be required after approval\n\n"
    text += "Confirm your request?"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Submit Request", callback_data="confirm_request")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_request")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^confirm_request$"))
async def handle_request_confirmation(client: Client, query: CallbackQuery):
    """Handle request confirmation and submission"""
    user_id = query.from_user.id
    session = request_sessions.get(user_id)

    if not session or session['step'] != 'confirmation':
        return await query.answer("❌ Session expired!", show_alert=True)

    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        data = session['data']

        # Create clone request
        request_data = {
            "request_id": request_id,
            "user_id": user_id,
            "bot_token": data['bot_token'],
            "bot_username": data['bot_username'],
            "bot_id": data['bot_id'],
            "mongodb_url": data['mongodb_url'],
            "subscription_plan": data['subscription_plan'],
            "plan_details": data['plan_details'],
            "status": "pending",
            "created_at": datetime.now(),
            "requester_info": {
                "first_name": query.from_user.first_name,
                "last_name": query.from_user.last_name,
                "username": query.from_user.username
            }
        }

        from bot.database.clone_db import create_clone_request
        success = await create_clone_request(request_data)
        
        if not success:
            await query.edit_message_text(
                "❌ **Error submitting request!**\n\n"
                "Please try again later or contact support."
            )
            return

        # Clean up session
        del request_sessions[user_id]

        # Notify user
        await query.edit_message_text(
            f"✅ **Clone Request Submitted Successfully!**\n\n"
            f"📋 **Request ID:** `{request_id}`\n"
            f"🤖 **Bot:** @{data['bot_username']}\n"
            f"💰 **Plan:** {data['plan_details']['name']}\n"
            f"📅 **Submitted:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"⏳ **Status:** Pending Review\n\n"
            f"You'll receive a notification once your request is reviewed by our administrators.\n\n"
            f"Thank you for choosing our service! 🎉"
        )

        # Notify admins
        await notify_admins_new_request(client, request_data)

    except Exception as e:
        logger.error(f"Error submitting clone request: {e}")
        await query.edit_message_text(
            "❌ **Error submitting request!**\n\n"
            "Please try again later or contact support."
        )

@Client.on_callback_query(filters.regex("^cancel_request$"))
async def handle_request_cancellation(client: Client, query: CallbackQuery):
    """Handle request cancellation"""
    user_id = query.from_user.id

    if user_id in request_sessions:
        del request_sessions[user_id]

    await query.edit_message_text(
        "❌ **Clone request cancelled.**\n\n"
        "You can start a new request anytime with /requestclone"
    )

async def notify_admins_new_request(client: Client, request_data):
    """Notify all admins about new clone request"""
    admin_ids = [Config.OWNER_ID] + list(Config.ADMINS)

    masked_token = f"{request_data['bot_token'][:8]}...{request_data['bot_token'][-4:]}"

    text = "🔔 **New Clone Request**\n\n"
    text += f"📋 **Request ID:** `{request_data['request_id'][:8]}...`\n"
    text += f"👤 **User:** {request_data['requester_info']['first_name']}"
    if request_data['requester_info']['username']:
        text += f" (@{request_data['requester_info']['username']})"
    text += f"\n🆔 **User ID:** `{request_data['user_id']}`\n"
    text += f"🤖 **Bot:** @{request_data['bot_username']}\n"
    text += f"🔑 **Token:** `{masked_token}`\n"
    text += f"💰 **Plan:** {request_data['plan_details']['name']} (${request_data['plan_details']['price']})\n"
    text += f"📅 **Submitted:** {request_data['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    text += "Use /admin to review and approve/reject this request."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Quick Approve", callback_data=f"quick_approve:{request_data['request_id']}"),
            InlineKeyboardButton("❌ Quick Reject", callback_data=f"quick_reject:{request_data['request_id']}")
        ],
        [InlineKeyboardButton("📋 View Details", callback_data=f"view_request:{request_data['request_id']}")]
    ])

    for admin_id in admin_ids:
        try:
            await client.send_message(admin_id, text, reply_markup=buttons)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# Database functions for clone requests are now in clone_db.py

async def get_pending_clone_request(user_id: int):
    """Get pending clone request for user"""
    from bot.database.clone_db import clone_db
    clone_requests = clone_db.clone_requests
    return await clone_requests.find_one({
        "user_id": user_id,
        "status": "pending"
    })

async def get_all_pending_requests():
    """Get all pending clone requests"""
    try:
        requests = await clone_requests.find({"status": "pending"}).to_list(None)
        return requests
    except Exception as e:
        print(f"ERROR: Error getting pending requests: {e}")
        return []

async def get_pending_request(request_id: str):
    """Get a specific pending request"""
    try:
        request = await clone_requests.find_one({"request_id": request_id, "status": "pending"})
        return request
    except Exception as e:
        print(f"ERROR: Error getting request {request_id}: {e}")
        return None

async def approve_request(request_id: str):
    """Approve a clone request"""
    try:
        from clone_manager import clone_manager
        from bot.database.subscription_db import create_subscription

        # Get the request
        request = await get_pending_request(request_id)
        if not request:
            return False, "Request not found"

        # Create the clone
        success, clone_data = await clone_manager.create_clone(
            request['bot_token'], 
            request['user_id'], 
            request['mongodb_url'], 
            request['plan_details']['tier']
        )

        if not success:
            return False, clone_data

        # Update request status
        await clone_requests.update_one(
            {"request_id": request_id},
            {"$set": {"status": "approved", "approved_at": datetime.now()}}
        )

        # Start the clone
        await clone_manager.start_clone(clone_data['bot_id'])

        # Notify the user
        try:
            from bot import Bot
            mother_bot = Bot()
            if mother_bot.is_connected:
                await mother_bot.send_message(
                    request['user_id'],
                    f"🎉 **Clone Request Approved!**\n\n"
                    f"🤖 **Your Bot:** @{clone_data['username']}\n"
                    f"💰 **Plan:** {request['plan_details']['name']}\n"
                    f"📅 **Expires:** {clone_data['expiry'].strftime('%Y-%m-%d')}\n\n"
                    f"Your bot is now active and ready to use!"
                )
        except Exception as e:
            print(f"ERROR: Failed to notify user {request['user_id']}: {e}")

        return True, clone_data

    except Exception as e:
        print(f"ERROR: Error approving request {request_id}: {e}")
        return False, str(e)

async def reject_request(request_id: str, reason: str = "No reason provided"):
    """Reject a clone request"""
    try:
        # Get the request
        request = await get_pending_request(request_id)
        if not request:
            return False, "Request not found"

        # Update request status
        await clone_requests.update_one(
            {"request_id": request_id},
            {"$set": {
                "status": "rejected", 
                "rejected_at": datetime.now(),
                "rejection_reason": reason
            }}
        )

        # Notify the user
        try:
            from bot import Bot
            mother_bot = Bot()
            if mother_bot.is_connected:
                await mother_bot.send_message(
                    request['user_id'],
                    f"❌ **Clone Request Rejected**\n\n"
                    f"🆔 **Request ID:** {request_id[:8]}...\n"
                    f"📝 **Reason:** {reason}\n\n"
                    f"You can submit a new request with `/requestclone` if needed."
                )
        except Exception as e:
            print(f"ERROR: Failed to notify user {request['user_id']}: {e}")

        return True, "Request rejected successfully"

    except Exception as e:
        print(f"ERROR: Error rejecting request {request_id}: {e}")
        return False, str(e)


async def get_clone_request(request_id: str):
    """Get specific clone request"""
    from bot.database.clone_db import clone_db
    clone_requests = clone_db.clone_requests
    return await clone_requests.find_one({"request_id": request_id})

async def update_clone_request_status(request_id: str, status: str, admin_id: int = None):
    """Update clone request status"""
    from bot.database.clone_db import clone_db
    clone_requests = clone_db.clone_requests

    update_data = {
        "status": status,
        "updated_at": datetime.now()
    }

    if admin_id:
        update_data["reviewed_by"] = admin_id
        update_data["reviewed_at"] = datetime.now()

    await clone_requests.update_one(
        {"request_id": request_id},
        {"$set": update_data}
    )

# Session cleanup
async def cleanup_expired_sessions():
    """Clean up expired request sessions"""
    current_time = datetime.now()
    expired_sessions = []

    for user_id, session in request_sessions.items():
        if (current_time - session['started_at']).seconds > 1800:  # 30 minutes
            expired_sessions.append(user_id)

    for user_id in expired_sessions:
        del request_sessions[user_id]