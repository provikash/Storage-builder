import asyncio
import os
import subprocess
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database import add_user, present_user
from bot.logging import LOGGER
from bot.utils.error_handler import safe_edit_message, safe_answer_callback
from pyrogram import enums

logger = LOGGER(__name__)

# Store active clones
active_clones = {}

# Clone creation is only available for mother bot - this handler is removed from clone bots

# settoken command is only available for mother bot - removed from clone bots

@Client.on_message(filters.command("manageclone") & filters.private)
async def manage_clone_command(client: Client, message: Message):
    """Manage user's clone bot"""
    user_id = message.from_user.id

    from bot.database.clone_db import get_user_clones
    user_clones = await get_user_clones(user_id)

    if not user_clones:
        return await message.reply_text(
            "📝 **You don't have any clone bots yet.**\n\n"
            "Use `/createclone` to create your first clone!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Create Clone", callback_data="start_clone_creation")]
            ])
        )

    # Show user's clone (assuming one clone per user)
    clone = user_clones[0]
    from bot.database.subscription_db import get_subscription
    subscription = await get_subscription(clone['_id'])

    from clone_manager import clone_manager
    is_running = clone['_id'] in clone_manager.get_running_clones()

    text = f"🤖 **Your Clone Bot**\n\n"
    text += f"🤖 **Bot:** @{clone['username']}\n"
    text += f"📊 **Status:** {'🟢 Running' if is_running else '🔴 Stopped'}\n"

    if subscription:
        text += f"💰 **Plan:** {subscription['tier']}\n"
        text += f"📅 **Expires:** {subscription['expires_at'].strftime('%Y-%m-%d')}\n"

    buttons = [
        [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{clone['username']}")],
        [InlineKeyboardButton("⚙️ Clone Admin", callback_data="clone_admin_panel")]
    ]

    if is_running:
        buttons.append([InlineKeyboardButton("⏸️ Stop Bot", callback_data=f"stop_clone:{clone['_id']}")])
    else:
        buttons.append([InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_clone:{clone['_id']}")])

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def create_clone_handler(client: Client, message):
    """Handler for creating clone - redirect to step clone creation"""
    user_id = message.from_user.id
    print(f"🔄 DEBUG CLONE: create_clone_handler called for user {user_id}")

    # Import and call the clone creation flow
    from bot.plugins.step_clone_creation import start_clone_creation
    await start_clone_creation(client, message)

@Client.on_message(filters.command("listclones") & filters.private)
async def list_clones(client: Client, message: Message):
    """List all active clones for admins only"""
    user_id = message.from_user.id

    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ Only administrators can list all clones.")

    from bot.database.clone_db import get_all_clones
    all_clones = await get_all_clones()

    if not all_clones:
        return await message.reply_text("📝 No clones found in the system.")

    clone_list = "🤖 **All System Clones:**\n\n"

    for i, clone in enumerate(all_clones[:10], 1):  # Show first 10
        status = "🟢 Active" if clone.get('status') == 'active' else "🔴 Inactive"
        clone_list += f"**{i}.** @{clone['username']}\n"
        clone_list += f"   📊 Status: {status}\n"
        clone_list += f"   👤 Admin: {clone['admin_id']}\n\n"

    await message.reply_text(clone_list)

def validate_bot_token(token: str) -> bool:
    """Validate bot token format"""
    import re
    pattern = r'^\d{8,10}:[a-zA-Z0-9_-]{35}$'
    return bool(re.match(pattern, token))

@Client.on_callback_query(filters.regex("^manage_my_clone$"))
async def manage_user_clone(client: Client, query: CallbackQuery):
    """Handle user clone management"""
    await query.answer()
    user_id = query.from_user.id

    # Import here to avoid circular imports
    from bot.database.clone_db import get_user_clones

    try:
        user_clones = await get_user_clones(user_id)

        if not user_clones:
            text = f"🤖 **No Clones Found**\n\n"
            text += f"You don't have any clone bots yet.\n"
            text += f"Create your first clone to get started!\n\n"
            text += f"💡 **What is a Clone?**\n"
            text += f"A clone is your personal copy of this bot with all features!"

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Create Clone", callback_data="start_clone_creation")],
                [InlineKeyboardButton("❓ Learn More", callback_data="creation_help")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])

            return await query.edit_message_text(text, reply_markup=buttons)

        # Show user's clones
        clone = user_clones[0]  # Show first clone
        status_emoji = "✅" if clone.get('status') == 'active' else "⏸️"

        text = f"🤖 **Your Clone Bot**\n\n"
        text += f"{status_emoji} **Bot:** @{clone.get('username', 'Unknown')}\n"
        text += f"🆔 **Bot ID:** `{clone['_id']}`\n"
        text += f"📊 **Status:** {clone.get('status', 'Unknown').title()}\n"
        text += f"📅 **Created:** {clone.get('created_at', 'Unknown')}\n\n"

        if clone.get('status') == 'active':
            text += f"🔗 **Bot Link:** https://t.me/{clone.get('username', '')}\n\n"
            text += f"🎛️ **Management Options:**"
        else:
            text += f"⚠️ **Status:** Your clone is not currently active."

        buttons = []
        if clone.get('status') == 'active':
            buttons.extend([
                [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{clone.get('username', '')}")],
                [
                    InlineKeyboardButton("⏸️ Stop Bot", callback_data=f"stop_clone:{clone['_id']}"),
                    InlineKeyboardButton("🔄 Restart", callback_data=f"restart_clone:{clone['_id']}")
                ],
                [InlineKeyboardButton("⚙️ Settings", callback_data=f"clone_settings:{clone['_id']}")]
            ])
        else:
            buttons.append([InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_clone:{clone['_id']}")])

        buttons.extend([
            [InlineKeyboardButton("💰 Extend Subscription", callback_data=f"extend_clone:{clone['_id']}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])

        await safe_edit_message(query, text, InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in manage_user_clone: {e}")
        await safe_edit_message(query,
            "❌ **Error Loading Clones**\n\n"
            "There was an error loading your clone information.\n"
            "Please try again or contact support.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="manage_my_clone")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )

async def create_bot_clone(bot_token: str, owner_id: int) -> tuple:
    """Create a new bot clone with the provided token"""
    try:
        # Test the bot token first
        test_client = Client(
            name=f"test_{bot_token[:10]}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=bot_token
        )

        await test_client.start()
        me = await test_client.get_me()
        bot_info = {
            'bot_id': me.id,
            'username': me.username,
            'first_name': me.first_name,
            'token': bot_token,
            'owner_id': owner_id,
            'running': True
        }
        await test_client.stop()

        # Start the clone in background
        await start_clone_process(bot_info)

        return True, bot_info

    except Exception as e:
        return False, str(e)

async def start_clone_process(bot_info: dict):
    """Start a clone bot process"""
    try:
        # Create a unique session name
        session_name = f"clone_{bot_info['bot_id']}"

        # Start the clone in background task
        asyncio.create_task(run_clone_bot(bot_info))

    except Exception as e:
        print(f"Error starting clone process: {e}")

# Placeholder for clone manager (if needed, can be expanded)
class CloneManager:
    def __init__(self):
        self.active_clones = {}

    def get_running_clones(self):
        return list(self.active_clones.keys())

    async def start_clone(self, clone_id):
        if clone_id in self.active_clones:
            return False, "Clone is already running."
        
        # In a real scenario, you'd fetch clone data and start it.
        # For now, we assume it's handled by run_clone_bot being called.
        # This is a placeholder to mimic the manager's interface.
        return True, "Clone starting process initiated."

clone_manager = CloneManager()

async def run_clone_bot(clone_data):
    """Run a single clone bot instance"""
    bot_token = clone_data['token']
    bot_id = clone_data['bot_id']
    clone_bot = None

    try:
        print(f"🚀 Starting clone bot {bot_id}")

        # Create clone bot instance
        clone_bot = Client(
            f"clone_{bot_id}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=bot_token,
            plugins=dict(root="bot/plugins")
        )

        # Store bot instance in clone manager
        clone_manager.active_clones[bot_id] = {
            'client': clone_bot,
            'data': clone_data,
            'status': 'running'
        }

        # Start the bot
        await clone_bot.start()
        print(f"✅ Clone bot @{clone_bot.me.username} started successfully!")

        # Keep running until stopped
        while clone_manager.active_clones.get(bot_id, {}).get('status') == 'running':
            await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error running clone {bot_id}: {e}")

    finally:
        # Cleanup - ensure proper shutdown
        if clone_bot and clone_bot.is_connected:
            try:
                # Use asyncio.create_task to avoid loop conflicts
                stop_task = asyncio.create_task(clone_bot.stop())
                await asyncio.wait_for(stop_task, timeout=10.0)
                print(f"🛑 Clone bot {bot_id} stopped properly")
            except asyncio.TimeoutError:
                print(f"⚠️ Timeout stopping clone {bot_id}")
            except Exception as e:
                print(f"⚠️ Error stopping clone {bot_id}: {e}")

        # Remove from active clones
        if bot_id in clone_manager.active_clones:
            del clone_manager.active_clones[bot_id]
            print(f"🗑️ Removed clone {bot_id} from active list")

@Client.on_callback_query(filters.regex("^select_plan:"))
async def select_plan_callback(client, query):
    """Handle plan selection for clone creation"""
    await query.answer()
    user_id = query.from_user.id
    plan_id = query.data.split(":")[1]

    # Store selected plan in session
    from bot.utils.session_manager import SessionManager
    session_manager = SessionManager()
    await session_manager.create_session(user_id, 'clone_creation', {'plan_id': plan_id})

    await query.edit_message_text(
        "🤖 **Create Your Bot Clone**\n\n"
        "Now provide your bot token from @BotFather:\n\n"
        "**Format:** `/settoken YOUR_BOT_TOKEN`\n\n"
        "**Example:** `/settoken 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`\n\n"
        "💡 **Need help?** Contact @BotFather on Telegram to create a new bot and get your token.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ How to get bot token", url="https://t.me/botfather")],
            [InlineKeyboardButton("🔙 Back to plans", callback_data="back_to_plans")]
        ])
    )

@Client.on_callback_query(filters.regex("^clone_info$"))
async def clone_info_callback(client, query):
    """Show information about clone creation"""
    await query.answer()

    text = "❓ **How Clone Creation Works**\n\n"
    text += "1️⃣ **Select a Plan** - Choose your subscription duration\n"
    text += "2️⃣ **Provide Bot Token** - Get one from @BotFather\n"
    text += "3️⃣ **Make Payment** - Secure payment processing\n"
    text += "4️⃣ **Clone Ready!** - Your bot will be activated\n\n"
    text += "✨ **Features:**\n"
    text += "• Full file sharing capabilities\n"
    text += "• Custom admin panel\n"
    text += "• Force subscribe channels\n"
    text += "• Token verification system\n"
    text += "• Request channels\n"
    text += "• Premium subscriptions\n\n"
    text += "🔒 **Secure & Reliable**\n"
    text += "Your bot runs on our infrastructure with 99.9% uptime!"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to plans", callback_data="back_to_plans")]
        ])
    )

@Client.on_callback_query(filters.regex("^back_to_plans$"))
async def back_to_plans_callback(client, query):
    """Go back to plan selection"""
    await query.answer()
    await create_clone_handler(client, query.message)

@Client.on_callback_query(filters.regex("^start_clone_creation$"))
async def start_clone_creation_callback(client, query):
    """Start clone creation process"""
    await query.answer()
    await create_clone_handler(client, query.message)

@Client.on_callback_query(filters.regex("^manage_clones$"))
async def manage_clones_callback(client, query):
    """Handle manage clones button"""
    await query.answer()
    await manage_clone_command(client, query.message)

@Client.on_callback_query(filters.regex("^proceed_payment$"))
async def proceed_payment_callback(client, query):
    """Handle payment processing"""
    await query.answer()
    user_id = query.from_user.id

    from bot.utils.session_manager import SessionManager
    session_manager = SessionManager()
    session = await session_manager.get_session(user_id)

    if not session:
        return await query.edit_message_text("❌ Session expired. Please start over with `/createclone`")

    # Get plan details
    plan_id = session['plan_id']
    from bot.database.subscription_db import get_pricing_tier
    plan = await get_pricing_tier(plan_id)

    # For now, we'll create the clone directly (you can add payment gateway later)
    await query.edit_message_text("🔄 Processing payment and creating clone...")

    try:
        # Create the clone directly
        bot_token = session['bot_token']
        bot_info = session['bot_info']

        # Create clone in database
        from bot.database.clone_db import create_clone, get_user_clone_by_bot_id
        from bot.database.subscription_db import create_subscription
        from datetime import datetime, timedelta

        clone_data = {
            '_id': str(bot_info['id']),
            'admin_id': user_id,
            'username': bot_info['username'],
            'bot_token': bot_token,
            'status': 'active',
            'created_at': datetime.now()
        }

        subscription_data = {
            '_id': str(bot_info['id']),
            'bot_id': str(bot_info['id']),
            'user_id': user_id,
            'tier': plan['name'],
            'price': plan['price'],
            'duration_days': plan['duration_days'],
            'status': 'active',
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(days=plan['duration_days']),
            'payment_verified': True
        }

        # Save to database
        await create_clone(clone_data)
        await create_subscription(subscription_data)

        # Start the clone
        success, message = await clone_manager.start_clone(str(bot_info['id']))

        if success:
            # Clear session
            await session_manager.clear_session(user_id)

            await query.edit_message_text(
                f"🎉 **Clone Created Successfully!**\n\n"
                f"🤖 **Bot:** @{bot_info['username']}\n"
                f"💰 **Plan:** {plan['name']}\n"
                f"📅 **Expires:** {subscription_data['expires_at'].strftime('%Y-%m-%d')}\n"
                f"📊 **Status:** Active\n\n"
                f"Your clone is now live and ready to use!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{bot_info['username']}")],
                    [InlineKeyboardButton("⚙️ Manage Clone", callback_data="manage_my_clone")]
                ])
            )
        else:
            await query.edit_message_text(f"❌ Clone created but failed to start: {message}")

    except Exception as e:
        await query.edit_message_text(f"❌ Error creating clone: {str(e)}")

