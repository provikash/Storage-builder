# Cleaned & Refactored by @Mak0912 (TG)

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.utils import get_messages, get_readable_time, schedule_manager, get_shortlink, handle_force_sub
from bot.database import add_user, present_user, is_verified, validate_token_and_verify, is_premium_user, increment_access_count
from bot.utils.command_verification import check_command_limit, use_command
from bot.database.verify_db import create_verification_token
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        from bot.database import get_command_stats
        from bot.utils.command_verification import check_command_limit

        stats = await get_command_stats(user_id)
        needs_verification, remaining = await check_command_limit(user_id, client)
        is_premium = await is_premium_user(user_id)

        # Determine status text based on user type
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
    # Check force subscription first
    if await handle_force_sub(client, query.message):
        await query.answer()
        return

    user = query.from_user

    try:
        # Check command count instead of verification status
        from bot.utils.command_verification import check_command_limit
        needs_verification, remaining = await check_command_limit(user.id, client)

        if not needs_verification and remaining > 0:
            await query.answer()
            return await query.edit_message_text(
                f"✅ You still have {remaining} commands remaining! No need to generate a new token."
            )

        # Generate and store token
        from bot.database.verify_db import create_verification_token
        from bot.utils.helper import get_shortlink

        token = await create_verification_token(user.id)

        # Create short link for /start=verify-<userid>-<token>
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

        # Prepare buttons
        buttons = []

        # Add refresh token button
        if short_url:
            buttons.append([InlineKeyboardButton("💫 Refresh Access Token", url=short_url)])

        # Add tutorial button
        if Config.TUTORIAL:
            buttons.append([InlineKeyboardButton("🎥 Tutorial Video", url=Config.TUTORIAL)])

        # Add remove ads button
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
        # Import start handler
        from bot.plugins.start_handler import start_handler

        # Create a fake message object for start handler
        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
                self.command = ["start"]
                self.text = "/start"

            async def reply_text(self, text, reply_markup=None, **kwargs):
                await query.edit_message_text(text, reply_markup=reply_markup)

        fake_message = FakeMessage(query)
        await start_handler(client, fake_message)

    except Exception as e:
        logger.error(f"Error in back_to_start callback: {e}")
        await query.answer("❌ Error going back to start. Please send /start", show_alert=True)

@Client.on_callback_query(filters.regex("^close$"))
async def close(client, query):
    await query.message.delete()
    await query.answer("Closed Successfully!")

# Mock functions for demonstration purposes if they are not defined elsewhere
async def check_command_access(client, user_id, feature_name):
    """
    Mock function to check command access.
    Replace with actual implementation.
    """
    logger.info(f"Checking command access for user {user_id}, feature: {feature_name}")
    # Placeholder: Assume access is granted if not admin and not limited
    if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
        return True

    needs_verification, remaining = await check_command_limit(user_id, client)
    if needs_verification:
        return False
    return True

async def handle_random_file_request(client, query: CallbackQuery):
    """
    Mock function to handle random file requests.
    Replace with actual implementation.
    """
    logger.info(f"Handling random file request for user {query.from_user.id}")
    await query.answer("Processing random files...", show_alert=False)
    try:
        from bot.plugins.search import handle_random_files
        await handle_random_files(client, query.message, is_callback=True, skip_command_check=True)
    except ImportError as e:
        logger.error(f"Import error for handle_random_files: {e}")
        await query.edit_message_text("❌ Random files feature temporarily unavailable.")
    except Exception as e:
        logger.error(f"Error in handle_random_file_request: {e}")
        await query.answer("❌ An error occurred while fetching random files.", show_alert=True)


