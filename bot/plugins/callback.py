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
async def random_files_callback(client, query: CallbackQuery):
    """Handle random files callback"""
    try:
        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        # Detect if this is mother bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or
            hasattr(client, 'is_clone') and client.is_clone or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

        # Redirect if mother bot
        if not is_clone_bot and bot_token == Config.BOT_TOKEN:
            await query.answer("❌ Random files feature is only available in clone bots.", show_alert=True)
            return

        user_id = query.from_user.id

        # Check command limit
        from bot.utils.command_verification import check_command_limit, use_command
        needs_verification, remaining = await check_command_limit(user_id, client)

        if needs_verification:
            # Get verification mode for appropriate message
            from bot.utils.token_verification import TokenVerificationManager
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = f"🔐 **Verification Required!**\n\nGet a verification token for {duration} hours of unlimited access!"
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = f"🔐 **Verification Required!**\n\nGet a verification token for {command_limit} more commands!"

            await query.answer()
            return await query.edit_message_text(message_text, reply_markup=buttons)

        # Use command
        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=buttons
            )

        await query.answer("Getting random files...", show_alert=False)

        # Import and execute random files
        from bot.plugins.search import handle_random_files
        await handle_random_files(client, query.message, is_callback=True, skip_command_check=True)

    except Exception as e:
        logger.error(f"ERROR in random_files_callback: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^recent_files$"))
async def recent_files_callback(client: Client, query: CallbackQuery):
    """Handle recent files button"""
    try:
        # Check if this is mother bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.answer("Recent file features are disabled in the mother bot. This functionality is only available in clone bots.", show_alert=True)
            return

        # Check if recent feature is enabled in clone settings
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or not clone_data.get('recent_mode', True):
            await query.answer("❌ Recent files feature is disabled by admin.", show_alert=True)
            return

        # Check command access and token verification
        if not await check_command_access(client, query.from_user.id, "recent"):
            await query.answer("❌ You don't have access or need to verify token.", show_alert=True)
            return

        # Rest of the recent files logic...
        await handle_recent_files_request(client, query)

    except Exception as e:
        logger.error(f"Error in recent files callback: {e}")
        await query.answer("❌ Error processing request.", show_alert=True)

@Client.on_callback_query(filters.regex("^popular_files$"))
async def popular_files_callback(client: Client, query: CallbackQuery):
    """Handle popular files button"""
    try:
        # Check if this is mother bot
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            await query.answer("Popular file features are disabled in the mother bot. This functionality is only available in clone bots.", show_alert=True)
            return

        # Check if popular feature is enabled in clone settings
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or not clone_data.get('popular_mode', True):
            await query.answer("❌ Popular files feature is disabled by admin.", show_alert=True)
            return

        # Check command access and token verification
        if not await check_command_access(client, query.from_user.id, "popular"):
            await query.answer("❌ You don't have access or need to verify token.", show_alert=True)
            return

        # Rest of the popular files logic...
        await handle_popular_files_request(client, query)

    except Exception as e:
        logger.error(f"Error in popular files callback: {e}")
        await query.answer("❌ Error processing request.", show_alert=True)

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
            
            # Show mother bot settings
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
        
        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Only clone admin can access settings.", show_alert=True)
            return
        
        # Load clone settings
        from bot.plugins.clone_admin_settings import clone_settings_command
        await clone_settings_command(client, query.message)
        
    except Exception as e:
        logger.error(f"Error in clone settings panel callback: {e}")
        await query.answer("❌ Error loading settings panel. Please try again.", show_alert=True)

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

# Removed conflicting handlers - these features are disabled in mother bot
            ])
        )
    except Exception as e:
        logger.error(f"ERROR in popular_files_callback: {e}")
        await query.answer("❌ Feature unavailable.", show_alert=True)

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

        status_text = "🔥 **Unlimited**" if remaining == -1 else f"🆓 **{remaining}/3**" if remaining > 0 else "❌ **Limit Reached**"

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