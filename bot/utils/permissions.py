
"""
Centralized permissions and admin verification system
"""
from functools import wraps
from typing import Callable, Optional
from pyrogram import Client
from pyrogram.types import CallbackQuery, Message
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

def is_mother_admin(user_id: int) -> bool:
    """Check if user is Mother Bot admin"""
    try:
        owner_id = getattr(Config, 'OWNER_ID', None)
        admins = getattr(Config, 'ADMINS', ())
        
        if isinstance(admins, tuple):
            admin_list = list(admins)
        else:
            admin_list = admins if isinstance(admins, list) else []
        
        is_owner = user_id == owner_id
        is_admin = user_id in admin_list
        return is_owner or is_admin
    except Exception as e:
        logger.error(f"Error checking mother admin status: {e}")
        return False

async def is_clone_admin(client: Client, user_id: int) -> bool:
    """Check if user is a clone bot admin"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return False
        
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        
        if not clone_data:
            return False
            
        return int(user_id) == int(clone_data.get('admin_id', 0))
    except Exception as e:
        logger.error(f"Error checking clone admin status: {e}")
        return False

def is_clone_bot_instance(client: Client) -> tuple[bool, Optional[str]]:
    """Check if the current bot instance is a clone bot"""
    bot_token = getattr(client, 'bot_token', None)
    if bot_token and bot_token != Config.BOT_TOKEN:
        return True, bot_token
    return False, None

def require_mother_admin(func: Callable) -> Callable:
    """Decorator to require mother bot admin privileges"""
    @wraps(func)
    async def wrapper(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        
        if not is_mother_admin(user_id):
            await query.answer("❌ Unauthorized access!", show_alert=True)
            return
            
        return await func(client, query)
    return wrapper

def require_clone_admin(func: Callable) -> Callable:
    """Decorator to require clone bot admin privileges"""
    @wraps(func)
    async def wrapper(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        
        if not await is_clone_admin(client, user_id):
            await query.answer("❌ Only clone admin can access this!", show_alert=True)
            return
            
        return await func(client, query)
    return wrapper
