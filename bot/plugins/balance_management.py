from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.balance_db import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^add_balance$"))
async def show_balance_options(client: Client, query: CallbackQuery):
    """Show balance addition options"""
    await query.answer()
    
    user_id = query.from_user.id
    current_balance = await get_user_balance(user_id)
    
    text = f"💳 **Add Balance**\n\n"
    text += f"💰 **Current Balance:** ${current_balance:.2f}\n\n"
    text += f"💵 **Quick Add Options:**\n\n"
    text += f"Choose an amount to add to your balance:\n"
    text += f"• Perfect for creating clones\n"
    text += f"• Instant credit after payment\n"
    text += f"• Secure payment processing\n\n"
    text += f"💡 **Minimum clone cost:** $3.00"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💵 $5", callback_data="add_balance_5"),
            InlineKeyboardButton("💰 $10", callback_data="add_balance_10")
        ],
        [
            InlineKeyboardButton("💎 $25", callback_data="add_balance_25"),
            InlineKeyboardButton("🎯 $50", callback_data="add_balance_50")
        ],
        [
            InlineKeyboardButton("💳 Custom Amount", callback_data="add_balance_custom"),
            InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{Config.OWNER_USERNAME if hasattr(Config, 'OWNER_USERNAME') else 'admin'}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_message(filters.command("balance") & filters.private)
async def check_balance_command(client: Client, message: Message):
    """Check user balance and transaction history"""
    user_id = message.from_user.id

    # Create user profile if doesn't exist
    user_profile = await create_user_profile(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    if not user_profile:
        return await message.reply_text("❌ Error accessing your profile. Please try again.")

    # Get transaction history
    transactions = await get_user_transactions(user_id, 5)

    # Build response
    response = (
        f"💰 **Your Wallet**\n\n"
        f"👤 **User:** {message.from_user.first_name}\n"
        f"💵 **Current Balance:** ${user_profile['balance']:.2f}\n"
        f"📊 **Total Spent:** ${user_profile.get('total_spent', 0):.2f}\n"
        f"📅 **Member Since:** {user_profile['created_at'].strftime('%Y-%m-%d')}\n\n"
    )

    if transactions:
        response += "📋 **Recent Transactions:**\n"
        for tx in transactions:
            tx_type = "+" if tx['type'] == 'credit' else "-"
            response += (
                f"• {tx_type}${tx['amount']:.2f} - {tx['description']}\n"
                f"  {tx['timestamp'].strftime('%m/%d %H:%M')}\n"
            )
    else:
        response += "📋 **No recent transactions**"

    # Add keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_balance")],
        [InlineKeyboardButton("📜 Full History", callback_data="full_transaction_history")]
    ])

    await message.reply_text(response, reply_markup=keyboard)

@Client.on_message(filters.command("addbalance") & filters.private)
async def add_balance_command(client: Client, message: Message):
    """Add balance to user (admin only)"""
    user_id = message.from_user.id

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only administrators can add balance to users.")

    # Parse command
    try:
        parts = message.text.split()
        if len(parts) < 3:
            return await message.reply_text(
                "❌ **Usage:** `/addbalance <user_id> <amount> [reason]`\n\n"
                "**Examples:**\n"
                "`/addbalance 123456789 10.50 Bonus credit`\n"
                "`/addbalance 123456789 25 Monthly allowance`"
            )

        target_user_id = int(parts[1])
        amount = float(parts[2])
        reason = " ".join(parts[3:]) if len(parts) > 3 else "Admin credit"

        if amount <= 0:
            return await message.reply_text("❌ Amount must be positive.")

        # Add balance
        success, result_message = await add_balance(target_user_id, amount, reason, user_id)

        if success:
            # Get user info
            try:
                target_user = await client.get_users(target_user_id)
                user_info = f"@{target_user.username}" if target_user.username else target_user.first_name
            except:
                user_info = f"User {target_user_id}"

            # Get updated balance
            from bot.database.balance_db import get_user_balance
            new_balance = await get_user_balance(target_user_id)

            await message.reply_text(
                f"✅ **Balance Added Successfully**\n\n"
                f"👤 **User:** {user_info}\n"
                f"💵 **Amount Added:** ${amount:.2f}\n"
                f"💰 **New Balance:** ${new_balance:.2f}\n"
                f"📝 **Reason:** {reason}\n"
                f"👨‍💼 **Added by:** {message.from_user.first_name}"
            )

            # Notify the user
            try:
                await client.send_message(
                    target_user_id,
                    f"💰 **Balance Credit Received**\n\n"
                    f"💵 **Amount:** +${amount:.2f}\n"
                    f"💰 **New Balance:** ${new_balance:.2f}\n"
                    f"📝 **Reason:** {reason}\n"
                    f"👨‍💼 **Added by:** Administrator\n\n"
                    f"Use `/balance` to check your updated balance."
                )
            except Exception as e:
                await message.reply_text(f"⚠️ Balance added but failed to notify user: {e}")
        else:
            await message.reply_text(f"❌ Failed to add balance: {result_message}")

    except ValueError:
        await message.reply_text("❌ Invalid user ID or amount format.")
    except Exception as e:
        await message.reply_text(f"❌ Error adding balance: {e}")

