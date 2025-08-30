import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_config, update_clone_config, get_clone_by_bot_token
from bot.utils import clone_config_loader
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store clone admin sessions
clone_admin_sessions = {}

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Not a clone if using mother bot token
        if bot_token == Config.BOT_TOKEN:
            return False

        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

def create_settings_keyboard():
    """Create the clone admin settings keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎲 Random Toggle", callback_data="clone_toggle_random"),
            InlineKeyboardButton("📊 Recent Toggle", callback_data="clone_toggle_recent")
        ],
        [
            InlineKeyboardButton("🔥 Popular Toggle", callback_data="clone_toggle_popular"),
            InlineKeyboardButton("📢 Force Join", callback_data="clone_force_join")
        ],
        [
            InlineKeyboardButton("🔑 Token Mode", callback_data="clone_token_mode"),
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener")
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

@Client.on_message(filters.command("cloneadmin") & filters.private)
async def clone_admin_command(client: Client, message: Message):
    """Clone admin panel command"""
    user_id = message.from_user.id

    # Strict clone bot detection
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    # Additional checks for clone bot detection
    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or 
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    if not is_clone_bot or bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ Clone admin panel is only available in clone bots!")

    # Get clone data to verify admin
    try:
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found!")

        if clone_data.get('admin_id') != user_id:
            return await message.reply_text("❌ Only clone admin can access this panel!")

    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        return await message.reply_text("❌ Error verifying admin access!")

    # Show clone admin panel
    await clone_admin_panel(client, message)

async def clone_admin_panel(client: Client, message):
    """Display clone admin panel"""
    text = f"⚙️ **Clone Bot Admin Panel**\n\n"
    text += f"🤖 **Bot Management:**\n"
    text += f"Manage your clone bot's settings and features.\n\n"
    text += f"🔧 **Available Options:**\n"
    text += f"• Configure bot features\n"
    text += f"• Manage force channels\n" 
    text += f"• Token verification settings\n"
    text += f"• URL shortener configuration\n\n"
    text += f"📊 **Choose an option below:**"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎛️ Bot Features", callback_data="clone_bot_features"),
            InlineKeyboardButton("🔐 Force Channels", callback_data="clone_local_force_channels")
        ],
        [
            InlineKeyboardButton("🔑 Token Settings", callback_data="clone_token_command_config"),
            InlineKeyboardButton("💰 Token Pricing", callback_data="clone_token_pricing")
        ],
        [
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener"),
            InlineKeyboardButton("📊 Subscription Status", callback_data="clone_subscription_status")
        ],
        [
            InlineKeyboardButton("🔄 Toggle Token System", callback_data="clone_toggle_token_system"),
            InlineKeyboardButton("📋 Request Channels", callback_data="clone_request_channels")
        ],
        [InlineKeyboardButton("💧 About Water", callback_data="clone_about_water")]
    ])

    if hasattr(message, 'edit_message_text'):
        await message.edit_message_text(text, reply_markup=buttons)
    else:
        await message.reply_text(text, reply_markup=buttons)


@Client.on_message(filters.command("clonesettings") & filters.private)
async def clone_settings_command(client: Client, message: Message):
    """Clone settings command for the settings button"""
    user_id = message.from_user.id

    # Strict clone bot detection  
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    # Additional checks for clone bot detection
    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or 
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    if not is_clone_bot or bot_token == Config.BOT_TOKEN:
        return await message.reply_text("❌ Settings panel is only available in clone bots!")

    # Get clone data to verify admin
    try:
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            return await message.reply_text("❌ Clone configuration not found!")

        if clone_data.get('admin_id') != user_id:
            return await message.reply_text("❌ Only clone admin can access settings!")

    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        return await message.reply_text("❌ Error verifying admin access!")

    # Show clone settings panel
    text = f"⚙️ **Clone Bot Settings**\n\n"
    text += f"🔧 **Configuration Panel**\n"
    text += f"Manage your clone bot's features and behavior.\n\n"
    text += f"📋 **Settings Categories:**\n"
    text += f"• File sharing features (Random, Recent, Popular)\n"
    text += f"• Force join channels\n"
    text += f"• Token verification mode\n"
    text += f"• URL shortener & API keys\n\n"
    text += f"⚡ **Quick Actions:**"

    # Get current settings
    try:
        show_random = clone_data.get('random_mode', True)
        show_recent = clone_data.get('recent_mode', True) 
        show_popular = clone_data.get('popular_mode', True)
        force_join = clone_data.get('force_join_enabled', True)
    except:
        show_random = show_recent = show_popular = force_join = True

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
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    if hasattr(message, 'edit_message_text'):
        await message.edit_message_text(text, reply_markup=buttons)
    else:
        await message.reply_text(text, reply_markup=buttons)


@Client.on_callback_query(filters.regex("^clone_"))
async def handle_clone_settings_callbacks(client: Client, query: CallbackQuery):
    """Handle clone settings callbacks"""
    user_id = query.from_user.id
    callback_data = query.data

    # Check if this is a clone bot and user is the admin
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or 
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    if not is_clone_bot:
        await query.answer("❌ Not available in this bot.", show_alert=True)
        return

    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Only clone admin can access settings.", show_alert=True)
        return

    try:
        clone_data = await get_clone_by_bot_token(bot_token)
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

        elif callback_data == "clone_toggle_popular":
            current_state = clone_data.get('popular_mode', False)
            new_state = not current_state
            await update_clone_setting(bot_id, 'popular_mode', new_state)
            await query.answer(f"🔥 Popular mode {'enabled' if new_state else 'disabled'}")

        elif callback_data == "clone_force_join":
            await handle_force_join_settings(client, query, clone_data)
            return

        elif callback_data == "clone_token_mode":
            await handle_token_mode_settings(client, query, clone_data)
            return

        elif callback_data == "clone_url_shortener":
            clone_admin_sessions[user_id] = {
                'action': 'set_shortener',
                'bot_id': bot_id,
                'message_id': query.message.id
            }

            await query.edit_message_text(
                "🔗 **URL Shortener Configuration**\n\n"
                "Send your shortener configuration in this format:\n"
                "`api_url|api_key`\n\n"
                "**Examples:**\n"
                "• `https://short.ly/api|your_api_key`\n"
                "• `https://tinyurl.com/api|your_key`\n\n"
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
            • Popular Mode: `{'ON' if clone_data.get('popular_mode') else 'OFF'}`
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
            **Popular Mode**: Shows most accessed files first
            **Token Verification**: Requires users to verify before access
            **Force Join**: Requires users to join channels before access
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
        
        elif callback_data == "clone_force_channels_list":
            await handle_force_channels_list(client, query, clone_data)
            return
        
        elif callback_data == "clone_advanced_settings":
            await handle_advanced_settings(client, query, clone_data)
            return

        # Refresh the settings display
        updated_clone_data = await get_clone_by_bot_token(client.bot_token)
        settings_text = f"""
        🛠️ **Clone Bot Settings**

        **Bot Info:**
        • Name: `{updated_clone_data.get('bot_name', 'Unknown')}`
        • Status: `{'Active' if updated_clone_data.get('status') == 'active' else 'Inactive'}`

        **File Display Settings:**
        • 🎲 Random Mode: `{'ON' if updated_clone_data.get('random_mode', False) else 'OFF'}`
        • 📊 Recent Mode: `{'ON' if updated_clone_data.get('recent_mode', False) else 'OFF'}`
        • 🔥 Popular Mode: `{'ON' if updated_clone_data.get('popular_mode', False) else 'OFF'}`

        **Access Control:**
        • 🔑 Token Verification: `{'ON' if updated_clone_data.get('token_verification', False) else 'OFF'}`
        • 📢 Force Join Channels: `{len(updated_clone_data.get('force_channels', []))}`

        **System Settings:**
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

