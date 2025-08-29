from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database import add_premium_user, remove_premium, get_users_count
from bot.database.premium_db import get_all_premium_users
import os
import asyncio
from dotenv import set_key, load_dotenv

# Admin verification decorator
def admin_only(func):
    async def wrapper(client, message):
        user_id = message.from_user.id
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            return await message.reply_text("❌ This command is only available to administrators.")
        return await func(client, message)
    return wrapper

@Client.on_message(filters.command("adminhelp") & filters.private)
@admin_only
async def admin_help_command(client: Client, message: Message):
    """Show admin help"""
    help_text = f"""
🔧 **Admin Commands Help**

🔗 **File Management:**
• `/genlink` - Generate single file link
• `/batch` - Generate batch file links  
• `/link` - Generate link for specific file
• `/indexchannel` - Index a channel for file storage

📊 **User Management:**
• `/users` - Get total user count
• `/broadcast` - Broadcast message to all users
• `/stats` - View bot statistics

🛠️ **Channel Management:**
• `/addforce <channel_id>` - Add force subscription channel
• `/removeforce <channel_id>` - Remove force subscription channel
• `/listforce` - List all force subscription channels

🔐 **Request Channels:**
• `/approveuser <user_id> <channel_id>` - Approve join request
• `/pendingrequests` - View pending requests

💰 **Payment Commands:**
• `/payments` - Show available payment methods
• `/addpremium <user_id> <days>` - Add premium subscription

⚙️ **System:**
• `/debug` - Debug information
• `/token` - Generate verification tokens

📨 **Contact:** @{Config.ADMIN_USERNAME}
    """
    await message.reply_text(help_text)

# Force Subscription Channel Management
@Client.on_message(filters.command("addforce") & filters.private)
@admin_only
async def add_force_channel(client: Client, message: Message):
    """Add force subscription channel"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/addforce <channel_id_or_username>`\nExample: `/addforce -1001234567890` or `/addforce @mychannel`")

    try:
        channel_input = message.command[1]
        
        # Handle username input
        if channel_input.startswith('@'):
            channel_input = channel_input[1:]  # Remove @ symbol
        
        # Test if bot can access the channel
        try:
            chat = await client.get_chat(channel_input)
            channel_id = chat.id
            channel_title = chat.title or f"Channel {channel_id}"
        except Exception as e:
            return await message.reply_text(f"❌ Cannot access channel {channel_input}. Make sure the bot is added to the channel and the channel ID/username is correct.\nError: {str(e)}")

        # Initialize Config.FORCE_SUB_CHANNEL if it doesn't exist
        if not hasattr(Config, 'FORCE_SUB_CHANNEL') or Config.FORCE_SUB_CHANNEL is None:
            Config.FORCE_SUB_CHANNEL = []

        # Update environment and config
        current_channels = set(Config.FORCE_SUB_CHANNEL)
        current_channels.add(channel_id)
        channel_list = " ".join(str(ch) for ch in current_channels)

        # Update .env file
        try:
            set_key(".env", "FORCE_SUB_CHANNEL", channel_list)
        except Exception as e:
            print(f"Warning: Could not update .env file: {e}")
            
        Config.FORCE_SUB_CHANNEL = list(current_channels)

        # Update bot's channel info
        try:
            if not hasattr(client, 'channel_info'):
                client.channel_info = {}
                
            invite_link = chat.invite_link
            if not invite_link:
                try:
                    invite_link = await client.export_chat_invite_link(channel_id)
                except Exception as e:
                    print(f"Could not export invite link: {e}")
                    invite_link = f"https://t.me/c/{str(channel_id)[4:]}" if str(channel_id).startswith('-100') else f"https://t.me/{channel_input}"

            client.channel_info[channel_id] = {
                'title': channel_title,
                'invite_link': invite_link
            }
        except Exception as e:
            print(f"Warning: Could not update channel info: {e}")

        await message.reply_text(f"✅ Added force subscription channel: **{channel_title}** (`{channel_id}`)")

    except Exception as e:
        await message.reply_text(f"❌ Error adding channel: {str(e)}")

@Client.on_message(filters.command("removeforce") & filters.private)
@admin_only
async def remove_force_channel(client: Client, message: Message):
    """Remove force subscription channel"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/removeforce <channel_id>`")

    try:
        channel_id = int(message.command[1])

        if channel_id not in Config.FORCE_SUB_CHANNEL:
            return await message.reply_text(f"❌ Channel {channel_id} is not in force subscription list.")

        # Update config
        current_channels = set(Config.FORCE_SUB_CHANNEL)
        current_channels.discard(channel_id)
        channel_list = " ".join(str(ch) for ch in current_channels)

        # Update .env file
        set_key(".env", "FORCE_SUB_CHANNEL", channel_list)
        Config.FORCE_SUB_CHANNEL = list(current_channels)

        # Remove from bot's channel info
        if channel_id in client.channel_info:
            del client.channel_info[channel_id]

        await message.reply_text(f"✅ Removed force subscription channel: `{channel_id}`")

    except ValueError:
        await message.reply_text("❌ Invalid channel ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error removing channel: {str(e)}")

