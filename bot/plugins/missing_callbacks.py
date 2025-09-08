
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER
from bot.database.users import get_user_stats
from bot.database.balance_db import get_user_balance, add_balance
from bot.database.premium_db import is_premium_user
from bot.database.clone_db import get_clone_by_bot_token
import asyncio
from datetime import datetime

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(documentation|video_tutorials|compare_plans|premium_trial|refresh_transactions|download_transactions|notification_settings|privacy_settings|security_settings|export_stats|rate_bot|report_bug|suggest_feature)$"))
async def handle_missing_features(client: Client, query: CallbackQuery):
    """Handle callbacks for features not yet implemented"""
    await query.answer()
    
    feature_names = {
        "documentation": "📚 Documentation",
        "video_tutorials": "🎥 Video Tutorials", 
        "compare_plans": "📋 Compare Plans",
        "premium_trial": "🎁 Free Trial",
        "refresh_transactions": "🔄 Refresh History",
        "download_transactions": "📱 Download Report",
        "notification_settings": "🔔 Notifications",
        "privacy_settings": "🔒 Privacy",
        "security_settings": "🔐 Security",
        "export_stats": "📱 Export Data",
        "rate_bot": "⭐ Rate Bot",
        "report_bug": "🐛 Report Bug",
        "suggest_feature": "💡 Suggest Feature"
    }
    
    feature_name = feature_names.get(query.data, "Feature")
    
    text = f"{feature_name}\n\n"
    text += f"🚧 **Coming Soon!**\n\n"
    text += f"This feature is currently under development.\n"
    text += f"Stay tuned for updates!\n\n"
    text += f"💬 **Need immediate assistance?**\n"
    text += f"Contact our support team for help."
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
            InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^user_profile_main$"))
async def user_profile_main_callback(client: Client, query: CallbackQuery):
    """Handle user profile main callback to avoid infinite loop"""
    # Redirect to user_profile callback
    query.data = "user_profile"
    from bot.plugins.start_handler import profile_callback
    await profile_callback(client, query)

