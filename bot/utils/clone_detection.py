
"""
Centralized Clone Detection Utilities
Consolidates clone detection logic from multiple files
"""
from typing import Tuple
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def is_clone_bot_instance(client) -> Tuple[bool, str]:
    """
    Detect if this is a clone bot instance
    Returns: (is_clone, bot_token)
    """
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        is_clone = hasattr(client, 'is_clone') and client.is_clone

        if not is_clone:
            is_clone = (
                bot_token != Config.BOT_TOKEN or
                hasattr(client, 'clone_config') and client.clone_config or
                hasattr(client, 'clone_data')
            )

        return is_clone, bot_token
    except Exception as e:
        logger.error(f"Error detecting clone bot: {e}")
        return False, Config.BOT_TOKEN

async def is_clone_admin(client, user_id: int) -> bool:
    """Check if user is admin of the current clone bot"""
    try:
        from bot.database.clone_db import get_clone_by_bot_token

        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False

        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            return user_id == clone_data.get('admin_id')
        return False
    except Exception as e:
        logger.error(f"Error checking clone admin: {e}")
        return False

def get_clone_id_from_client(client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except Exception as e:
        logger.error(f"Error getting clone ID: {e}")
        return None

def is_admin_user(user_id: int) -> bool:
    """Check if user is admin or owner"""
    return user_id in [Config.OWNER_ID] + list(Config.ADMINS)
