from .connection import db
import logging

logger = logging.getLogger(__name__)

user_data = db['users']


async def present_user(user_id: int) -> bool:
    found = await user_data.find_one({'_id': user_id})
    return bool(found)


async def add_user(user_id: int):
    try:
        await user_data.insert_one({'_id': user_id})
        return True
    except Exception as e:
        # Handle duplicate key error (user already exists)
        if 'E11000' in str(e) or 'duplicate key error' in str(e):
            return False  # User already exists
        raise e  # Re-raise other exceptions


async def full_userbase():
    user_ids = []
    async for doc in user_data.find():
        user_ids.append(doc['_id'])
    return user_ids


async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})


async def get_users_count():
    """Get total count of users"""
    try:
        count = await user_data.count_documents({})
        return count
    except Exception as e:
        print(f"Error getting users count: {e}")
        return 0


async def get_user_stats(user_id: int):
    """Get user statistics"""
    try:
        user_doc = await get_user(user_id)
        if user_doc:
            return {
                'command_count': user_doc.get('command_count', 0),
                'downloads': user_doc.get('downloads', 0),
                'searches': user_doc.get('searches', 0),
                'active_days': user_doc.get('active_days', 1),
                'total_spent': user_doc.get('total_spent', 0),
                'last_command_at': user_doc.get('last_command_at'),
                'last_reset': user_doc.get('last_reset')
            }
        return {
            'command_count': 0,
            'downloads': 0,
            'searches': 0,
            'active_days': 1,
            'total_spent': 0,
            'last_command_at': None,
            'last_reset': None
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}


async def get_user(user_id: int):
    """Get user data by user ID"""
    try:
        user = await user_data.find_one({'_id': user_id})
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None