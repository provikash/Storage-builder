import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import *
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store clone admin sessions
clone_admin_sessions = {}

def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    if not hasattr(client, 'clone_config') or not client.clone_config:
        return False
    return user_id == client.clone_config.get('admin_id')

def create_settings_keyboard():
    """Create the clone admin settings keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎲 Random Toggle", callback_data="clone_toggle_random"),
            InlineKeyboardButton("📊 Recent Toggle", callback_data="clone_toggle_recent")
        ],
        [
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_set_shortener"),
            InlineKeyboardButton("🔑 Token Mode", callback_data="clone_toggle_token")
        ],
        [
            InlineKeyboardButton("⏱️ Command Limit", callback_data="clone_set_limit"),
            InlineKeyboardButton("⏰ Time Base", callback_data="clone_set_timebase")
        ],
        [
            InlineKeyboardButton("📈 Clone Stats", callback_data="clone_view_stats"),
            InlineKeyboardButton("ℹ️ About Settings", callback_data="clone_about_settings")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command("settings") & filters.private)
async def clone_settings_command(client: Client, message: Message):
    """Handle /settings command for clone admins only"""
    user_id = message.from_user.id

    # Check if this is a clone bot and user is the admin
    if not hasattr(client, 'is_clone') or not client.is_clone:
        await message.reply_text("❌ This command is only available in clone bots.")
        return

    if not is_clone_admin(client, user_id):
        await message.reply_text("❌ Only the clone admin can access settings.")
        return

    try:
        # Get current clone settings
        clone_data = await get_clone_by_bot_token(client.bot_token)
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return

        settings_text = f"""
🛠️ **Clone Bot Settings**

**Bot Info:**
• Name: `{clone_data.get('bot_name', 'Unknown')}`
• Status: `{'Active' if clone_data.get('status') == 'active' else 'Inactive'}`

**Current Settings:**
• 🎲 Random Mode: `{'ON' if clone_data.get('random_mode', False) else 'OFF'}`
• 📊 Recent Mode: `{'ON' if clone_data.get('recent_mode', False) else 'OFF'}`
• 🔑 Token Verification: `{'ON' if clone_data.get('token_verification', False) else 'OFF'}`
• ⏱️ Command Limit: `{clone_data.get('command_limit', 'Unlimited')}`
• 🔗 URL Shortener: `{clone_data.get('shortener_api', 'Not Set')}`