@Client.on_message(filters.command("listforce") & filters.private)
@admin_only
async def list_force_channels(client: Client, message: Message):
    """List all force subscription channels"""
    if not Config.FORCE_SUB_CHANNEL:
        return await message.reply_text("📋 No force subscription channels configured.")

    text = "📢 **Force Subscription Channels:**\n\n"
    valid_channels = []
    
    for i, channel_id in enumerate(Config.FORCE_SUB_CHANNEL, 1):
        try:
            # Skip invalid entries
            if not channel_id or channel_id == "..." or str(channel_id).strip() == "":
                continue
                
            if hasattr(client, 'channel_info') and channel_id in client.channel_info:
                title = client.channel_info[channel_id]['title']
            else:
                chat = await client.get_chat(channel_id)
                title = chat.title or f"Channel {channel_id}"

            text += f"{i}. **{title}**\n   ID: `{channel_id}`\n\n"
            valid_channels.append(channel_id)
        except Exception as e:
            text += f"{i}. **Invalid Channel**\n   ID: `{channel_id}` ❌\n   Error: {str(e)[:50]}...\n\n"

    # Update config with only valid channels
    if len(valid_channels) != len(Config.FORCE_SUB_CHANNEL):
        Config.FORCE_SUB_CHANNEL = valid_channels
        text += f"\n🔧 **Auto-cleaned invalid channels. Valid channels: {len(valid_channels)}**"

    await message.reply_text(text)

# Request Channel Management
@Client.on_message(filters.command("addrequest") & filters.private)
@admin_only
async def add_request_channel(client: Client, message: Message):
    """Add request approval channel"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/addrequest <channel_id>`\nExample: `/addrequest -1001234567890`")

    try:
        channel_id = int(message.command[1])

        # Test if bot can access the channel
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title or f"Channel {channel_id}"
        except:
            return await message.reply_text(f"❌ Cannot access channel {channel_id}. Make sure the bot is added to the channel.")

        # Update environment and config
        current_channels = set(getattr(Config, 'REQUEST_CHANNEL', []))
        current_channels.add(channel_id)
        channel_list = " ".join(str(ch) for ch in current_channels)

        # Update .env file
        set_key(".env", "REQUEST_CHANNEL", channel_list)
        Config.REQUEST_CHANNEL = list(current_channels)

        await message.reply_text(f"✅ Added request approval channel: **{channel_title}** (`{channel_id}`)")

    except ValueError:
        await message.reply_text("❌ Invalid channel ID. Please provide a valid channel ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error adding request channel: {str(e)}")

@Client.on_message(filters.command("removerequest") & filters.private)
@admin_only
async def remove_request_channel(client: Client, message: Message):
    """Remove request approval channel"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/removerequest <channel_id>`")

    try:
        channel_id = int(message.command[1])

        current_channels = set(getattr(Config, 'REQUEST_CHANNEL', []))
        if channel_id not in current_channels:
            return await message.reply_text(f"❌ Channel {channel_id} is not in request approval list.")

        # Update config
        current_channels.discard(channel_id)
        channel_list = " ".join(str(ch) for ch in current_channels)

        # Update .env file
        set_key(".env", "REQUEST_CHANNEL", channel_list)
        Config.REQUEST_CHANNEL = list(current_channels)

        await message.reply_text(f"✅ Removed request approval channel: `{channel_id}`")

    except ValueError:
        await message.reply_text("❌ Invalid channel ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error removing request channel: {str(e)}")

