
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from info import Config


async def handle_force_sub(client, message: Message):
    user = message.from_user
    user_id = user.id
    
    # Admin exemption - skip force subscription for admins and owner
    if user_id == Config.OWNER_ID or user_id in Config.ADMINS:
        print(f"DEBUG: Admin/Owner {user_id} exempted from force subscription")
        return True  # Allow admin to continue without force sub check

    not_joined_force = []
    joined = []
    buttons = []

    # Get force channels from config (local) and global database 
    config_force_channels = getattr(Config, 'FORCE_SUB_CHANNEL', [])
    config_request_channels = getattr(Config, 'REQUEST_CHANNEL', [])
    
    # Get global force channels from database
    try:
        from bot.database.clone_db import get_global_force_channels
        global_force_channels = await get_global_force_channels()
    except Exception as e:
        print(f"Error fetching global force channels: {e}")
        global_force_channels = []
    
    # Combine local config and global channels
    force_channels = config_force_channels + global_force_channels
    request_channels = config_request_channels
    all_channels = force_channels + request_channels

    if not all_channels:
        return True  # No force sub channels configured, allow user to continue

    # Check membership for force subscription channels
    for ch in force_channels:
        try:
            # Skip empty or invalid channels
            if not ch or ch == "..." or str(ch).strip() == "":
                print(f"DEBUG: Skipping invalid channel: {ch}")
                continue
                
            # Convert to int if it's a string number
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                ch = int(ch)
            
            member = await client.get_chat_member(ch, user_id)
            if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                joined.append(ch)
            else:
                not_joined_force.append(ch)
        except Exception as e:
            print(f"Error checking membership for force channel {ch}: {e}")
            not_joined_force.append(ch)

    # Check membership for request channels (optional)
    for ch in request_channels:
        try:
            # Skip empty or invalid channels
            if not ch or ch == "..." or str(ch).strip() == "":
                print(f"DEBUG: Skipping invalid request channel: {ch}")
                continue
                
            # Convert to int if it's a string number
            if isinstance(ch, str) and ch.lstrip('-').isdigit():
                ch = int(ch)
                
            member = await client.get_chat_member(ch, user_id)
            if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                joined.append(ch)
        except Exception as e:
            print(f"Error checking membership for request channel {ch}: {e}")

    # If user hasn't joined required force channels, show force sub message
    if not_joined_force:
        print(f"DEBUG: User {user_id} needs to join {len(not_joined_force)} force channels")
        
        # Create buttons for force subscription channels
        for ch in not_joined_force:
            try:
                # Skip invalid channels
                if not ch or ch == "..." or str(ch).strip() == "":
                    continue
                    
                # Convert to int if it's a string number
                if isinstance(ch, str) and ch.lstrip('-').isdigit():
                    ch = int(ch)
                
                if hasattr(client, 'channel_info') and client.channel_info.get(ch):
                    info = client.channel_info.get(ch)
                    title = info.get('title', f'Channel {ch}')
                    url = info.get('invite_link')
                else:
                    try:
                        chat = await client.get_chat(ch)
                        title = chat.title or f'Channel {ch}'
                        url = chat.invite_link
                    except Exception as e:
                        print(f"Error getting chat info for {ch}: {e}")
                        title = f'Channel {ch}'
                        url = None

                if not url:
                    try:
                        url = await client.export_chat_invite_link(ch)
                    except Exception as e:
                        print(f"Error exporting invite link for {ch}: {e}")
                        # Create fallback URL
                        if str(ch).startswith('-100'):
                            url = f"https://t.me/c/{str(ch)[4:]}"
                        else:
                            url = f"https://t.me/{ch}"

                if url and url.strip():
                    buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=url)])
                    
            except Exception as e:
                print(f"Error creating button for force channel {ch}: {e}")

        # Create joined channels text
        joined_txt = ""
        if joined:
            joined_txt = "✅ **Joined Channels:**\n"
            for ch in joined[:5]:  # Show max 5 joined channels
                try:
                    if isinstance(ch, str) and ch.lstrip('-').isdigit():
                        ch = int(ch)
                    chat = await client.get_chat(ch)
                    title = chat.title or f'Channel {ch}'
                    joined_txt += f"• {title}\n"
                except:
                    joined_txt += f"• Channel {ch}\n"
            joined_txt += "\n"

        # Create force subscription message
        final_message = f"🔒 **Access Restricted**\n\n"
        final_message += f"To use this bot, you must join the following channels:\n\n"
        
        if joined_txt:
            final_message += joined_txt
            
        final_message += f"❌ **Pending Channels ({len(not_joined_force)}):**\n"
        final_message += f"Click the buttons below to join the required channels.\n\n"
        final_message += f"📝 After joining all channels, send /start again to continue."

        # Ensure message doesn't exceed Telegram's 4096 character limit
        if len(final_message) > 4096:
            final_message = final_message[:4090] + "..."
            print(f"WARNING: Force subscription message truncated due to length")

        # Add check button
        buttons.append([InlineKeyboardButton("🔄 Check Membership", callback_data="check_membership")])

        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

        try:
            await message.reply(
                final_message,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            return False  # Block user until they join required channels
        except Exception as e:
            print(f"Error sending force subscription message: {e}")
            try:
                clean_message = "🔒 Please join the required channels to continue using this bot."
                await message.reply(clean_message, reply_markup=reply_markup)
            except Exception as e2:
                print(f"Error sending fallback message: {e2}")
                await message.reply("❌ Please join the required channels to continue.")
            return False

    print(f"DEBUG: User {user_id} has joined all required channels")
    return True  # User has joined all required channels


async def is_user_member(client, channel_id, user_id):
    """Check if user is a member of the specified channel"""
    try:
        # Skip invalid channels
        if not channel_id or channel_id == "..." or str(channel_id).strip() == "":
            return False
            
        # Convert to int if it's a string number
        if isinstance(channel_id, str) and channel_id.lstrip('-').isdigit():
            channel_id = int(channel_id)
            
        member = await client.get_chat_member(channel_id, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        print(f"Error checking membership for channel {channel_id}: {e}")
        return False


async def check_all_subscriptions(client, user_id):
    """Check if user is subscribed to all required channels"""
    # Admin exemption
    if user_id == Config.OWNER_ID or user_id in Config.ADMINS:
        return True
        
    # Get all required channels
    config_force_channels = getattr(Config, 'FORCE_SUB_CHANNEL', [])
    
    try:
        from bot.database.clone_db import get_global_force_channels
        global_force_channels = await get_global_force_channels()
    except:
        global_force_channels = []
    
    all_required_channels = config_force_channels + global_force_channels
    
    if not all_required_channels:
        return True
    
    # Check membership for all required channels
    for channel in all_required_channels:
        if not await is_user_member(client, channel, user_id):
            return False
    
    return True
