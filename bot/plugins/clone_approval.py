
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from clone_manager import clone_manager
from bot.plugins.clone_request import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^quick_approve:"))
async def quick_approve_request(client: Client, query: CallbackQuery):
    """Quick approve clone request from notification"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    request_id = query.data.split(':')[1]
    await process_request_approval(client, query, request_id, quick=True)

@Client.on_callback_query(filters.regex("^quick_reject:"))
async def quick_reject_request(client: Client, query: CallbackQuery):
    """Quick reject clone request from notification"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    request_id = query.data.split(':')[1]
    await process_request_rejection(client, query, request_id, quick=True)

@Client.on_callback_query(filters.regex("^view_request:"))
async def view_request_details(client: Client, query: CallbackQuery):
    """View detailed request information"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    request_id = query.data.split(':')[1]
    request_data = await get_clone_request(request_id)
    
    if not request_data:
        return await query.answer("❌ Request not found!", show_alert=True)
    
    await show_request_details(client, query, request_data)

async def show_request_details(client: Client, query: CallbackQuery, request_data):
    """Show detailed request information to admin"""
    masked_token = f"{request_data['bot_token'][:8]}...{request_data['bot_token'][-4:]}"
    masked_db = f"{request_data['mongodb_url'][:25]}...{request_data['mongodb_url'][-15:]}"
    
    text = f"📋 **Clone Request Details**\n\n"
    text += f"**Request ID:** `{request_data['request_id']}`\n\n"
    
    text += f"**👤 Requester Information:**\n"
    text += f"• Name: {request_data['requester_info']['first_name']}"
    if request_data['requester_info']['last_name']:
        text += f" {request_data['requester_info']['last_name']}"
    text += "\n"
    if request_data['requester_info']['username']:
        text += f"• Username: @{request_data['requester_info']['username']}\n"
    text += f"• User ID: `{request_data['user_id']}`\n\n"
    
    text += f"**🤖 Bot Information:**\n"
    text += f"• Username: @{request_data['bot_username']}\n"
    text += f"• Bot ID: `{request_data['bot_id']}`\n"
    text += f"• Token: `{masked_token}`\n\n"
    
    text += f"**🗄️ Database:**\n"
    text += f"• URL: `{masked_db}`\n\n"
    
    text += f"**💰 Subscription:**\n"
    text += f"• Plan: {request_data['plan_details']['name']}\n"
    text += f"• Price: ${request_data['plan_details']['price']}\n"
    text += f"• Duration: {request_data['plan_details']['duration_days']} days\n\n"
    
    text += f"**📅 Timeline:**\n"
    text += f"• Submitted: {request_data['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n"
    text += f"• Status: {request_data['status'].title()}\n"
    
    if request_data.get('reviewed_at'):
        text += f"• Reviewed: {request_data['reviewed_at'].strftime('%Y-%m-%d %H:%M UTC')}\n"
        text += f"• Reviewed by: {request_data.get('reviewed_by', 'Unknown')}\n"
    
    buttons = []
    if request_data['status'] == 'pending':
        buttons.append([
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_request:{request_data['request_id']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_request:{request_data['request_id']}")
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back to Requests", callback_data="mother_pending_requests")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^approve_request:"))
async def approve_request_callback(client: Client, query: CallbackQuery):
    """Handle request approval"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    request_id = query.data.split(':')[1]
    await process_request_approval(client, query, request_id)

@Client.on_callback_query(filters.regex("^reject_request:"))
async def reject_request_callback(client: Client, query: CallbackQuery):
    """Handle request rejection"""
    if query.from_user.id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await query.answer("❌ Unauthorized access!", show_alert=True)
    
    request_id = query.data.split(':')[1]
    await process_request_rejection(client, query, request_id)

async def process_request_approval(client: Client, query: CallbackQuery, request_id: str, quick: bool = False):
    """Process clone request approval"""
    admin_id = query.from_user.id
    
    try:
        request_data = await get_clone_request(request_id)
        if not request_data:
            return await query.answer("❌ Request not found!", show_alert=True)
        
        if request_data['status'] != 'pending':
            return await query.answer("❌ Request already processed!", show_alert=True)
        
        # Create the clone
        processing_msg = "🔄 **Processing approval...**\n\nCreating clone bot..."
        if quick:
            await query.edit_message_text(processing_msg)
        else:
            await query.answer("🔄 Processing approval...", show_alert=True)
            await query.edit_message_text(processing_msg)
        
        # Create clone using clone manager
        success, result = await clone_manager.create_clone(
            request_data['bot_token'],
            request_data['user_id'],
            request_data['mongodb_url'],
            request_data['subscription_plan']
        )
        
        if success:
            # Update request status
            await update_clone_request_status(request_id, 'approved', admin_id)
            
            # Log the approval
            await log_admin_action(admin_id, 'approve_clone', {
                'request_id': request_id,
                'user_id': request_data['user_id'],
                'bot_username': request_data['bot_username']
            })
            
            # Notify requester
            await notify_requester_approval(client, request_data, result)
            
            success_text = f"✅ **Clone Request Approved!**\n\n"
            success_text += f"🤖 **Bot:** @{request_data['bot_username']}\n"
            success_text += f"👤 **User:** {request_data['user_id']}\n"
            success_text += f"💰 **Plan:** {request_data['plan_details']['name']}\n"
            success_text += f"📅 **Approved:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            success_text += f"The clone has been created and activated successfully!"
            
            buttons = []
            if not quick:
                buttons.append([InlineKeyboardButton("🔙 Back to Requests", callback_data="mother_pending_requests")])
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
            
        else:
            # Approval failed
            error_text = f"❌ **Approval Failed!**\n\n"
            error_text += f"Error: {result}\n\n"
            error_text += f"Please check the bot token and database URL, then try again."
            
            buttons = []
            if not quick:
                buttons.append([
                    InlineKeyboardButton("🔄 Retry", callback_data=f"approve_request:{request_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_request:{request_id}")
                ])
                buttons.append([InlineKeyboardButton("🔙 Back to Requests", callback_data="mother_pending_requests")])
            
            await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
            
    except Exception as e:
        logger.error(f"Error processing approval for {request_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error processing approval!**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or contact technical support."
        )

