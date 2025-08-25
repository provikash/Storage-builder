from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

@Client.on_message(filters.command("activate_clone") & filters.private)
async def activate_clone_command(client: Client, message: Message):
    """Activate a clone bot"""
    user_id = message.from_user.id
    print(f"DEBUG: activate_clone command from user {user_id}")

    # Debug admin check
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    print(f"DEBUG: activate_clone admin check - user_id: {user_id}, admin_list: {admin_list}")

    if user_id not in admin_list:
        print(f"DEBUG: activate_clone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot admins can activate clones.")

    print(f"DEBUG: activate_clone access granted for user {user_id}")

    if len(message.command) < 2:
        print(f"DEBUG: activate_clone invalid format from user {user_id}")
        return await message.reply_text("❌ Usage: `/activate_clone <bot_id>`")

    bot_id = message.command[1]
    print(f"DEBUG: activate_clone attempting to activate bot_id: {bot_id}")

    try:
        # Get clone data
        clone_data = await get_clone(bot_id)
        if not clone_data:
            print(f"DEBUG: activate_clone clone not found: {bot_id}")
            return await message.reply_text(f"❌ Clone {bot_id} not found.")

        print(f"DEBUG: activate_clone found clone: {clone_data.get('username', 'Unknown')}")

        # Update status to active
        await update_clone_status(bot_id, 'active')
        print(f"DEBUG: activate_clone updated status to active for {bot_id}")

        # Start the clone
        success, result = await clone_manager.start_clone(bot_id)
        print(f"DEBUG: activate_clone start result: success={success}, result={result}")

        if success:
            await message.reply_text(
                f"✅ **Clone Activated Successfully!**\n\n"
                f"🤖 **Bot:** @{clone_data.get('username', 'Unknown')}\n"
                f"🆔 **Bot ID:** {bot_id}\n"
                f"📊 **Status:** Active & Running"
            )
        else:
            await message.reply_text(f"⚠️ Clone activated but failed to start: {result}")

    except Exception as e:
        print(f"DEBUG: activate_clone error: {e}")
        await message.reply_text(f"❌ Error activating clone: {str(e)}")

@Client.on_message(filters.command("dashboard") & filters.private)
async def dashboard_command(client: Client, message: Message):
    """Show dashboard with system overview"""
    user_id = message.from_user.id
    print(f"DEBUG: dashboard command from user {user_id}")

    # Debug admin check
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    print(f"DEBUG: dashboard admin check - user_id: {user_id}, admin_list: {admin_list}")

    if user_id not in admin_list:
        print(f"DEBUG: dashboard access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot admins can access dashboard.")

    print(f"DEBUG: dashboard access granted for user {user_id}")

    try:
        # Get system stats
        total_clones = len(await get_all_clones())
        active_clones = len([c for c in await get_all_clones() if c['status'] == 'active'])
        running_clones = len(clone_manager.get_running_clones())
        total_subscriptions = len(await get_all_subscriptions())

        print(f"DEBUG: dashboard stats - total_clones: {total_clones}, active_clones: {active_clones}, running_clones: {running_clones}")

        dashboard_text = f"📊 **System Dashboard**\n\n"
        dashboard_text += f"🤖 **Clone Statistics:**\n"
        dashboard_text += f"• Total Clones: {total_clones}\n"
        dashboard_text += f"• Active Clones: {active_clones}\n"
        dashboard_text += f"• Running Clones: {running_clones}\n\n"
        dashboard_text += f"💰 **Subscriptions:**\n"
        dashboard_text += f"• Total Subscriptions: {total_subscriptions}\n\n"
        dashboard_text += f"⏱️ **System Status:**\n"
        dashboard_text += f"• Mother Bot: Running\n"
        dashboard_text += f"• Clone Manager: Active\n"
        dashboard_text += f"• Database: Connected\n"
        dashboard_text += f"• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        dashboard_text += f"**Quick Commands:**\n"
        dashboard_text += f"• `/admin` - Admin Panel\n"
        dashboard_text += f"• `/createclone` - Create New Clone\n"
        dashboard_text += f"• `/activate_clone <id>` - Activate Clone"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎛️ Admin Panel", callback_data="mother_admin_panel")],
            [InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="refresh_dashboard")]
        ])

        await message.reply_text(dashboard_text, reply_markup=buttons)
        print(f"DEBUG: dashboard sent successfully to user {user_id}")

    except Exception as e:
        print(f"DEBUG: dashboard error: {e}")
        await message.reply_text(f"❌ Error loading dashboard: {str(e)}")

