"""
Clone Admin Settings Panel
Handles clone bot admin settings and configuration
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from bot.database.clone_db import (
    get_clone_config, 
    toggle_clone_feature, 
    update_clone_shortener,
    update_clone_command_limit,
    update_clone_time_settings,
    get_clone_admin_id
)
from info import Config

# Helper function to check if user is clone admin
async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        # Get bot's own ID
        me = await client.get_me()
        bot_id = str(me.id)
        
        # Check if user is the admin of this specific clone
        clone_admin_id = await get_clone_admin_id(bot_id)
        
        # Also check if user is mother bot admin
        is_mother_admin = user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        
        return user_id == clone_admin_id or is_mother_admin
    except:
        return False

@Client.on_callback_query(filters.regex("^clone_admin_settings$"))
async def clone_admin_settings_panel(client: Client, query: CallbackQuery):
    """Show clone admin settings panel"""
    user_id = query.from_user.id
    
    # Check if user is admin of this clone
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied! Only clone admins can access this panel.", show_alert=True)
        return
    
    await query.answer()
    
    try:
        # Get bot's own ID
        me = await client.get_me()
        bot_id = str(me.id)
        
        # Get current clone configuration
        config = await get_clone_config(bot_id)
        if not config:
            await query.edit_message_text(
                "❌ **Configuration Error**\n\n"
                "Unable to load clone configuration. Please contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
                ])
            )
            return
        
        features = config.get("features", {})
        token_settings = config.get("token_settings", {})
        shortener_settings = config.get("shortener_settings", {})
        time_settings = config.get("time_settings", {})
        
        # Build settings text
        text = f"⚙️ **Clone Admin Settings**\n\n"
        text += f"🤖 **Bot:** @{me.username}\n"
        text += f"🆔 **Bot ID:** `{me.id}`\n\n"
        
        text += f"📊 **Current Settings:**\n\n"
        
        # Feature toggles
        text += f"🎲 **Random Files:** {'✅ Enabled' if features.get('random_button', True) else '❌ Disabled'}\n"
        text += f"📈 **Recent Files:** {'✅ Enabled' if features.get('recent_button', True) else '❌ Disabled'}\n"
        text += f"🔐 **Token Verification:** {'✅ Enabled' if features.get('token_verification', True) else '❌ Disabled'}\n\n"
        
        # URL Shortener
        text += f"🔗 **URL Shortener:** {'✅ Enabled' if shortener_settings.get('enabled', True) else '❌ Disabled'}\n"
        text += f"🌐 **API URL:** `{shortener_settings.get('api_url', 'Not set')}`\n\n"
        
        # Command limits and timing
        text += f"⏱️ **Command Limit:** {token_settings.get('command_limit', 100)} per session\n"
        text += f"🕐 **Auto Delete Time:** {time_settings.get('auto_delete_time', 600)} seconds\n\n"
        
        text += f"🎯 **Choose a setting to configure:**"
        
        # Settings buttons
        buttons = [
            # Row 1: Feature Toggles
            [
                InlineKeyboardButton(
                    f"🎲 Random Files {'✅' if features.get('random_button', True) else '❌'}", 
                    callback_data="toggle_random_files"
                ),
                InlineKeyboardButton(
                    f"📈 Recent Files {'✅' if features.get('recent_button', True) else '❌'}", 
                    callback_data="toggle_recent_files"
                )
            ],
            # Row 2: Token & Verification
            [
                InlineKeyboardButton(
                    f"🔐 Token Verify {'✅' if features.get('token_verification', True) else '❌'}", 
                    callback_data="toggle_token_verification"
                ),
                InlineKeyboardButton("⏱️ Command Limit", callback_data="set_command_limit")
            ],
            # Row 3: URL Shortener
            [
                InlineKeyboardButton(
                    f"🔗 URL Shortener {'✅' if shortener_settings.get('enabled', True) else '❌'}", 
                    callback_data="toggle_shortener"
                ),
                InlineKeyboardButton("🌐 Configure API", callback_data="configure_shortener_api")
            ],
            # Row 4: Time Settings
            [
                InlineKeyboardButton("🕐 Auto Delete Time", callback_data="set_auto_delete_time"),
                InlineKeyboardButton("⏲️ Session Timeout", callback_data="set_session_timeout")
            ],
            # Row 5: Navigation
            [
                InlineKeyboardButton("🔄 Refresh Settings", callback_data="clone_admin_settings"),
                InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")
            ]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        print(f"❌ ERROR in clone admin settings: {e}")
        await query.answer("❌ Error loading settings panel!", show_alert=True)

# Feature toggle handlers
@Client.on_callback_query(filters.regex("^toggle_(random_files|recent_files|token_verification|shortener)$"))
async def handle_feature_toggles(client: Client, query: CallbackQuery):
    """Handle feature toggle buttons"""
    user_id = query.from_user.id
    
    # Check admin permissions
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        # Get bot ID and current config
        me = await client.get_me()
        bot_id = str(me.id)
        config = await get_clone_config(bot_id)
        
        feature_map = {
            "toggle_random_files": "random_button",
            "toggle_recent_files": "recent_button", 
            "toggle_token_verification": "token_verification"
        }
        
        if query.data == "toggle_shortener":
            # Handle shortener toggle
            current_enabled = config.get("shortener_settings", {}).get("enabled", True)
            new_enabled = not current_enabled
            
            from bot.database.clone_db import clone_configs_collection
            from datetime import datetime
            await clone_configs_collection.update_one(
                {"_id": bot_id},
                {"$set": {
                    "shortener_settings.enabled": new_enabled,
                    "updated_at": datetime.now()
                }}
            )
            
            await query.answer(f"🔗 URL Shortener {'enabled' if new_enabled else 'disabled'}!", show_alert=True)
        else:
            # Handle feature toggles
            feature_key = feature_map.get(query.data)
            if feature_key:
                current_enabled = config.get("features", {}).get(feature_key, True)
                new_enabled = not current_enabled
                
                await toggle_clone_feature(bot_id, feature_key, new_enabled)
                
                feature_names = {
                    "random_button": "Random Files",
                    "recent_button": "Recent Files",
                    "token_verification": "Token Verification"
                }
                
                feature_name = feature_names.get(feature_key, "Feature")
                await query.answer(f"🎯 {feature_name} {'enabled' if new_enabled else 'disabled'}!", show_alert=True)
        
        # Refresh the settings panel
        await clone_admin_settings_panel(client, query)
        
    except Exception as e:
        print(f"❌ ERROR in feature toggle: {e}")
        await query.answer("❌ Error updating setting!", show_alert=True)

@Client.on_callback_query(filters.regex("^(set_command_limit|set_auto_delete_time|set_session_timeout|configure_shortener_api)$"))
async def handle_setting_configuration(client: Client, query: CallbackQuery):
    """Handle configuration setting buttons"""
    user_id = query.from_user.id
    
    # Check admin permissions
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        me = await client.get_me()
        config = await get_clone_config(str(me.id))
        
        if query.data == "set_command_limit":
            current_limit = config.get("token_settings", {}).get("command_limit", 100)
            
            text = f"⏱️ **Command Limit Configuration**\n\n"
            text += f"📊 **Current Limit:** {current_limit} commands per session\n\n"
            text += f"🎯 **Choose a new limit:**\n"
            text += f"This controls how many commands users can run before needing a new token.\n\n"
            text += f"**Recommended values:**\n"
            text += f"• 50 - Strict (frequent token renewal)\n"
            text += f"• 100 - Balanced (default)\n"
            text += f"• 200 - Generous (less frequent renewal)\n"
            text += f"• 500 - Very generous (rare renewal)"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("50 Commands", callback_data="set_limit_50"),
                    InlineKeyboardButton("100 Commands", callback_data="set_limit_100")
                ],
                [
                    InlineKeyboardButton("200 Commands", callback_data="set_limit_200"),
                    InlineKeyboardButton("500 Commands", callback_data="set_limit_500")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_admin_settings")
                ]
            ])
            
        elif query.data == "set_auto_delete_time":
            current_time = config.get("time_settings", {}).get("auto_delete_time", 600)
            
            text = f"🕐 **Auto Delete Time Configuration**\n\n"
            text += f"⏰ **Current Time:** {current_time} seconds ({current_time//60} minutes)\n\n"
            text += f"🎯 **Choose deletion time:**\n"
            text += f"Files will be automatically deleted after this time.\n\n"
            text += f"**Recommended values:**\n"
            text += f"• 5 minutes - Quick cleanup\n"
            text += f"• 10 minutes - Standard (default)\n"
            text += f"• 30 minutes - Extended access\n"
            text += f"• 60 minutes - Long-term access"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("5 Minutes", callback_data="set_delete_300"),
                    InlineKeyboardButton("10 Minutes", callback_data="set_delete_600")
                ],
                [
                    InlineKeyboardButton("30 Minutes", callback_data="set_delete_1800"),
                    InlineKeyboardButton("60 Minutes", callback_data="set_delete_3600")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_admin_settings")
                ]
            ])
            
        elif query.data == "configure_shortener_api":
            shortener_settings = config.get("shortener_settings", {})
            current_api = shortener_settings.get("api_url", "Not set")
            
            text = f"🌐 **URL Shortener API Configuration**\n\n"
            text += f"🔗 **Current API:** `{current_api}`\n\n"
            text += f"🎯 **Choose a shortener service:**\n"
            text += f"Configure your preferred URL shortening service.\n\n"
            text += f"**Popular Services:**\n"
            text += f"• TeraBox Links - Fast and reliable\n"
            text += f"• Short.io - Professional service\n"
            text += f"• TinyURL - Simple and free\n"
            text += f"• Custom API - Your own service"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔗 TeraBox Links", callback_data="api_terabox"),
                    InlineKeyboardButton("🌐 Short.io", callback_data="api_shortio")
                ],
                [
                    InlineKeyboardButton("📎 TinyURL", callback_data="api_tinyurl"),
                    InlineKeyboardButton("⚙️ Custom API", callback_data="api_custom")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_admin_settings")
                ]
            ])
        
        else:  # set_session_timeout
            current_timeout = config.get("time_settings", {}).get("session_timeout", 3600)
            
            text = f"⏲️ **Session Timeout Configuration**\n\n"
            text += f"🕐 **Current Timeout:** {current_timeout} seconds ({current_timeout//60} minutes)\n\n"
            text += f"🎯 **Choose session duration:**\n"
            text += f"How long user sessions remain active.\n\n"
            text += f"**Recommended values:**\n"
            text += f"• 30 minutes - Short sessions\n"
            text += f"• 60 minutes - Standard (default)\n"
            text += f"• 2 hours - Extended sessions\n"
            text += f"• 4 hours - Long sessions"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("30 Minutes", callback_data="set_session_1800"),
                    InlineKeyboardButton("60 Minutes", callback_data="set_session_3600")
                ],
                [
                    InlineKeyboardButton("2 Hours", callback_data="set_session_7200"),
                    InlineKeyboardButton("4 Hours", callback_data="set_session_14400")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="clone_admin_settings")
                ]
            ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        print(f"❌ ERROR in setting configuration: {e}")
        await query.answer("❌ Error loading configuration!", show_alert=True)

# Value setting handlers
@Client.on_callback_query(filters.regex("^(set_limit_|set_delete_|set_session_|api_)"))
async def handle_value_settings(client: Client, query: CallbackQuery):
    """Handle specific value setting buttons"""
    user_id = query.from_user.id
    
    # Check admin permissions
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        me = await client.get_me()
        bot_id = str(me.id)
        
        if query.data.startswith("set_limit_"):
            # Handle command limit setting
            limit = int(query.data.split("_")[2])
            await update_clone_command_limit(bot_id, limit)
            await query.answer(f"✅ Command limit set to {limit}!", show_alert=True)
            
        elif query.data.startswith("set_delete_"):
            # Handle auto delete time setting
            time_seconds = int(query.data.split("_")[2])
            await update_clone_time_settings(bot_id, "auto_delete_time", time_seconds)
            await query.answer(f"✅ Auto delete time set to {time_seconds//60} minutes!", show_alert=True)
            
        elif query.data.startswith("set_session_"):
            # Handle session timeout setting
            timeout_seconds = int(query.data.split("_")[2])
            await update_clone_time_settings(bot_id, "session_timeout", timeout_seconds)
            await query.answer(f"✅ Session timeout set to {timeout_seconds//60} minutes!", show_alert=True)
            
        elif query.data.startswith("api_"):
            # Handle API configuration
            api_type = query.data.split("_")[1]
            api_urls = {
                "terabox": "https://teraboxlinks.com/",
                "shortio": "https://short.io/",
                "tinyurl": "https://tinyurl.com/api-create.php",
                "custom": ""
            }
            
            api_url = api_urls.get(api_type, "")
            await update_clone_shortener(bot_id, api_url, "")
            
            if api_type == "custom":
                await query.answer("✅ Custom API selected! Please set your API URL manually.", show_alert=True)
            else:
                await query.answer(f"✅ {api_type.title()} API configured!", show_alert=True)
        
        # Go back to main settings panel
        await clone_admin_settings_panel(client, query)
        
    except Exception as e:
        print(f"❌ ERROR in value setting: {e}")
        await query.answer("❌ Error updating setting!", show_alert=True)