async def handle_recent_files_request(client, query: CallbackQuery):
    """
    Mock function to handle recent files requests.
    Replace with actual implementation.
    """
    logger.info(f"Handling recent files request for user {query.from_user.id}")
    await query.answer("Processing recent files...", show_alert=False)
    try:
        from bot.plugins.search import handle_recent_files_direct
        await handle_recent_files_direct(client, query.message, is_callback=True)
    except Exception as e:
        logger.error(f"Error in handle_recent_files_request: {e}")
        await query.answer("❌ An error occurred while fetching recent files.", show_alert=True)

async def handle_popular_files_request(client, query: CallbackQuery):
    """
    Mock function to handle popular files requests.
    Replace with actual implementation.
    """
    logger.info(f"Handling popular files request for user {query.from_user.id}")
    await query.answer("Processing popular files...", show_alert=False)
    try:
        from bot.plugins.search import handle_popular_files_direct
        await handle_popular_files_direct(client, query.message, is_callback=True)
    except Exception as e:
        logger.error(f"Error in handle_popular_files_request: {e}")
        await query.answer("❌ An error occurred while fetching popular files.", show_alert=True)


@Client.on_callback_query(filters.regex("^random_files$"))
async def random_files_callback(client: Client, query: CallbackQuery):
    """Handle random files button"""
    user_id = query.from_user.id
    logger.info(f"Random files callback from user {user_id}")

    # Check if feature is enabled
    from bot.utils.clone_config_loader import clone_config_loader
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config.get('features', {}).get('random_files', True):
        await query.answer("❌ This feature is disabled by the admin.", show_alert=True)
        return

    # Check force subscription first
    if await handle_force_sub(client, query.message):
        return

    # Placeholder for random files functionality
    await query.edit_message_text("🎲 **Random Files**\n\nShowing random files...")

@Client.on_callback_query(filters.regex("^recent_files$"))
async def recent_files_callback(client: Client, query: CallbackQuery):
    """Handle recent files button"""
    user_id = query.from_user.id
    logger.info(f"Recent files callback from user {user_id}")

    # Check if feature is enabled
    from bot.utils.clone_config_loader import clone_config_loader
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config.get('features', {}).get('recent_files', True):
        await query.answer("❌ This feature is disabled by the admin.", show_alert=True)
        return

    # Check force subscription first
    if await handle_force_sub(client, query.message):
        return

    # Placeholder for recent files functionality
    await query.edit_message_text("🆕 **Recent Files**\n\nShowing recent files...")

@Client.on_callback_query(filters.regex("^popular_files$"))
async def popular_files_callback(client: Client, query: CallbackQuery):
    """Handle popular files button"""
    user_id = query.from_user.id
    logger.info(f"Popular files callback from user {user_id}")

    # Check if feature is enabled
    from bot.utils.clone_config_loader import clone_config_loader
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config.get('features', {}).get('popular_files', True):
        await query.answer("❌ This feature is disabled by the admin.", show_alert=True)
        return

    # Check force subscription first  
    if await handle_force_sub(client, query.message):
        return

    # Placeholder for popular files functionality
    await query.edit_message_text("🔥 **Most Popular Files**\n\nShowing most popular files...")

