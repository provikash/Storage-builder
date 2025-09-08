
def admin_required(func):
    """Simple admin verification decorator"""
    async def wrapper(client, message):
        user_id = message.from_user.id
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            return await message.reply_text("❌ This command is only available to administrators.")
        return await func(client, message)
    return wrapper
"""
Admin verification utility
"""

from info import Config
import logging

logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    try:
        return user_id in Config.ADMINS
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

async def is_owner(user_id: int) -> bool:
    """Check if user is the owner"""
    try:
        return user_id == Config.OWNER_ID
    except Exception as e:
        logger.error(f"Error checking owner status: {e}")
        return False
