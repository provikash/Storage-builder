import asyncio
from shortzy import Shortzy

async def get_shortlink(api, site, long_url):
    shortzy = Shortzy(api, site)
    try:
        link = await shortzy.convert(long_url)
    except Exception:
        link = await shortzy.get_quick_link(long_url)
    return link

def get_readable_time(seconds: int, long: bool = False) -> str:
    """Convert seconds to readable time format"""
    if seconds <= 0:
        return "0 seconds" if long else "0s"

    time_units = []
    time_labels = ["second", "minute", "hour", "day"] if long else ["s", "m", "h", "d"]

    # Calculate days
    days, seconds = divmod(seconds, 86400)  # 24 * 60 * 60
    if days > 0:
        label = "days" if long and days > 1 else "day" if long else "d"
        time_units.append(f"{days} {label}" if long else f"{days}{label}")

    # Calculate hours
    hours, seconds = divmod(seconds, 3600)  # 60 * 60
    if hours > 0:
        label = "hours" if long and hours > 1 else "hour" if long else "h"
        time_units.append(f"{hours} {label}" if long else f"{hours}{label}")

    # Calculate minutes
    minutes, seconds = divmod(seconds, 60)
    if minutes > 0:
        label = "minutes" if long and minutes > 1 else "minute" if long else "m"
        time_units.append(f"{minutes} {label}" if long else f"{minutes}{label}")

    # Calculate seconds
    if seconds > 0:
        label = "seconds" if long and seconds > 1 else "second" if long else "s"
        time_units.append(f"{seconds} {label}" if long else f"{seconds}{label}")

    # Join the units appropriately
    if long:
        if len(time_units) > 1:
            return ", ".join(time_units[:-1]) + " and " + time_units[-1]
        else:
            return time_units[0]
    else:
        return " ".join(time_units)

def get_readable_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable file size (centralized version)"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(size_bytes.bit_length() // 10) if size_bytes > 0 else 0
    if i >= len(size_names):
        i = len(size_names) - 1
    
    p = 1024 ** i
    s = round(size_bytes / p, 2)
    
    return f"{int(s) if i == 0 else s} {size_names[i]}"

def get_collection_name(channel_id=None):
    """Get collection name for database operations"""
    # Return default collection name for file indexing
    return "file_index"

async def handle_force_sub(client, message):
    """
    Handle force subscription check
    Returns True if user should be blocked, False if allowed to proceed
    """
    try:
        from info import Config
        
        # If no force sub channels configured, allow all users
        if not hasattr(Config, 'FORCE_SUB_CHANNELS') or not Config.FORCE_SUB_CHANNELS:
            return False
            
        # Allow admins to bypass force subscription
        user_id = message.from_user.id
        if user_id in [Config.OWNER_ID] + list(Config.ADMINS):
            return False
            
        # Check if user is subscribed to required channels
        for channel_id in Config.FORCE_SUB_CHANNELS:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                if member.status in ['left', 'kicked']:
                    # Send force subscription message
                    text = "🔒 **Access Restricted**\n\n"
                    text += "You must join our channel to use this bot.\n\n"
                    text += "Click the button below to join:"
                    
                    try:
                        chat = await client.get_chat(channel_id)
                        invite_link = chat.invite_link or f"https://t.me/{chat.username}"
                        
                        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
                            [InlineKeyboardButton("🔄 Check Again", callback_data="check_sub")]
                        ])
                        
                        await message.reply_text(text, reply_markup=keyboard)
                    except:
                        await message.reply_text(text)
                    
                    return True  # Block user
            except Exception as e:
                # If we can't check membership, allow user to proceed
                print(f"Error checking force sub for channel {channel_id}: {e}")
                continue
                
        return False  # Allow user to proceed
        
    except Exception as e:
        print(f"Error in handle_force_sub: {e}")
        return False  # Allow user to proceed on error