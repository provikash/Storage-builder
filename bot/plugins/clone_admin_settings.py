import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import Config
from bot.database.clone_db import get_clone_config, update_clone_config, get_clone_by_bot_token, update_clone_setting, get_clone_user_count, get_clone_file_count, update_clone_token_verification, update_clone_shortener_settings
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

async def is_feature_enabled_for_user(client: Client, feature_name: str) -> bool:
    """Check if feature is enabled for normal users based on clone admin settings"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Mother bot - features available by default
        if bot_token == Config.BOT_TOKEN:
            return True

        # Clone bot - check configuration
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if clone_data:
            # Check the actual feature setting from clone admin
            return clone_data.get(feature_name, True)
        return True
    except Exception as e:
        logger.error(f"Error checking feature availability: {e}")
        return True

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
async def clone_settings_command(client: Client, message):
    """Clone settings command for the settings button"""
    user_id = message.from_user.id

    # Strict clone bot detection  
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN

    # Additional checks for clone bot detection
    if not is_clone_bot:
        is_clone_bot = (
            hasattr(client, 'is_clone') and client.is_clone or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    logger.info(f"Clone settings: user_id={user_id}, bot_token={bot_token}, is_clone_bot={is_clone_bot}")

    if not is_clone_bot:
        error_msg = "❌ Settings panel is only available in clone bots!"
        if hasattr(message, 'edit_message_text'):
            return await message.edit_message_text(error_msg)
        else:
            return await message.reply_text(error_msg)

    # Get clone data to verify admin
    try:
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            error_msg = "❌ Clone configuration not found!"
            if hasattr(message, 'edit_message_text'):
                return await message.edit_message_text(error_msg)
            else:
                return await message.reply_text(error_msg)

        if clone_data.get('admin_id') != user_id:
            error_msg = "❌ Only clone admin can access settings!"
            if hasattr(message, 'edit_message_text'):
                return await message.edit_message_text(error_msg)
            else:
                return await message.reply_text(error_msg)

    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        error_msg = "❌ Error verifying admin access!"
        if hasattr(message, 'edit_message_text'):
            return await message.edit_message_text(error_msg)
        else:
            return await message.reply_text(error_msg)

    # Get current settings from database
    try:
        # Refresh clone data to get latest values
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data:
            error_msg = "❌ Clone configuration not found after refresh!"
            if hasattr(message, 'edit_message_text'):
                return await message.edit_message_text(error_msg)
            else:
                return await message.reply_text(error_msg)
        
        show_random = clone_data.get('random_mode', False)
        show_recent = clone_data.get('recent_mode', False) 
        show_popular = clone_data.get('popular_mode', False)
        force_join = clone_data.get('force_join_enabled', False)
        
        bot_id = clone_data.get('bot_id')
        logger.info(f"Current settings for clone {bot_id}: random={show_random}, recent={show_recent}, popular={show_popular}, force_join={force_join}")
    except Exception as e:
        logger.error(f"Error getting current settings: {e}")
        show_random = show_recent = show_popular = force_join = False

    # Show clone settings panel with current actual values
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
            InlineKeyboardButton("🔑 Token Verification Mode", callback_data="clone_token_verification_mode"),
            InlineKeyboardButton("🔗 URL Shortener", callback_data="clone_url_shortener_config")
        ],
        [
            InlineKeyboardButton("📋 Force Channels", callback_data="clone_force_channels_list"),
            InlineKeyboardButton("🔧 Advanced Settings", callback_data="clone_advanced_settings")
        ],
        [
            InlineKeyboardButton("🔍 Debug Settings", callback_data="clone_debug_settings"),
            InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
        ]
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

    if not is_clone_bot or bot_token == Config.BOT_TOKEN:
        await query.answer("❌ Not available in this bot.", show_alert=True)
        return

    # Verify user is clone admin
    try:
        clone_data = await get_clone_by_bot_token(bot_token)
        if not clone_data or clone_data.get('admin_id') != user_id:
            await query.answer("❌ Only clone admin can access settings.", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Error verifying clone admin: {e}")
        await query.answer("❌ Error verifying admin access.", show_alert=True)
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

            # Update clone data directly
            await update_clone_setting(bot_id, 'random_mode', new_state)

            # Update both collections to ensure synchronization
            from bot.database.clone_db import clones_collection, clone_configs_collection
            
            # Update clones collection (PRIMARY - where get_clone_by_bot_token reads from)
            await clones_collection.update_one(
                {"bot_id": bot_id},
                {"$set": {
                    "random_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )
            
            # Also try updating by _id field in case bot_id doesn't match
            await clones_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "random_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )

            # Update clone configs collection for consistency - this is where buttons read from
            await clone_configs_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "features.random_files": new_state, 
                    "random_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Also update using string bot_id format
            await clone_configs_collection.update_one(
                {"_id": bot_id},
                {"$set": {
                    "features.random_files": new_state, 
                    "random_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Force cache clear and immediate verification
            logger.info(f"Updated random_mode to {new_state} in both collections for bot {bot_id}")

            # Clear config cache to force reload
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, 'clone_config_cache'):
                    clone_config_loader.clone_config_cache.pop(bot_token, None)
                    logger.info(f"Cleared config cache for bot_token: {bot_token}")
            except Exception as e:
                logger.error(f"Error clearing config cache: {e}")

            # Log the change for debugging
            logger.info(f"Random mode toggled to {new_state} for clone {bot_id}")

            # Verify the update was applied
            updated_clone_data = await get_clone_by_bot_token(bot_token)
            actual_state = updated_clone_data.get('random_mode', None) if updated_clone_data else None
            logger.info(f"Verified random_mode state in DB: {actual_state}")

            await query.answer(f"🎲 Random mode {'enabled' if new_state else 'disabled'}")
            
            # Clear any cached configs to force fresh database reads
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, '_config_cache'):
                    clone_config_loader._config_cache.clear()
            except:
                pass
            
            # Refresh the settings panel
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_toggle_recent":
            current_state = clone_data.get('recent_mode', False)
            new_state = not current_state

            # Update clone data directly
            await update_clone_setting(bot_id, 'recent_mode', new_state)

            # Update both collections to ensure synchronization
            from bot.database.clone_db import clones_collection, clone_configs_collection
            
            # Update clones collection (PRIMARY - where get_clone_by_bot_token reads from)
            await clones_collection.update_one(
                {"bot_id": bot_id},
                {"$set": {
                    "recent_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )
            
            # Also try updating by _id field in case bot_id doesn't match
            await clones_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "recent_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )

            # Update clone configs collection for consistency - this is where buttons read from
            await clone_configs_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "features.recent_files": new_state, 
                    "recent_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Also update using string bot_id format
            await clone_configs_collection.update_one(
                {"_id": bot_id},
                {"$set": {
                    "features.recent_files": new_state, 
                    "recent_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Force cache clear and immediate verification
            logger.info(f"Updated recent_mode to {new_state} in both collections for bot {bot_id}")

            # Clear config cache to force reload
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, 'clone_config_cache'):
                    clone_config_loader.clone_config_cache.pop(bot_token, None)
                    logger.info(f"Cleared config cache for bot_token: {bot_token}")
            except Exception as e:
                logger.error(f"Error clearing config cache: {e}")

            # Log the change for debugging
            logger.info(f"Recent mode toggled to {new_state} for clone {bot_id}")

            # Verify the update was applied
            updated_clone_data = await get_clone_by_bot_token(bot_token)
            actual_state = updated_clone_data.get('recent_mode', None) if updated_clone_data else None
            logger.info(f"Verified recent_mode state in DB: {actual_state}")

            await query.answer(f"📊 Recent mode {'enabled' if new_state else 'disabled'}")
            
            # Clear any cached configs to force fresh database reads
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, '_config_cache'):
                    clone_config_loader._config_cache.clear()
            except:
                pass
                
            # Refresh the settings panel
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_toggle_popular":
            current_state = clone_data.get('popular_mode', False)
            new_state = not current_state

            # Update clone data directly
            await update_clone_setting(bot_id, 'popular_mode', new_state)

            # Update both collections to ensure synchronization
            from bot.database.clone_db import clones_collection, clone_configs_collection
            
            # Update clones collection (PRIMARY - where get_clone_by_bot_token reads from)
            await clones_collection.update_one(
                {"bot_id": bot_id},
                {"$set": {
                    "popular_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )
            
            # Also try updating by _id field in case bot_id doesn't match
            await clones_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "popular_mode": new_state,
                    "updated_at": datetime.now()
                }}
            )

            # Update clone configs collection for consistency - this is where buttons read from
            await clone_configs_collection.update_one(
                {"_id": str(bot_id)},
                {"$set": {
                    "features.popular_files": new_state, 
                    "popular_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Also update using string bot_id format
            await clone_configs_collection.update_one(
                {"_id": bot_id},
                {"$set": {
                    "features.popular_files": new_state, 
                    "popular_mode": new_state,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            
            # Force cache clear and immediate verification
            logger.info(f"Updated popular_mode to {new_state} in both collections for bot {bot_id}")

            # Clear config cache to force reload
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, 'clone_config_cache'):
                    clone_config_loader.clone_config_cache.pop(bot_token, None)
                    logger.info(f"Cleared config cache for bot_token: {bot_token}")
            except Exception as e:
                logger.error(f"Error clearing config cache: {e}")

            # Log the change for debugging
            logger.info(f"Popular mode toggled to {new_state} for clone {bot_id}")

            # Verify the update was applied
            updated_clone_data = await get_clone_by_bot_token(bot_token)
            actual_state = updated_clone_data.get('popular_mode', None) if updated_clone_data else None
            logger.info(f"Verified popular_mode state in DB: {actual_state}")

            await query.answer(f"🔥 Popular mode {'enabled' if new_state else 'disabled'}")
            
            # Clear any cached configs to force fresh database reads
            try:
                import bot.utils.clone_config_loader as clone_config_loader
                if hasattr(clone_config_loader, '_config_cache'):
                    clone_config_loader._config_cache.clear()
            except:
                pass
                
            # Refresh the settings panel
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_toggle_force_join":
            current_state = clone_data.get('force_join_enabled', True)
            new_state = not current_state
            await update_clone_setting(bot_id, 'force_join_enabled', new_state)
            await query.answer(f"🔐 Force join {'enabled' if new_state else 'disabled'}")
            # Refresh the settings panel
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_force_join":
            await handle_force_join_settings(client, query, clone_data)
            return

        elif callback_data == "clone_token_mode":
            await handle_token_mode_settings(client, query, clone_data)
            return

        elif callback_data == "clone_token_verification_mode":
            await handle_token_verification_mode_settings(client, query, clone_data)
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
            
        elif callback_data == "clone_debug_settings":
            # Debug function to show exact database values
            debug_text = f"🔍 **Debug Settings Info**\n\n"
            debug_text += f"**Bot ID:** `{bot_id}`\n"
            debug_text += f"**Bot Token:** `{bot_token[:10]}...`\n\n"
            debug_text += f"**Database Values:**\n"
            debug_text += f"• random_mode: `{clone_data.get('random_mode')}`\n"
            debug_text += f"• recent_mode: `{clone_data.get('recent_mode')}`\n"
            debug_text += f"• popular_mode: `{clone_data.get('popular_mode')}`\n"
            debug_text += f"• force_join_enabled: `{clone_data.get('force_join_enabled')}`\n\n"
            debug_text += f"**All Clone Data Keys:**\n"
            debug_text += f"`{list(clone_data.keys())}`"
            
            await query.edit_message_text(
                debug_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_back_to_settings")]
                ])
            )
            return

        elif callback_data == "clone_cancel_input":
            if user_id in clone_admin_sessions:
                del clone_admin_sessions[user_id]
            await clone_settings_command(client, query.message)
            return

        elif callback_data == "clone_force_channels_list":
            await handle_force_join_settings(client, query, clone_data)
            return

        elif callback_data == "clone_url_shortener_config":
            await handle_shortener_config_settings(client, query)
            return

        elif callback_data == "clone_advanced_settings":
            await handle_advanced_settings(client, query, clone_data)
            return

        elif callback_data == "clone_toggle_batch":
            current_state = clone_data.get('batch_links', True)
            new_state = not current_state
            await update_clone_setting(bot_id, 'batch_links', new_state)
            await query.answer(f"🔄 Batch links {'enabled' if new_state else 'disabled'}")
            await handle_advanced_settings(client, query, await get_clone_by_bot_token(bot_token))
            return

        elif callback_data == "clone_toggle_auto_delete":
            current_state = clone_data.get('auto_delete', True)
            new_state = not current_state
            await update_clone_setting(bot_id, 'auto_delete', new_state)
            await query.answer(f"🗑️ Auto delete {'enabled' if new_state else 'disabled'}")
            await handle_advanced_settings(client, query, await get_clone_by_bot_token(bot_token))
            return

        elif callback_data == "clone_set_shortener_url":
            clone_admin_sessions[user_id] = {
                'action': 'set_shortener_url',
                'bot_id': bot_id,
                'message_id': query.message.id
            }
            await query.edit_message_text(
                "🔗 **Set Shortener URL**\n\n"
                "Send the API URL for your shortener service.\n\n"
                "**Examples:**\n"
                "• `https://teraboxlinks.com/`\n"
                "• `https://short.io/`\n"
                "• `https://tinyurl.com/`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_set_shortener_key":
            clone_admin_sessions[user_id] = {
                'action': 'set_shortener_key',
                'bot_id': bot_id,
                'message_id': query.message.id
            }
            await query.edit_message_text(
                "🔑 **Set Shortener API Key**\n\n"
                "Send your API key for the shortener service.\n\n"
                "**Security Note:**\n"
                "Your API key will be securely stored and masked in displays.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_add_force_channel":
            clone_admin_sessions[user_id] = {
                'action': 'add_force_channel',
                'bot_id': bot_id,
                'message_id': query.message.id
            }
            await query.edit_message_text(
                "➕ **Add Force Join Channel**\n\n"
                "Send the channel ID or username to add as force join channel.\n\n"
                "**Examples:**\n"
                "• `-1001234567890`\n"
                "• `@yourchannel`\n\n"
                "**Note:** Make sure the bot is admin in the channel!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
            return

        elif callback_data == "clone_remove_force_channel":
            force_channels = clone_data.get('force_channels', [])
            if not force_channels:
                await query.answer("❌ No force channels to remove.")
                return

            clone_admin_sessions[user_id] = {
                'action': 'remove_force_channel',
                'bot_id': bot_id,
                'message_id': query.message.id
            }
            await query.edit_message_text(
                "➖ **Remove Force Join Channel**\n\n"
                "Send the channel ID or username to remove from force join.\n\n"
                "**Current Channels:**\n" + 
                "\n".join([f"• `{ch}`" for ch in force_channels]),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="clone_cancel_input")]
                ])
            )
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

async def handle_token_verification_mode_settings(client: Client, query: CallbackQuery, clone_data):
    """Handle token verification mode settings"""
    user_id = query.from_user.id
    bot_id = clone_data.get('bot_id')

    # Get current config
    config = await get_clone_config(str(bot_id))
    token_settings = config.get('token_settings', {}) if config else {}

    current_mode = token_settings.get('verification_mode', 'command_limit')
    token_enabled = clone_data.get('token_verification', True) # Use clone_data for enabled status
    command_limit = token_settings.get('command_limit', 3)
    time_duration = token_settings.get('time_duration', 24)

    text = f"🔑 **Token Verification Settings**\n\n"
    text += f"**Current Status:** {'✅ Enabled' if token_enabled else '❌ Disabled'}\n"
    text += f"**Current Mode:** {current_mode.replace('_', ' ').title()}\n\n"

    if current_mode == 'command_limit':
        text += f"**Command Limit Mode:**\n"
        text += f"• Commands per token: {command_limit}\n"
        text += f"• Users get {command_limit} commands after verification\n\n"
    elif current_mode == 'time_based':
        text += f"**Time-Based Mode:**\n"
        text += f"• Token duration: {time_duration} hours\n"
        text += f"• Users get unlimited commands for {time_duration} hours\n\n"

    text += "**Available Modes:**\n"
    text += "• **Command Limit** - Token gives specific number of commands\n"
    text += "• **Time Based** - Token valid for specific time period\n\n"
    text += "**Commands:**\n"
    text += "• `/settokenmode command_limit|time_based`\n"
    text += "• `/setcommandlimit <number>` (for command mode)\n"
    text += "• `/settimeduration <hours>` (for time mode)\n"
    text += "• `/toggletoken` - Enable/disable system"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Toggle System", callback_data="clone_toggle_token_system"),
                InlineKeyboardButton("📊 Command Mode", callback_data="clone_set_token_command_limit")
            ],
            [
                InlineKeyboardButton("⏰ Time Mode", callback_data="clone_set_token_time_based"),
                InlineKeyboardButton("⚙️ Shortener Config", callback_data="clone_url_shortener_config")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="clone_back_to_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("^clone_toggle_token_system$"))
async def toggle_token_system(client: Client, query: CallbackQuery):
    """Toggle token verification system"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    current_state = clone_data.get('token_verification', False)
    new_state = not current_state
    bot_id = clone_data.get('bot_id')

    await update_clone_setting(bot_id, 'token_verification', new_state)
    await query.answer(f"🔑 Token system {'enabled' if new_state else 'disabled'}")

    # Refresh the token mode settings
    await handle_token_verification_mode_settings(client, query, await get_clone_by_bot_token(client.bot_token))