async def handle_force_join_settings(client: Client, query: CallbackQuery, clone_data):
    """Handle force join channel settings"""
    user_id = query.from_user.id
    bot_id = clone_data.get('bot_id')
    force_channels = clone_data.get('force_channels', [])

    text = f"📢 **Force Join Channel Settings**\n\n"

    if force_channels:
        text += "**Current Force Join Channels:**\n"
        for i, channel in enumerate(force_channels, 1):
            try:
                chat = await client.get_chat(channel)
                text += f"{i}. {chat.title} (`{channel}`)\n"
            except:
                text += f"{i}. Channel ID: `{channel}`\n"
        text += "\n"
    else:
        text += "❌ No force join channels configured.\n\n"

    text += "**Management Commands:**\n"
    text += "• `/addforce <channel_id>` - Add force join channel\n"
    text += "• `/removeforce <channel_id>` - Remove force join channel\n"
    text += "• `/listforce` - List all force join channels\n\n"
    text += "Note: Users must join these channels to access files."

    clone_admin_sessions[user_id] = {
        'action': 'manage_force_channels',
        'bot_id': bot_id,
        'message_id': query.message.id
    }

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Channel", callback_data="clone_add_force_channel")],
            [InlineKeyboardButton("➖ Remove Channel", callback_data="clone_remove_force_channel")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_back_to_settings")]
        ])
    )

