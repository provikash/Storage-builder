from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate, UsernameInvalid
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def handle_force_sub(client: Client, message):
    """
    Handle force subscription with admin exemption
    Returns True if user should proceed, False if blocked
    """
    user_id = message.from_user.id

    # Admin exemption - allow all admins to bypass force subscription
    if user_id == Config.OWNER_ID or user_id in Config.ADMINS:
        print(f"✅ DEBUG FORCE: Admin {user_id} exempt from force subscription")
        return True

    # Check if force subscription is enabled
    force_channels = getattr(Config, 'FORCE_SUB_CHANNEL', [])
    if not force_channels:
        print(f"✅ DEBUG FORCE: No force channels configured")
        return True

    print(f"🔍 DEBUG FORCE: Checking {len(force_channels)} force channels for user {user_id}")

    # Check each force channel
    not_joined = []

    for channel_id in force_channels:
        try:
            # Skip invalid channels
            if not channel_id or channel_id == 0:
                continue

            await client.get_chat_member(channel_id, user_id)
            print(f"✅ DEBUG FORCE: User {user_id} is member of {channel_id}")

        except UserNotParticipant:
            print(f"❌ DEBUG FORCE: User {user_id} not in channel {channel_id}")
            not_joined.append(channel_id)
        except Exception as e:
            print(f"⚠️ DEBUG FORCE: Error checking channel {channel_id}: {e}")
            # Skip problematic channels instead of blocking user
            continue

    # If user hasn't joined required channels, show subscription message
    if not_joined:
        await send_force_sub_message(client, message, not_joined)
        return False

    return True

async def send_force_sub_message(client: Client, message, channels):
    """Send force subscription message with join buttons"""
    buttons = []

    for channel_id in channels:
        try:
            # Get channel info safely with better error handling
            chat = await client.get_chat(channel_id)

            if chat.username:
                channel_link = f"https://t.me/{chat.username}"
                button_text = f"Join {chat.title or 'Channel'}"
                buttons.append([InlineKeyboardButton(button_text, url=channel_link)])
            else:
                # For private channels, try to create invite link
                try:
                    invite_link = await client.export_chat_invite_link(channel_id)
                    button_text = f"Join {chat.title or 'Channel'}"
                    buttons.append([InlineKeyboardButton(button_text, url=invite_link)])
                except Exception as invite_error:
                    print(f"⚠️ Cannot create invite link for {channel_id}: {invite_error}")
                    continue  # Skip channels we can't create buttons for

        except UsernameInvalid:
            print(f"⚠️ Invalid username for channel {channel_id}")
            continue
        except Exception as e:
            print(f"⚠️ Error creating button for force channel {channel_id}: {e}")
            continue

    # Only show message if we have valid buttons
    if not buttons:
        print(f"⚠️ No valid force channel buttons created, allowing user to proceed")
        return

    # Add membership check button
    buttons.append([InlineKeyboardButton("✅ I Joined All Channels", callback_data="check_membership")])

    text = (
        "🔒 **Access Required**\n\n"
        "To use this bot, you must join our official channels first.\n\n"
        "📢 **Please join all channels below:**\n"
        "👆 Click the buttons above to join\n\n"
        "✅ After joining all channels, click the 'I Joined All Channels' button"
    )

    try:
        if isinstance(message, CallbackQuery):
            await message.edit_message_text(
                text, 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await message.reply_text(
                text, 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        print(f"⚠️ Error sending force sub message: {e}")

async def check_all_subscriptions(client: Client, user_id: int) -> bool:
    """Check if user has joined all required channels"""

    # Admin exemption
    if user_id == Config.OWNER_ID or user_id in Config.ADMINS:
        return True

    force_channels = getattr(Config, 'FORCE_SUB_CHANNEL', [])
    if not force_channels:
        return True

    for channel_id in force_channels:
        try:
            if not channel_id or channel_id == 0:
                continue
            await client.get_chat_member(channel_id, user_id)
        except UserNotParticipant:
            return False
        except Exception as e:
            print(f"⚠️ Error checking subscription for {channel_id}: {e}")
            continue  # Don't block for problematic channels

    return True