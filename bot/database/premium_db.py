from datetime import datetime, timedelta
from .connection import db

premium_data = db['premium_users']

async def add_premium_user(user_id: int, plan_type: str, tokens: int):
    """Add premium user with token-based system"""
    try:
        # Calculate expiry date (1 year for unlimited, otherwise no expiry for token-based)
        expiry_date = datetime.utcnow() + timedelta(days=365) if tokens == -1 else datetime.utcnow() + timedelta(days=365)

        user_data = {
            '_id': user_id,
            'plan_type': plan_type,
            'tokens_remaining': tokens,  # -1 for unlimited
            'expiry_date': expiry_date,
            'created_at': datetime.utcnow()
        }

        # Use upsert to avoid duplicate key errors
        result = await premium_data.replace_one(
            {'_id': user_id}, 
            user_data, 
            upsert=True
        )

        print(f"Premium user added: {user_id}, Plan: {plan_type}, Tokens: {tokens}")
        return True

    except Exception as e:
        print(f"Error adding premium user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def is_premium_user(user_id: int) -> bool:
    """Check if user has active premium tokens or unlimited access"""
    user = await premium_data.find_one({'_id': user_id})
    if not user:
        return False

    try:
        # Check if required fields exist
        if 'tokens_remaining' not in user or 'is_active' not in user:
            # Data is corrupted, deactivate and return False
            await premium_data.update_one(
                {'_id': user_id}, 
                {'$set': {'is_active': False}}
            )
            return False

        if not user['is_active']:
            return False

        # Check unlimited access (tokens = -1)
        if user['tokens_remaining'] == -1:
            # Check if unlimited plan has expired
            if 'expiry_date' in user and user['expiry_date'] < datetime.utcnow():
                await premium_data.update_one(
                    {'_id': user_id}, 
                    {'$set': {'is_active': False}}
                )
                return False
            return True

        # Check token-based access
        if user['tokens_remaining'] > 0:
            return True
        else:
            # No tokens left, deactivate
            await premium_data.update_one(
                {'_id': user_id}, 
                {'$set': {'is_active': False}}
            )
            return False

    except Exception:
        # Handle any other data corruption issues
        await premium_data.update_one(
            {'_id': user_id}, 
            {'$set': {'is_active': False}}
        )
        return False

async def get_premium_info(user_id: int):
    """Get premium user information"""
    try:
        user = await premium_data.find_one({'_id': user_id})
        if not user:
            return None

        # Check for minimal required fields - be more lenient
        if 'is_active' not in user:
            user['is_active'] = False

        if not user.get('is_active'):
            return None

        # Set default values for missing fields
        if 'plan_type' not in user:
            user['plan_type'] = 'Unknown'
        if 'start_date' not in user:
            user['start_date'] = datetime.utcnow()
        if 'tokens_remaining' not in user:
            user['tokens_remaining'] = 0

        # Add expiry_date for unlimited plans if missing
        if user.get('tokens_remaining') == -1 and 'expiry_date' not in user:
            expiry_date = datetime.utcnow() + timedelta(days=365)
            await premium_data.update_one(
                {'_id': user_id},
                {'$set': {'expiry_date': expiry_date}}
            )
            user['expiry_date'] = expiry_date

        return user
    except Exception:
        return None

async def use_premium_token(user_id: int) -> bool:
    """Use one premium token, returns True if token was used successfully"""
    user = await premium_data.find_one({'_id': user_id})
    if not user or not user.get('is_active'):
        return False

    # Unlimited users don't use tokens
    if user.get('tokens_remaining') == -1:
        return True

    # Check if user has tokens
    if user.get('tokens_remaining', 0) > 0:
        await premium_data.update_one(
            {'_id': user_id},
            {'$inc': {'tokens_remaining': -1}}
        )
        return True

    return False

async def remove_premium(user_id: int):
    """Remove premium membership"""
    await premium_data.update_one(
        {'_id': user_id}, 
        {'$set': {'is_active': False}}
    )

async def get_all_premium_users():
    """Get all premium users"""
    users = []
    async for user in premium_data.find({'is_active': True}):
        users.append(user)
    return users