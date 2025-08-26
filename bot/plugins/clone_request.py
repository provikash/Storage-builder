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

# This command handler is moved to step_clone_creation.py to prevent conflicts
# @Client.on_message(filters.command("createclone") & filters.private)
# async def create_clone_command(client: Client, message: Message):
#     """Handle /createclone command"""

# Removed conflicting input handler - step_clone_creation.py handles all clone creation input

    # Check if session is expired (2 hours)
    elapsed_time = (datetime.now() - session['started_at']).total_seconds()
    if elapsed_time > 7200:  # 2 hours
        del request_sessions[user_id]
        await message.reply_text(
            "⏰ **Session expired!**\n\n"
            "Your clone creation session has timed out. Please start again with /createclone"
        )
        return
    
    # Update session activity
    session['last_activity'] = datetime.now()

    step = session['step']
    user_input = message.text.strip()

    if step == 'bot_token':
        print(f"🔑 DEBUG INPUT: Processing bot token for user {user_id}")
        print(f"🔍 DEBUG INPUT: Token length: {len(user_input) if user_input else 0}")
        
        # Validate bot token format
        if not user_input or ':' not in user_input or len(user_input) < 20:
            print(f"❌ DEBUG INPUT: Invalid token format for user {user_id}")
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
        print(f"🗄️ DEBUG INPUT: Processing MongoDB URL for user {user_id}")
        print(f"🔍 DEBUG INPUT: URL starts with: '{user_input[:20]}...' (truncated)")
        
        # Validate MongoDB URL format
        if not user_input.startswith(('mongodb://', 'mongodb+srv://')):
            print(f"❌ DEBUG INPUT: Invalid MongoDB URL format for user {user_id}")
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

    if not session:
        return await query.answer("❌ Session expired! Please start over with /createclone", show_alert=True)
    
    # Check session timeout
    elapsed_time = (datetime.now() - session['started_at']).total_seconds()
    if elapsed_time > 7200:  # 2 hours
        del request_sessions[user_id]
        return await query.answer("❌ Session expired! Please start over with /createclone", show_alert=True)
    
    if session['step'] != 'subscription_plan':
        return await query.answer("❌ Invalid session state! Please start over with /createclone", show_alert=True)
    
    # Update session activity
    session['last_activity'] = datetime.now()

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
    text += f"⚠️ **Important Notes:**\n"
    text += f"• Your request will be reviewed by administrators\n"
    text += f"• You'll be notified once approved/rejected\n"
    text += f"• Payment will be manually verified by admin\n"
    text += f"• Your clone will start automatically after approval\n\n"
    text += f"Confirm your request?"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Submit Request", callback_data="confirm_request")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_request")]
    ])

    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^confirm_request$"))
async def handle_request_confirmation(client: Client, query: CallbackQuery):
    """Handle clone creation with automatic balance processing"""
    user_id = query.from_user.id
    session = request_sessions.get(user_id)

    if not session or session['step'] != 'confirmation':
        return await query.answer("❌ Session expired!", show_alert=True)

    try:
        data = session['data']
        plan_details = data['plan_details']
        required_amount = plan_details['price']

        # Check balance
        from bot.database.balance_db import get_user_balance, check_sufficient_balance
        current_balance = await get_user_balance(user_id)

        if not await check_sufficient_balance(user_id, required_amount):
            await query.edit_message_text(
                f"❌ **Insufficient Balance!**\n\n"
                f"💰 **Required:** ${required_amount:.2f}\n"
                f"💰 **Your Balance:** ${current_balance:.2f}\n"
                f"💰 **Needed:** ${required_amount - current_balance:.2f}\n\n"
                f"Please add balance to your account and try again.\n\n"
                f"Use the 'Add Balance' button in the main menu to top up your account."
            )
            # Clean up session
            del request_sessions[user_id]
            return

        # Process automatic clone creation
        processing_msg = await query.edit_message_text(
            f"⚙️ **Creating Your Clone...**\n\n"
            f"💰 **Deducting ${required_amount:.2f} from your balance...**\n"
            f"🤖 **Setting up @{data['bot_username']}...**\n\n"
            f"Please wait, this may take a few moments..."
        )

        success, result = await process_clone_auto_approval(user_id, data)

        if success:
            # Clean up session
            del request_sessions[user_id]

            if isinstance(result, dict):
                message_text = (
                    f"🎉 **Clone Created Successfully!**\n\n"
                    f"🤖 **Bot:** @{result['bot_username']}\n"
                    f"💰 **Plan:** {result['plan']}\n"
                    f"💵 **Amount Deducted:** ${result['amount_deducted']:.2f}\n"
                )

                if result['clone_started']:
                    message_text += f"\n✅ **Status:** Your bot is now running and ready to use!"
                    message_text += f"\n🔗 **Bot Link:** https://t.me/{result['bot_username']}"
                else:
                    message_text += f"\n⚠️ **Status:** Clone created but will start automatically within a few minutes."

                # Get remaining balance
                remaining_balance = await get_user_balance(user_id)
                message_text += f"\n💰 **Remaining Balance:** ${remaining_balance:.2f}"

                await processing_msg.edit_text(message_text)
            else:
                await processing_msg.edit_text(
                    f"🎉 **Clone Created Successfully!**\n\n"
                    f"🤖 **Bot:** @{data['bot_username']}\n"
                    f"💰 **Plan:** {plan_details['name']}\n"
                    f"💵 **Amount Deducted:** ${required_amount:.2f}\n\n"
                    f"✅ Your clone is now being set up and will be ready shortly!"
                )
        else:
            # Clean up session
            del request_sessions[user_id]

            await processing_msg.edit_text(
                f"❌ **Clone Creation Failed!**\n\n"
                f"Error: {result}\n\n"
                f"Your balance has not been deducted. Please try again or contact support."
            )

    except Exception as e:
        logger.error(f"Error creating clone: {e}")
        # Clean up session
        if user_id in request_sessions:
            del request_sessions[user_id]

        await query.edit_message_text(
            "❌ **Error creating clone!**\n\n"
            "Please try again later or contact support."
        )

