from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta

from bot.database import add_premium_user, is_premium_user, get_premium_info, remove_premium
from info import Config

# Premium plan configurations - Token-based system
PREMIUM_PLANS = {
    "basic": {
        "name": "Basic Token Pack",
        "price": "₹29",
        "tokens": 50,
        "description": "50 Command Tokens"
    },
    "standard": {
        "name": "Standard Token Pack", 
        "price": "₹79",
        "tokens": 150,
        "description": "150 Command Tokens"
    },
    "premium": {
        "name": "Premium Token Pack",
        "price": "₹149", 
        "tokens": 300,
        "description": "300 Command Tokens"
    },
    "unlimited": {
        "name": "Unlimited Access",
        "price": "₹299",
        "tokens": -1,  # -1 means unlimited
        "description": "Unlimited Commands for 1 Year"
    }
}

@Client.on_message(filters.command("premium") & filters.private)
async def premium_handler(client, message):
    user = message.from_user

    # Check if user is already premium
    if await is_premium_user(user.id):
        premium_info = await get_premium_info(user.id)
        expiry = premium_info['expiry_date'].strftime("%d/%m/%Y %H:%M")

        return await message.reply_text(
            f"✨ **You're already a Premium Member!**\n\n"
            f"📋 **Plan:** {premium_info['plan_type']}\n"
            f"⏰ **Expires:** {expiry}\n\n"
            f"🎉 **Benefits:**\n"
            f"• 🚫 **No Ads** - Skip all verification\n"
            f"• ⚡ **Instant Access** - Direct file downloads\n"
            f"• 🔥 **Unlimited Downloads** - No restrictions\n"
            f"• 👑 **Premium Support** - Priority assistance"
        )

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

    await message.reply_text(
        "💎 **Upgrade to Premium Membership**\n\n"
        "🎯 **Premium Benefits:**\n"
        "• 🚫 **No Ads** - Skip all verification steps\n"
        "• ⚡ **Instant Access** - Direct file downloads\n"
        "• 🔥 **Unlimited Downloads** - No restrictions\n"
        "• 👑 **Premium Support** - Priority assistance\n\n"
        "💰 **Choose Your Plan:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^buy_premium:"))
async def buy_premium_callback(client, query: CallbackQuery):
    plan_key = query.data.split(":")[1]
    plan = PREMIUM_PLANS.get(plan_key)

    if not plan:
        return await query.answer("❌ Invalid plan selected!", show_alert=True)

    # Payment instructions
    payment_text = (
        f"💎 **{plan['name']} Membership**\n"
        f"💰 **Price:** ₹{plan['price']}\n"
        f"⏱️ **Tokens:** {plan['tokens']} \n\n"
        f"💳 **Payment Instructions:**\n"
        f"1. Pay ₹{plan['price']} to the following:\n"
        f"📱 **UPI ID:** `{Config.PAYMENT_UPI}`\n"
        f"🏦 **Phone Pay:** `{Config.PAYMENT_PHONE}`\n\n"
        f"2. Send screenshot to @{Config.ADMIN_USERNAME}\n"
        f"3. Include your User ID: `{query.from_user.id}`\n\n"
        f"⚠️ **Note:** Manual verification takes 5-10 minutes"
    )

    buttons = [
        [InlineKeyboardButton("📱 Contact Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}")],
        [InlineKeyboardButton("🔙 Back", callback_data="show_premium_plans")]
    ]

    await query.edit_message_text(
        payment_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^show_premium_plans$"))
async def show_premium_plans_callback(client, query: CallbackQuery):
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

# Admin commands for premium management
@Client.on_message(filters.command("addpremium") & filters.private)
async def add_premium_command(client, message):
    # Check if user is admin
    user_id = message.from_user.id
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ This command is only available to administrators.")
    
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/addpremium <user_id> <plan_type>`\n\nPlans: basic, standard, premium, unlimited")

    try:
        target_user_id = int(message.command[1])
        plan_type = message.command[2].lower()

        if plan_type not in PREMIUM_PLANS:
            return await message.reply_text("❌ Invalid plan type!\n\nAvailable plans: basic, standard, premium, unlimited")

        plan = PREMIUM_PLANS[plan_type]
        await add_premium_user(target_user_id, plan['name'], plan['tokens'])

        await message.reply_text(f"✅ Premium membership added!\n**User:** {target_user_id}\n**Plan:** {plan['name']}\n**Tokens:** {plan['tokens']}")

        # Notify user
        try:
            await client.send_message(
                target_user_id,
                f"🎉 **Congratulations!**\n\n"
                f"✨ You have been upgraded to **{plan['name']} Membership**\n"
                f"⏰ **Valid for:** {plan['tokens']} tokens\n\n"
                f"🎯 **Enjoy Premium Benefits:**\n"
                f"• 🚫 No Ads\n"
                f"• ⚡ Instant Access\n"
                f"• 🔥 Unlimited Downloads"
            )
        except Exception as e:
            await message.reply_text(f"✅ Premium added but couldn't notify user: {e}")

    except ValueError:
        await message.reply_text("❌ Invalid user ID! Please provide a numeric user ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command("removepremium") & filters.private)
async def remove_premium_command(client, message):
    # Check if user is admin
    user_id = message.from_user.id
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        return await message.reply_text("❌ This command is only available to administrators.")
    
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/removepremium <user_id>`")

    try:
        target_user_id = int(message.command[1])
        await remove_premium(target_user_id)
        await message.reply_text(f"✅ Premium membership removed for user {target_user_id}")
    except ValueError:
        await message.reply_text("❌ Invalid user ID! Please provide a numeric user ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Alias for testing compatibility
premium_info_command = premium_handler