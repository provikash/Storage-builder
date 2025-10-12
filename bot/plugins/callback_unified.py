
"""
Unified Callback Handler System
Consolidates all callback query handlers from the entire project
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.utils import get_messages, get_readable_time, schedule_manager, get_shortlink, handle_force_sub
from bot.database import add_user, present_user, is_verified, validate_token_and_verify, is_premium_user, increment_access_count
from bot.utils.command_verification import check_command_limit, use_command
from bot.database.verify_db import create_verification_token
from bot.utils.callback_error_handler import safe_callback_handler
from bot.logging import LOGGER
import traceback
import logging

logger = LOGGER(__name__)

# =====================================================
# CALLBACK PRIORITIES
# =====================================================
CALLBACK_PRIORITIES = {
    "emergency": -10,
    "clone_settings": -8,
    "admin": 1,
    "search": 4,
    "general": 5,
    "settings": 6,
    "catchall": 99
}

# =====================================================
# CLONE SETTINGS HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex("^clone_settings_panel$"), group=-5)
async def clone_settings_panel_callback(client: Client, query: CallbackQuery):
    """Handle clone settings panel callback"""
    user_id = query.from_user.id
    logger.info(f"Clone settings panel callback from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    if not is_clone_bot or bot_token == Config.BOT_TOKEN:
        await query.answer("❌ Not available in this bot.", show_alert=True)
        return

    try:
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Only clone admin can access settings.", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        await query.answer("❌ Error verifying admin access.", show_alert=True)
        return

    await query.answer()

    try:
        from bot.plugins.clone_admin_unified import clone_settings_command
        await clone_settings_command(client, query)
    except Exception as e:
        logger.error(f"Error in clone settings panel: {e}")
        await query.edit_message_text("❌ Error loading settings panel.")

# =====================================================
# FILE BROWSING HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex(r"^(random_files|recent_files|popular_files)$"), group=-3)
async def file_browsing_callback_handler(client: Client, query: CallbackQuery):
    """Handle file browsing callbacks for clone bots"""
    callback_data = query.data
    user_id = query.from_user.id

    logger.info(f"File browsing callback: {callback_data} from user {user_id}")

    try:
        await query.answer()

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot = bot_token != Config.BOT_TOKEN

        if not is_clone_bot:
            await query.edit_message_text(
                "📁 **File Browsing**\n\n"
                "File browsing features are only available in clone bots.\n"
                "Create a clone bot to access these features.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")]
                ])
            )
            return

        try:
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)
            if clone_data:
                feature_enabled = False
                if callback_data == "random_files":
                    feature_enabled = clone_data.get('random_mode', False)
                elif callback_data == "recent_files":
                    feature_enabled = clone_data.get('recent_mode', False)
                elif callback_data == "popular_files":
                    feature_enabled = clone_data.get('popular_mode', False)

                if not feature_enabled:
                    await query.edit_message_text(
                        f"❌ **Feature Disabled**\n\n"
                        f"The {callback_data.replace('_', ' ').title()} feature has been disabled by the bot admin.\n\n"
                        f"Contact the bot administrator if you need access.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                        ])
                    )
                    return
        except Exception as e:
            logger.error(f"Error checking feature availability: {e}")

        if callback_data == "random_files":
            await handle_random_files(client, query)
        elif callback_data == "recent_files":
            await handle_recent_files(client, query)
        elif callback_data == "popular_files":
            await handle_popular_files(client, query)

    except Exception as e:
        logger.error(f"Error in file browsing callback handler: {e}")
        await query.edit_message_text("❌ An error occurred while processing your request.")

# =====================================================
# TOGGLE SETTINGS HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex(r"^toggle_(random|recent|popular)$"), group=-4)
async def handle_toggle_settings(client: Client, query: CallbackQuery):
    """Handle toggle settings"""
    await query.answer()
    user_id = query.from_user.id

    setting = query.data.split("_")[1]

    try:
        from bot.database.clone_db import get_clone_by_bot_token, update_clone_settings

        bot_token = getattr(client, 'bot_token', None)
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Unauthorized", show_alert=True)
            return

        setting_key = f"{setting}_mode"
        current_value = clone_data.get(setting_key, False)
        new_value = not current_value

        await update_clone_settings(bot_token, {setting_key: new_value})
        await clone_settings_panel_callback(client, query)

    except Exception as e:
        logger.error(f"Error toggling {setting}: {e}")
        await query.answer("❌ Error updating setting", show_alert=True)

# =====================================================
# GENERAL CALLBACK HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex("^about$"))
async def about_callback(client, query: CallbackQuery):
    text = f"""