@Client.on_callback_query(filters.regex("^cancel_request$"))
async def handle_request_cancellation(client: Client, query: CallbackQuery):
    """Handle request cancellation"""
    user_id = query.from_user.id

    if user_id in request_sessions:
        del request_sessions[user_id]

    await query.edit_message_text(
        "❌ **Clone creation cancelled.**\n\n"
        "You can start creating a clone anytime with /createclone"
    )

async def notify_admins_new_request(request_data):
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
            # Assuming 'client' is accessible here or passed as an argument
            # If not, this needs to be refactored to pass the client object
            pass # Placeholder, as client is not directly available here
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

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
        elapsed_time = (current_time - session['started_at']).total_seconds()
        if elapsed_time > 7200:  # 2 hours
            expired_sessions.append(user_id)

    for user_id in expired_sessions:
        del request_sessions[user_id]
        
    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired clone creation sessions")

async def process_clone_auto_approval(user_id: int, request_data: dict):
    """Process auto-approval if balance is sufficient"""
    try:
        from bot.database.balance_db import check_sufficient_balance, deduct_balance
        from bot.database.subscription_db import create_subscription, PRICING_TIERS
        from bot.database.clone_db import create_clone
        from clone_manager import clone_manager

        plan_name = request_data.get('plan_details', {}).get('name', 'Monthly Plan').lower()

        # Map plan names to valid clone plan keys (removed token verification plans)
        plan_mapping = {
            'monthly plan': 'monthly',
            '3 months plan': 'quarterly',
            '6 months plan': 'semi_annual',
            'yearly plan': 'yearly'
        }

        plan_key = plan_mapping.get(plan_name, 'monthly')
        plan_data = PRICING_TIERS.get(plan_key, PRICING_TIERS['monthly'])
        required_amount = plan_data['price']

        # Check if user has sufficient balance
        has_balance = await check_sufficient_balance(user_id, required_amount)

        if not has_balance:
            logger.info(f"⚠️ Auto-approval failed for user {user_id}: insufficient balance (${required_amount} required)")
            return False, f"Insufficient balance. Required: ${required_amount:.2f}"

        # Deduct balance
        success, message = await deduct_balance(
            user_id=user_id,
            amount=required_amount,
            description=f"Clone purchase - {plan_data['name']} plan"
        )

        if not success:
            return False, message

        # Extract bot details
        bot_token = request_data['bot_token']
        mongodb_url = request_data['mongodb_url']
        bot_username = request_data.get('bot_username', 'Unknown')
        bot_id = bot_token.split(':')[0]

        # Create clone entry
        clone_data = {
            "_id": bot_id,
            "bot_token": bot_token,
            "username": bot_username,
            "admin_id": user_id,
            "mongodb_url": mongodb_url,
            "status": "active",
            "created_at": datetime.now(),
            "auto_approved": True,
            "approved_at": datetime.now()
        }

        clone_success = await create_clone(clone_data)

        if clone_success:
            # Create subscription with payment verified (auto-approved)
            sub_success = await create_subscription(
                bot_id=bot_id,
                user_id=user_id,
                plan=plan_key,
                payment_verified=True
            )

            if sub_success:
                # Activate subscription
                from bot.database.subscription_db import activate_subscription
                await activate_subscription(bot_id)

                # Activate clone
                from bot.database.clone_db import activate_clone
                await activate_clone(bot_id)

                # Start the clone bot
                try:
                    await asyncio.sleep(1)  # Wait for database sync
                    start_success, start_message = await clone_manager.start_clone(bot_id)

                    if start_success:
                        logger.info(f"✅ Auto-approved and started clone {bot_id} for user {user_id}")
                        return True, {
                            'bot_id': bot_id,
                            'bot_username': bot_username,
                            'plan': plan_data['name'],
                            'amount_deducted': required_amount,
                            'clone_started': True
                        }
                    else:
                        logger.warning(f"⚠️ Clone {bot_id} created but failed to start: {start_message}")
                        return True, {
                            'bot_id': bot_id,
                            'bot_username': bot_username,
                            'plan': plan_data['name'],
                            'amount_deducted': required_amount,
                            'clone_started': False,
                            'start_error': start_message
                        }

                except Exception as start_error:
                    logger.error(f"❌ Error starting auto-approved clone {bot_id}: {start_error}")
                    return True, {
                        'bot_id': bot_id,
                        'bot_username': bot_username,
                        'plan': plan_data['name'],
                        'amount_deducted': required_amount,
                        'clone_started': False,
                        'start_error': str(start_error)
                    }
            else:
                logger.error(f"❌ Failed to create subscription for auto-approved clone {bot_id}")
                return False, "Failed to create subscription"
        else:
            logger.error(f"❌ Failed to create clone {bot_id}")
            return False, "Failed to create clone"

    except Exception as e:
        logger.error(f"❌ Error in auto-approval process: {e}")
        return False, str(e)

