# Cleaned & Refactored by @Mak0912 (TG)

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.utils import get_messages, get_readable_time, schedule_manager, get_shortlink, handle_force_sub
from bot.database import add_user, present_user, is_verified, validate_token_and_verify, is_premium_user, increment_access_count
from bot.utils.command_verification import check_command_limit, use_command
from bot.database.verify_db import create_verification_token
import traceback

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
        needs_verification, remaining = await check_command_limit(user_id)
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
        print(f"ERROR in my_stats_callback: {e}")
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
        needs_verification, remaining = await check_command_limit(user.id)

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
            print(f"Shortlink error: {e}")
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
        print(f"Token callback error: {e}")
        await query.answer()
        await query.edit_message_text("⚠️ An error occurred. Please try again later.")

@Client.on_callback_query(filters.regex("^close$"))
async def close(client, query):
    await query.message.delete()
    await query.answer("Closed Successfully!")

@Client.on_callback_query(filters.regex("^execute_rand$"))
async def execute_rand_callback(client, query: CallbackQuery):
    """Handle Get Random Files button click"""
    try:
        print(f"DEBUG: Execute rand callback triggered by user {query.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        # First check if verification is needed
        needs_verification, remaining = await check_command_limit(user_id)

        if needs_verification:
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Verification Required!**\n\nYou need to verify your account to continue. Get a verification token to access 3 more commands!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Try to use command
        if not await use_command(user_id):
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Acknowledge the callback first
        await query.answer("Getting random files...", show_alert=False)

        # Import and execute the random files function
        try:
            from bot.plugins.search import handle_random_files
            await handle_random_files(client, query.message, is_callback=True, skip_command_check=True)
        except ImportError as e:
            print(f"Import error for handle_random_files: {e}")
            await query.edit_message_text("❌ Random files feature temporarily unavailable.")

    except Exception as e:
        print(f"ERROR in execute_rand_callback: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

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
            buttons.append([
                InlineKeyboardButton(
                    f"💎 {plan_info['name']} - ₹{plan_info['price']}",
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
            "💰 **Choose Your Plan:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        print(f"Error showing premium plans: {e}")
        await query.answer("❌ Error loading premium plans. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^rand_recent$"))
async def recent_files_callback(client, query: CallbackQuery):
    """Handle Recent Added button click - send recent files directly"""
    try:
        print(f"DEBUG: Recent files callback triggered by user {query.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        # First check if verification is needed
        needs_verification, remaining = await check_command_limit(user_id)

        if needs_verification:
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Verification Required!**\n\nYou need to verify your account to continue. Get a verification token to access 3 more commands!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Try to use command
        if not await use_command(user_id):
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Acknowledge the callback first
        await query.answer("Getting recent files...", show_alert=False)

        # Import and execute the recent files function
        try:
            from bot.plugins.search import handle_recent_files_direct
            await handle_recent_files_direct(client, query.message, is_callback=True)
        except ImportError as e:
            print(f"Import error for handle_recent_files_direct: {e}")
            await query.edit_message_text("❌ Recent files feature temporarily unavailable.")

    except Exception as e:
        print(f"ERROR in recent_files_callback: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^rand_popular$"))
async def popular_files_callback(client, query: CallbackQuery):
    """Handle Popular button click - send popular files directly"""
    try:
        print(f"DEBUG: Popular files callback triggered by user {query.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        # First check if verification is needed
        needs_verification, remaining = await check_command_limit(user_id)

        if needs_verification:
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Verification Required!**\n\nYou need to verify your account to continue. Get a verification token to access 3 more commands!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Try to use command
        if not await use_command(user_id):
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Acknowledge the callback first
        await query.answer("Getting popular files...", show_alert=False)

        # Import and execute the popular files function (direct media sending)
        try:
            from bot.plugins.search import handle_popular_files_direct
            await handle_popular_files_direct(client, query.message, is_callback=True)
        except ImportError as e:
            print(f"Import error for handle_popular_files_direct: {e}")
            await query.edit_message_text("❌ Popular files feature temporarily unavailable.")

    except Exception as e:
        print(f"ERROR in popular_files_callback: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

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
        needs_verification, remaining = await check_command_limit(user_id)

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
        print(f"ERROR in rand_stats_callback: {e}")
        await query.answer("❌ Error retrieving stats. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex("^rand_new$"))
async def new_random_callback(client, query: CallbackQuery):
    """Handle More Random button click - send new random files"""
    try:
        print(f"DEBUG: New random callback triggered by user {query.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, query.message):
            await query.answer()
            return

        user_id = query.from_user.id

        # First check if verification is needed
        needs_verification, remaining = await check_command_limit(user_id)

        if needs_verification:
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Verification Required!**\n\nYou need to verify your account to continue. Get a verification token to access 3 more commands!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Try to use command
        if not await use_command(user_id):
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await query.answer()
            return await query.edit_message_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Acknowledge the callback first
        await query.answer("Getting new random files...", show_alert=False)

        # Import and execute the random files function
        try:
            from bot.plugins.search import handle_random_files
            await handle_random_files(client, query.message, is_callback=True, skip_command_check=True)
        except ImportError as e:
            print(f"Import error for handle_random_files: {e}")
            await query.edit_message_text("❌ Random files feature temporarily unavailable.")

    except Exception as e:
        print(f"ERROR in new_random_callback: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

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
            "basic": {"name": "Basic Token Pack", "price": "29", "tokens": 50},
            "standard": {"name": "Standard Token Pack", "price": "79", "tokens": 150},
            "premium": {"name": "Premium Token Pack", "price": "149", "tokens": 300},
            "unlimited": {"name": "Unlimited Access", "price": "299", "tokens": -1}
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
        print(f"Error in buy_premium_callback: {e}")
        await query.answer("❌ Error processing request. Please try again.", show_alert=True)

# Removed debug callback handler to prevent conflicts with specific handlers