@Client.on_callback_query(filters.regex("^clone_set_token_"))
async def set_token_mode(client: Client, query: CallbackQuery):
    """Set token verification mode"""
    user_id = query.from_user.id
    mode = query.data.replace("clone_set_token_", "")

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = str(clone_data.get('bot_id'))

    # Update token verification mode
    await update_clone_token_verification(bot_id, verification_mode=mode)
    await query.answer(f"🔑 Token mode set to {mode.replace('_', ' ').title()}")

    # Refresh the token mode settings
    updated_clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    await handle_token_verification_mode_settings(client, query, updated_clone_data)

@Client.on_callback_query(filters.regex("^clone_url_shortener_config$"))
async def handle_shortener_config_settings(client: Client, query: CallbackQuery):
    """Handle URL shortener configuration"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    # Get current config
    config = await get_clone_config(str(clone_data.get('bot_id')))
    shortener_settings = config.get('shortener_settings', {}) if config else {}

    current_url = shortener_settings.get('api_url', 'https://teraboxlinks.com/')
    current_key = shortener_settings.get('api_key', 'Not Set')
    enabled = shortener_settings.get('enabled', True)

    text = f"🔗 **URL Shortener Configuration**\n\n"
    text += f"**Current Settings:**\n"
    text += f"• Status: {'✅ Enabled' if enabled else '❌ Disabled'}\n"
    text += f"• API URL: `{current_url}`\n"
    text += f"• API Key: `{'*' * (len(current_key) - 4) + current_key[-4:] if len(current_key) > 4 else current_key}`\n\n"
    text += "**Commands:**\n"
    text += "• `/setshortenerurl <api_url>` - Set API URL\n"
    text += "• `/setshortenerkey <api_key>` - Set API key\n"
    text += "• `/toggleshortener` - Enable/disable shortener\n\n"
    text += "**Popular Shortener APIs:**\n"
    text += "• `https://teraboxlinks.com/` (Default)\n"
    text += "• `https://short.io/`\n"
    text += "• `https://tinyurl.com/`"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Toggle Shortener", callback_data="clone_toggle_shortener"),
                InlineKeyboardButton("🔧 Test Config", callback_data="clone_test_shortener")
            ],
            [InlineKeyboardButton("🔙 Back to Token Settings", callback_data="clone_token_verification_mode")]
        ])
    )

@Client.on_callback_query(filters.regex("^clone_toggle_shortener$"))
async def toggle_shortener(client: Client, query: CallbackQuery):
    """Toggle URL shortener system"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = str(clone_data.get('bot_id'))
    config = await get_clone_config(bot_id)
    current_enabled = config.get('shortener_settings', {}).get('enabled', True) if config else True
    new_state = not current_enabled

    await update_clone_shortener_settings(bot_id, enabled=new_state)
    await query.answer(f"🔗 URL Shortener {'enabled' if new_state else 'disabled'}")

    # Refresh the shortener config
    await handle_shortener_config_settings(client, query)
    await handle_token_verification_mode_settings(client, query, await get_clone_by_bot_token(client.bot_token))

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

    if not is_clone_bot or not await is_clone_admin(client, user_id):
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

        elif action == 'add_force_channel':
            channel_input = message.text.strip()
            try:
                # Try to get chat info to validate
                chat = await client.get_chat(channel_input)

                # Get current force channels
                clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
                current_channels = clone_data.get('force_channels', [])

                # Add new channel if not already present
                if chat.id not in current_channels:
                    current_channels.append(chat.id)
                    await update_clone_setting(bot_id, 'force_channels', current_channels)
                    await message.reply_text(f"✅ Added force join channel: {chat.title}")
                else:
                    await message.reply_text("❌ Channel already in force join list.")

            except Exception as e:
                await message.reply_text(f"❌ Error adding channel: {str(e)}")
                return

        elif action == 'remove_force_channel':
            channel_input = message.text.strip()
            try:
                # Get current force channels
                clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
                current_channels = clone_data.get('force_channels', [])

                # Convert input to channel ID if needed
                try:
                    chat = await client.get_chat(channel_input)
                    channel_id = chat.id
                except:
                    channel_id = int(channel_input) if channel_input.lstrip('-').isdigit() else channel_input

                # Remove channel if present
                if channel_id in current_channels:
                    current_channels.remove(channel_id)
                    await update_clone_setting(bot_id, 'force_channels', current_channels)
                    await message.reply_text(f"✅ Removed force join channel.")
                else:
                    await message.reply_text("❌ Channel not found in force join list.")

            except Exception as e:
                await message.reply_text(f"❌ Error removing channel: {str(e)}")
                return

        elif action == 'set_shortener_url':
            url = message.text.strip()
            try:
                await update_clone_shortener_settings(bot_id, api_url=url)
                await message.reply_text(f"✅ Shortener URL updated to: {url}")
            except Exception as e:
                await message.reply_text(f"❌ Error updating URL: {str(e)}")
                return

        elif action == 'set_shortener_key':
            key = message.text.strip()
            try:
                await update_clone_shortener_settings(bot_id, api_key=key)
                await message.reply_text("✅ Shortener API key updated successfully.")
            except Exception as e:
                await message.reply_text(f"❌ Error updating API key: {str(e)}")
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

        # Get current config and update the specific field
        current_config = await get_clone_config(bot_id)
        if current_config:
            # Update the setting in the clone data directly
            from bot.database.clone_db import update_clone_data
            await update_clone_data(bot_id, {key: value})
        else:
            # If no config exists, create one with the setting
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

