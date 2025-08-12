from .connection import db

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