async def handle_token_mode_settings(client: Client, query: CallbackQuery, clone_data):
    """Handle token verification mode settings"""
    user_id = query.from_user.id
    bot_id = clone_data.get('bot_id')
    current_mode = clone_data.get('token_mode', 'one_time')
    token_enabled = clone_data.get('token_verification', False)

    text = f"🔑 **Token Verification Settings**\n\n"
    text += f"**Current Status:** {'Enabled' if token_enabled else 'Disabled'}\n"
    text += f"**Current Mode:** {current_mode.replace('_', ' ').title()}\n\n"

    text += "**Available Modes:**\n"
    text += "• **One Time** - Token valid for single use\n"
    text += "• **Command Limit** - Token valid for multiple commands\n"
    text += "• **Time Based** - Token valid for specific time period\n\n"

    text += "**Current Settings:**\n"
    text += f"• Command Limit: {clone_data.get('command_limit', 'Unlimited')}\n"
    text += f"• Token Price: ${clone_data.get('token_price', 1.0)}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Toggle System", callback_data="clone_toggle_token_system"),
                InlineKeyboardButton("⚙️ One Time", callback_data="clone_set_token_one_time")
            ],
            [
                InlineKeyboardButton("📊 Command Limit", callback_data="clone_set_token_command_limit"),
                InlineKeyboardButton("⏰ Time Based", callback_data="clone_set_token_time_based")
            ],
            [
                InlineKeyboardButton("💰 Set Price", callback_data="clone_set_token_price"),
                InlineKeyboardButton("🔙 Back", callback_data="clone_back_to_settings")
            ]
        ])
    )

@Client.on_callback_query(filters.regex("^clone_toggle_token_system$"))
async def toggle_token_system(client: Client, query: CallbackQuery):
    """Toggle token verification system"""
    user_id = query.from_user.id

    if not is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(client.bot_token)
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    current_state = clone_data.get('token_verification', False)
    new_state = not current_state
    bot_id = clone_data.get('bot_id')

    await update_clone_setting(bot_id, 'token_verification', new_state)
    await query.answer(f"🔑 Token system {'enabled' if new_state else 'disabled'}")

    # Refresh the token mode settings
    await handle_token_mode_settings(client, query, await get_clone_by_bot_token(client.bot_token))