async def handle_url_shortener_settings(client: Client, query: CallbackQuery, clone_data):
    """Handle URL shortener settings display"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get current config
    config = await get_clone_config(str(clone_data.get('bot_id')))
    shortener_settings = config.get('shortener_settings', {}) if config else {}

    current_url = shortener_settings.get('api_url', 'https://teraboxlinks.com/')
    current_key = shortener_settings.get('api_key', 'Not Set')
    enabled = shortener_settings.get('enabled', True)

    text = f"🔗 **URL Shortener Configuration**\n\n"
    text += f"**Current Settings:**\n"
    text += f"• Status: {'✅ Enabled' if enabled else '❌ Disabled'}\n"
    text += f"• API URL: `{current_url}`\n"
    text += f"• API Key: `{'*' * (len(current_key) - 4) + current_key[-4:] if len(current_key) > 4 else current_key}`\n\n"
    text += "**Management:**\n"
    text += "Use the buttons below to configure your shortener settings."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Toggle Shortener", callback_data="clone_toggle_shortener"),
                InlineKeyboardButton("🔧 Set URL", callback_data="clone_set_shortener_url")
            ],
            [
                InlineKeyboardButton("🔑 Set API Key", callback_data="clone_set_shortener_key"),
                InlineKeyboardButton("🧪 Test Config", callback_data="clone_test_shortener")
            ],
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

@Client.on_callback_query(filters.regex("^clone_token_verification_mode$"))
async def clone_token_verification_mode_handler(client: Client, query: CallbackQuery):
    """Handle token verification mode settings"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get clone data
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    await handle_token_verification_mode_settings(client, query, clone_data)