@Client.on_message(filters.command("listrequest") & filters.private)
@admin_only
async def list_request_channels(client: Client, message: Message):
    """List all request approval channels"""
    request_channels = getattr(Config, 'REQUEST_CHANNEL', [])
    if not request_channels:
        return await message.reply_text("📋 No request approval channels configured.")

    text = "🔔 **Request Approval Channels:**\n\n"
    for i, channel_id in enumerate(request_channels, 1):
        try:
            chat = await client.get_chat(channel_id)
            title = chat.title or f"Channel {channel_id}"
            text += f"{i}. **{title}**\n   ID: `{channel_id}`\n\n"
        except:
            text += f"{i}. **Unknown Channel**\n   ID: `{channel_id}`\n\n"

    await message.reply_text(text)

# Shortlink Management
@Client.on_message(filters.command("setshortlink") & filters.private)
@admin_only
async def set_shortlink(client: Client, message: Message):
    """Configure shortlink API and URL"""
    if len(message.command) < 3:
        return await message.reply_text("❌ Usage: `/setshortlink <api_key> <shortlink_url>`\nExample: `/setshortlink your_api_key teraboxlinks.com`")

    try:
        api_key = message.command[1]
        shortlink_url = message.command[2]

        # Add https:// if not present
        if not shortlink_url.startswith(('http://', 'https://')):
            shortlink_url = f"https://{shortlink_url}/"

        # Update .env file
        set_key(".env", "SHORTLINK_API", api_key)
        set_key(".env", "SHORTLINK_URL", shortlink_url)

        # Update config
        Config.SHORTLINK_API = api_key
        Config.SHORTLINK_URL = shortlink_url

        await message.reply_text(f"✅ Shortlink configuration updated:\n**API Key:** `{api_key}`\n**URL:** `{shortlink_url}`")

    except Exception as e:
        await message.reply_text(f"❌ Error updating shortlink configuration: {str(e)}")

@Client.on_message(filters.command("shortlinkinfo") & filters.private)
@admin_only
async def shortlink_info(client: Client, message: Message):
    """View current shortlink settings"""
    api_key = getattr(Config, 'SHORTLINK_API', 'Not set')
    shortlink_url = getattr(Config, 'SHORTLINK_URL', 'Not set')

    info_text = f"""
🔗 **Current Shortlink Configuration**

**API Key:** `{api_key}`
**Shortlink URL:** `{shortlink_url}`
**Verify Mode:** `{Config.VERIFY_MODE}`

Use `/setshortlink <api_key> <url>` to update configuration.
    """
    await message.reply_text(info_text)

# Existing premium and stats commands
@Client.on_message(filters.command("listpremium") & filters.private)
@admin_only
async def list_premium_users(client: Client, message: Message):
    """List all premium users"""
    try:
        premium_users = await get_all_premium_users()

        if not premium_users:
            return await message.reply_text("📋 No premium users found.")

        text = "👑 **Premium Users List:**\n\n"
        for i, user in enumerate(premium_users[:20], 1):
            user_id = user.get('_id')
            plan = user.get('plan_type', 'Unknown')
            tokens = user.get('tokens_remaining', 0)

            if tokens == -1:
                token_info = "Unlimited"
            else:
                token_info = f"{tokens} tokens"

            text += f"{i}. **User:** `{user_id}`\n   **Plan:** {plan}\n   **Tokens:** {token_info}\n\n"

        if len(premium_users) > 20:
            text += f"... and {len(premium_users) - 20} more users"

        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error retrieving premium users: {e}")

@Client.on_message(filters.command("users") & filters.private)
@admin_only
async def users_count(client: Client, message: Message):
    """Get total user count"""
    try:
        total_users = await get_users_count()
        await message.reply_text(f"👥 **Total Users:** {total_users}")
    except Exception as e:
        await message.reply_text(f"❌ Error getting user count: {e}")