Click the buttons below to modify settings:
        """

        await message.reply_text(
            settings_text,
            reply_markup=create_settings_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in clone settings command: {e}")
        await message.reply_text("❌ Error loading settings. Please try again.")

@Client.on_callback_query(filters.regex("^clone_"))
async def handle_clone_settings_callbacks(client: Client, query: CallbackQuery):
    """Handle clone settings callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    # Check if this is a clone bot and user is the admin
    if not hasattr(client, 'is_clone') or not client.is_clone:
        await query.answer("❌ Not available in this bot.", show_alert=True)
        return

    if not is_clone_admin(client, user_id):
        await query.answer("❌ Only clone admin can access settings.", show_alert=True)
        return

    try:
        clone_data = await get_clone_by_bot_token(client.bot_token)
        if not clone_data:
            await query.answer("❌ Clone configuration not found.", show_alert=True)
            return

        bot_id = clone_data.get('bot_id')

        if callback_data == "clone_toggle_random":
            current_state = clone_data.get('random_mode', False)
            new_state = not current_state
            await update_clone_setting(bot_id, 'random_mode', new_state)
            await query.answer(f"🎲 Random mode {'enabled' if new_state else 'disabled'}")

        elif callback_data == "clone_toggle_recent":
            current_state = clone_data.get('recent_mode', False)
            new_state = not current_state
            await update_clone_setting(bot_id, 'recent_mode', new_state)
            await query.answer(f"📊 Recent mode {'enabled' if new_state else 'disabled'}")

        elif callback_data == "clone_toggle_token":
            current_state = clone_data.get('token_verification', False)
            new_state = not current_state
            await update_clone_setting(bot_id, 'token_verification', new_state)
            await query.answer(f"🔑 Token verification {'enabled' if new_state else 'disabled'}")

        elif callback_data == "clone_set_shortener":
            clone_admin_sessions[user_id] = {
                'action': 'set_shortener',
                'bot_id': bot_id,
                'message_id': query.message.id
            }

            await query.edit_message_text(
                "🔗 **Set URL Shortener**\n\n"
                "Send your shortener API URL and key in this format:\n"
                "`api_url|api_key`\n\n"
                "Example: `https://short.ly/api|your_api_key`\n\n"
                "Send 'none' to disable shortener.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_set_limit":
            clone_admin_sessions[user_id] = {
                'action': 'set_limit',
                'bot_id': bot_id,
                'message_id': query.message.id
            }

            await query.edit_message_text(
                "⏱️ **Set Command Limit**\n\n"
                "Send the maximum number of commands per user per day.\n\n"
                "Examples:\n"
                "• `10` - 10 commands per day\n"
                "• `0` - Unlimited\n",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_set_timebase":
            clone_admin_sessions[user_id] = {
                'action': 'set_timebase',
                'bot_id': bot_id,
                'message_id': query.message.id
            }

            await query.edit_message_text(
                "⏰ **Set Time Base**\n\n"
                "Send time in hours for command limit reset.\n\n"
                "Examples:\n"
                "• `24` - Reset daily\n"
                "• `1` - Reset hourly\n"
                "• `168` - Reset weekly",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_view_stats":
            stats_text = f"""
📈 **Clone Bot Statistics**

**Usage Stats:**
• Total Users: `{await get_clone_user_count(bot_id)}`
• Files Shared: `{await get_clone_file_count(bot_id)}`
• Active Since: `{clone_data.get('created_at', 'Unknown')}`

**Current Settings:**
• Random Mode: `{'ON' if clone_data.get('random_mode') else 'OFF'}`
• Recent Mode: `{'ON' if clone_data.get('recent_mode') else 'OFF'}`
• Token Verification: `{'ON' if clone_data.get('token_verification') else 'OFF'}`
            """

            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="clone_back_to_settings")]
                ])
            )
            return

        elif callback_data == "clone_about_settings":
            about_text = """
ℹ️ **About Clone Settings**

**Random Mode**: Shows random files when browsing
**Recent Mode**: Shows recently added files first
**Token Verification**: Requires users to verify before access
**Command Limit**: Limits user commands per time period
**URL Shortener**: Shortens shared file links
**Time Base**: Time period for command limit reset

All settings are applied immediately and affect all users of your clone bot.
            """

            await query.edit_message_text(
                about_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="clone_back_to_settings")]
                ])
            )
            return

        elif callback_data == "clone_back_to_settings":
            # Refresh and show main settings
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_cancel_input":
            if user_id in clone_admin_sessions:
                del clone_admin_sessions[user_id]
            await clone_settings_command(client, query.message)
            return

        # Refresh the settings display
        updated_clone_data = await get_clone_by_bot_token(client.bot_token)
        settings_text = f"""
🛠️ **Clone Bot Settings**

**Bot Info:**
• Name: `{updated_clone_data.get('bot_name', 'Unknown')}`
• Status: `{'Active' if updated_clone_data.get('status') == 'active' else 'Inactive'}`

**Current Settings:**
• 🎲 Random Mode: `{'ON' if updated_clone_data.get('random_mode', False) else 'OFF'}`
• 📊 Recent Mode: `{'ON' if updated_clone_data.get('recent_mode', False) else 'OFF'}`
• 🔑 Token Verification: `{'ON' if updated_clone_data.get('token_verification', False) else 'OFF'}`
• ⏱️ Command Limit: `{updated_clone_data.get('command_limit', 'Unlimited')}`
• 🔗 URL Shortener: `{updated_clone_data.get('shortener_api', 'Not Set')}`

Click the buttons below to modify settings:
        """

        await query.edit_message_text(
            settings_text,
            reply_markup=create_settings_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in clone settings callback: {e}")
        await query.answer("❌ Error processing request. Please try again.", show_alert=True)

@Client.on_message(filters.text & filters.private)
async def handle_clone_admin_input(client: Client, message: Message):
    """Handle text input from clone admin for settings"""
    user_id = message.from_user.id

    if user_id not in clone_admin_sessions:
        return

    if not hasattr(client, 'is_clone') or not client.is_clone or not is_clone_admin(client, user_id):
        return

    session = clone_admin_sessions[user_id]
    action = session.get('action')
    bot_id = session.get('bot_id')

    try:
        if action == 'set_shortener':
            text = message.text.strip()
            if text.lower() == 'none':
                await update_clone_setting(bot_id, 'shortener_api', None)
                await message.reply_text("✅ URL Shortener disabled.")
            elif '|' in text:
                api_url, api_key = text.split('|', 1)
                shortener_config = {'api_url': api_url.strip(), 'api_key': api_key.strip()}
                await update_clone_setting(bot_id, 'shortener_api', shortener_config)
                await message.reply_text("✅ URL Shortener configuration updated.")
            else:
                await message.reply_text("❌ Invalid format. Use: `api_url|api_key`")
                return

        elif action == 'set_limit':
            try:
                limit = int(message.text.strip())
                if limit < 0:
                    await message.reply_text("❌ Command limit cannot be negative.")
                    return
                await update_clone_setting(bot_id, 'command_limit', limit if limit > 0 else None)
                await message.reply_text(f"✅ Command limit set to {'unlimited' if limit == 0 else limit}.")
            except ValueError:
                await message.reply_text("❌ Please send a valid number.")
                return

        elif action == 'set_timebase':
            try:
                hours = int(message.text.strip())
                if hours <= 0:
                    await message.reply_text("❌ Time base must be greater than 0.")
                    return
                await update_clone_setting(bot_id, 'time_base_hours', hours)
                await message.reply_text(f"✅ Time base set to {hours} hours.")
            except ValueError:
                await message.reply_text("❌ Please send a valid number of hours.")
                return

        # Clean up session
        del clone_admin_sessions[user_id]

        # Show updated settings
        await asyncio.sleep(1)
        await clone_settings_command(client, message)

    except Exception as e:
        logger.error(f"Error handling clone admin input: {e}")
        await message.reply_text("❌ Error processing your input. Please try again.")
        if user_id in clone_admin_sessions:
            del clone_admin_sessions[user_id]