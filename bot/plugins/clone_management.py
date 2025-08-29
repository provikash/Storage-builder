
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER
from bot.database.clone_db import get_user_clones, get_clone, update_clone_status
from bot.database.subscription_db import get_subscription
from bot.database.balance_db import get_user_balance
from clone_manager import clone_manager

logger = LOGGER(__name__)

async def manage_user_clone(client: Client, query: CallbackQuery):
    """Manage user's clone bot"""
    user_id = query.from_user.id
    
    try:
        # Get user's clones
        user_clones = await get_user_clones(user_id)
        
        if not user_clones:
            text = "🤖 **My Clone Bots**\n\n"
            text += "❌ You don't have any clone bots yet.\n\n"
            text += "💡 **Get Started:**\n"
            text += "• Create your first clone bot\n"
            text += "• Choose from various subscription plans\n"
            text += "• Start sharing files instantly!\n\n"
            text += "🚀 Ready to create your clone bot?"
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Create Clone Bot", callback_data="start_clone_creation")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(text, reply_markup=buttons)
            return
        
        # Show user's clones
        text = "🤖 **My Clone Bots**\n\n"
        buttons = []
        
        for clone in user_clones:
            clone_id = clone['_id']
            bot_username = clone.get('username', 'Unknown')
            status = clone.get('status', 'inactive')
            
            # Get subscription info
            subscription = await get_subscription(clone_id)
            
            if subscription:
                days_left = (subscription['expiry_date'] - datetime.now()).days
                sub_status = "🟢 Active" if subscription['status'] == 'active' else "🔴 Expired"
                
                text += f"🤖 **@{bot_username}**\n"
                text += f"📊 Status: {sub_status}\n"
                text += f"⏰ Days Left: {days_left}\n"
                text += f"💰 Plan: {subscription.get('tier', 'Unknown')}\n\n"
                
                # Check if clone is running
                running_clones = clone_manager.get_running_clones()
                is_running = clone_id in running_clones
                
                action_text = "🔴 Start" if not is_running else "🟢 Running"
                buttons.append([
                    InlineKeyboardButton(f"⚙️ Manage @{bot_username}", callback_data=f"manage_clone:{clone_id}"),
                    InlineKeyboardButton(action_text, callback_data=f"toggle_clone:{clone_id}")
                ])
            else:
                text += f"🤖 **@{bot_username}**\n"
                text += f"📊 Status: ❌ No Subscription\n\n"
                
                buttons.append([
                    InlineKeyboardButton(f"💳 Activate @{bot_username}", callback_data=f"activate_clone:{clone_id}")
                ])
        
        buttons.append([InlineKeyboardButton("🚀 Create New Clone", callback_data="start_clone_creation")])
        buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        logger.error(f"Error in manage_user_clone: {e}")
        await query.answer("❌ Error loading clone management. Please try again.", show_alert=True)

async def my_clones_callback(client: Client, query: CallbackQuery):
    """Handle my clones callback - alias for manage_user_clone"""
    await manage_user_clone(client, query)