# Add debug logging to existing commands
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config
from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.utils.clone_config_loader import clone_config_loader
from clone_manager import clone_manager

# Mother Bot Commands
@Client.on_message(filters.command("createclone") & filters.private)
async def create_clone_command(client: Client, message: Message):
    """Create a new clone bot"""
    user_id = message.from_user.id
    print(f"DEBUG: createclone command from user {user_id}")

    # Debug admin check
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    print(f"DEBUG: createclone admin check - user_id: {user_id}, owner_id: {owner_id}, admins: {admins}, admin_list: {admin_list}")

    if user_id not in admin_list:
        print(f"DEBUG: createclone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot admins can create clones.")

    print(f"DEBUG: createclone access granted for user {user_id}")

    if len(message.command) < 4:
        return await message.reply_text(
            "❌ **Invalid format!**\n\n"
            "Usage: `/createclone <bot_token> <admin_id> <db_url> [tier]`"
        )

    bot_token = message.command[1]
    try:
        admin_id = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ Admin ID must be a valid number!")

    db_url = message.command[3]
    tier = message.command[4] if len(message.command) > 4 else "monthly"

    processing_msg = await message.reply_text("🔄 Creating clone bot... Please wait.")

    try:
        success, result = await clone_manager.create_clone(bot_token, admin_id, db_url, tier)

        if success:
            await processing_msg.edit_text(
                f"🎉 **Clone Created Successfully!**\n\n"
                f"🤖 **Bot Username:** @{result['username']}\n"
                f"🆔 **Bot ID:** {result['bot_id']}\n"
                f"👤 **Admin ID:** {result['admin_id']}\n"
                f"💰 **Tier:** {tier}\n"
                f"📊 **Status:** Pending Payment"
            )
        else:
            await processing_msg.edit_text(f"❌ **Failed to create clone:**\n{result}")

    except Exception as e:
        await processing_msg.edit_text(f"❌ **Error creating clone:**\n{str(e)}")

@Client.on_message(filters.command("setglobalchannels") & filters.private)
async def set_global_channels(client: Client, message: Message):
    """Set global force channels"""
    user_id = message.from_user.id
    print(f"DEBUG: setglobalchannels command from user {user_id}")

    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: setglobalchannels access denied for user {user_id}")
        return await message.reply_text("❌ Access denied.")

    print(f"DEBUG: setglobalchannels access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setglobalchannels channel1 channel2 ...`\n\n"
            "Example: `/setglobalchannels @channel1 @channel2 -1001234567890`"
        )

    channels = message.command[1:]
    await set_global_force_channels(channels)

    await message.reply_text(
        f"✅ **Global force channels updated!**\n\n"
        f"**Channels set:**\n" + 
        "\n".join(f"• {channel}" for channel in channels)
    )

@Client.on_message(filters.command("setglobalabout") & filters.private)
async def set_global_about(client: Client, message: Message):
    """Set global about page"""
    user_id = message.from_user.id
    print(f"DEBUG: setglobalabout command from user {user_id}")

    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: setglobalabout access denied for user {user_id}")
        return await message.reply_text("❌ Access denied.")

    print(f"DEBUG: setglobalabout access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: /setglobalabout <about_text>")

    about_text = " ".join(message.command[1:])
    from bot.database.clone_db import set_global_setting
    await set_global_setting("global_about", about_text)

    await message.reply_text(f"✅ **Global about page updated!**\n\nPreview:\n{about_text[:200]}{'...' if len(about_text) > 200 else ''}")