@Client.on_callback_query(filters.regex("^settings$"))
async def settings_callback(client: Client, query: CallbackQuery):
    """Handle settings button callback"""
    try:
        user_id = query.from_user.id
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        logger.info(f"Settings callback triggered by user {user_id}, bot_token: {bot_token}")

        # Check if this is a clone bot
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN and
            (hasattr(client, 'is_clone') and client.is_clone or
             hasattr(client, 'clone_config') and client.clone_config or
             hasattr(client, 'clone_data'))
        )

        logger.info(f"Is clone bot: {is_clone_bot}")

        if is_clone_bot:
            # Check if user is clone admin
            from bot.database.clone_db import get_clone_by_bot_token
            clone_data = await get_clone_by_bot_token(bot_token)

            logger.info(f"Clone data: {clone_data}")

            if clone_data and clone_data.get('admin_id') == user_id:
                # Create a fake message object for clone settings
                class FakeMessage:
                    def __init__(self, query):
                        self.from_user = query.from_user
                        self.chat = query.message.chat
                        self.message_id = query.message.id

                    async def reply_text(self, text, reply_markup=None, **kwargs):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                    async def edit_message_text(self, text, reply_markup=None, **kwargs):
                        await query.edit_message_text(text, reply_markup=reply_markup)

                # Redirect to clone settings
                from bot.plugins.clone_admin_settings import clone_settings_command
                fake_message = FakeMessage(query)
                await clone_settings_command(client, fake_message)
                return
            else:
                await query.answer("❌ Only clone admin can access settings.", show_alert=True)
                return
        else:
            # Mother bot settings - only for admins
            if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
                await query.answer("❌ Only admins can access settings.", show_alert=True)
                return

            # Import token verification manager to check settings
            from bot.utils.token_verification import TokenVerificationManager
            token_settings = await TokenVerificationManager.get_clone_token_settings(client) # This gets global settings or clone-specific if applicable
            verification_mode = token_settings.get('verification_mode', 'command_limit') # Default to command_limit if not set

            # Build the settings text dynamically
            text = "⚙️ **Mother Bot Settings**\n\n"
            text += f"Current Token Verification Mode: **{verification_mode.replace('_', ' ').title()}**\n\n"
            text += "🔧 **Admin Panel Access Only**\n"
            text += "Settings are managed through admin commands."

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Change Token Mode", callback_data="change_token_mode")],
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )

    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        traceback.print_exc()
        await query.answer("❌ Error loading settings. Please try again.", show_alert=True)


@Client.on_callback_query(filters.regex("^show_premium_plans$"))
async def show_premium_callback(client, query: CallbackQuery):
    # Check force subscription first
    if await handle_force_sub(client, query.message):
        await query.answer()
        return

    user_id = query.from_user.id

    # Check if user is already premium
    if await is_premium_user(user_id):
        return await query.answer("✨ You're already a Premium Member!", show_alert=True)

    # Show premium plans directly
    try:
        # Premium plan configurations
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
                "tokens": -1,  # -1 means unlimited
                "description": "Unlimited Commands for 1 Year"
            }
        }

        # Premium purchase buttons
        buttons = []
        for plan_key, plan_info in PREMIUM_PLANS.items():
            discount_text = f" ({plan_info['discount']} OFF)" if plan_info.get('discount', "0%") != "0%" else ""
            buttons.append([
                InlineKeyboardButton(
                    f"💎 {plan_info['name']} - {plan_info['price']}{discount_text}",
                    callback_data=f"buy_premium:{plan_key}"
                )
            ])

        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])

        await query.edit_message_text(
            "💎 **Upgrade to Premium Membership**\n\n"
            "🎯 **Premium Benefits:**\n"
            "• 🚫 **No Ads** - Skip all verification steps\n"
            "• ⚡ **Instant Access** - Direct file downloads\n"
            "• 🔥 **Unlimited Downloads** - No restrictions\n"
            "• 👑 **Premium Support** - Priority assistance\n\n"
            "💰 **Plan Duration & Pricing:**\n"
            "• Monthly: $2.99/month (0% discount)\n"
            "• 3-Month: $2.66/month (11% discount)\n"
            "• 6-Month: $2.50/month (16% discount) \n"
            "• 12-Month: $2.25/month (25% discount)\n\n"
            "💸 **Choose Your Plan:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error showing premium plans: {e}")
        await query.answer("❌ Error loading premium plans. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^clone_settings_panel$"))