async def process_request_rejection(client: Client, query: CallbackQuery, request_id: str, quick: bool = False):
    """Process clone request rejection"""
    admin_id = query.from_user.id
    
    try:
        request_data = await get_clone_request(request_id)
        if not request_data:
            return await query.answer("❌ Request not found!", show_alert=True)
        
        if request_data['status'] != 'pending':
            return await query.answer("❌ Request already processed!", show_alert=True)
        
        # Update request status
        await update_clone_request_status(request_id, 'rejected', admin_id)
        
        # Log the rejection
        await log_admin_action(admin_id, 'reject_clone', {
            'request_id': request_id,
            'user_id': request_data['user_id'],
            'bot_username': request_data['bot_username']
        })
        
        # Notify requester
        await notify_requester_rejection(client, request_data)
        
        success_text = f"❌ **Clone Request Rejected**\n\n"
        success_text += f"🤖 **Bot:** @{request_data['bot_username']}\n"
        success_text += f"👤 **User:** {request_data['user_id']}\n"
        success_text += f"📅 **Rejected:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        success_text += f"The requester has been notified of the rejection."
        
        buttons = []
        if not quick:
            buttons.append([InlineKeyboardButton("🔙 Back to Requests", callback_data="mother_pending_requests")])
        
        await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
        
    except Exception as e:
        logger.error(f"Error processing rejection for {request_id}: {e}")
        await query.edit_message_text(
            f"❌ **Error processing rejection!**\n\n"
            f"Error: {str(e)}"
        )

async def notify_requester_approval(client: Client, request_data, clone_result):
    """Notify requester that their request was approved"""
    user_id = request_data['user_id']
    
    text = f"🎉 **Clone Request Approved!**\n\n"
    text += f"Congratulations! Your clone bot request has been approved.\n\n"
    text += f"**📋 Request Details:**\n"
    text += f"• Request ID: `{request_data['request_id'][:8]}...`\n"
    text += f"• Bot: @{request_data['bot_username']}\n"
    text += f"• Plan: {request_data['plan_details']['name']} (${request_data['plan_details']['price']})\n"
    text += f"• Duration: {request_data['plan_details']['duration_days']} days\n\n"
    text += f"**🚀 Next Steps:**\n"
    text += f"1. Your bot is now active and running\n"
    text += f"2. Use /admin in your bot to access the admin panel\n"
    text += f"3. Configure your bot settings as needed\n"
    text += f"4. Your subscription is valid until payment is verified\n\n"
    text += f"**📞 Support:** Contact us if you need any assistance!\n\n"
    text += f"Thank you for choosing our service! 🎉"
    
    try:
        await client.send_message(user_id, text)
    except Exception as e:
        logger.error(f"Failed to notify approved user {user_id}: {e}")

async def notify_requester_rejection(client: Client, request_data):
    """Notify requester that their request was rejected"""
    user_id = request_data['user_id']
    
    text = f"❌ **Clone Request Rejected**\n\n"
    text += f"We're sorry, but your clone bot request has been rejected after review.\n\n"
    text += f"**📋 Request Details:**\n"
    text += f"• Request ID: `{request_data['request_id'][:8]}...`\n"
    text += f"• Bot: @{request_data['bot_username']}\n"
    text += f"• Submitted: {request_data['created_at'].strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    text += f"**🔄 What's Next:**\n"
    text += f"• You can submit a new request with corrected information\n"
    text += f"• Contact support for specific rejection reasons\n"
    text += f"• Ensure your bot token and database URL are valid\n\n"
    text += f"**📞 Need Help?**\n"
    text += f"Contact our support team for assistance with your next request.\n\n"
    text += f"Thank you for your interest in our service."
    
    try:
        await client.send_message(user_id, text)
    except Exception as e:
        logger.error(f"Failed to notify rejected user {user_id}: {e}")

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
        logger.error(f"Failed to log admin action: {e}")
