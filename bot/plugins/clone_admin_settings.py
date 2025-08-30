
"""
Clone Admin Settings Panel
Handles clone bot admin settings and configuration with comprehensive controls
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from bot.database.clone_db import (
    get_clone_config, 
    toggle_clone_feature, 
    update_clone_shortener,
    update_clone_command_limit,
    update_clone_time_settings,
    get_clone_admin_id,
    update_clone_config
)
from bot.utils.clone_config_loader import clone_config_loader
from info import Config
from datetime import datetime

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

@Client.on_message(filters.command("settings") & filters.private)
async def clone_settings_command(client: Client, message: Message):
    """Clone settings command - only visible to clone admin"""
    user_id = message.from_user.id
    
    # Check if user is admin of this clone
    if not await is_clone_admin(client, user_id):
        # Don't show error to non-admins, just ignore
        return
    
    await show_clone_settings_panel(client, message)

async def show_clone_settings_panel(client: Client, query_or_message):
    """Show comprehensive clone admin settings panel"""
    user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id
    
    # Double-check admin permissions
    if not await is_clone_admin(client, user_id):
        if hasattr(query_or_message, 'answer'):
            await query_or_message.answer("❌ Access denied!", show_alert=True)
        return
    
    try:
        # Get bot's own ID and configuration
        me = await client.get_me()
        bot_id = str(me.id)
        
        config = await get_clone_config(bot_id)
        if not config:
            error_text = "❌ **Configuration Error**\n\nUnable to load clone configuration."
            if hasattr(query_or_message, 'edit_message_text'):
                await query_or_message.edit_message_text(error_text)
            else:
                await query_or_message.reply_text(error_text)
            return
        
        features = config.get("features", {})
        token_settings = config.get("token_settings", {})
        shortener_settings = config.get("shortener_settings", {})
        time_settings = config.get("time_settings", {})
        
        # Build comprehensive settings text
        text = f"⚙️ **Clone Admin Settings**\n\n"
        text += f"🤖 **Bot:** @{me.username}\n"
        text += f"🆔 **Bot ID:** `{me.id}`\n\n"
        
        text += f"📊 **Feature Status:**\n\n"
        
        # Core Features
        text += f"🎲 **Random Files:** {'✅ Enabled' if features.get('random_button', True) else '❌ Disabled'}\n"
        text += f"📈 **Recent Files:** {'✅ Enabled' if features.get('recent_button', True) else '❌ Disabled'}\n"
        text += f"🔐 **Token Verification:** {'✅ Enabled' if features.get('token_verification', True) else '❌ Disabled'}\n"
        text += f"🔗 **URL Shortener:** {'✅ Enabled' if shortener_settings.get('enabled', True) else '❌ Disabled'}\n\n"
        
        # Token & Command Settings
        text += f"🎯 **Token & Commands:**\n"
        text += f"• Command Limit: {token_settings.get('command_limit', 100)} per session\n"
        text += f"• Token Price: ${token_settings.get('pricing', 1.0)}\n"
        text += f"• Auto Delete: {time_settings.get('auto_delete_time', 600)} seconds\n\n"
        
        # URL Shortener Info
        shortener_api = shortener_settings.get('api_url', 'Not configured')
        text += f"🌐 **Shortener API:** {shortener_api[:30]}{'...' if len(shortener_api) > 30 else ''}\n\n"
        
        text += f"🎯 **Choose a setting to configure:**"
        
        # Create comprehensive settings buttons
        buttons = [
            # Row 1: Core Feature Toggles
            [
                InlineKeyboardButton(
                    f"🎲 Random {'✅' if features.get('random_button', True) else '❌'}", 
                    callback_data="toggle_random_files"
                ),
                InlineKeyboardButton(
                    f"📈 Recent {'✅' if features.get('recent_button', True) else '❌'}", 
                    callback_data="toggle_recent_files"
                )
            ],
            # Row 2: Security & Verification
            [
                InlineKeyboardButton(
                    f"🔐 Token Verify {'✅' if features.get('token_verification', True) else '❌'}", 
                    callback_data="toggle_token_verification"
                ),
                InlineKeyboardButton(
                    f"🔗 URL Shortener {'✅' if shortener_settings.get('enabled', True) else '❌'}", 
                    callback_data="toggle_shortener"
                )
            ],
            # Row 3: Command & Token Management
            [
                InlineKeyboardButton("⏱️ Command Limit", callback_data="set_command_limit"),
                InlineKeyboardButton("💰 Token Price", callback_data="set_token_price")
            ],
            # Row 4: Time & API Settings
            [
                InlineKeyboardButton("🕐 Auto Delete Time", callback_data="set_auto_delete_time"),
                InlineKeyboardButton("🌐 Shortener API", callback_data="configure_shortener_api")
            ],
            # Row 5: Advanced Settings
            [
                InlineKeyboardButton("⚙️ Advanced Settings", callback_data="advanced_settings"),
                InlineKeyboardButton("📊 View All Settings", callback_data="view_all_settings")
            ],
            # Row 6: Navigation
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_settings"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")
            ]
        ]
        
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        print(f"❌ ERROR in clone settings panel: {e}")
        error_text = f"❌ Error loading settings panel: {str(e)}"
        if hasattr(query_or_message, 'answer'):
            await query_or_message.answer(error_text, show_alert=True)
        elif hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(error_text)
        else:
            await query_or_message.reply_text(error_text)

# Feature toggle handlers
@Client.on_callback_query(filters.regex("^(toggle_random_files|toggle_recent_files|toggle_token_verification|toggle_shortener)$"))
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
            
            await update_clone_config(bot_id, {
                "shortener_settings.enabled": new_enabled,
                "updated_at": datetime.now()
            })
            
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
        
        # Clear cache and refresh the settings panel
        clone_config_loader.clear_cache(getattr(client, 'bot_token', Config.BOT_TOKEN))
        await show_clone_settings_panel(client, query)
        
    except Exception as e:
        print(f"❌ ERROR in feature toggle: {e}")
        await query.answer("❌ Error updating setting!", show_alert=True)

@Client.on_callback_query(filters.regex("^(set_command_limit|set_token_price|set_auto_delete_time|configure_shortener_api|advanced_settings|view_all_settings)$"))
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
        bot_id = str(me.id)
        config = await get_clone_config(bot_id)
        
        if query.data == "set_command_limit":
            current_limit = config.get("token_settings", {}).get("command_limit", 100)
            
            text = f"⏱️ **Command Limit Configuration**\n\n"
            text += f"📊 **Current Limit:** {current_limit} commands per session\n\n"
            text += f"🎯 **Choose a new limit:**\n"
            text += f"This controls how many commands users can run before needing a new token.\n\n"
            text += f"**Recommended values:**\n"
            text += f"• 25 - Very strict (frequent renewal)\n"
            text += f"• 50 - Strict (regular renewal)\n"
            text += f"• 100 - Balanced (default)\n"
            text += f"• 200 - Generous (less frequent renewal)\n"
            text += f"• 500 - Very generous (rare renewal)\n"
            text += f"• 1000 - Unlimited-like experience"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("25 Commands", callback_data="set_limit_25"),
                    InlineKeyboardButton("50 Commands", callback_data="set_limit_50")
                ],
                [
                    InlineKeyboardButton("100 Commands", callback_data="set_limit_100"),
                    InlineKeyboardButton("200 Commands", callback_data="set_limit_200")
                ],
                [
                    InlineKeyboardButton("500 Commands", callback_data="set_limit_500"),
                    InlineKeyboardButton("1000 Commands", callback_data="set_limit_1000")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
            
        elif query.data == "set_token_price":
            current_price = config.get("token_settings", {}).get("pricing", 1.0)
            
            text = f"💰 **Token Price Configuration**\n\n"
            text += f"💵 **Current Price:** ${current_price}\n\n"
            text += f"🎯 **Choose a new price:**\n"
            text += f"This sets how much users pay for token access.\n\n"
            text += f"**Recommended prices:**\n"
            text += f"• $0.50 - Budget friendly\n"
            text += f"• $1.00 - Standard pricing\n"
            text += f"• $2.00 - Premium pricing\n"
            text += f"• $5.00 - High-value content\n"
            text += f"• $10.00 - Exclusive access"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("$0.50", callback_data="set_price_0.50"),
                    InlineKeyboardButton("$1.00", callback_data="set_price_1.00")
                ],
                [
                    InlineKeyboardButton("$2.00", callback_data="set_price_2.00"),
                    InlineKeyboardButton("$5.00", callback_data="set_price_5.00")
                ],
                [
                    InlineKeyboardButton("$10.00", callback_data="set_price_10.00"),
                    InlineKeyboardButton("💲 Custom Price", callback_data="set_custom_price")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
            
        elif query.data == "set_auto_delete_time":
            current_time = config.get("time_settings", {}).get("auto_delete_time", 600)
            
            text = f"🕐 **Auto Delete Time Configuration**\n\n"
            text += f"⏰ **Current Time:** {current_time} seconds ({current_time//60} minutes)\n\n"
            text += f"🎯 **Choose deletion time:**\n"
            text += f"Files will be automatically deleted after this time.\n\n"
            text += f"**Recommended values:**\n"
            text += f"• 2 minutes - Quick cleanup\n"
            text += f"• 5 minutes - Fast cleanup\n"
            text += f"• 10 minutes - Standard (default)\n"
            text += f"• 30 minutes - Extended access\n"
            text += f"• 60 minutes - Long-term access\n"
            text += f"• 120 minutes - Very long access"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("2 Minutes", callback_data="set_delete_120"),
                    InlineKeyboardButton("5 Minutes", callback_data="set_delete_300")
                ],
                [
                    InlineKeyboardButton("10 Minutes", callback_data="set_delete_600"),
                    InlineKeyboardButton("30 Minutes", callback_data="set_delete_1800")
                ],
                [
                    InlineKeyboardButton("60 Minutes", callback_data="set_delete_3600"),
                    InlineKeyboardButton("120 Minutes", callback_data="set_delete_7200")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
            
        elif query.data == "configure_shortener_api":
            shortener_settings = config.get("shortener_settings", {})
            current_api = shortener_settings.get("api_url", "Not set")
            current_key = shortener_settings.get("api_key", "Not set")
            
            text = f"🌐 **URL Shortener API Configuration**\n\n"
            text += f"🔗 **Current API:** `{current_api}`\n"
            text += f"🔑 **API Key:** `{current_key[:20]}...` (hidden)\n\n"
            text += f"🎯 **Choose a shortener service:**\n"
            text += f"Configure your preferred URL shortening service.\n\n"
            text += f"**Popular Services:**\n"
            text += f"• TeraBox Links - Fast and reliable\n"
            text += f"• Short.io - Professional service\n"
            text += f"• TinyURL - Simple and free\n"
            text += f"• Bit.ly - Popular choice\n"
            text += f"• Custom API - Your own service"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔗 TeraBox Links", callback_data="api_terabox"),
                    InlineKeyboardButton("🌐 Short.io", callback_data="api_shortio")
                ],
                [
                    InlineKeyboardButton("📎 TinyURL", callback_data="api_tinyurl"),
                    InlineKeyboardButton("🔵 Bit.ly", callback_data="api_bitly")
                ],
                [
                    InlineKeyboardButton("⚙️ Custom API", callback_data="api_custom"),
                    InlineKeyboardButton("🔑 Set API Key", callback_data="set_api_key")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
            
        elif query.data == "advanced_settings":
            features = config.get("features", {})
            
            text = f"⚙️ **Advanced Settings**\n\n"
            text += f"🔧 **Additional Features & Controls:**\n\n"
            
            # Advanced features
            text += f"📱 **Media Features:**\n"
            text += f"• Video Quality: {'✅ Enabled' if features.get('video_quality', True) else '❌ Disabled'}\n"
            text += f"• File Compression: {'✅ Enabled' if features.get('file_compression', False) else '❌ Disabled'}\n"
            text += f"• Batch Downloads: {'✅ Enabled' if features.get('batch_downloads', True) else '❌ Disabled'}\n\n"
            
            text += f"🔐 **Security Features:**\n"
            text += f"• Rate Limiting: {'✅ Enabled' if features.get('rate_limiting', True) else '❌ Disabled'}\n"
            text += f"• IP Blocking: {'✅ Enabled' if features.get('ip_blocking', False) else '❌ Disabled'}\n"
            text += f"• Captcha Verification: {'✅ Enabled' if features.get('captcha', False) else '❌ Disabled'}\n\n"
            
            text += f"📊 **Analytics:**\n"
            text += f"• Download Stats: {'✅ Enabled' if features.get('download_stats', True) else '❌ Disabled'}\n"
            text += f"• User Analytics: {'✅ Enabled' if features.get('user_analytics', False) else '❌ Disabled'}"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📱 Media Settings", callback_data="media_settings"),
                    InlineKeyboardButton("🔐 Security Settings", callback_data="security_settings")
                ],
                [
                    InlineKeyboardButton("📊 Analytics Settings", callback_data="analytics_settings"),
                    InlineKeyboardButton("⚡ Performance Settings", callback_data="performance_settings")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
            
        elif query.data == "view_all_settings":
            token_settings = config.get("token_settings", {})
            shortener_settings = config.get("shortener_settings", {})
            time_settings = config.get("time_settings", {})
            features = config.get("features", {})
            
            text = f"📊 **Complete Settings Overview**\n\n"
            text += f"🤖 **Bot:** @{me.username}\n"
            text += f"🆔 **Bot ID:** `{me.id}`\n\n"
            
            text += f"🎲 **Core Features:**\n"
            for feature, enabled in features.items():
                if feature in ['random_button', 'recent_button', 'token_verification', 'search', 'genlink']:
                    emoji = "✅" if enabled else "❌"
                    feature_name = feature.replace('_', ' ').title()
                    text += f"• {emoji} {feature_name}\n"
            
            text += f"\n🔗 **URL Shortener:**\n"
            text += f"• Status: {'✅ Enabled' if shortener_settings.get('enabled', True) else '❌ Disabled'}\n"
            text += f"• API: {shortener_settings.get('api_url', 'Not set')}\n"
            
            text += f"\n🎯 **Token Settings:**\n"
            text += f"• Command Limit: {token_settings.get('command_limit', 100)}\n"
            text += f"• Price: ${token_settings.get('pricing', 1.0)}\n"
            text += f"• Validity: {token_settings.get('validity_hours', 24)} hours\n"
            
            text += f"\n⏰ **Time Settings:**\n"
            text += f"• Auto Delete: {time_settings.get('auto_delete_time', 600)} seconds\n"
            text += f"• Session Timeout: {time_settings.get('session_timeout', 3600)} seconds\n"
            
            text += f"\n🔧 **Last Updated:** {config.get('updated_at', 'Unknown')}"
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📝 Export Settings", callback_data="export_settings"),
                    InlineKeyboardButton("🔄 Reset to Default", callback_data="reset_settings")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")
                ]
            ])
        
        await query.edit_message_text(text, reply_markup=buttons)
        
    except Exception as e:
        print(f"❌ ERROR in setting configuration: {e}")
        await query.answer("❌ Error loading configuration!", show_alert=True)

# Value setting handlers
@Client.on_callback_query(filters.regex("^(set_limit_|set_price_|set_delete_|api_)"))
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
            
        elif query.data.startswith("set_price_"):
            # Handle token price setting
            price = float(query.data.split("_")[2])
            await update_clone_config(bot_id, {
                "token_settings.pricing": price,
                "updated_at": datetime.now()
            })
            await query.answer(f"✅ Token price set to ${price}!", show_alert=True)
            
        elif query.data.startswith("set_delete_"):
            # Handle auto delete time setting
            time_seconds = int(query.data.split("_")[2])
            await update_clone_time_settings(bot_id, "auto_delete_time", time_seconds)
            await query.answer(f"✅ Auto delete time set to {time_seconds//60} minutes!", show_alert=True)
            
        elif query.data.startswith("api_"):
            # Handle API configuration
            api_type = query.data.split("_")[1]
            api_urls = {
                "terabox": "https://teraboxlinks.com/api",
                "shortio": "https://short.io/api",
                "tinyurl": "https://tinyurl.com/api-create.php",
                "bitly": "https://api-ssl.bitly.com/v4/shorten",
                "custom": ""
            }
            
            api_url = api_urls.get(api_type, "")
            await update_clone_shortener(bot_id, api_url, "")
            
            if api_type == "custom":
                await query.answer("✅ Custom API selected! Use 'Set API Key' to configure.", show_alert=True)
            else:
                await query.answer(f"✅ {api_type.title()} API configured!", show_alert=True)
        
        # Clear cache and refresh settings panel
        clone_config_loader.clear_cache(getattr(client, 'bot_token', Config.BOT_TOKEN))
        await show_clone_settings_panel(client, query)
        
    except Exception as e:
        print(f"❌ ERROR in value setting: {e}")
        await query.answer("❌ Error updating setting!", show_alert=True)

# Navigation and utility handlers
@Client.on_callback_query(filters.regex("^(refresh_settings|back_to_start)$"))
async def handle_navigation(client: Client, query: CallbackQuery):
    """Handle navigation buttons"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    await query.answer()
    
    if query.data == "refresh_settings":
        # Clear cache and refresh
        clone_config_loader.clear_cache(getattr(client, 'bot_token', Config.BOT_TOKEN))
        await show_clone_settings_panel(client, query)
    elif query.data == "back_to_start":
        # Go back to main start menu
        from bot.plugins.start_handler import send_start_message
        await send_start_message(client, query.message, user_id)

# Add settings button to start message for clone admins
@Client.on_callback_query(filters.regex("^clone_admin_settings$"))
async def clone_admin_settings_callback(client: Client, query: CallbackQuery):
    """Handle clone admin settings callback from start menu"""
    user_id = query.from_user.id
    
    if not await is_clone_admin(client, user_id):
        await query.answer("❌ Access denied! Only clone admins can access settings.", show_alert=True)
        return
    
    await show_clone_settings_panel(client, query)