async def clone_settings_panel_callback(client: Client, query: CallbackQuery):
    """Handle clone settings panel callback"""
    try:
        user_id = query.from_user.id
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is a clone bot
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or
            hasattr(client, 'is_clone') and client.is_clone or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

        if not is_clone_bot or bot_token == Config.BOT_TOKEN:
            await query.answer("❌ Settings panel is only available in clone bots.", show_alert=True)
            return

        # Verify user is clone admin
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data:
            await query.answer("❌ Clone configuration not found.", show_alert=True)
            return
            
        # Convert both to int for proper comparison, handling MongoDB Int64 type
        stored_admin_id = clone_data.get('admin_id')
        try:
            user_id_int = int(user_id)
            stored_admin_id_int = int(stored_admin_id) if stored_admin_id else 0
            
            if user_id_int != stored_admin_id_int:
                await query.answer("❌ Only clone admin can access settings.", show_alert=True)
                return
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting IDs for comparison: {e}")
            await query.answer("❌ Error verifying admin access!", show_alert=True)
            return

        # Load clone settings
        from bot.plugins.clone_admin_settings import clone_settings_command
        await clone_settings_command(client, query.message)

    except Exception as e:
        logger.error(f"Error in clone settings panel callback: {e}")
        await query.answer("❌ Error loading settings panel. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^change_token_mode$"))
async def change_token_mode_callback(client: Client, query: CallbackQuery):
    """Handle changing token verification mode"""
    try:
        user_id = query.from_user.id

        # Only admins can change this setting
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            await query.answer("❌ Only admins can change this setting.", show_alert=True)
            return

        # Get current settings
        from bot.utils.token_verification import TokenVerificationManager
        token_settings = await TokenVerificationManager.get_clone_token_settings(client)
        current_mode = token_settings.get('verification_mode', 'command_limit')

        # Prepare buttons for changing mode
        buttons = [
            [InlineKeyboardButton("✅ Command Limit Based", callback_data="set_token_mode:command_limit")],
            [InlineKeyboardButton("⏰ Time Based", callback_data="set_token_mode:time_based")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ]

        await query.edit_message_text(
            f"⚙️ **Change Token Verification Mode**\n\n"
            f"Current Mode: **{current_mode.replace('_', ' ').title()}**\n\n"
            "Select the new mode:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in change_token_mode callback: {e}")
        await query.answer("❌ Error changing token mode. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^set_token_mode:"))
async def set_token_mode_callback(client: Client, query: CallbackQuery):
    """Handle setting the new token verification mode"""
    try:
        user_id = query.from_user.id

        # Only admins can change this setting
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            await query.answer("❌ Only admins can change this setting.", show_alert=True)
            return

        new_mode = query.data.split(":")[1]

        # Update settings
        from bot.utils.token_verification import TokenVerificationManager
        await TokenVerificationManager.set_clone_token_settings(client, {'verification_mode': new_mode})

        await query.answer(f"✅ Token verification mode set to {new_mode.replace('_', ' ').title()}!")
        # Refresh the settings message
        await settings_callback(client, query)

    except Exception as e:
        logger.error(f"Error in set_token_mode callback: {e}")
        await query.answer("❌ Error setting token mode. Please try again.", show_alert=True)


@Client.on_callback_query(filters.regex("^rand_stats$"))
async def rand_stats_callback(client, query: CallbackQuery):
    """Handle stats button click from random files"""
    try:
        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        from bot.database import get_command_stats
        from bot.utils.command_verification import check_command_limit

        stats = await get_command_stats(user_id)
        needs_verification, remaining = await check_command_limit(user_id, client)

        status_text = "🔥 **Unlimited**" if remaining == -1 else "🆓 **" + str(remaining) + "/3**" if remaining > 0 else "❌ **Limit Reached**"

        stats_text = f"""📊 **Your Usage Stats**

👤 **User:** {query.from_user.first_name}
🎯 **Current Status:** {status_text}
📈 **Total Commands Used:** {stats['command_count']}

⏰ **Last Command:** {stats['last_command_at'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_command_at'] else 'Never'}
🔄 **Last Reset:** {stats['last_reset'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_reset'] else 'Never'}

💡 **Get Premium** for unlimited access!"""

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 More Random", callback_data="rand_new")],
                [InlineKeyboardButton("💎 Premium", callback_data="show_premium_plans")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        )

    except Exception as e:
        logger.error(f"ERROR in rand_stats_callback: {e}")
        await query.answer("❌ Error retrieving stats. Please try again.", show_alert=True)