@Client.on_message(filters.command("disableclone") & filters.private)
async def disable_clone_command(client: Client, message: Message):
    """Disable a clone bot"""
    user_id = message.from_user.id
    print(f"DEBUG: disableclone command from user {user_id}")

    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: disableclone access denied for user {user_id}")
        return await message.reply_text("❌ Access denied.")

    print(f"DEBUG: disableclone access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: /disableclone <bot_id>")

    bot_id = message.command[1]

    try:
        await deactivate_clone(bot_id)
        await clone_manager.stop_clone(bot_id)
        await message.reply_text(f"✅ Clone {bot_id} has been disabled and stopped.")
    except Exception as e:
        await message.reply_text(f"❌ Error disabling clone: {str(e)}")

# Clone Bot Commands
@Client.on_message(filters.command("addforce") & filters.private)
async def add_force_channel(client: Client, message: Message):
    """Add local force channel"""
    user_id = message.from_user.id
    print(f"DEBUG: addforce command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        print(f"DEBUG: addforce not a clone bot")
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: addforce access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: addforce access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addforce <channel_id_or_username>`")

    channel = message.command[1]
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)

    channels = current_config.get('channels', {})
    local_force = channels.get('force_channels', [])

    if channel not in local_force:
        local_force.append(channel)
        channels['force_channels'] = local_force

        await update_clone_config(bot_id, {'channels': channels})
        clone_config_loader.clear_cache(bot_token)

        await message.reply_text(f"✅ Added force channel: {channel}")
    else:
        await message.reply_text("❌ Channel already in force list.")

@Client.on_message(filters.command("removeforce") & filters.private)
async def remove_force_channel(client: Client, message: Message):
    """Remove local force channel"""
    user_id = message.from_user.id
    print(f"DEBUG: removeforce command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: removeforce access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: removeforce access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/removeforce <channel_id_or_username>`")

    channel = message.command[1]
    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)

    channels = current_config.get('channels', {})
    local_force = channels.get('force_channels', [])

    if channel in local_force:
        local_force.remove(channel)
        channels['force_channels'] = local_force

        await update_clone_config(bot_id, {'channels': channels})
        clone_config_loader.clear_cache(bot_token)

        await message.reply_text(f"✅ Removed force channel: {channel}")
    else:
        await message.reply_text("❌ Channel not found in force list.")

@Client.on_message(filters.command("settokenmode") & filters.private)
async def set_token_mode(client: Client, message: Message):
    """Set token verification mode"""
    user_id = message.from_user.id
    print(f"DEBUG: settokenmode command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: settokenmode access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: settokenmode access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/settokenmode <mode>`\n\n"
            "Available modes:\n"
            "• `one_time` - Single use tokens\n"
            "• `command_limit` - Limited uses per token"
        )

    mode = message.command[1].lower()
    if mode not in ['one_time', 'command_limit']:
        return await message.reply_text("❌ Invalid mode. Use 'one_time' or 'command_limit'")

    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['mode'] = mode

    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)

    await message.reply_text(f"✅ Token mode set to: {mode.replace('_', ' ').title()}")

@Client.on_message(filters.command("setcommandlimit") & filters.private)
async def set_command_limit(client: Client, message: Message):
    """Set command limit for tokens"""
    user_id = message.from_user.id
    print(f"DEBUG: setcommandlimit command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: setcommandlimit access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: setcommandlimit access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/setcommandlimit <number>`")

    try:
        limit = int(message.command[1])
        if limit < 1:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Please provide a valid positive number.")

    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['command_limit'] = limit

    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)

    await message.reply_text(f"✅ Command limit set to: {limit}")

@Client.on_message(filters.command("settokenprice") & filters.private)
async def set_token_price(client: Client, message: Message):
    """Set token price"""
    user_id = message.from_user.id
    print(f"DEBUG: settokenprice command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: settokenprice access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: settokenprice access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/settokenprice <price>`")

    try:
        price = float(message.command[1])
        if price < 0.10 or price > 10.00:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Price must be between $0.10 and $10.00")

    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})
    token_settings['pricing'] = price

    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)

    await message.reply_text(f"✅ Token price set to: ${price}")

