import secrets
from datetime import datetime, timedelta

from .connection import db
from loguru import logger

users_col = db["verified_users"]
tokens_col = db["verified_tokens"]

async def create_verification_token(user_id: int) -> str:
    """Create verification token for user"""
    try:
        # Generate unique token
        token = secrets.token_urlsafe(16)

        token_data = {
            "_id": user_id,
            "user_id": user_id,
            "token": token,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "used": False,
            "token_type": "command_limit"
        }

        await tokens_col.replace_one(
            {"_id": user_id},
            token_data,
            upsert=True
        )

        logger.info(f"✅ Created verification token for user {user_id}")
        return token

    except Exception as e:
        logger.error(f"❌ Error creating verification token: {e}")
        return None

async def create_time_based_token(user_id: int, expires_at: datetime) -> str:
    """Create time-based verification token for user"""
    try:
        # Generate unique token
        token = secrets.token_urlsafe(16)

        token_data = {
            "_id": user_id,
            "user_id": user_id,
            "token": token,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "used": False,
            "token_type": "time_based"
        }

        await tokens_col.replace_one(
            {"_id": user_id},
            token_data,
            upsert=True
        )

        logger.info(f"✅ Created time-based verification token for user {user_id} valid until {expires_at}")
        return token

    except Exception as e:
        logger.error(f"❌ Error creating time-based verification token: {e}")
        return None

async def get_user_time_token(user_id: int) -> dict:
    """Get user's time-based token if valid"""
    try:
        token_data = await tokens_col.find_one({"user_id": user_id})

        if not token_data:
            return None

        # Check if it's a time-based token and still valid
        if (token_data.get('token_type') == 'time_based' and 
            token_data.get('expires_at') and 
            datetime.now() < token_data.get('expires_at')):
            return token_data

        return None

    except Exception as e:
        logger.error(f"❌ Error getting user time token: {e}")
        return None


async def set_verified(user_id: int):
    await users_col.update_one(
        {"_id": user_id},
        {"$set": {"is_verified": True}},
        upsert=True
    )

async def is_verified(user_id: int) -> bool:
    user = await users_col.find_one({"_id": user_id})
    if not user or not user.get("is_verified"):
        return False
    return True

async def verify_user(user_id: int) -> bool:
    """Verify a user - alias for is_verified function"""
    return await is_verified(user_id)

async def get_verification_token(user_id: int) -> str:
    """Get verification token for user - alias for create_verification_token"""
    return await create_verification_token(user_id)

async def validate_token_and_verify(user_id: int, token: str) -> bool:
    """Validate token and verify user, then delete the token"""
    try:
        print(f"DEBUG: Validating token for user {user_id}, token: {token[:8]}...")

        # Validate token format - tokens from create_verification_token are URL-safe base64
        if not isinstance(token, str) or len(token) < 16:
            print(f"DEBUG: Invalid token format - length: {len(token) if token else 0}")
            return False

        # Use tokens_col collection name to match create_verification_token
        collection = tokens_col

        print(f"DEBUG: Looking for token in database...")

        # Find and delete the token in one operation (atomic)
        result = await collection.find_one_and_delete({
            'user_id': user_id,
            'token': token,
            'used': False,
            'expires_at': {'$gte': datetime.utcnow()}
        })

        if result:
            print(f"DEBUG: Token found and validated for user {user_id}")

            # Set user as verified
            await set_verified(user_id)

            # Reset command count for the user
            from ..database.command_usage_db import reset_command_count
            await reset_command_count(user_id)

            # Clean up any expired tokens for this user
            await collection.delete_many({
                'user_id': user_id,
                'expires_at': {'$lt': datetime.utcnow()}
            })

            return True

        print(f"DEBUG: Token not found or expired for user {user_id}")
        return False

    except Exception as e:
        print(f"Error validating token: {e}")
        return False