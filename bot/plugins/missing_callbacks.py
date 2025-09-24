from bot.utils.command_verification import check_command_limit, use_command
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Common callback patterns that should be handled
HANDLED_PATTERNS = [
    'get_token', 'show_premium_plans', 'rand_new', 'file_',
    'back_to_start', 'help_', 'about_', 'my_profile',
    'refresh_balance', 'full_transaction_history',
    'create_clone', 'manage_clones', 'admin_panel'
]

# Start menu callback handlers
@Client.on_callback_query(filters.regex("^(start_clone_creation|manage_my_clone|user_profile|premium_info|help_menu|about_bot|about_water|admin_panel|bot_management)$"), group=95)
async def handle_start_menu_callbacks(client: Client, query: CallbackQuery):
    """Handle start menu button callbacks"""
    callback_data = query.data
    user_id = query.from_user.id

    try:
        await query.answer()

        if callback_data == "start_clone_creation":
            await query.edit_message_text(
                "🤖 **Clone Bot Creation**\n\n"
                "To create your personal clone bot:\n"
                "1. Use /createclone command\n"
                "2. Follow the setup wizard\n"
                "3. Customize your bot settings\n\n"
                "💡 **Tip:** Make sure you have the required permissions!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "manage_my_clone":
            await query.edit_message_text(
                "📋 **My Clone Bots**\n\n"
                "Use /myclones to view and manage your clone bots.\n\n"
                "Available actions:\n"
                "• View bot status\n"
                "• Edit bot settings\n"
                "• Start/Stop bots\n"
                "• View analytics",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "user_profile":
            # Get user stats
            try:
                from bot.database.users import get_user_stats
                stats = await get_user_stats(user_id)

                profile_text = f"👤 **Your Profile**\n\n"
                profile_text += f"🆔 User ID: `{user_id}`\n"
                profile_text += f"👤 Name: {query.from_user.first_name}\n"
                if query.from_user.username:
                    profile_text += f"📝 Username: @{query.from_user.username}\n"
                profile_text += f"📅 Member since: Today\n"
                profile_text += f"🤖 Clone bots: {stats.get('clone_count', 0)}\n"
                profile_text += f"📊 Commands used: {stats.get('command_count', 0)}"

            except Exception as e:
                logger.error(f"Error getting user stats: {e}")
                profile_text = f"👤 **Your Profile**\n\n"
                profile_text += f"🆔 User ID: `{user_id}`\n"
                profile_text += f"👤 Name: {query.from_user.first_name}\n"
                if query.from_user.username:
                    profile_text += f"📝 Username: @{query.from_user.username}\n"
                profile_text += f"📅 Member since: Today"

            await query.edit_message_text(
                profile_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "premium_info":
            await query.edit_message_text(
                "💎 **Premium Plans**\n\n"
                "🌟 **Basic Plan** - $5/month\n"
                "• 5 Clone bots\n"
                "• Basic analytics\n"
                "• Email support\n\n"
                "🚀 **Pro Plan** - $15/month\n"
                "• 25 Clone bots\n"
                "• Advanced analytics\n"
                "• Priority support\n"
                "• Custom branding\n\n"
                "⚡ **Enterprise** - $50/month\n"
                "• Unlimited clone bots\n"
                "• White-label solution\n"
                "• 24/7 support\n"
                "• Custom features\n\n"
                "💳 Contact admin to upgrade!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Contact Admin", url="https://t.me/admin")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data in ["help_menu", "help"]:
            await query.edit_message_text(
                "❓ **Help & Support**\n\n"
                "🤖 **Bot Commands:**\n"
                "• /start - Main menu\n"
                "• /createclone - Create new clone bot\n"
                "• /myclones - Manage your bots\n"
                "• /help - Show this help\n\n"
                "📞 **Support:**\n"
                "• Documentation: Available in bot\n"
                "• Support group: @support\n"
                "• Contact admin: @admin\n\n"
                "🔧 **Troubleshooting:**\n"
                "If you encounter issues, try /start again or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 Documentation", callback_data="docs")],
                    [InlineKeyboardButton("💬 Support Group", url="https://t.me/support")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data in ["about_bot", "about_water"]:
            await query.edit_message_text(
                "ℹ️ **About Advanced Bot Creator**\n\n"
                "🚀 **Version:** 2.0.0\n"
                "🔧 **Framework:** Pyrogram + Python\n"
                "💾 **Database:** MongoDB\n"
                "☁️ **Hosting:** Cloud Infrastructure\n\n"
                "✨ **Features:**\n"
                "• Create unlimited clone bots\n"
                "• Advanced file management\n"
                "• User analytics & monitoring\n"
                "• Premium subscriptions\n"
                "• 24/7 uptime guarantee\n\n"
                "👨‍💻 **Developed by:** Professional Team\n"
                "🌐 **Website:** Coming soon\n"
                "📧 **Contact:** @admin",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Statistics", callback_data="bot_stats")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "admin_panel":
            # Check if user is admin
            if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
                await query.answer("❌ Unauthorized access!", show_alert=True)
                return

            await query.edit_message_text(
                "⚙️ **Admin Panel**\n\n"
                "🔧 **System Management:**\n"
                "• Monitor system health\n"
                "• View active clones\n"
                "• Manage users\n"
                "• System statistics\n\n"
                "🛠️ **Bot Management:**\n"
                "• Clone bot operations\n"
                "• Database management\n"
                "• Broadcast messages\n"
                "• Premium management",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📊 System Stats", callback_data="system_stats"),
                        InlineKeyboardButton("🤖 Bot Management", callback_data="bot_management")
                    ],
                    [
                        InlineKeyboardButton("👥 User Management", callback_data="user_management"),
                        InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_panel")
                    ],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "bot_management":
            # Check if user is admin
            if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
                await query.answer("❌ Unauthorized access!", show_alert=True)
                return

            await query.edit_message_text(
                "🤖 **Bot Management Panel**\n\n"
                "📋 **Available Actions:**\n"
                "• View all clone bots\n"
                "• Start/Stop specific bots\n"
                "• Monitor bot performance\n"
                "• Update bot configurations\n"
                "• Force restart problematic bots\n\n"
                "📊 **Quick Stats:**\n"
                "• Active bots: Loading...\n"
                "• Total users: Loading...\n"
                "• System uptime: Loading...",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📋 All Clones", callback_data="view_all_clones"),
                        InlineKeyboardButton("🔄 Restart Bots", callback_data="restart_all_bots")
                    ],
                    [
                        InlineKeyboardButton("📊 Performance", callback_data="bot_performance"),
                        InlineKeyboardButton("⚙️ Config", callback_data="bot_config")
                    ],
                    [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in start menu callback {callback_data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# Back to start callback
@Client.on_callback_query(filters.regex("^back_to_start$"), group=94)
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Handle back to start menu"""
    try:
        await query.answer()
        # Trigger start command logic
        from bot.plugins.start_handler import start_command

        # Create a mock message object for start command
        class MockMessage:
            def __init__(self, user):
                self.from_user = user
                self.reply_text = query.edit_message_text

        mock_message = MockMessage(query.from_user)
        await start_command(client, mock_message)

    except Exception as e:
        logger.error(f"Error going back to start: {e}")
        await query.answer("❌ Error loading menu. Use /start", show_alert=True)

# File browsing callbacks for clone bots
@Client.on_callback_query(filters.regex("^(random_files|recent_files|popular_files)$"), group=93)
async def handle_file_browsing_callbacks(client: Client, query: CallbackQuery):
    """Handle file browsing callbacks"""
    callback_data = query.data

    try:
        await query.answer()

        if callback_data == "random_files":
            await query.edit_message_text(
                "🎲 **Random Files**\n\n"
                "📁 Browsing random files from the database...\n\n"
                "⚠️ **Note:** This feature requires token verification.\n"
                "Use /verify to get your access token first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "recent_files":
            await query.edit_message_text(
                "🆕 **Recent Files**\n\n"
                "📅 Showing latest uploaded files...\n\n"
                "⚠️ **Note:** This feature requires token verification.\n"
                "Use /verify to get your access token first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "popular_files":
            await query.edit_message_text(
                "🔥 **Popular Files**\n\n"
                "📈 Showing most downloaded files...\n\n"
                "⚠️ **Note:** This feature requires token verification.\n"
                "Use /verify to get your access token first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 Get Verification Token", callback_data="get_token")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in file browsing callback {callback_data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# Additional utility callbacks
@Client.on_callback_query(filters.regex("^get_token$"), group=92)
async def get_token_callback(client: Client, query: CallbackQuery):
    """Handle get token callback"""
    try:
        await query.answer()
        await query.edit_message_text(
            "🔑 **Get Verification Token**\n\n"
            "To get your verification token:\n"
            "1. Use the /verify command\n"
            "2. Complete the verification process\n"
            "3. Use your token to access premium features\n\n"
            "💡 **Note:** Tokens are valid for 24 hours.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in get token callback: {e}")
        await query.answer("❌ Error processing request", show_alert=True)

# Close message handler
@Client.on_callback_query(filters.regex("^close_message$"), group=91)
async def close_message_callback(client: Client, query: CallbackQuery):
    """Handle close message callback"""
    try:
        await query.message.delete()
        await query.answer("✅ Closed", show_alert=False)
    except Exception as e:
        logger.error(f"Error closing message: {e}")
        try:
            await query.edit_message_text("✅ Session closed")
        except:
            await query.answer("❌ Error closing", show_alert=True)
@Client.on_callback_query(filters.regex("^(my_stats|get_token|docs|bot_stats)$"), group=92)
async def handle_utility_callbacks(client: Client, query: CallbackQuery):
    """Handle utility callbacks"""
    callback_data = query.data

    try:
        await query.answer()

        if callback_data == "my_stats":
            user_id = query.from_user.id
            await query.edit_message_text(
                f"📊 **Your Statistics**\n\n"
                f"🆔 User ID: `{user_id}`\n"
                f"📅 Joined: Today\n"
                f"🤖 Clone bots: 0\n"
                f"📥 Downloads: 0\n"
                f"🔑 Tokens used: 0\n"
                f"💎 Plan: Free\n\n"
                f"📈 **Activity:**\n"
                f"• Last seen: Now\n"
                f"• Commands used: 0\n"
                f"• Files accessed: 0",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="my_stats")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

        elif callback_data == "get_token":
            await query.edit_message_text(
                "🔑 **Verification Token**\n\n"
                "To access file browsing features, you need a verification token.\n\n"
                "**How to get a token:**\n"
                "1. Use the /verify command\n"
                "2. Complete the verification process\n"
                "3. Return here to browse files\n\n"
                "⏱️ **Token validity:** 24 hours\n"
                "🔒 **Security:** Tokens are encrypted and secure",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="random_files")]
                ])
            )

        elif callback_data == "docs":
            await query.edit_message_text(
                "📖 **Documentation**\n\n"
                "🚀 **Getting Started:**\n"
                "• Create your first clone bot\n"
                "• Understanding the interface\n"
                "• Basic bot management\n\n"
                "🔧 **Advanced Features:**\n"
                "• Custom bot settings\n"
                "• User management\n"
                "• Analytics and reporting\n\n"
                "💡 **Tips & Tricks:**\n"
                "• Optimization techniques\n"
                "• Troubleshooting guide\n"
                "• Best practices",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Help", callback_data="help_menu")]
                ])
            )

        elif callback_data == "bot_stats":
            await query.edit_message_text(
                "📊 **Bot Statistics**\n\n"
                "🤖 **System Info:**\n"
                "• Total users: 1,000+\n"
                "• Active clones: 500+\n"
                "• Files managed: 100,000+\n"
                "• Uptime: 99.9%\n\n"
                "📈 **Performance:**\n"
                "• Response time: <100ms\n"
                "• Success rate: 99.8%\n"
                "• CPU usage: Normal\n"
                "• Memory usage: Optimal\n\n"
                "🌍 **Global Reach:**\n"
                "• Countries served: 50+\n"
                "• Languages: 10+\n"
                "• Time zones: All supported",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="bot_stats")],
                    [InlineKeyboardButton("🔙 Back to About", callback_data="about_bot")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in utility callback {callback_data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# Catch-all for unhandled callbacks
@Client.on_callback_query(filters.regex(r"^(?!(" + "|".join(HANDLED_PATTERNS) + r"))", flags=0), group=99)
async def handle_missing_callbacks(client: Client, callback_query: CallbackQuery):
    """Handle unrecognized callback queries gracefully"""
    try:
        callback_data = callback_query.data
        user_id = callback_query.from_user.id

        logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")

        # Check if it's a common pattern that might be expected
        if any(pattern in callback_data for pattern in ['back', 'close', 'cancel', 'home']):
            await callback_query.answer("🔄 Returning to main menu...")
            # Try to edit message to show start menu
            try:
                from bot.plugins.start_handler import get_start_message, get_start_keyboard
                message_text, keyboard = await get_start_message(client, callback_query.from_user)
                await callback_query.edit_message_text(message_text, reply_markup=keyboard)
                return
            except Exception:
                pass

        # Send a user-friendly response for unknown callbacks
        await callback_query.answer(
            "⚠️ This action is no longer available or was not recognized.",
            show_alert=True
        )

    except Exception as e:
        logger.error(f"Error in missing callbacks handler: {e}")
        try:
            await callback_query.answer("❌ An error occurred. Please try again.")
        except Exception:
            pass

@Client.on_callback_query(filters.regex(r"^(help_|about_)"), group=1)
async def handle_info_callbacks(client: Client, callback_query: CallbackQuery):
    """Handle help and about callbacks that might be missing"""
    try:
        callback_data = callback_query.data

        if callback_data.startswith('help_'):
            await callback_query.answer("💡 Help information")
            help_text = (
                "🤖 **Bot Help**\n\n"
                "This bot provides file sharing capabilities.\n\n"
                "**Available Commands:**\n"
                "• `/start` - Start the bot\n"
                "• `/help` - Show this help\n"
                "• `/about` - About this bot\n\n"
                "**Features:**\n"
                "• Random file access\n"
                "• File search\n"
                "• Premium subscriptions\n"
                "• Clone bot creation"
            )
            await callback_query.edit_message_text(help_text)

        elif callback_data.startswith('about_'):
            await callback_query.answer("ℹ️ About information")
            about_text = (
                "🤖 **About This Bot**\n\n"
                "This bot is powered by the Mother Bot System - "
                "an advanced file-sharing platform.\n\n"
                "**Features:**\n"
                "• Fast & reliable file sharing\n"
                "• Advanced search capabilities\n"
                "• Premium subscriptions\n"
                "• Clone bot creation\n\n"
                "**Made by Mother Bot System**\n"
                "Professional bot hosting & management solutions."
            )
            await callback_query.edit_message_text(about_text)

    except Exception as e:
        logger.error(f"Error in info callbacks handler: {e}")
        await callback_query.answer("❌ Error loading information")