@Client.on_callback_query(filters.regex("^clone_set_token_"))
async def set_token_mode(client: Client, query: CallbackQuery):
    """Set token verification mode"""
    user_id = query.from_user.id
    mode = query.data.replace("clone_set_token_", "")

    if not is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(client.bot_token)
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = clone_data.get('bot_id')
    await update_clone_setting(bot_id, 'token_mode', mode)
    await query.answer(f"🔑 Token mode set to {mode.replace('_', ' ').title()}")

    # Refresh the token mode settings
    await handle_token_mode_settings(client, query, await get_clone_by_bot_token(client.bot_token))

@Client.on_message(filters.text & filters.private)
async def handle_clone_admin_input(client: Client, message: Message):
    """Handle text input from clone admin for settings"""
    user_id = message.from_user.id

    if user_id not in clone_admin_sessions:
        return

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or 
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    if not is_clone_bot or not is_clone_admin(client, user_id):
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

async def update_clone_setting(bot_id, key, value):
    """Update a specific clone setting"""
    try:
        if ':' in str(bot_id):
            bot_id = bot_id.split(':')[0]
        await update_clone_config(bot_id, {key: value})
        return True
    except Exception as e:
        logger.error(f"Error updating clone setting: {e}")
        return False

async def get_clone_user_count(bot_id):
    """Get user count for clone bot"""
    try:
        # This would need to be implemented based on your user tracking system
        return 0
    except:
        return 0

async def get_clone_file_count(bot_id):
    """Get file count for clone bot"""
    try:
        # This would need to be implemented based on your file tracking system
        return 0
    except:
        return 0

async def handle_force_channels_list(client: Client, query: CallbackQuery, clone_data):
    """Handle force channels list display"""
    force_channels = clone_data.get('force_channels', [])

    text = f"📋 **Force Join Channels**\n\n"

    if force_channels:
        text += f"**Current Channels ({len(force_channels)}):**\n"
        for i, channel in enumerate(force_channels, 1):
            try:
                chat = await client.get_chat(channel)
                text += f"{i}. {chat.title} (`{channel}`)\n"
            except:
                text += f"{i}. Channel ID: `{channel}`\n"
    else:
        text += f"❌ No force join channels configured.\n"

    text += f"\n💡 **Management:**\n"
    text += f"• Use commands to add/remove channels\n"
    text += f"• Users must join these channels to access files\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Channel", callback_data="clone_add_force_channel")],
            [InlineKeyboardButton("➖ Remove Channel", callback_data="clone_remove_force_channel")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_back_to_settings")]
        ])
    )

async def handle_advanced_settings(client: Client, query: CallbackQuery, clone_data):
    """Handle advanced settings display"""
    text = f"🔧 **Advanced Settings**\n\n"
    text += f"⚙️ **System Configuration:**\n"
    text += f"• Command Limit: {clone_data.get('command_limit', 'Unlimited')}\n"
    text += f"• Time Base: {clone_data.get('time_base_hours', 24)} hours\n"
    text += f"• Auto Delete: {clone_data.get('auto_delete_time', 600)} seconds\n"
    text += f"• Session Timeout: {clone_data.get('session_timeout', 3600)} seconds\n\n"
    text += f"🎛️ **Feature Toggles:**\n"
    text += f"• Batch Links: {'✅' if clone_data.get('batch_links', True) else '❌'}\n"
    text += f"• Auto Delete: {'✅' if clone_data.get('auto_delete', True) else '❌'}\n"
    text += f"• Premium Features: {'✅' if clone_data.get('premium_features', True) else '❌'}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏱️ Set Command Limit", callback_data="clone_set_limit"),
                InlineKeyboardButton("⏰ Set Time Base", callback_data="clone_set_timebase")
            ],
            [
                InlineKeyboardButton("🔄 Toggle Batch Links", callback_data="clone_toggle_batch"),
                InlineKeyboardButton("🗑️ Toggle Auto Delete", callback_data="clone_toggle_auto_delete")
            ],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_back_to_settings")]
        ])
    )