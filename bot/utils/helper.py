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
    """Convert bytes to human readable file size"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    # Format without decimal for bytes, with decimal for larger units
    if i == 0:
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.1f} {size_names[i]}"

def get_collection_name(channel_id=None):
    """Get collection name for database operations"""
    # Return default collection name for file indexing
    return "file_index"