@Client.on_callback_query(filters.regex("^user_profile$"))
async def profile_callback(client: Client, query: CallbackQuery):
    """Handle user profile callback"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        # Get user data
        balance = await get_user_balance(user_id)
        is_premium = await is_premium_user(user_id)
        user_stats = await get_user_stats(user_id)
        
        text = f"👤 **User Profile**\n\n"
        text += f"📝 **Name:** {query.from_user.first_name}\n"
        text += f"🆔 **User ID:** `{user_id}`\n"
        text += f"👤 **Username:** @{query.from_user.username or 'Not set'}\n"
        text += f"💰 **Balance:** ${balance:.2f}\n"
        text += f"💎 **Status:** {'Premium' if is_premium else 'Free'}\n"
        text += f"📊 **Commands Used:** {user_stats.get('command_count', 0)}\n"
        text += f"📅 **Joined:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
        text += f"🎯 **Quick Actions:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💰 Add Balance", callback_data="add_balance"),
                InlineKeyboardButton("💎 Upgrade Plan", callback_data="premium_info")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="user_settings"),
                InlineKeyboardButton("📊 Statistics", callback_data="my_stats")
            ],
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in profile_callback: {e}")
        await query.edit_message_text("❌ Error loading profile. Please try again.")

@Client.on_callback_query(filters.regex("^my_stats$"))
async def my_stats_callback(client: Client, query: CallbackQuery):
    """Handle user statistics callback"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        user_stats = await get_user_stats(user_id)
        balance = await get_user_balance(user_id)
        is_premium = await is_premium_user(user_id)
        
        text = f"📊 **Your Statistics**\n\n"
        text += f"📈 **Usage Stats:**\n"
        text += f"• Commands Used: {user_stats.get('command_count', 0)}\n"
        text += f"• Files Downloaded: {user_stats.get('downloads', 0)}\n"
        text += f"• Searches Made: {user_stats.get('searches', 0)}\n"
        text += f"• Days Active: {user_stats.get('active_days', 1)}\n\n"
        text += f"💰 **Financial Stats:**\n"
        text += f"• Current Balance: ${balance:.2f}\n"
        text += f"• Total Spent: ${user_stats.get('total_spent', 0):.2f}\n"
        text += f"• Account Type: {'Premium' if is_premium else 'Free'}\n\n"
        text += f"📅 **Account Info:**\n"
        text += f"• Member Since: {datetime.now().strftime('%Y-%m-%d')}\n"
        text += f"• Last Active: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📱 Export Data", callback_data="export_stats"),
                InlineKeyboardButton("🔄 Refresh", callback_data="my_stats")
            ],
            [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in my_stats_callback: {e}")
        await query.edit_message_text("❌ Error loading statistics. Please try again.")

@Client.on_callback_query(filters.regex("^add_balance$"))
async def add_balance_callback(client: Client, query: CallbackQuery):
    """Handle add balance callback"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        current_balance = await get_user_balance(user_id)
        
        text = f"💰 **Add Balance**\n\n"
        text += f"💳 **Current Balance:** ${current_balance:.2f}\n\n"
        text += f"💎 **Available Packages:**\n"
        text += f"• $5.00 - Basic Package\n"
        text += f"• $10.00 - Standard Package\n"
        text += f"• $25.00 - Premium Package\n"
        text += f"• $50.00 - Professional Package\n\n"
        text += f"🎯 **Choose a package to add to your balance:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💵 $5.00", callback_data="add_balance_5"),
                InlineKeyboardButton("💴 $10.00", callback_data="add_balance_10")
            ],
            [
                InlineKeyboardButton("💶 $25.00", callback_data="add_balance_25"),
                InlineKeyboardButton("💷 $50.00", callback_data="add_balance_50")
            ],
            [
                InlineKeyboardButton("💳 Custom Amount", callback_data="add_balance_custom"),
                InlineKeyboardButton("📜 Payment History", callback_data="payment_history")
            ],
            [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in add_balance_callback: {e}")
        await query.edit_message_text("❌ Error loading balance page. Please try again.")

@Client.on_callback_query(filters.regex("^add_balance_(\d+)$"))
async def add_balance_amount_callback(client: Client, query: CallbackQuery):
    """Handle specific balance amount selection"""
    await query.answer()
    user_id = query.from_user.id
    amount = int(query.data.split("_")[2])
    
    try:
        text = f"💰 **Payment Confirmation**\n\n"
        text += f"💳 **Amount:** ${amount}.00\n"
        text += f"👤 **User:** {query.from_user.first_name}\n"
        text += f"🆔 **User ID:** {user_id}\n\n"
        text += f"🚧 **Payment System Coming Soon!**\n\n"
        text += f"We're currently setting up secure payment processing.\n"
        text += f"For now, contact support to add balance manually.\n\n"
        text += f"📞 **Contact:** @{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
                InlineKeyboardButton("🔙 Back", callback_data="add_balance")
            ]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in add_balance_amount_callback: {e}")
        await query.edit_message_text("❌ Error processing payment. Please try again.")

@Client.on_callback_query(filters.regex("^premium_info$"))
async def premium_info_callback(client: Client, query: CallbackQuery):
    """Handle premium info callback"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        is_premium = await is_premium_user(user_id)
        
        if is_premium:
            text = f"💎 **Premium Status**\n\n"
            text += f"✅ **You have Premium access!**\n\n"
            text += f"🌟 **Premium Benefits:**\n"
            text += f"• ⚡ Priority support\n"
            text += f"• 🚀 Faster processing\n"
            text += f"• 📁 Unlimited file access\n"
            text += f"• 🎯 Advanced features\n"
            text += f"• 💎 Exclusive content\n\n"
            text += f"🎯 **Manage your Premium subscription:**"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Usage Stats", callback_data="premium_stats"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="premium_settings")
                ],
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
            ])
        else:
            text = f"💎 **Upgrade to Premium**\n\n"
            text += f"🌟 **Premium Benefits:**\n"
            text += f"• ⚡ Priority support & faster processing\n"
            text += f"• 📁 Unlimited file downloads\n"
            text += f"• 🎯 Advanced search features\n"
            text += f"• 💎 Exclusive premium content\n"
            text += f"• 🚀 No usage limits\n"
            text += f"• 🛡️ Enhanced security features\n\n"
            text += f"💰 **Pricing Plans:**\n"
            text += f"• Monthly: $9.99/month\n"
            text += f"• Yearly: $99.99/year (17% off)\n\n"
            text += f"🎯 **Choose your plan:**"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📅 Monthly Plan", callback_data="premium_monthly"),
                    InlineKeyboardButton("📆 Yearly Plan", callback_data="premium_yearly")
                ],
                [
                    InlineKeyboardButton("🎁 Free Trial", callback_data="premium_trial"),
                    InlineKeyboardButton("📋 Compare Plans", callback_data="compare_plans")
                ],
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="user_profile")]
            ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in premium_info_callback: {e}")
        await query.edit_message_text("❌ Error loading premium info. Please try again.")

