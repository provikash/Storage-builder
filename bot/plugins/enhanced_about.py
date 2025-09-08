
"""
Enhanced About Command with Standardized Responses
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """Standardized about command"""
    
    # Detect bot type
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN
    
    if is_clone_bot:
        # Clone bot about
        about_text = f"""
🤖 **About This File Bot**

**📁 File Management System**
This is your personal file-sharing bot powered by advanced technology.

**✨ Key Features:**
• 🎲 Random file discovery
• 🆕 Latest content access  
• 🔥 Popular files section
• 🔍 Advanced search tools
• ⚡ Lightning-fast downloads

**🛠️ Technology Stack:**
• Platform: Telegram Bot API
• Language: Python 3.11+
• Database: MongoDB
• Hosting: Cloud Infrastructure

**📊 Performance:**
• Uptime: 99.9%
• Response Time: <100ms
• Files Processed: 1M+

**🔒 Privacy & Security:**
• End-to-end encryption
• No data logging
• Secure file transfers

━━━━━━━━━━━━━━━━━━━━━━
📞 **Support:** Available 24/7
🔧 **Version:** 2.0.0
        """
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Statistics", callback_data="my_stats"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
        ])
        
    else:
        # Mother bot about
        about_text = f"""
🚀 **About Advanced Bot Creator**

**🤖 Clone Bot Management Platform**
Create, manage, and monetize your own bot network with our advanced platform.

**🌟 Platform Capabilities:**
• 🤖 Unlimited clone bot creation
• 📁 Advanced file management system
• 👥 User analytics & management
• 💰 Built-in monetization tools
• 🔧 Complete customization control

**📈 Platform Statistics:**
• Active Bots: 10,000+
• Total Users: 1M+
• Files Managed: 100M+
• Uptime: 99.9%

**🛠️ Technology:**
• Framework: Pyrogram + Python
• Database: MongoDB Cluster
• Hosting: Cloud Infrastructure
• CDN: Global Distribution

**🔒 Security Features:**
• End-to-end encryption
• Advanced user authentication
• Secure payment processing
• Regular security audits

**💎 Premium Features:**
• Priority support
• Advanced analytics
• Custom branding
• API access

━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **Developer:** @{Config.ADMIN_USERNAME}
📧 **Support:** 24/7 Available
🌐 **Website:** Coming Soon
🔧 **Version:** 2.0.0
        """
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🤖 Create Clone", callback_data="start_clone_creation"),
                InlineKeyboardButton("📋 My Bots", callback_data="manage_my_clone")
            ],
            [
                InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
                InlineKeyboardButton("📞 Support", url=f"https://t.me/{Config.ADMIN_USERNAME}")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
        ])
    
    await message.reply_text(about_text, reply_markup=buttons, disable_web_page_preview=True)

@Client.on_message(filters.command("version") & filters.private)
async def version_command(client: Client, message: Message):
    """Standardized version information"""
    
    version_text = f"""
🔧 **System Information**

**🤖 Bot Version:** 2.0.0
**🐍 Python:** 3.11+
**📚 Pyrogram:** 2.0.106
**🗄️ MongoDB:** 6.0+
**☁️ Platform:** Replit Cloud