@Client.on_callback_query(filters.regex("^clone_url_shortener_settings$"))
async def clone_url_shortener_settings_handler(client: Client, query: CallbackQuery):
    """Handle URL shortener settings"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    # Get clone data
    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    await handle_url_shortener_settings(client, query, clone_data)

@Client.on_callback_query(filters.regex("^clone_set_token_time_based$"))
async def set_token_time_based(client: Client, query: CallbackQuery):
    """Set token verification mode to time-based"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = str(clone_data.get('bot_id'))

    # Update token verification mode
    await update_clone_token_verification(bot_id, verification_mode="time_based")
    await query.answer(f"🔑 Token mode set to Time-Based (24 hours)")

    # Refresh the token mode settings
    updated_clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    await handle_token_verification_mode_settings(client, query, updated_clone_data)

@Client.on_callback_query(filters.regex("^clone_set_token_command_limit$"))
async def set_token_command_limit(client: Client, query: CallbackQuery):
    """Set token verification mode to command limit"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = str(clone_data.get('bot_id'))

    # Update token verification mode
    await update_clone_token_verification(bot_id, verification_mode="command_limit")
    await query.answer(f"🔑 Token mode set to Command Limit")

    # Refresh the token mode settings
    updated_clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    await handle_token_verification_mode_settings(client, query, updated_clone_data)

@Client.on_callback_query(filters.regex("^clone_disable_token_verification$"))
async def disable_token_verification(client: Client, query: CallbackQuery):
    """Disable token verification completely"""
    user_id = query.from_user.id

    if not await is_clone_admin(client, user_id):
        return await query.answer("❌ Unauthorized access!", show_alert=True)

    clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    if not clone_data:
        return await query.answer("❌ Clone configuration not found.", show_alert=True)

    bot_id = str(clone_data.get('bot_id'))

    # Disable token verification
    await update_clone_token_verification(bot_id, enabled=False)
    await query.answer(f"🔑 Token verification disabled")

    # Refresh the token mode settings
    updated_clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token', Config.BOT_TOKEN))
    await handle_token_verification_mode_settings(client, query, updated_clone_data)