@Client.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_callback(client: Client, query: CallbackQuery):
    """Handle help menu callback"""
    await query.answer()
    
    try:
        text = f"❓ **Help & Support**\n\n"
        text += f"🎯 **Quick Help Topics:**\n"
        text += f"• 🚀 Getting started\n"
        text += f"• 📁 File management\n"
        text += f"• 🔍 Search features\n"
        text += f"• 💰 Balance & payments\n"
        text += f"• 💎 Premium features\n"
        text += f"• ⚙️ Settings & configuration\n\n"
        text += f"📚 **Resources:**\n"
        text += f"• Documentation & guides\n"
        text += f"• Video tutorials\n"
        text += f"• FAQ section\n"
        text += f"• Community support\n\n"
        text += f"🎯 **Choose a help topic:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 Getting Started", callback_data="help_getting_started"),
                InlineKeyboardButton("📁 File Management", callback_data="help_files")
            ],
            [
                InlineKeyboardButton("🔍 Search Help", callback_data="help_search"),
                InlineKeyboardButton("💰 Balance Help", callback_data="help_balance")
            ],
            [
                InlineKeyboardButton("💎 Premium Help", callback_data="help_premium"),
                InlineKeyboardButton("⚙️ Settings Help", callback_data="help_settings")
            ],
            [
                InlineKeyboardButton("📚 Documentation", callback_data="documentation"),
                InlineKeyboardButton("🎥 Video Tutorials", callback_data="video_tutorials")
            ],
            [
                InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
                InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
            ]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in help_menu_callback: {e}")
        await query.edit_message_text("❌ Error loading help menu. Please try again.")

@Client.on_callback_query(filters.regex("^about_bot$"))
async def about_bot_callback(client: Client, query: CallbackQuery):
    """Handle about bot callback"""
    await query.answer()
    
    try:
        text = f"ℹ️ **About This Bot**\n\n"
        text += f"🤖 **Advanced File Sharing Bot**\n"
        text += f"Version 2.0 - Next Generation\n\n"
        text += f"🌟 **Features:**\n"
        text += f"• 📁 Advanced file management\n"
        text += f"• 🔍 Powerful search engine\n"
        text += f"• 💎 Premium subscriptions\n"
        text += f"• 🤖 Clone bot creation\n"
        text += f"• 💰 Balance system\n"
        text += f"• 🔐 Secure & encrypted\n\n"
        text += f"👨‍💻 **Developer:** {Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'Admin'}\n"
        text += f"📅 **Last Updated:** {datetime.now().strftime('%Y-%m-%d')}\n"
        text += f"🌐 **Server Status:** Online\n\n"
        text += f"🎯 **Get more information:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Bot Statistics", callback_data="bot_stats"),
                InlineKeyboardButton("🔄 System Status", callback_data="system_status")
            ],
            [
                InlineKeyboardButton("📝 Release Notes", callback_data="release_notes"),
                InlineKeyboardButton("🛡️ Privacy Policy", callback_data="privacy_policy")
            ],
            [
                InlineKeyboardButton("⭐ Rate Bot", callback_data="rate_bot"),
                InlineKeyboardButton("💡 Suggest Feature", callback_data="suggest_feature")
            ],
            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in about_bot_callback: {e}")
        await query.edit_message_text("❌ Error loading about page. Please try again.")

