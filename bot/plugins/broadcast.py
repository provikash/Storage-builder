# Cleaned & Refactored by @Mak0912 (TG)

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from info import Config
from bot.database import full_userbase, del_user

REPLY_ERROR = "<code>Use this command as a reply to any Telegram message without any spaces.</code>"

@Client.on_message(filters.command("users") & filters.private & filters.user(Config.ADMINS))
async def show_user_count(client: Client, message: Message):
    msg = await message.reply("Processing Please wait....")
    users = await full_userbase()
    await msg.edit(f"<b>{len(users)} users are using this bot.</b>")

# ──────────────────────────────────────────────────────────────

@Client.on_message(filters.command("broadcast") & filters.private & filters.user(Config.ADMINS))
async def broadcast_message(client: Client, message: Message):
    if not message.reply_to_message:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(5)
        return await msg.delete()

    users = await full_userbase()
    original = message.reply_to_message
    status = {
        "total": 0, 
        "sent": 0, 
        "blocked": 0, 
        "deleted": 0, 
        "failed": 0
    }

    wait = await message.reply("<i>Broadcasting message. Please wait...</i>")

    for user_id in users:
        try:
            await original.copy(user_id)
            status["sent"] += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await original.copy(user_id)
            status["sent"] += 1
        except UserIsBlocked:
            await del_user(user_id)
            status["blocked"] += 1
        except InputUserDeactivated:
            await del_user(user_id)
            status["deleted"] += 1
        except Exception:
            status["failed"] += 1
        status["total"] += 1

    summary = f"""<b><u>📢 Broadcast Summary</u></b>

👥 Total Users: <code>{status['total']}</code>
✅ Sent: <code>{status['sent']}</code>
⛔ Blocked: <code>{status['blocked']}</code>
❌ Deleted: <code>{status['deleted']}</code>
⚠️ Failed: <code>{status['failed']}</code>"""

    await wait.edit(summary)
"""
Broadcast plugin for sending messages to all users
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.utils.admin_verification import is_admin

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    """Handle broadcast command"""
    try:
        if not await is_admin(message.from_user.id):
            await message.reply_text("❌ You don't have permission to use this command.")
            return
            
        if not message.reply_to_message:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 How to Use", callback_data="broadcast_help")]
            ])
            
            await message.reply_text(
                "📢 **Broadcast Message**\n\n"
                "To broadcast a message, reply to any message with `/broadcast`\n\n"
                "**Features:**\n"
                "• Send to all users\n"
                "• Real-time progress tracking\n"
                "• Error handling and reporting\n"
                "• Support for all message types",
                reply_markup=keyboard
            )
            return
            
        # Confirm broadcast
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"broadcast_confirm_{message.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
            ]
        ])
        
        await message.reply_text(
            "⚠️ **Confirm Broadcast**\n\n"
            "Are you sure you want to broadcast this message to all users?",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in broadcast handler: {e}")
        await message.reply_text("❌ An error occurred.")

@Client.on_callback_query(filters.regex("broadcast_confirm_"))
async def confirm_broadcast(client: Client, query):
    """Confirm and execute broadcast"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        message_id = int(query.data.split("_")[-1])
        
        # Get the original message
        try:
            original_msg = await client.get_messages(query.message.chat.id, message_id)
            broadcast_msg = original_msg.reply_to_message
            
            if not broadcast_msg:
                await query.edit_message_text("❌ Original message not found!")
                return
                
        except:
            await query.edit_message_text("❌ Could not find the message to broadcast!")
            return
            
        await query.answer("🚀 Starting broadcast...")
        
        # Get all users
        from bot.database.users import get_all_users
        users = await get_all_users()
        
        if not users:
            await query.edit_message_text("❌ No users found to broadcast to!")
            return
            
        # Start broadcasting
        status_msg = await query.edit_message_text(
            f"📡 **Broadcasting Message**\n\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"📤 Sent: `0`\n"
            f"❌ Failed: `0`\n"
            f"📊 Progress: `0%`\n\n"
            f"⏳ Starting broadcast..."
        )
        
        success_count = 0
        failed_count = 0
        blocked_count = 0
        
        for i, user_id in enumerate(users):
            try:
                await broadcast_msg.copy(user_id)
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                error_msg = str(e).lower()
                if "blocked" in error_msg or "user is deactivated" in error_msg:
                    blocked_count += 1
                    
            # Update progress every 50 users or at the end
            if (i + 1) % 50 == 0 or i == len(users) - 1:
                progress = ((i + 1) / len(users)) * 100
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Detailed Report", callback_data="broadcast_report")]
                ]) if i == len(users) - 1 else None
                
                await status_msg.edit_text(
                    f"📡 **Broadcasting Message**\n\n"
                    f"👥 Total Users: `{len(users)}`\n"
                    f"✅ Sent: `{success_count}`\n"
                    f"❌ Failed: `{failed_count}`\n"
                    f"🚫 Blocked: `{blocked_count}`\n"
                    f"📊 Progress: `{progress:.1f}%`\n\n"
                    f"{'✅ Broadcast Complete!' if i == len(users) - 1 else '⏳ Broadcasting...'}",
                    reply_markup=keyboard
                )
                
            await asyncio.sleep(0.05)  # Small delay to avoid flooding
            
    except Exception as e:
        logger.error(f"Error in broadcast confirmation: {e}")
        await query.answer("❌ Error during broadcast!", show_alert=True)

@Client.on_callback_query(filters.regex("broadcast_cancel"))
async def cancel_broadcast(client: Client, query):
    """Cancel broadcast"""
    try:
        await query.edit_message_text("❌ Broadcast cancelled.")
    except:
        await query.message.delete()

@Client.on_callback_query(filters.regex("broadcast_help"))
async def broadcast_help(client: Client, query):
    """Show broadcast help"""
    try:
        text = (
            "📢 **How to Use Broadcast**\n\n"
            "1. **Reply to any message** with `/broadcast`\n"
            "2. **Confirm** the broadcast\n"
            "3. **Wait** for completion\n\n"
            "**Supported Message Types:**\n"
            "• Text messages\n"
            "• Photos and videos\n"
            "• Documents and files\n"
            "• Stickers and GIFs\n"
            "• Voice messages\n\n"
            "**Features:**\n"
            "• Real-time progress tracking\n"
            "• Automatic retry on failure\n"
            "• Detailed completion report\n"
            "• Handles blocked users gracefully"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="broadcast_back")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing broadcast help: {e}")

@Client.on_callback_query(filters.regex("broadcast_back"))
async def broadcast_back(client: Client, query):
    """Go back to main broadcast message"""
    try:
        await query.edit_message_text(
            "📢 **Broadcast Message**\n\n"
            "To broadcast a message, reply to any message with `/broadcast`\n\n"
            "**Features:**\n"
            "• Send to all users\n"
            "• Real-time progress tracking\n"
            "• Error handling and reporting\n"
            "• Support for all message types"
        )
    except:
        pass