@Client.on_message(filters.command("userbalances") & filters.private)
async def list_user_balances_command(client: Client, message: Message):
    """List all user balances (admin only)"""
    user_id = message.from_user.id

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only administrators can view user balances.")

    try:
        users = await get_all_user_balances()

        if not users:
            return await message.reply_text("📊 No user profiles found.")

        # Build response
        response = "💰 **All User Balances**\n\n"
        total_balance = 0

        for i, user in enumerate(users[:20]):  # Limit to top 20
            total_balance += user['balance']
            username_display = f"@{user.get('username', 'N/A')}" if user.get('username') else "No username"
            response += (
                f"{i+1}. **{user.get('first_name', 'Unknown')}** ({username_display})\n"
                f"   💵 ${user['balance']:.2f} | 📊 Spent: ${user.get('total_spent', 0):.2f}\n"
            )

        response += f"\n💼 **Total System Balance:** ${total_balance:.2f}"

        if len(users) > 20:
            response += f"\n\n*Showing top 20 of {len(users)} users*"

        await message.reply_text(response)

    except Exception as e:
        await message.reply_text(f"❌ Error retrieving balances: {e}")

@Client.on_message(filters.command("checkbalance") & filters.private)
async def check_user_balance_command(client: Client, message: Message):
    """Check any user's balance (admin only)"""
    user_id = message.from_user.id

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only administrators can check other users' balances.")

    # Parse command
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.reply_text(
                "❌ **Usage:** `/checkbalance <user_id>`\n\n"
                "**Example:**\n"
                "`/checkbalance 123456789`"
            )

        target_user_id = int(parts[1])

        # Get user profile and balance
        from bot.database.balance_db import get_user_profile, get_user_transactions
        profile = await get_user_profile(target_user_id)

        if not profile:
            return await message.reply_text(f"❌ User {target_user_id} not found in database.")

        # Get recent transactions
        transactions = await get_user_transactions(target_user_id, 5)

        # Get user info
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"@{target_user.username}" if target_user.username else target_user.first_name
        except:
            user_info = f"User {target_user_id}"

        text = f"💳 **Balance Information**\n\n"
        text += f"👤 **User:** {user_info}\n"
        text += f"🆔 **ID:** `{target_user_id}`\n"
        text += f"💰 **Current Balance:** ${profile['balance']:.2f}\n"
        text += f"💸 **Total Spent:** ${profile.get('total_spent', 0):.2f}\n"
        text += f"💵 **Total Earned:** ${profile.get('total_earned', 0):.2f}\n"
        text += f"📅 **Member Since:** {profile['created_at'].strftime('%Y-%m-%d')}\n"
        text += f"🔄 **Last Transaction:** {profile['last_transaction'].strftime('%Y-%m-%d %H:%M')}\n\n"

        if transactions:
            text += f"📊 **Recent Transactions:**\n"
            for trans in transactions:
                sign = "+" if trans['type'] == 'credit' else "-"
                text += f"• {sign}${trans['amount']:.2f} - {trans['description']}\n"
        else:
            text += f"📊 **No recent transactions**"

        await message.reply_text(text)

    except ValueError:
        await message.reply_text("❌ Invalid user ID format.")
    except Exception as e:
        await message.reply_text(f"❌ Error checking balance: {e}")

# Callback handlers
@Client.on_callback_query(filters.regex("^refresh_balance$"))
async def refresh_balance_callback(client: Client, query: CallbackQuery):
    """Refresh balance display"""
    await query.answer("🔄 Refreshing...")

    # Simulate the balance command
    fake_message = type('Message', (), {
        'from_user': query.from_user,
        'reply_text': lambda text, reply_markup=None: query.edit_message_text(text, reply_markup=reply_markup)
    })()

    await check_balance_command(client, fake_message)

@Client.on_callback_query(filters.regex("^full_transaction_history$"))
async def full_transaction_history_callback(client: Client, query: CallbackQuery):
    """Show full transaction history"""
    user_id = query.from_user.id

    try:
        transactions = await get_user_transactions(user_id, 20)

        if not transactions:
            return await query.answer("No transactions found.", show_alert=True)

        response = "📜 **Transaction History**\n\n"

        for tx in transactions:
            tx_type = "📈 Credit" if tx['type'] == 'credit' else "📉 Debit"
            amount_display = f"+${tx['amount']:.2f}" if tx['type'] == 'credit' else f"-${tx['amount']:.2f}"
            response += (
                f"**{tx_type}:** {amount_display}\n"
                f"📝 {tx['description']}\n"
                f"📅 {tx['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"💰 Balance After: ${tx.get('balance_after', 0):.2f}\n\n"
            )

        await query.edit_message_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Balance", callback_data="refresh_balance")]
            ])
        )

    except Exception as e:
        await query.answer(f"Error loading history: {e}", show_alert=True)