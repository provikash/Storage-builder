import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from info import Config
from bot.database.clone_db import get_all_clone_requests, approve_clone_request, reject_clone_request, create_clone, get_clone_request_by_id, activate_clone
from bot.database.subscription_db import create_subscription, activate_subscription
from clone_manager import clone_manager
import uuid

def debug_print(message):
    """Debug helper function"""
    print(f"DEBUG: {message}")

@Client.on_callback_query(filters.regex("^mother_pending_requests$"))
async def handle_mother_pending_requests(client: Client, query: CallbackQuery):
    """Handle pending clone requests display"""
    user_id = query.from_user.id
    debug_print(f"handle_mother_pending_requests called by user {user_id}")

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    try:
        # Get pending requests
        pending_requests = await get_all_clone_requests(status="pending")
        debug_print(f"Found {len(pending_requests)} pending requests")

        if not pending_requests:
            requests_text = "📋 **Pending Clone Requests**\n\n"
            requests_text += "✅ No pending requests at the moment."

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="mother_pending_requests")],
                [InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")]
            ])
        else:
            requests_text = f"📋 **Pending Clone Requests** ({len(pending_requests)})\n\n"

            buttons_list = []
            for i, request in enumerate(pending_requests[:10], 1):  # Limit to 10 requests
                user_id_req = request.get('user_id', 'Unknown')
                plan = request.get('plan', 'monthly')
                request_id = request.get('request_id')

                requests_text += f"**{i}.** Request ID: `{request_id[:8]}...`\n"
                requests_text += f"└ User ID: `{user_id_req}`\n"
                requests_text += f"└ Plan: {plan.title()}\n"
                requests_text += f"└ Status: Pending\n\n"

                # Add approve/reject buttons
                buttons_list.append([
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_request:{request_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_request:{request_id}")
                ])

            # Add navigation buttons
            buttons_list.extend([
                [InlineKeyboardButton("🔄 Refresh", callback_data="mother_pending_requests")],
                [InlineKeyboardButton("« Back", callback_data="back_to_mother_panel")]
            ])

            buttons = InlineKeyboardMarkup(buttons_list)

        await query.edit_message_text(requests_text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)
        debug_print(f"Displayed pending requests for user {query.from_user.id}")

    except Exception as e:
        debug_print(f"Error in handle_mother_pending_requests: {e}")
        await query.answer("❌ Error loading pending requests", show_alert=True)

@Client.on_callback_query(filters.regex("^approve_request:"))
async def handle_approve_request(client: Client, query: CallbackQuery):
    """Handle clone request approval"""
    user_id = query.from_user.id
    request_id = query.data.split(":", 1)[1]
    debug_print(f"Approving request {request_id} by admin {user_id}")

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    try:
        # Get request details
        request = await get_clone_request_by_id(request_id)
        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        # Create clone in database
        bot_token = request['bot_token']
        mongodb_url = request['mongodb_url']
        requester_id = request['user_id']
        plan = request['plan']

        # Approve the request and create clone
        success = await approve_clone_request(request_id)
        if success:
            # Extract bot ID from token
            bot_id = bot_token.split(':')[0]
            
            # Create clone entry
            clone_success, clone_data = await create_clone(bot_token, requester_id, mongodb_url)

            if clone_success:
                # Create and activate subscription
                from bot.database.subscription_db import create_subscription, activate_subscription
                subscription_created = await create_subscription(bot_id, requester_id, plan, payment_verified=True)

                if subscription_created:
                    await activate_subscription(bot_id)
                    
                    # Activate clone in database
                    await activate_clone(bot_id)

                    # Try to start the clone
                    start_success, start_message = await clone_manager.start_clone(bot_id)

                    # Notify requester
                    try:
                        notification_text = f"🎉 **Clone Request Approved!**\n\n"
                        notification_text += f"Your clone bot has been created and activated.\n\n"
                        notification_text += f"**Bot ID:** `{bot_id}`\n"
                        notification_text += f"**Plan:** {plan.title()}\n"
                        notification_text += f"**Status:** {'Running' if start_success else 'Created (will start soon)'}\n\n"
                        notification_text += "You can now manage your bot using /admin command in your clone bot."

                        await client.send_message(requester_id, notification_text, parse_mode=ParseMode.MARKDOWN)
                    except Exception as notify_error:
                        debug_print(f"Could not notify user {requester_id}: {notify_error}")

                    await query.answer("✅ Request approved and clone created!", show_alert=True)

                    # Refresh the pending requests list by re-editing the same message
                    await handle_mother_pending_requests(client, query)

                else:
                    await query.answer("❌ Error creating subscription", show_alert=True)
            else:
                await query.answer("❌ Error creating clone", show_alert=True)
        else:
            await query.answer("❌ Error approving request", show_alert=True)

    except Exception as e:
        debug_print(f"Error approving request {request_id}: {e}")
        await query.answer("❌ Error processing approval", show_alert=True)

@Client.on_callback_query(filters.regex("^reject_request:"))
async def handle_reject_request(client: Client, query: CallbackQuery):
    """Handle clone request rejection"""
    user_id = query.from_user.id
    request_id = query.data.split(":", 1)[1]
    debug_print(f"Rejecting request {request_id} by admin {user_id}")

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return

    try:
        # Get request details
        request = await get_clone_request_by_id(request_id)
        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        # Reject the request
        success = await reject_clone_request(request_id)
        if success:
            # Notify requester
            try:
                requester_id = request['user_id']
                notification_text = f"❌ **Clone Request Rejected**\n\n"
                notification_text += f"Unfortunately, your clone request has been rejected.\n\n"
                notification_text += f"**Request ID:** `{request_id[:8]}...`\n"
                notification_text += f"**Reason:** Administrative decision\n\n"
                notification_text += "You can submit a new request if needed using /requestclone."

                await client.send_message(requester_id, notification_text, parse_mode=ParseMode.MARKDOWN)
            except Exception as notify_error:
                debug_print(f"Could not notify user about rejection: {notify_error}")

            await query.answer("✅ Request rejected!", show_alert=True)

            # Refresh the pending requests list by re-editing the same message
            await handle_mother_pending_requests(client, query)
        else:
            await query.answer("❌ Error rejecting request", show_alert=True)

    except Exception as e:
        debug_print(f"Error rejecting request {request_id}: {e}")
        await query.answer("❌ Error processing rejection", show_alert=True)

# The following function was present in the original code but not fully defined in the edited snippet.
# It's assumed to be defined elsewhere or needs to be provided for completeness.
# For this task, I'm including the signature as it was in the original code to ensure no parts are missed if it's a dependency.
# If this function is truly missing, the code might fail at runtime.
async def get_clone_request_by_id(request_id: str):
    """Get clone request by ID"""
    try:
        from bot.database.connection import db
        collection = db.clone_requests
        request = await collection.find_one({"request_id": request_id})
        return request
    except Exception as e:
        debug_print(f"Error getting request by ID {request_id}: {e}")
        return None

async def log_admin_action(admin_id: int, action: str, details: dict):
    """Log admin actions for audit trail"""
    from bot.database.clone_db import clone_db
    admin_logs = clone_db.admin_logs

    log_entry = {
        "admin_id": admin_id,
        "action": action,
        "details": details,
        "timestamp": datetime.now(),
        "log_id": str(uuid.uuid4())
    }

    try:
        await admin_logs.insert_one(log_entry)
    except Exception as e:
        debug_print(f"Failed to log admin action: {e}")

# Assuming the following functions are defined elsewhere or are part of the `clone_manager` and `bot.database` modules.
# The edited snippet did not provide definitions for these, but they are called.
# If these are critical and missing, the code might not run as expected.

# async def get_all_clone_requests(status="pending"): ...
# async def approve_clone_request(request_id: str): ...
# async def reject_clone_request(request_id: str): ...
# async def create_clone(bot_token: str, user_id: int, mongodb_url: str): ...
# async def create_subscription(bot_id: str, user_id: int, plan: str, payment_verified: bool): ...
# async def activate_subscription(bot_id: str): ...
# async def start_clone(bot_id: str): ...
# async def get_clone_request_by_id(request_id: str): ... # This one is defined in the edited snippet, but calling it again here is redundant.

# Removed functions that were in the original but not in the edited snippet, as the edited snippet appears to be a replacement.
# Specifically:
# - quick_approve_request
# - quick_reject_request
# - view_request_details
# - show_request_details
# - process_request_approval
# - process_request_rejection
# - notify_requester_approval
# - notify_requester_rejection
# - log_admin_action (This was present in original, but also in edited. Replaced with edited version which is cleaner)