@Client.on_callback_query(filters.regex("^cancel_creation$"))
async def cancel_creation_callback(client, query):
    """Cancel clone creation"""
    await query.answer()
    user_id = query.from_user.id

    from bot.utils.session_manager import SessionManager
    session_manager = SessionManager()
    await session_manager.clear_session(user_id)

    await query.edit_message_text(
        "❌ **Clone creation cancelled.**\n\n"
        "You can start again anytime with `/createclone`"
    )

# Example database helper functions (replace with actual implementation)
async def get_all_clones_from_db():
    """Placeholder: Fetch all active clones from the database."""
    print("Fetching all clones from DB (placeholder)...")
    # Replace with actual database query
    return []

async def get_clone_by_id_from_db(clone_id: int):
    """Placeholder: Fetch a specific clone by its ID from the database."""
    print(f"Fetching clone {clone_id} from DB (placeholder)...")
    # Replace with actual database query
    return None

async def stop_clone_in_db(clone_id: int):
    """Placeholder: Update clone status to stopped in the database."""
    print(f"Stopping clone {clone_id} in DB (placeholder)...")
    # Replace with actual database update
    pass

async def start_clone_in_db(clone_id: int):
    """Placeholder: Update clone status to running in the database."""
    print(f"Starting clone {clone_id} in DB (placeholder)...")
    # Replace with actual database update
    pass