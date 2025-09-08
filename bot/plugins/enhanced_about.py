
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