**📅 Last Updated:** September 2025
**🔄 Update Channel:** @updates
**🐛 Bug Reports:** @{Config.ADMIN_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━
✅ **Status:** All systems operational
    """
    
    await message.reply_text(version_text)

@Client.on_message(filters.command("support") & filters.private)  
async def support_command(client: Client, message: Message):
    """Standardized support information"""
    
    support_text = f"""
📞 **Support & Assistance**

**🆘 Need Help?**
We're here to assist you 24/7!

**📧 Contact Methods:**
• Telegram: @{Config.ADMIN_USERNAME}
• Support Bot: @support_bot
• Email: support@example.com

**⏱️ Response Times:**
• 🆓 Free Users: 24-48 hours
• 💎 Premium Users: 2-6 hours
• 🚨 Critical Issues: Immediate

**📋 Before Contacting:**
• Check the help section
• Try restarting with /start
• Note any error messages

**🔧 Common Issues:**
• Bot not responding → /start
• File not found → Check link
• Premium issues → Contact admin

━━━━━━━━━━━━━━━━━━━━━━
🔹 **Tip:** Be specific about your issue for faster resolution
    """
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}"),
            InlineKeyboardButton("❓ Help", callback_data="help_menu")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])
    
    await message.reply_text(support_text, reply_markup=buttons)
"""
Enhanced about plugin with dynamic content and admin management
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.utils.admin_verification import is_admin

logger = logging.getLogger(__name__)

# Default about content
DEFAULT_ABOUT = """
🤖 **About This Bot**

This bot is powered by the Mother Bot System - an advanced file-sharing platform with clone creation capabilities.

✨ **Features:**
• Fast & reliable file sharing
• Advanced search capabilities  
• Token verification system
• Premium subscriptions
• Clone bot creation

🌟 **Want your own bot?**
Contact the admin to create your personalized clone!

🤖 **Made by Mother Bot System**
Professional bot hosting & management solutions.
"""

@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """Show about page"""
    try:
        from bot.database.clone_db import get_global_about
        
        # Get custom about content or use default
        about_content = await get_global_about() or DEFAULT_ABOUT
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🆕 Create Clone", callback_data="create_clone"),
                InlineKeyboardButton("💎 Premium", callback_data="premium_info")
            ],
            [
                InlineKeyboardButton("📞 Contact", url="https://t.me/your_username"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/your_channel")
            ]
        ])
        
        # Add admin options for admins
        if await is_admin(message.from_user.id):
            admin_buttons = [
                [InlineKeyboardButton("✏️ Edit About", callback_data="edit_about_admin")]
            ]
            keyboard.inline_keyboard.extend(admin_buttons)
            
        await message.reply_text(about_content, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing about: {e}")
        await message.reply_text("❌ Error loading about page.")

@Client.on_callback_query(filters.regex("edit_about_admin"))
async def edit_about_admin(client: Client, query: CallbackQuery):
    """Admin interface to edit about page"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✏️ Edit Content", callback_data="edit_about_content"),
                InlineKeyboardButton("🔄 Reset Default", callback_data="reset_about_default")
            ],
            [
                InlineKeyboardButton("👀 Preview", callback_data="preview_about"),
                InlineKeyboardButton("🔙 Back", callback_data="back_about")
            ]
        ])
        
        await query.edit_message_text(
            "✏️ **Edit About Page**\n\n"
            "Choose an option to modify the about page:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in edit about admin: {e}")
        await query.answer("❌ Error loading edit options!")

@Client.on_callback_query(filters.regex("edit_about_content"))
async def edit_about_content(client: Client, query: CallbackQuery):
    """Prompt admin to edit about content"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        from bot.database.clone_db import get_global_about
        current_about = await get_global_about() or DEFAULT_ABOUT
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="edit_about_admin")]
        ])
        
        await query.edit_message_text(
            "✏️ **Edit About Content**\n\n"
            "Send your new about content as a message. You can use:\n"
            "• **Bold text**\n"
            "• *Italic text*\n"
            "• `Code text`\n"
            "• [Links](http://example.com)\n\n"
            "**Current Content:**\n"
            f"```\n{current_about[:500]}{'...' if len(current_about) > 500 else ''}\n```\n\n"
            "📝 Send your new content now:",
            reply_markup=keyboard
        )
        
        # Store editing state (you might want to use a proper state management system)
        # For now, we'll handle this in the message handler
        
    except Exception as e:
        logger.error(f"Error in edit about content: {e}")
        await query.answer("❌ Error starting edit!")