@Client.on_callback_query(filters.regex("^buy_premium:"))
async def buy_premium_callback(client, query: CallbackQuery):
    """Handle premium purchase callbacks"""
    # Check force subscription first
    if await handle_force_sub(client, query.message):
        await query.answer()
        return

    try:
        plan_key = query.data.split(":")[1]

        # Premium plan configurations
        PREMIUM_PLANS = {
            "monthly": {
                "name": "Monthly Plan",
                "price": "2.99",
                "duration": "1 Month",
                "per_month": "$2.99",
                "discount": "0%"
            },
            "quarterly": {
                "name": "3-Month Plan",
                "price": "7.99",
                "duration": "3 Months",
                "per_month": "$2.66",
                "discount": "11%"
            },
            "biannual": {
                "name": "6-Month Plan",
                "price": "14.99",
                "duration": "6 Months",
                "per_month": "$2.50",
                "discount": "16%"
            },
            "annual": {
                "name": "12-Month Plan",
                "price": "26.99",
                "duration": "12 Months",
                "per_month": "$2.25",
                "discount": "25%"
            }
        }

        plan = PREMIUM_PLANS.get(plan_key)
        if not plan:
            return await query.answer("❌ Invalid plan selected!", show_alert=True)

        # Payment instructions
        payment_text = (
            f"💎 **{plan['name']} Membership**\n"
            f"💰 **Price:** ₹{plan['price']}\n"
            f"⏱️ **Tokens:** {plan['tokens'] if plan['tokens'] != -1 else 'Unlimited'}\n\n"
            f"💳 **Payment Instructions:**\n"
            f"1. Pay ₹{plan['price']} to the following:\n"
            f"📱 **UPI ID:** `{Config.PAYMENT_UPI}`\n"
            f"🏦 **Phone Pay:** `{Config.PAYMENT_PHONE}`\n\n"
            f"2. Send screenshot to @{Config.ADMIN_USERNAME}\n"
            f"3. Include your User ID: `{query.from_user.id}`\n\n"
            f"⚠️ **Note:** Manual verification takes 5-10 minutes"
        )

        buttons = [
            [InlineKeyboardButton("📱 Contact Admin", url=f"https://t.me/termuxro")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_premium_plans")]
        ]

        await query.edit_message_text(
            payment_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in buy_premium_callback: {e}")
        await query.answer("❌ Error processing request. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("check_membership"))
async def check_membership_callback(client: Client, query: CallbackQuery):
    """Handle membership check callback"""
    user_id = query.from_user.id

    # Admin exemption
    if user_id == Config.OWNER_ID or user_id in Config.ADMINS:
        await query.answer("✅ Admin access granted!", show_alert=True)
        await query.message.delete()
        return

    # Check token verification status for non-admins
    from bot.utils.token_verification import TokenVerificationManager
    is_verified_user = await TokenVerificationManager.is_user_verified(client, user_id)

    if not is_verified_user:
        await query.answer("❌ Please verify your account first!", show_alert=True)
        return

    logger.info(f"🔍 DEBUG: Checking membership for user {user_id}")

    try:
        from bot.utils.subscription import check_all_subscriptions

        if await check_all_subscriptions(client, user_id):
            await query.answer("✅ All channels joined successfully!", show_alert=True)
            await query.message.delete()
            # Send welcome message
            await client.send_message(
                user_id,
                "🎉 **Welcome!** You have successfully joined all required channels.\n\n"
                "You can now use the bot freely. Send /start to begin!"
            )
        else:
            await query.answer("❌ Please join all required channels first!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in membership check: {e}")
        await query.answer("❌ Error checking membership. Please try again.", show_alert=True)

# Removed debug callback handler to prevent conflicts with specific handlers