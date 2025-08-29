# Cleaned & Updated by @Mak0912 (TG)

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from info import Config


async def handle_force_sub(client, message: Message):
    user = message.from_user
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
    except:
        global_force_channels = []
    
    # Combine local config and global channels
    force_channels = config_force_channels + global_force_channels
    request_channels = config_request_channels
    all_channels = force_channels + request_channels

    if not all_channels:
        return True  # No force sub channels configured, allow user to continue

    # Check force subscription channels (direct join)
    for ch in force_channels:
        try:
            member = await client.get_chat_member(ch, user.id)
            if member.status in (
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER,
            ):
                joined.append(ch)
            else:
                not_joined_force.append(ch)
        except Exception:
            not_joined_force.append(ch)

    # Check request channels (treat RESTRICTED as joined too)
    for ch in request_channels:
        try:
            member = await client.get_chat_member(ch, user.id)
            if member.status in (
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.RESTRICTED  # treat join request as joined
            ):
                joined.append(ch)
        except Exception:
            pass  # ignore failure in request channel

    # If all required channels are joined, allow user to continue
    if not not_joined_force:
        return True  # User has joined all required channels

    # Create buttons for force subscription channels
    for ch in force_channels:
        try:
            if hasattr(client, 'channel_info') and client.channel_info.get(ch):
                info = client.channel_info.get(ch)
            else:
                chat = await client.get_chat(ch)
                info = {
                    'title': chat.title,
                    'invite_link': chat.invite_link
                }

            url = info.get("invite_link")
            title = info.get("title", f"Channel {ch}")

            if not url:
                try:
                    url = await client.export_chat_invite_link(ch)
                except:
                    url = f"https://t.me/c/{str(ch)[4:]}"

            if url and url.strip():
                if ch in joined:
                    buttons.append([InlineKeyboardButton(f"✅ {title}", url=url)])
                else:
                    buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=url)])
        except Exception as e:
            print(f"Error creating button for force channel {ch}: {e}")
            buttons.append([InlineKeyboardButton(f"📢 Join Channel", url=f"https://t.me/c/{str(ch)[4:]}")])

    # Create buttons for request channels (optional display only)
    for ch in request_channels:
        try:
            chat = await client.get_chat(ch)
            title = chat.title or f"Channel {ch}"

            if ch in joined:
                buttons.append([InlineKeyboardButton(f"✅ {title}", url=f"https://t.me/c/{str(ch)[4:]}")])
            elif Config.JOIN_REQUEST_ENABLE:
                try:
                    invite_link = await client.create_chat_invite_link(
                        ch,
                        creates_join_request=True,
                        name=f"Join Request for {user.first_name or user.id}"
                    )
                    url = invite_link.invite_link
                    buttons.append([InlineKeyboardButton(f"🔔 Request to Join {title}", url=url)])
                except Exception as e:
                    print(f"DEBUG: Failed to create join request link for {ch}: {e}")
                    try:
                        url = await client.export_chat_invite_link(ch)
                        buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=url)])
                    except:
                        buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=f"https://t.me/c/{str(ch)[4:]}")])
        except Exception as e:
            print(f"Error creating button for request channel {ch}: {e}")

    # Add "Try Again" button if payload is present
    if hasattr(message, 'command') and len(message.command) > 1:
        payload = message.command[1]
        if client.username:
            buttons.append([
                InlineKeyboardButton("🔁 Try Again", url=f"https://t.me/{client.username}?start={payload}")
            ])

    # Build channel join status text
    joined_txt = ""

    # Force sub channels
    for ch in force_channels:
        try:
            if hasattr(client, 'channel_info') and client.channel_info.get(ch):
                title = client.channel_info.get(ch).get("title", f"Channel {ch}")
            else:
                chat = await client.get_chat(ch)
                title = chat.title
        except:
            title = f"Channel {ch}"

        if ch in joined:
            joined_txt += f"✅ <b>{title}</b> (Force Sub)\n"
        else:
            joined_txt += f"❌ <b>{title}</b> (Force Sub)\n"

    # Request channels
    for ch in request_channels:
        try:
            chat = await client.get_chat(ch)
            title = chat.title or f"Channel {ch}"
        except:
            title = f"Channel {ch}"

        if ch in joined:
            joined_txt += f"✅ <b>{title}</b> (Request)</b>\n"
        else:
            joined_txt += f"❌ <b>{title}</b> (Request)</b>\n"

    # Format base message
    fsub_msg = Config.FORCE_MSG.format(
        first=user.first_name,
        last=user.last_name or "",
        username=f"@{user.username}" if user.username else "N/A",
        mention=user.mention,
        id=user.id
    )

    final_message = f"{fsub_msg}\n\n<b>📋 Channel Join Status:</b>\n{joined_txt}"

    # Instructions only for force sub (since request can pass even unapproved)
    if not_joined_force:
        final_message += f"\n🔽 <b>Instructions:</b>\n"
        final_message += f"📢 <b>Force Sub:</b> Click the buttons below to join the required channels."

    # Ensure message doesn't exceed Telegram's 4096 character limit
    if len(final_message) > 4096:
        # Truncate the message and add indicator
        final_message = final_message[:4090] + "..."
        print(f"WARNING: Force subscription message truncated due to length: {len(final_message)} chars")

    # If buttons exist, add markup
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
        # Try sending without formatting if there's still an error
        try:
            clean_message = final_message.replace("<b>", "").replace("</b>", "")
            if len(clean_message) > 4096:
                clean_message = clean_message[:4090] + "..."
            await message.reply(
                clean_message,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e2:
            print(f"Error sending fallback message: {e2}")
            await message.reply("❌ Please join the required channels to continue.")
        return False  # Block user until they join required channels