@Client.on_callback_query(filters.regex("^manage_clone:"))
async def handle_manage_specific_clone(client: Client, query: CallbackQuery):
    """Handle management of specific clone"""
    user_id = query.from_user.id
    clone_id = query.data.split(":")[1]
    
    try:
        # Verify ownership
        clone = await get_clone(clone_id)
        if not clone or clone['admin_id'] != user_id:
            await query.answer("❌ Clone not found or access denied!", show_alert=True)
            return
        
        subscription = await get_subscription(clone_id)
        running_clones = clone_manager.get_running_clones()
        is_running = clone_id in running_clones
        
        text = f"⚙️ **Managing @{clone.get('username', 'Unknown')}**\n\n"
        text += f"🆔 **Bot ID:** `{clone_id}`\n"
        text += f"🔄 **Running:** {'✅ Yes' if is_running else '❌ No'}\n"
        
        if subscription:
            days_left = (subscription['expiry_date'] - datetime.now()).days
            text += f"💰 **Plan:** {subscription.get('tier', 'Unknown')}\n"
            text += f"⏰ **Days Left:** {days_left}\n"
            text += f"📊 **Status:** {subscription['status']}\n"
        else:
            text += f"💰 **Plan:** ❌ No Active Subscription\n"
        
        buttons = []
        
        if subscription and subscription['status'] == 'active':
            if is_running:
                buttons.append([InlineKeyboardButton("🛑 Stop Bot", callback_data=f"stop_clone:{clone_id}")])
            else:
                buttons.append([InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_clone:{clone_id}")])
            
            buttons.append([InlineKeyboardButton("🎛️ Clone Admin Panel", url=f"https://t.me/{clone.get('username', 'unknown')}")])
            buttons.append([InlineKeyboardButton("💳 Extend Subscription", callback_data=f"extend_subscription:{clone_id}")])
        else:
            buttons.append([InlineKeyboardButton("💳 Activate Subscription", callback_data=f"activate_clone:{clone_id}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back to My Clones", callback_data="manage_my_clone")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        logger.error(f"Error managing specific clone: {e}")
        await query.answer("❌ Error loading clone details. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^(start_clone|stop_clone|toggle_clone):"))
async def handle_clone_actions(client: Client, query: CallbackQuery):
    """Handle clone start/stop actions"""
    user_id = query.from_user.id
    action, clone_id = query.data.split(":")
    
    try:
        # Verify ownership
        clone = await get_clone(clone_id)
        if not clone or clone['admin_id'] != user_id:
            await query.answer("❌ Access denied!", show_alert=True)
            return
        
        # Check subscription
        subscription = await get_subscription(clone_id)
        if not subscription or subscription['status'] != 'active':
            await query.answer("❌ No active subscription found!", show_alert=True)
            return
        
        if action == "start_clone":
            success, message = await clone_manager.start_clone(clone_id)
            await query.answer(f"{'✅' if success else '❌'} {message}", show_alert=True)
            
        elif action == "stop_clone":
            success, message = await clone_manager.stop_clone(clone_id)
            await query.answer(f"{'✅' if success else '❌'} {message}", show_alert=True)
            
        elif action == "toggle_clone":
            running_clones = clone_manager.get_running_clones()
            is_running = clone_id in running_clones
            
            if is_running:
                success, message = await clone_manager.stop_clone(clone_id)
            else:
                success, message = await clone_manager.start_clone(clone_id)
            
            await query.answer(f"{'✅' if success else '❌'} {message}", show_alert=True)
        
        # Refresh the management page
        await handle_manage_specific_clone(client, query)
        
    except Exception as e:
        logger.error(f"Error in clone action {action}: {e}")
        await query.answer("❌ Error performing action. Please try again.", show_alert=True)

@Client.on_message(filters.command("myclones") & filters.private)
async def myclones_command(client: Client, message: Message):
    """Handle /myclones command"""
    try:
        # Create fake callback query for reuse
        fake_query = type('obj', (object,), {
            'from_user': message.from_user,
            'message': message,
            'answer': lambda text="", show_alert=False: None,
            'edit_message_text': message.reply_text
        })()
        
        await manage_user_clone(client, fake_query)
        
    except Exception as e:
        logger.error(f"Error in myclones command: {e}")
        await message.reply_text("❌ Error loading your clones. Please try /start")

@Client.on_message(filters.command("clonestatus") & filters.private)
async def clonestatus_command(client: Client, message: Message):
    """Handle /clonestatus command"""
    user_id = message.from_user.id
    
    try:
        user_clones = await get_user_clones(user_id)
        
        if not user_clones:
            await message.reply_text(
                "🤖 **Clone Status**\n\n"
                "❌ You don't have any clone bots.\n\n"
                "Use /createclone to create your first clone bot!"
            )
            return
        
        text = "🤖 **Clone Status Report**\n\n"
        running_clones = clone_manager.get_running_clones()
        
        for clone in user_clones:
            clone_id = clone['_id']
            bot_username = clone.get('username', 'Unknown')
            is_running = clone_id in running_clones
            
            subscription = await get_subscription(clone_id)
            
            text += f"🤖 **@{bot_username}**\n"
            text += f"🔄 Running: {'✅ Yes' if is_running else '❌ No'}\n"
            
            if subscription:
                days_left = (subscription['expiry_date'] - datetime.now()).days
                text += f"⏰ Days Left: {days_left}\n"
                text += f"📊 Status: {subscription['status']}\n"
            else:
                text += f"📊 Status: ❌ No Subscription\n"
            
            text += "\n"
        
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error in clonestatus command: {e}")
        await message.reply_text("❌ Error loading clone status. Please try /start")