async def submit_clone_request(user_id: int):
    """Submit clone request with auto-approval check"""
    try:
        session = request_sessions[user_id]
        request_data = session['data']

        # Try auto-approval first
        auto_success, auto_result = await process_clone_auto_approval(user_id, request_data)

        if auto_success:
            # Auto-approval successful
            from bot import Bot
            bot = Bot()

            if isinstance(auto_result, dict):
                message_text = (
                    f"🎉 **Clone Auto-Approved & Created!**\n\n"
                    f"🤖 **Bot:** @{auto_result['bot_username']}\n"
                    f"💰 **Plan:** {auto_result['plan']}\n"
                    f"💵 **Amount Deducted:** ${auto_result['amount_deducted']:.2f}\n"
                )

                if auto_result['clone_started']:
                    message_text += f"\n✅ **Status:** Your bot is now running and ready to use!"
                else:
                    message_text += f"\n⚠️ **Status:** Clone created but will start automatically within a few minutes."

                # Get remaining balance
                from bot.database.balance_db import get_user_balance
                remaining_balance = await get_user_balance(user_id)
                message_text += f"\n💰 **Remaining Balance:** ${remaining_balance:.2f}"

                await bot.send_message(user_id, message_text)

            # Clean up session
            del request_sessions[user_id]
            return True

        else:
            # Auto-approval failed, proceed with manual approval
            logger.info(f"⚠️ Auto-approval failed for user {user_id}: {auto_result}")

            # Continue with existing manual approval process
            request_id = str(uuid.uuid4())

            # Store in database for manual approval
            request_doc = {
                "request_id": request_id,
                "user_id": user_id,
                "bot_token": request_data['bot_token'],
                "bot_username": request_data.get('bot_username', 'Unknown'),
                "mongodb_url": request_data['mongodb_url'],
                "plan_details": request_data['plan_details'],
                "status": "pending",
                "created_at": datetime.now(),
                "auto_approval_failed": True,
                "failure_reason": auto_result
            }

            await store_clone_request(request_doc)

            from bot import Bot
            bot = Bot()

            await bot.send_message(
                user_id,
                f"⏳ **Clone Request Submitted for Manual Review**\n\n"
                f"🆔 **Request ID:** `{request_id[:8]}...`\n"
                f"🤖 **Bot Username:** @{request_data.get('bot_username', 'Unknown')}\n"
                f"💰 **Plan:** {request_data['plan_details']['name']}\n"
                f"💵 **Required:** ${request_data['plan_details']['price']:.2f}\n\n"
                f"❌ **Auto-approval failed:** {auto_result}\n\n"
                f"Your request has been forwarded to administrators for manual review.\n"
                f"You will be notified once it's processed."
            )

            # Notify admins
            await notify_admins_new_request(request_doc)

            # Clean up session
            del request_sessions[user_id]
            return True

    except Exception as e:
        logger.error(f"❌ Error submitting clone request: {e}")
        return False