@Client.on_message(filters.command("stats") & filters.private)
@admin_only
async def bot_stats(client: Client, message: Message):
    """Get bot statistics"""
    try:
        total_users = await get_users_count()
        premium_users = await get_all_premium_users()
        premium_count = len(premium_users) if premium_users else 0

        premium_rate = (premium_count/total_users*100) if total_users > 0 else 0

        stats_text = f"""
📊 **Bot Statistics**

👥 **Total Users:** {total_users}
👑 **Premium Users:** {premium_count}
📈 **Premium Rate:** {premium_rate:.1f}%
📢 **Force Sub Channels:** {len(Config.FORCE_SUB_CHANNEL)}
🔔 **Request Channels:** {len(getattr(Config, 'REQUEST_CHANNEL', []))}

🤖 **System Status:** Online ✅
        """
        await message.reply_text(stats_text)
    except Exception as e:
        await message.reply_text(f"❌ Error getting bot stats: {e}")

@Client.on_message(filters.command("testadmin") & filters.private)
@admin_only
async def test_admin(client: Client, message: Message):
    """Test admin functionality"""
    user_id = message.from_user.id
    await message.reply_text(f"✅ Admin verification successful!\n**Your ID:** {user_id}\n**Admin Status:** Confirmed")

@Client.on_message(filters.command("addpremium") & filters.private)
@admin_only
async def add_premium_user_cmd(client: Client, message: Message):
    """Add premium user"""
    if len(message.command) < 3:
        return await message.reply_text("❌ Usage: `/addpremium <user_id> <plan>`\nPlans: basic, standard, premium, unlimited")

    try:
        user_id = int(message.command[1])
        plan = message.command[2].lower()

        PREMIUM_PLANS = {
            "basic": {"tokens": 50, "price": "29"},
            "standard": {"tokens": 150, "price": "79"},
            "premium": {"tokens": 300, "price": "149"},
            "unlimited": {"tokens": -1, "price": "299"}
        }

        if plan not in PREMIUM_PLANS:
            return await message.reply_text("❌ Invalid plan. Available plans: basic, standard, premium, unlimited")

        plan_info = PREMIUM_PLANS[plan]
        
        # Show processing message
        processing_msg = await message.reply_text("⏳ Adding premium membership...")
        
        success = await add_premium_user(user_id, plan, plan_info["tokens"])

        if success:
            await processing_msg.edit_text(f"✅ Successfully added premium membership for user {user_id}\n**Plan:** {plan}\n**Tokens:** {plan_info['tokens'] if plan_info['tokens'] != -1 else 'Unlimited'}")
            
            # Try to notify the user
            try:
                await client.send_message(
                    user_id,
                    f"🎉 **Congratulations!**\n\n"
                    f"✨ You have been upgraded to **{plan.title()} Premium**\n"
                    f"🎯 **Tokens:** {plan_info['tokens'] if plan_info['tokens'] != -1 else 'Unlimited'}\n\n"
                    f"🎯 **Benefits:**\n"
                    f"• 🚫 No Ads\n"
                    f"• ⚡ Instant Access\n"
                    f"• 🔥 Unlimited Downloads"
                )
            except Exception as notify_error:
                await message.reply_text(f"✅ Premium added but couldn't notify user: {notify_error}")
        else:
            await processing_msg.edit_text("❌ Failed to add premium membership. Please check logs for details.")

    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a valid user ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error adding premium user: {str(e)}")
        print(f"Error in addpremium command: {e}")
        import traceback
        traceback.print_exc()