@Client.on_message(filters.command("toggletoken") & filters.private)
async def toggle_token_system(client: Client, message: Message):
    """Toggle token system on/off"""
    user_id = message.from_user.id
    print(f"DEBUG: toggletoken command from user {user_id}")

    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    config = await clone_config_loader.get_bot_config(bot_token)

    if not config['bot_info'].get('is_clone', False):
        return

    expected_admin = config['bot_info'].get('admin_id')
    if user_id != expected_admin:
        print(f"DEBUG: toggletoken access denied for user {user_id}, expected admin: {expected_admin}")
        return await message.reply_text("❌ Only clone admin can modify settings.")

    print(f"DEBUG: toggletoken access granted for user {user_id}")

    bot_id = bot_token.split(':')[0]
    current_config = await get_clone_config(bot_id)
    token_settings = current_config.get('token_settings', {})

    current_status = token_settings.get('enabled', True)
    new_status = not current_status
    token_settings['enabled'] = new_status

    await update_clone_config(bot_id, {'token_settings': token_settings})
    clone_config_loader.clear_cache(bot_token)

    status_text = "enabled" if new_status else "disabled"
    await message.reply_text(f"✅ Token system {status_text}!")

@Client.on_message(filters.command("approveclone") & filters.private)
async def approve_clone_command(client: Client, message: Message):
    """Approve a clone request via command"""
    user_id = message.from_user.id
    print(f"DEBUG: approveclone command from user {user_id}. Owner: {Config.OWNER_ID}, Admins: {Config.ADMINS}")

    # Check admin permissions  
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        print(f"DEBUG: approveclone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot administrators can approve clones.")

    print(f"DEBUG: approveclone access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/approveclone <request_id>`")

    request_id = message.command[1]

    try:
        from bot.plugins.clone_approval import approve_clone_request

        # Create a fake query object for the approval function
        class FakeQuery:
            def __init__(self, message):
                self.from_user = message.from_user
                self.message = message
                self.data = f"approve_request:{request_id}"

            async def answer(self, text, show_alert=False):
                await message.reply_text(text)

        fake_query = FakeQuery(message)
        await approve_clone_request(client, fake_query, request_id)

    except Exception as e:
        await message.reply_text(f"❌ Error approving clone: {str(e)}")

@Client.on_message(filters.command("rejectclone") & filters.private)
async def reject_clone_command(client: Client, message: Message):
    """Reject a clone request via command"""
    user_id = message.from_user.id

    # Check admin permissions  
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can reject clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/rejectclone <request_id>`")

    request_id = message.command[1]

    try:
        from bot.plugins.clone_approval import reject_clone_request

        # Create a fake query object for the rejection function
        class FakeQuery:
            def __init__(self, message):
                self.from_user = message.from_user
                self.message = message
                self.data = f"reject_request:{request_id}"

            async def answer(self, text, show_alert=False):
                await message.reply_text(text)

        fake_query = FakeQuery(message)
        await reject_clone_request(client, fake_query, request_id)

    except Exception as e:
        await message.reply_text(f"❌ Error rejecting clone: {str(e)}")

@Client.on_message(filters.command("startclone") & filters.private)
async def start_clone_command(client: Client, message: Message):
    """Manually start a specific clone"""
    user_id = message.from_user.id

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can start clones.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/startclone <bot_id>`")

    bot_id = message.command[1]

    try:
        from clone_manager import clone_manager
        success, msg = await clone_manager.start_clone(bot_id)
        
        if success:
            await message.reply_text(f"✅ Clone {bot_id} started successfully!\n{msg}")
        else:
            await message.reply_text(f"❌ Failed to start clone {bot_id}:\n{msg}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error starting clone: {str(e)}")

