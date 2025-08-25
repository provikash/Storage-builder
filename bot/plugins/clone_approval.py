import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.logging import LOGGER
from clone_manager import clone_manager

logger = LOGGER(__name__)

def debug_print(message):
    """Debug helper function"""
    print(f"DEBUG: {message}")
    logger.info(f"APPROVAL_DEBUG: {message}")

async def approve_clone_request(client: Client, query: CallbackQuery, request_id: str):
    """Approve a clone request"""
    user_id = query.from_user.id
    debug_print(f"Approving request {request_id} by admin {user_id}")

    try:
        # Get request details
        request = await get_clone_request_by_id(request_id)
        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        if request['status'] != 'pending':
            await query.answer("❌ Request already processed!", show_alert=True)
            return

        # Extract details from request
        bot_token = request['bot_token']
        mongodb_url = request['mongodb_url']
        requester_id = request['user_id']
        plan_details = request.get('plan_details', {})
        bot_username = request.get('bot_username', 'Unknown')

        # Extract bot ID from token
        bot_id = bot_token.split(':')[0]

        debug_print(f"Creating clone for bot ID: {bot_id}, admin: {requester_id}")

        # Create clone entry
        clone_data = {
            "_id": bot_id,
            "bot_token": bot_token,
            "username": bot_username,
            "admin_id": requester_id,
            "mongodb_url": mongodb_url,
            "status": "active",
            "created_at": datetime.now(),
            "approved_by": user_id,
            "approved_at": datetime.now()
        }

        clone_success = await create_clone(clone_data)

        if clone_success:
            debug_print(f"Clone created successfully for bot {bot_id}")

            # Create subscription
            plan_name = plan_details.get('name', 'basic').lower()
            # Map plan names to valid plan keys
            plan_mapping = {
                'monthly plan': 'monthly',
                'basic': 'basic',
                'premium': 'premium',
                'unlimited': 'unlimited',
                '3 months plan': 'quarterly',
                '6 months plan': 'semi_annual',
                'yearly plan': 'yearly'
            }
            
            plan_key = plan_mapping.get(plan_name, 'basic')
            debug_print(f"Creating subscription with plan_key: {plan_key}")
            
            sub_success = await create_subscription(
                bot_id=bot_id,
                user_id=requester_id,
                plan=plan_key,
                payment_verified=True
            )

            if sub_success:
                debug_print(f"Subscription created for bot {bot_id}")

                # Update request status
                await update_clone_request_status(request_id, "approved", user_id)

                # Start the clone bot
                try:
                    await clone_manager.start_clone(bot_id)
                    debug_print(f"Clone bot {bot_id} started successfully")
                except Exception as start_error:
                    debug_print(f"Error starting clone bot {bot_id}: {start_error}")

                # Notify the requester
                try:
                    await client.send_message(
                        requester_id,
                        f"🎉 **Clone Request Approved!**\n\n"
                        f"🤖 **Your Bot:** @{bot_username}\n"
                        f"💰 **Plan:** {plan_details.get('name', 'Monthly')}\n"
                        f"📅 **Expires:** {datetime.now().strftime('%Y-%m-%d')}\n\n" # Assuming expiry calculation happens in create_subscription or is not needed here for notification
                        f"Your bot is now active and ready to use!"
                    )
                    debug_print(f"Notification sent to user {requester_id}")
                except Exception as notify_error:
                    debug_print(f"Error notifying user {requester_id}: {notify_error}")

                await query.answer("✅ Request approved and clone created!", show_alert=True)

                # Refresh the pending requests panel
                from bot.plugins.admin_panel import handle_mother_pending_requests
                await handle_mother_pending_requests(client, query)

            else:
                await query.answer("❌ Error creating subscription", show_alert=True)
                debug_print(f"Failed to create subscription for bot {bot_id}")
        else:
            await query.answer("❌ Error creating clone", show_alert=True)
            debug_print(f"Failed to create clone for bot {bot_id}")

    except Exception as e:
        debug_print(f"Error approving request {request_id}: {e}")
        await query.answer("❌ Error processing approval", show_alert=True)

async def reject_clone_request(client: Client, query: CallbackQuery, request_id: str):
    """Reject a clone request"""
    user_id = query.from_user.id
    debug_print(f"Rejecting request {request_id} by admin {user_id}")

    try:
        # Get request details
        request = await get_clone_request_by_id(request_id)
        if not request:
            await query.answer("❌ Request not found!", show_alert=True)
            return

        if request['status'] != 'pending':
            await query.answer("❌ Request already processed!", show_alert=True)
            return

        # Update request status
        await update_clone_request_status(request_id, "rejected", user_id)

        # Notify the requester
        try:
            await client.send_message(
                request['user_id'],
                f"❌ **Clone Request Rejected**\n\n"
                f"🆔 **Request ID:** {request_id[:8]}...\n"
                f"📝 **Reason:** Request rejected by administrator\n\n"
                f"You can submit a new request with `/requestclone` if needed."
            )
            debug_print(f"Rejection notification sent to user {request['user_id']}")
        except Exception as notify_error:
            debug_print(f"Error notifying user {request['user_id']}: {notify_error}")

        await query.answer("✅ Request rejected successfully!", show_alert=True)

        # Refresh the pending requests panel
        from bot.plugins.admin_panel import handle_mother_pending_requests
        await handle_mother_pending_requests(client, query)

    except Exception as e:
        debug_print(f"Error rejecting request {request_id}: {e}")
        await query.answer("❌ Error processing rejection", show_alert=True)

# Add the missing database functions
async def get_clone_request_by_id(request_id: str):
    """Get clone request by ID"""
    try:
        from bot.database.clone_db import get_clone_request_by_id as db_get_clone_request
        return await db_get_clone_request(request_id)
    except Exception as e:
        debug_print(f"Error getting clone request {request_id}: {e}")
        return None

async def update_clone_request_status(request_id: str, status: str, admin_id: int = None):
    """Update clone request status"""
    try:
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
        debug_print(f"Updated request {request_id} status to {status}")
        return True
    except Exception as e:
        debug_print(f"Error updating request {request_id} status: {e}")
        return False