@Client.on_message(filters.command("removepremium") & filters.private)
@admin_only
async def remove_premium_user_cmd(client: Client, message: Message):
    """Remove premium user"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/removepremium <user_id>`")

    try:
        user_id = int(message.command[1])
        success = await remove_premium(user_id)

        if success:
            await message.reply_text(f"✅ Successfully removed premium membership for user {user_id}")
        else:
            await message.reply_text("❌ Failed to remove premium membership. User might not be premium.")

    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a valid user ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error removing premium user: {str(e)}")

@Client.on_message(filters.command("broadcast") & filters.private)
@admin_only
async def broadcast_message(client: Client, message: Message):
    """Broadcast message to all users"""
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/broadcast <message>`\nExample: `/broadcast Hello everyone! New updates available.`")

    try:
        broadcast_text = message.text.split(None, 1)[1]

        from bot.database import get_all_users
        users = await get_all_users()

        if not users:
            return await message.reply_text("❌ No users found in database.")

        status_msg = await message.reply_text(f"📢 Broadcasting to {len(users)} users...")

        success_count = 0
        failed_count = 0

        for user_id in users:
            try:
                await client.send_message(user_id, broadcast_text)
                success_count += 1
                await asyncio.sleep(0.1)  # Avoid rate limits
            except Exception:
                failed_count += 1

        await status_msg.edit_text(


@Client.on_message(filters.command("clearinvalidchannels") & filters.private)
@admin_only
async def clear_invalid_channels(client: Client, message: Message):
    """Clear invalid force subscription channels"""
    if not Config.FORCE_SUB_CHANNEL:
        return await message.reply_text("📋 No force subscription channels configured.")

    valid_channels = []
    invalid_channels = []
    
    for channel_id in Config.FORCE_SUB_CHANNEL:
        try:
            # Skip obviously invalid entries
            if not channel_id or channel_id == "..." or str(channel_id).strip() == "":
                invalid_channels.append(channel_id)
                continue
                
            # Test channel access
            chat = await client.get_chat(channel_id)
            valid_channels.append(channel_id)
        except Exception as e:
            print(f"Invalid channel detected: {channel_id} - {e}")
            invalid_channels.append(channel_id)

    # Update config
    Config.FORCE_SUB_CHANNEL = valid_channels
    
    # Update .env file
    try:
        channel_list = " ".join(str(ch) for ch in valid_channels)
        set_key(".env", "FORCE_SUB_CHANNEL", channel_list)
    except Exception as e:
        print(f"Warning: Could not update .env file: {e}")

    result_text = f"🔧 **Channel Cleanup Complete**\n\n"
    result_text += f"✅ **Valid Channels:** {len(valid_channels)}\n"
    result_text += f"❌ **Removed Invalid:** {len(invalid_channels)}\n\n"
    
    if invalid_channels:
        result_text += f"**Removed Channels:**\n"
        for ch in invalid_channels:
            result_text += f"• `{ch}`\n"

    await message.reply_text(result_text)

            f"📢 **Broadcast Complete**\n\n"
            f"✅ **Successful:** {success_count}\n"
            f"❌ **Failed:** {failed_count}\n"
            f"📊 **Total:** {len(users)}"
        )

    except Exception as e:
        await message.reply_text(f"❌ Error during broadcast: {str(e)}")

@Client.on_message(filters.command("approveuser") & filters.private)
@admin_only
async def approve_user_request(client: Client, message: Message):
    """Approve user join request"""
    if len(message.command) < 3:
        return await message.reply_text("❌ Usage: `/approveuser <user_id> <channel_id>`")

    try:
        user_id = int(message.command[1])
        channel_id = int(message.command[2])

        # Approve the user in the channel
        await client.approve_chat_join_request(channel_id, user_id)
        await message.reply_text(f"✅ Approved join request for user {user_id} in channel {channel_id}")

    except ValueError:
        await message.reply_text("❌ Invalid user ID or channel ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error approving user: {str(e)}")

@Client.on_message(filters.command("pendingrequests") & filters.private)
@admin_only
async def pending_requests(client: Client, message: Message):
    """View pending join requests"""
    request_channels = getattr(Config, 'REQUEST_CHANNEL', [])

    if not request_channels:
        return await message.reply_text("❌ No request channels configured.")

    pending_text = "🔔 **Pending Join Requests:**\n\n"

    for channel_id in request_channels:
        try:
            chat = await client.get_chat(channel_id)
            pending_text += f"**{chat.title}** (`{channel_id}`)\n"
            pending_text += f"Use `/approveuser <user_id> {channel_id}` to approve requests\n\n"
        except Exception as e:
            pending_text += f"**Channel {channel_id}:** Error accessing - {str(e)}\n\n"

    await message.reply_text(pending_text)

@Client.on_message(filters.command("payments") & filters.private)
@admin_only
async def payments_command(client: Client, message: Message):
    """Show available payment methods"""
    payment_text = "💰 **Available Payment Methods**\n\n"

    # Traditional payment methods
    payment_text += f"📱 **UPI:** `{Config.PAYMENT_UPI}`\n"
    payment_text += f"📞 **Phone:** `{Config.PAYMENT_PHONE}`\n\n"

    # Cryptocurrency payments
    if Config.CRYPTO_ENABLED:
        payment_text += "🪙 **Cryptocurrency Options:**\n\n"

        if Config.BITCOIN_ADDRESS:
            payment_text += f"₿ **Bitcoin (BTC):**\n`{Config.BITCOIN_ADDRESS}`\n\n"

        if Config.ETHEREUM_ADDRESS:
            payment_text += f"🔷 **Ethereum (ETH):**\n`{Config.ETHEREUM_ADDRESS}`\n\n"

        if Config.USDT_TRC20_ADDRESS:
            payment_text += f"💵 **USDT (TRC20):**\n`{Config.USDT_TRC20_ADDRESS}`\n\n"

        if Config.USDT_ERC20_ADDRESS:
            payment_text += f"💵 **USDT (ERC20):**\n`{Config.USDT_ERC20_ADDRESS}`\n\n"

    payment_text += f"📨 **Contact Admin:** @{Config.ADMIN_USERNAME}"

    await message.reply_text(payment_text)

@Client.on_message(filters.command("indexchannel") & filters.private)
@admin_only  
async def index_channel_command(client: Client, message: Message):
    """Index a channel by providing channel ID"""
    if len(message.command) < 2:
        help_text = """