@Client.on_message(filters.command("startallclones") & filters.private)
async def start_all_clones_command(client: Client, message: Message):
    """Manually start all active clones"""
    user_id = message.from_user.id

    # Check admin permissions
    if user_id not in [Config.OWNER_ID] + list(Config.ADMINS):
        return await message.reply_text("❌ Only Mother Bot administrators can start clones.")

    try:
        from clone_manager import clone_manager
        started, total = await clone_manager.start_all_clones()
        await message.reply_text(f"🚀 Clone startup completed!\n✅ Started: {started}/{total} clones")
        
    except Exception as e:
        await message.reply_text(f"❌ Error starting clones: {str(e)}")

@Client.on_message(filters.command("deleteclone") & filters.private)
async def delete_clone_command(client: Client, message: Message):
    """Delete a clone permanently"""
    user_id = message.from_user.id
    print(f"DEBUG: deleteclone command from user {user_id}")

    # Check admin permissions
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: deleteclone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot administrators can delete clones.")

    print(f"DEBUG: deleteclone access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/deleteclone <bot_id>`")

    bot_id = message.command[1]

    try:
        # Get clone info before deletion
        clone = await get_clone(bot_id)
        if not clone:
            return await message.reply_text("❌ Clone not found.")

        # Stop the clone if running
        if bot_id in clone_manager.instances:
            await clone_manager.stop_clone(bot_id)

        # Delete from database
        await delete_clone(bot_id)
        await delete_subscription(bot_id)
        await delete_clone_config(bot_id)

        await message.reply_text(
            f"🗑️ **Clone Deleted Successfully**\n\n"
            f"🤖 **Bot:** @{clone.get('username', 'Unknown')}\n"
            f"🆔 **ID:** {bot_id}\n\n"
            f"⚠️ **This action is permanent and cannot be undone.**"
        )

    except Exception as e:
        await message.reply_text(f"❌ Error deleting clone: {str(e)}")

@Client.on_message(filters.command("enableclone") & filters.private)
async def enable_clone_command(client: Client, message: Message):
    """Enable a disabled clone"""
    user_id = message.from_user.id
    print(f"DEBUG: enableclone command from user {user_id}")

    # Check admin permissions
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: enableclone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot administrators can enable clones.")

    print(f"DEBUG: enableclone access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/enableclone <bot_id>`")

    bot_id = message.command[1]

    try:
        # Update status to active
        await update_clone_status(bot_id, 'active')

        # Start the clone
        success, result = await clone_manager.start_clone(bot_id)

        if success:
            await message.reply_text(
                f"✅ **Clone Enabled & Started**\n\n"
                f"🆔 **Bot ID:** {bot_id}\n"
                f"📊 **Status:** Active & Running"
            )
        else:
            await message.reply_text(f"⚠️ Clone enabled but failed to start: {result}")

    except Exception as e:
        await message.reply_text(f"❌ Error enabling clone: {str(e)}")

@Client.on_message(filters.command("disableclone") & filters.private)
async def disable_clone_command(client: Client, message: Message):
    """Disable a clone"""
    user_id = message.from_user.id
    print(f"DEBUG: disableclone command from user {user_id}")

    # Check admin permissions
    admin_list = [Config.OWNER_ID] + list(Config.ADMINS)
    if user_id not in admin_list:
        print(f"DEBUG: disableclone access denied for user {user_id}")
        return await message.reply_text("❌ Only Mother Bot administrators can disable clones.")

    print(f"DEBUG: disableclone access granted for user {user_id}")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/disableclone <bot_id>`")

    bot_id = message.command[1]

    try:
        # Stop the clone if running
        if bot_id in clone_manager.instances:
            await clone_manager.stop_clone(bot_id)

        # Update status to inactive
        await update_clone_status(bot_id, 'inactive')

        await message.reply_text(
            f"🛑 **Clone Disabled**\n\n"
            f"🆔 **Bot ID:** {bot_id}\n"
            f"📊 **Status:** Inactive & Stopped"
        )

    except Exception as e:
        await message.reply_text(f"❌ Error disabling clone: {str(e)}")