👨‍💻 <b>Developer:</b> This Person

🤖 <b>Bot:</b> <a href='https://t.me/MoviesSearch4U_bot'>@MoviesSearch4U_bot</a>
"""
    await query.message.edit_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )

@Client.on_callback_query(filters.regex("^my_stats$"))
async def my_stats_callback(client, query: CallbackQuery):
    """Handle My Stats button click"""
    try:
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        from bot.database import get_command_stats
        from bot.utils.command_verification import check_command_limit

        stats = await get_command_stats(user_id)
        needs_verification, remaining = await check_command_limit(user_id, client)
        is_premium = await is_premium_user(user_id)

        if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
            status_text = "🔥 **Admin - Unlimited**"
        elif is_premium and remaining == -1:
            status_text = "💎 **Premium - Unlimited**"
        elif is_premium and remaining > 0:
            status_text = f"💎 **Premium - {remaining} tokens**"
        elif is_premium and remaining == 0:
            status_text = "❌ **Premium Expired**"
        elif remaining > 0:
            status_text = f"🆓 **{remaining}/3 free commands**"
        else:
            status_text = "❌ **Limit Reached**"

        stats_text = f"""📊 **Your Command Usage Stats**

👤 **User:** {query.from_user.first_name}
🎯 **Current Status:** {status_text}
📈 **Total Commands Used:** {stats['command_count']}