📋 **Index Channel Command:**

**Usage:** `/indexchannel <channel_id>`
**Example:** `/indexchannel -1001234567890`

ℹ️ **Note:** 
• The bot must be an admin in the channel
• Use the channel ID (starts with -100)
• This will set the channel as your file storage channel
        """
        return await message.reply_text(help_text)

    try:
        channel_id = int(message.command[1])
        
        # Test if bot can access the channel
        try:
            chat = await client.get_chat(channel_id)
            channel_title = chat.title or f"Channel {channel_id}"
        except Exception as e:
            return await message.reply_text(f"❌ Cannot access channel {channel_id}. Make sure the bot is added as admin.\nError: {str(e)}")

        # Update the bot's db_channel
        try:
            client.db_channel = chat
            await message.reply_text(f"✅ Successfully indexed channel: **{channel_title}**\nChannel ID: `{channel_id}`\n\n🎯 This channel is now set as your file storage channel.")
        except Exception as e:
            await message.reply_text(f"❌ Error setting channel: {str(e)}")

    except ValueError:
        await message.reply_text("❌ Invalid channel ID. Please provide a valid channel ID starting with -100.")
    except Exception as e:
        await message.reply_text(f"❌ Error indexing channel: {str(e)}")

@Client.on_message(filters.command("debug") & filters.private)
@admin_only
async def debug_command(client: Client, message: Message):
    """Debug command to check bot status and configuration"""
    if message.reply_to_message:
        msg = message.reply_to_message
        debug_info = f"**Message Debug Info:**\n\n"
        debug_info += f"Message ID: {msg.id}\n"
        debug_info += f"Is Forwarded: {bool(msg.forward_from_chat)}\n"
        if msg.forward_from_chat:
            debug_info += f"Forward From: {msg.forward_from_chat.title or msg.forward_from_chat.username}\n"
            debug_info += f"Forward From ID: {msg.forward_from_chat.id}\n"
            debug_info += f"Forward From Type: {msg.forward_from_chat.type}\n"
        debug_info += f"Has Media: {bool(msg.media)}\n"
        debug_info += f"Media Type: {msg.media if msg.media else 'None'}\n"
        debug_info += f"Text: {msg.text[:100] if msg.text else 'None'}\n"
        debug_info += f"Caption: {msg.caption[:100] if msg.caption else 'None'}\n"
        await message.reply_text(debug_info)
    else:
        # General bot debug info
        from bot.database import get_users_count
        total_users = await get_users_count()

        debug_info = f"""
🔧 **Bot Debug Information**

**Database Status:** Connected ✅
**Total Users:** {total_users}
**Force Sub Channels:** {len(Config.FORCE_SUB_CHANNEL)}
**Request Channels:** {len(getattr(Config, 'REQUEST_CHANNEL', []))}
**Auto Delete:** {'Enabled' if Config.AUTO_DELETE_TIME > 0 else 'Disabled'}
**Verify Mode:** {'Enabled' if Config.VERIFY_MODE else 'Disabled'}

**Bot Username:** @{client.me.username if hasattr(client, 'me') and client.me else 'Unknown'}
**Bot ID:** {client.me.id if hasattr(client, 'me') and client.me else 'Unknown'}

Reply to a message to debug specific message properties.
        """
        await message.reply_text(debug_info)