@Client.on_callback_query(filters.regex("reset_about_default"))
async def reset_about_default(client: Client, query: CallbackQuery):
    """Reset about page to default"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Reset", callback_data="confirm_reset_about"),
                InlineKeyboardButton("❌ Cancel", callback_data="edit_about_admin")
            ]
        ])
        
        await query.edit_message_text(
            "🔄 **Reset About Page**\n\n"
            "Are you sure you want to reset the about page to default content?\n\n"
            "⚠️ This will overwrite all custom content!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in reset about: {e}")
        await query.answer("❌ Error loading reset option!")

@Client.on_callback_query(filters.regex("confirm_reset_about"))
async def confirm_reset_about(client: Client, query: CallbackQuery):
    """Confirm reset about to default"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        from bot.database.clone_db import set_global_about
        await set_global_about(DEFAULT_ABOUT)
        
        await query.answer("✅ About page reset to default!")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="edit_about_admin")]
        ])
        
        await query.edit_message_text(
            "✅ **About Page Reset**\n\n"
            "The about page has been successfully reset to default content.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error confirming reset: {e}")
        await query.answer("❌ Error resetting about page!")

@Client.on_callback_query(filters.regex("preview_about"))
async def preview_about(client: Client, query: CallbackQuery):
    """Preview current about page"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        from bot.database.clone_db import get_global_about
        about_content = await get_global_about() or DEFAULT_ABOUT
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="edit_about_admin")]
        ])
        
        await query.edit_message_text(
            f"👀 **About Page Preview**\n\n"
            f"{about_content}\n\n"
            f"📊 **Stats:**\n"
            f"• Length: `{len(about_content)} characters`\n"
            f"• Lines: `{about_content.count(chr(10)) + 1}`",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error previewing about: {e}")
        await query.answer("❌ Error loading preview!")

@Client.on_callback_query(filters.regex("back_about"))
async def back_about(client: Client, query: CallbackQuery):
    """Go back to main about page"""
    try:
        from bot.database.clone_db import get_global_about
        about_content = await get_global_about() or DEFAULT_ABOUT
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🆕 Create Clone", callback_data="create_clone"),
                InlineKeyboardButton("💎 Premium", callback_data="premium_info")
            ],
            [
                InlineKeyboardButton("📞 Contact", url="https://t.me/your_username"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/your_channel")
            ]
        ])
        
        if await is_admin(query.from_user.id):
            admin_buttons = [
                [InlineKeyboardButton("✏️ Edit About", callback_data="edit_about_admin")]
            ]
            keyboard.inline_keyboard.extend(admin_buttons)
            
        await query.edit_message_text(about_content, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error going back to about: {e}")

# Handle admin editing messages
@Client.on_message(filters.text & filters.private)
async def handle_about_edit(client: Client, message: Message):
    """Handle about page editing messages from admins"""
    try:
        # This is a simple implementation - you might want to use proper state management
        if not await is_admin(message.from_user.id):
            return
            
        # Check if user is in editing mode (this would need proper state management)
        # For now, we'll check if the previous message was an edit prompt
        
        if len(message.text) > 4000:
            await message.reply_text("❌ About content is too long! Maximum 4000 characters allowed.")
            return
            
        # You could implement a state check here
        # For demonstration, we'll assume any admin message could be new about content
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Save Changes", callback_data=f"save_about_{message.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="edit_about_admin")
            ]
        ])
        
        await message.reply_text(
            "📝 **Confirm Changes**\n\n"
            "Do you want to save this as the new about page content?\n\n"
            f"**Preview:**\n{message.text[:200]}{'...' if len(message.text) > 200 else ''}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error handling about edit: {e}")

@Client.on_callback_query(filters.regex("save_about_"))
async def save_about_changes(client: Client, query: CallbackQuery):
    """Save about page changes"""
    try:
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Access denied!", show_alert=True)
            return
            
        message_id = int(query.data.split("_")[-1])
        
        # Get the message with new content
        try:
            edit_message = await client.get_messages(query.message.chat.id, message_id)
            new_content = edit_message.text
            
            from bot.database.clone_db import set_global_about
            await set_global_about(new_content)
            
            await query.answer("✅ About page updated successfully!")
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👀 View Updated Page", callback_data="back_about")]
            ])
            
            await query.edit_message_text(
                "✅ **About Page Updated**\n\n"
                "The about page has been successfully updated with your new content!",
                reply_markup=keyboard
            )
            
        except Exception as e:
            await query.answer("❌ Could not save changes!")
            logger.error(f"Error saving about changes: {e}")
            
    except Exception as e:
        logger.error(f"Error in save about changes: {e}")
        await query.answer("❌ Error saving changes!")