⏰ **Last Command:** {stats['last_command_at'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_command_at'] else 'Never'}
🔄 **Last Reset:** {stats['last_reset'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_reset'] else 'Never'}

💡 **Get Premium** for unlimited access without verification!"""

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Premium", callback_data="show_premium_plans")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        )

    except Exception as e:
        logger.error(f"ERROR in my_stats_callback: {e}")
        await query.answer("❌ Error retrieving stats. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^get_token$"))
async def get_token_callback(client, query):
    if await handle_force_sub(client, query.message):
        await query.answer()
        return

    user = query.from_user

    try:
        from bot.utils.command_verification import check_command_limit
        needs_verification, remaining = await check_command_limit(user.id, client)

        if not needs_verification and remaining > 0:
            await query.answer()
            return await query.edit_message_text(
                f"✅ You still have {remaining} commands remaining! No need to generate a new token."
            )

        from bot.database.verify_db import create_verification_token
        from bot.utils.helper import get_shortlink

        token = await create_verification_token(user.id)

        try:
            short_url = await get_shortlink(
                Config.SHORTLINK_API,
                Config.SHORTLINK_URL,
                f"https://t.me/{client.username}?start=verify-{user.id}-{token}"
            )
        except Exception as e:
            logger.warning(f"Shortlink error: {e}")
            await query.answer()
            return await query.edit_message_text("⚠️ Failed to generate shortlink. Please try again later.")

        buttons = []
        if short_url:
            buttons.append([InlineKeyboardButton("💫 Refresh Access Token", url=short_url)])

        if Config.TUTORIAL:
            buttons.append([InlineKeyboardButton("🎥 Tutorial Video", url=Config.TUTORIAL)])

        buttons.append([InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")])

        await query.answer()
        await query.edit_message_text(
            f"<i><b>🔐 Your New Access Token Generated:</b>\n\n⚠️ <b>Token Usage:</b> Complete verification to get 3 fresh commands.\n\n📋 <b>How it works:</b>\n• Every user gets 3 free commands\n• After using 3 commands, verify to get 3 more\n• This cycle continues indefinitely\n\nThis is an ads-based access token. Complete the verification to reset your command count.</i>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Token callback error: {e}")
        await query.answer()
        await query.edit_message_text("⚠️ An error occurred. Please try again later.")

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_callback(client: Client, query: CallbackQuery):
    """Handle back to start callback"""
    try:
        from bot.plugins.start_handler import start_command

        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
                self.command = ["start"]
                self.text = "/start"

            async def reply_text(self, text, reply_markup=None, **kwargs):
                await query.edit_message_text(text, reply_markup=reply_markup)

        fake_message = FakeMessage(query)
        await start_command(client, fake_message)

    except Exception as e:
        logger.error(f"Error in back_to_start callback: {e}")
        await query.answer("❌ Error going back to start. Please send /start", show_alert=True)

@Client.on_callback_query(filters.regex("^close$"))
async def close(client, query):
    await query.message.delete()
    await query.answer("Closed Successfully!")

@Client.on_callback_query(filters.regex("^show_premium_plans$"))
async def show_premium_callback(client, query: CallbackQuery):
    if await handle_force_sub(client, query.message):
        await query.answer()
        return

    user_id = query.from_user.id

    if await is_premium_user(user_id):
        return await query.answer("✨ You're already a Premium Member!", show_alert=True)

    try:
        PREMIUM_PLANS = {
            "basic": {
                "name": "Basic Token Pack",
                "price": "29",
                "tokens": 50,
                "description": "50 Command Tokens"
            },
            "standard": {
                "name": "Standard Token Pack",
                "price": "79",
                "tokens": 150,
                "description": "150 Command Tokens"
            },
            "premium": {
                "name": "Premium Token Pack",
                "price": "149",
                "tokens": 300,
                "description": "300 Command Tokens"
            },
            "unlimited": {
                "name": "Unlimited Access",
                "price": "299",
                "tokens": -1,
                "description": "Unlimited Commands for 1 Year"
            }
        }

        buttons = []
        for plan_key, plan_info in PREMIUM_PLANS.items():
            buttons.append([
                InlineKeyboardButton(
                    f"💎 {plan_info['name']} - {plan_info['price']}",
                    callback_data=f"buy_premium:{plan_key}"
                )
            ])

        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])

        await query.edit_message_text(
            "💎 **Upgrade to Premium Membership**\n\n"
            "Choose your plan:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error showing premium plans: {e}")
        await query.answer("❌ Error loading plans", show_alert=True)

@Client.on_callback_query(filters.regex("^settings$"))
async def settings_callback(client: Client, query: CallbackQuery):
    """Handle settings button callback"""
    try:
        user_id = query.from_user.id
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        is_clone_bot = (
            bot_token != Config.BOT_TOKEN and
            (hasattr(client, 'is_clone') and client.is_clone or
             hasattr(client, 'clone_config') and client.clone_config or
             hasattr(client, 'clone_data'))
        )

        if is_clone_bot:
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            if clone_data and clone_data.get('admin_id') == user_id:
                class FakeMessage:
                    def __init__(self, query):
                        self.from_user = query.from_user
                        self.chat = query.message.chat
                        self.message_id = query.message.id

                    async def reply_text(self, text, reply_markup=None, **kwargs):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                    async def edit_message_text(self, text, reply_markup=None, **kwargs):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                from bot.plugins.clone_admin_unified import clone_settings_command
                fake_message = FakeMessage(query)
                await clone_settings_command(client, fake_message)
                return
            else:
                await query.answer("❌ Only clone admin can access settings.", show_alert=True)
                return
        else:
            if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
                await query.answer("❌ Only admins can access settings.", show_alert=True)
                return

            text = "⚙️ **Mother Bot Settings**\n\n"
            text += "🔧 **Admin Panel Access Only**\n"
            text += "Settings are managed through admin commands."

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        traceback.print_exc()
        await query.answer("❌ Error loading settings. Please try again.", show_alert=True)

# =====================================================
# START MENU HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex("^(manage_my_clone|user_profile|premium_info|help_menu|about_bot|about_water|admin_panel|bot_management)$"), group=95)
async def handle_start_menu_callbacks(client: Client, query: CallbackQuery):
    """Handle start menu button callbacks"""
    callback_data = query.data
    user_id = query.from_user.id

    try:
        await query.answer()

        if callback_data == "user_profile":
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

        elif callback_data == "manage_my_clone":
            # Import and call the management handler
            try:
                from bot.handlers.clonebot.management import handle_manage_clones
                await handle_manage_clones(client, query)
            except Exception as e:
                logger.error(f"Error loading clone management: {e}")
                await query.edit_message_text(
                    "❌ Error loading clone management. Please try /start",
                    reply_markup=InlineKeyboardMarkup([
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
                "• Contact admin: @admin",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in start menu callback {callback_data}: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# =====================================================
# CLONE SPECIFIC HANDLERS
# =====================================================
@Client.on_callback_query(filters.regex("^goto_clone_settings$"))
async def handle_goto_clone_settings(client: Client, query: CallbackQuery):
    """Handle goto clone settings callback"""
    try:
        from bot.plugins.clone_admin_unified import clone_settings_command
        await clone_settings_command(client, query)
    except Exception as e:
        logger.error(f"Error in goto clone settings: {e}")
        await query.answer("❌ Error opening settings.", show_alert=True)

@Client.on_callback_query(filters.regex("^goto_admin_panel$"))
async def handle_goto_admin_panel(client: Client, query: CallbackQuery):
    """Handle goto admin panel callback"""
    try:
        from bot.plugins.clone_admin_unified import clone_admin_command
        await clone_admin_command(client, query)
    except Exception as e:
        logger.error(f"Error in goto admin panel: {e}")
        await query.answer("❌ Error opening admin panel.", show_alert=True)

# =====================================================
# HELPER FUNCTIONS
# =====================================================
async def handle_random_files(client: Client, query: CallbackQuery):
    """Handle random files browsing"""
    try:
        await query.edit_message_text(
            "🎲 **Random Files**\n\n"
            "This feature shows random files from the clone's database.\n\n"
            "⚠️ **Feature Implementation Needed**\n"
            "Random file browsing is not yet implemented for this clone.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in random files handler: {e}")
        await query.edit_message_text("❌ Error loading random files.")

async def handle_recent_files(client: Client, query: CallbackQuery):
    """Handle recent files browsing"""
    try:
        await query.edit_message_text(
            "🆕 **Recent Files**\n\n"
            "This feature shows recently added files from the clone's database.\n\n"
            "⚠️ **Feature Implementation Needed**\n"
            "Recent file browsing is not yet implemented for this clone.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in recent files handler: {e}")
        await query.edit_message_text("❌ Error loading recent files.")

async def handle_popular_files(client: Client, query: CallbackQuery):
    """Handle popular files browsing"""
    try:
        await query.edit_message_text(
            "🔥 **Popular Files**\n\n"
            "This feature shows popular/most downloaded files from the clone's database.\n\n"
            "⚠️ **Feature Implementation Needed**\n"
            "Popular file browsing is not yet implemented for this clone.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in popular files handler: {e}")
        await query.edit_message_text("❌ Error loading popular files.")

# =====================================================
# CATCH-ALL HANDLER
# =====================================================
@Client.on_callback_query(group=99)
async def catch_all_callback_handler(client: Client, query: CallbackQuery):
    """Catch-all callback handler for unhandled callbacks"""
    callback_data = query.data
    user_id = query.from_user.id

    logger.warning(f"Unhandled callback: {callback_data} from user {user_id}")

    try:
        await query.answer("⚠️ This button is not yet implemented.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in catch-all callback handler: {e}")