@Client.on_callback_query(filters.regex("^clone_settings_panel$"))
async def clone_settings_panel_callback(client: Client, query: CallbackQuery):
    """Handle clone settings panel callback for clone admins"""
    await query.answer()
    user_id = query.from_user.id
    
    try:
        # Check if this is a clone bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.edit_message_text("❌ Settings panel is only available in clone bots!")
            return
        
        # Get clone data and verify admin
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            await query.edit_message_text("❌ Clone configuration not found!")
            return
        
        if int(user_id) != int(clone_data.get('admin_id')):
            await query.edit_message_text("❌ Only clone admin can access settings!")
            return
        
        # Get current settings
        show_random = clone_data.get('random_mode', True)
        show_recent = clone_data.get('recent_mode', True)
        show_popular = clone_data.get('popular_mode', True)
        force_join = clone_data.get('force_join_enabled', False)
        
        text = f"⚙️ **Clone Bot Settings**\n\n"
        text += f"🔧 **Configuration Panel**\n"
        text += f"Manage your clone bot's features and behavior.\n\n"
        text += f"📋 **Current Settings:**\n"
        text += f"• 🎲 Random Files: {'✅ Enabled' if show_random else '❌ Disabled'}\n"
        text += f"• 🆕 Recent Files: {'✅ Enabled' if show_recent else '❌ Disabled'}\n"
        text += f"• 🔥 Popular Files: {'✅ Enabled' if show_popular else '❌ Disabled'}\n"
        text += f"• 🔐 Force Join: {'✅ Enabled' if force_join else '❌ Disabled'}\n\n"
        text += f"⚡ **Quick Actions:**"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🎲 Random: {'✅' if show_random else '❌'}", callback_data="clone_toggle_random"),
                InlineKeyboardButton(f"🆕 Recent: {'✅' if show_recent else '❌'}", callback_data="clone_toggle_recent")
            ],
            [
                InlineKeyboardButton(f"🔥 Popular: {'✅' if show_popular else '❌'}", callback_data="clone_toggle_popular"),
                InlineKeyboardButton(f"🔐 Force Join: {'✅' if force_join else '❌'}", callback_data="clone_toggle_force_join")
            ],
            [
                InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_verification_mode"),
                InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener_config")
            ],
            [
                InlineKeyboardButton("📋 Force Channels", callback_data="clone_force_channels_list"),
                InlineKeyboardButton("🔧 Advanced Settings", callback_data="clone_advanced_settings")
            ],
            [
                InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
            ]
        ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone_settings_panel_callback: {e}")
        await query.edit_message_text("❌ Error loading settings panel. Please try again.")

@Client.on_callback_query(filters.regex("^file_(sample|recent|popular)"))
async def handle_sample_file_callbacks(client: Client, query: CallbackQuery):
    """Handle sample file callbacks from file browsing"""
    await query.answer()
    
    file_id = query.data
    file_name = "Sample File"
    
    if "sample" in file_id:
        file_name = "Sample File"
    elif "recent" in file_id:
        file_name = "Recent File"
    elif "popular" in file_id:
        file_name = "Popular File"
    
    text = f"📁 **{file_name}**\n\n"
    text += f"🔍 **File ID:** `{file_id}`\n"
    text += f"📊 **Size:** 125.6 MB\n"
    text += f"⏰ **Added:** 2 hours ago\n"
    text += f"📥 **Downloads:** 1,234\n\n"
    text += f"🎯 **Actions:**"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Download", url="https://t.me/example"),
            InlineKeyboardButton("📤 Share", callback_data=f"share_{file_id}")
        ],
        [
            InlineKeyboardButton("ℹ️ More Info", callback_data=f"info_{file_id}"),
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{file_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

# Add more specific help callbacks
@Client.on_callback_query(filters.regex("^help_(getting_started|files|search|balance|premium|settings)$"))
async def help_specific_callback(client: Client, query: CallbackQuery):
    """Handle specific help topic callbacks"""
    await query.answer()
    
    topic = query.data.split("_", 1)[1]
    
    help_content = {
        "getting_started": {
            "title": "🚀 Getting Started",
            "content": "Welcome! Here's how to get started:\n\n• Use /start to begin\n• Browse files with the buttons\n• Add balance for premium features\n• Contact support if you need help"
        },
        "files": {
            "title": "📁 File Management",
            "content": "File features:\n\n• Browse random files\n• Check recent uploads\n• View popular downloads\n• Search by keywords\n• Download with one click"
        },
        "search": {
            "title": "🔍 Search Help",
            "content": "Search features:\n\n• Use keywords to find files\n• Filter by file type\n• Sort by relevance or date\n• Save favorite searches\n• Get search suggestions"
        },
        "balance": {
            "title": "💰 Balance Help",
            "content": "Balance system:\n\n• Add funds to your account\n• Use balance for premium features\n• View transaction history\n• Auto-renewal options\n• Refund policies"
        },
        "premium": {
            "title": "💎 Premium Help",
            "content": "Premium benefits:\n\n• Unlimited downloads\n• Priority support\n• Advanced features\n• No ads or limits\n• Exclusive content access"
        },
        "settings": {
            "title": "⚙️ Settings Help",
            "content": "Available settings:\n\n• Notification preferences\n• Privacy controls\n• Security options\n• Display preferences\n• Account management"
        }
    }
    
    info = help_content.get(topic, {"title": "❓ Help", "content": "Help content not available."})
    
    text = f"{info['title']}\n\n{info['content']}\n\n"
    text += f"Need more help? Contact our support team!"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}"),
            InlineKeyboardButton("🔙 Back to Help", callback_data="help_menu")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
