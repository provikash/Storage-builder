import asyncio
import os
import subprocess
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database import add_user, present_user

# Store active clones
active_clones = {}

@Client.on_message(filters.command("createclone") & filters.private)
async def create_clone_handler(client: Client, message: Message):
    """Handle clone creation request"""
    user_id = message.from_user.id

    # Check if user is admin (you can modify this logic)
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ Only administrators can create bot clones.")

    await message.reply_text(
        "🤖 **Create Your Bot Clone**\n\n"
        "Please provide your bot token from @BotFather in the format:\n"
        "`/settoken YOUR_BOT_TOKEN`\n\n"
        "Example: `/settoken 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`"
    )

@Client.on_message(filters.command("settoken") & filters.private)
async def set_bot_token(client: Client, message: Message):
    """Set bot token for clone creation"""
    user_id = message.from_user.id

    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ Only administrators can create bot clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide a bot token.\n\nUsage: `/settoken YOUR_BOT_TOKEN`")

    bot_token = message.command[1]

    # Validate bot token format
    if not validate_bot_token(bot_token):
        return await message.reply_text("❌ Invalid bot token format. Please get a valid token from @BotFather.")

    # Try to create the clone
    processing_msg = await message.reply_text("🔄 Creating your bot clone... Please wait.")

    try:
        success, clone_info = await create_bot_clone(bot_token, user_id)

        if success:
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Start Your Bot", url=f"https://t.me/{clone_info['username']}")],
                [InlineKeyboardButton("📋 Manage Clones", callback_data="manage_clones")]
            ])

            await processing_msg.edit_text(
                f"🎉 **Clone Created Successfully!**\n\n"
                f"🤖 **Bot Username:** @{clone_info['username']}\n"
                f"🆔 **Bot ID:** {clone_info['bot_id']}\n"
                f"📊 **Status:** Running\n\n"
                f"Your bot is now live and ready to use!",
                reply_markup=buttons
            )

            # Store clone info
            active_clones[user_id] = active_clones.get(user_id, [])
            active_clones[user_id].append(clone_info)

        else:
            await processing_msg.edit_text(
                f"❌ **Failed to create clone:**\n{clone_info}"
            )

    except Exception as e:
        await processing_msg.edit_text(
            f"❌ **Error creating clone:**\n{str(e)}"
        )

@Client.on_message(filters.command("listclones") & filters.private)
async def list_clones(client: Client, message: Message):
    """List all active clones for the user"""
    user_id = message.from_user.id

    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ Only administrators can manage clones.")

    user_clones = active_clones.get(user_id, [])

    if not user_clones:
        return await message.reply_text("📝 You don't have any active bot clones yet.\n\nUse `/createclone` to create your first clone!")

    clone_list = "🤖 **Your Active Bot Clones:**\n\n"

    for i, clone in enumerate(user_clones, 1):
        status = "🟢 Running" if clone.get('running', True) else "🔴 Stopped"
        clone_list += f"**{i}.** @{clone['username']}\n"
        clone_list += f"   📊 Status: {status}\n"
        clone_list += f"   🆔 ID: {clone['bot_id']}\n\n"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Create New Clone", callback_data="create_new_clone")],
        [InlineKeyboardButton("🛠️ Manage Clones", callback_data="manage_clones")]
    ])

    await message.reply_text(clone_list, reply_markup=buttons)

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
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        logger.error(f"Error in manage_user_clone: {e}")
        await query.edit_message_text(
            "❌ **Error Loading Clones**\n\n"
            "There was an error loading your clone information.\n"
            "Please try again or contact support.",
            reply_markup=InlineKeyboardMarkup([
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

@Client.on_callback_query(filters.regex("^create_new_clone$"))
async def create_new_clone_callback(client, query):
    """Handle create new clone button"""
    await query.answer()
    await query.edit_message_text(
        "🤖 **Create Your Bot Clone**\n\n"
        "Please provide your bot token from @BotFather in the format:\n"
        "`/settoken YOUR_BOT_TOKEN`\n\n"
        "Example: `/settoken 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`"
    )

@Client.on_callback_query(filters.regex("^manage_clones$"))
async def manage_clones_callback(client, query):
    """Handle manage clones button"""
    await query.answer()
    await query.edit_message_text(
        "🛠️ **Clone Management**\n\n"
        "Available commands:\n"
        "• `/listclones` - View all your clones\n"
        "• `/createclone` - Create a new clone\n"
        "• `/stopclone <bot_id>` - Stop a specific clone\n"
        "• `/startclone <bot_id>` - Start a stopped clone"
    )

# --- Missing Handlers and Database Functions ---

# Example handler for mother_create_clone
@Client.on_callback_query(filters.regex("^mother_create_clone$"))
async def mother_create_clone_handler(client: Client, query):
    await query.answer("Processing create clone request...")
    # Implement logic to create a new bot clone
    await query.edit_message_text("Bot clone creation logic goes here.")

# Example handler for mother_manage_clones
@Client.on_callback_query(filters.regex("^mother_manage_clones$"))
async def mother_manage_clones_handler(client: Client, query):
    await query.answer("Fetching clone management options...")
    # Implement logic to display clone management options
    await query.edit_message_text("Clone management options go here.")

# Example handler for mother_subscriptions
@Client.on_callback_query(filters.regex("^mother_subscriptions$"))
async def mother_subscriptions_handler(client: Client, query):
    await query.answer("Fetching subscription details...")
    # Implement logic to display subscription information
    await query.edit_message_text("Subscription details go here.")

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