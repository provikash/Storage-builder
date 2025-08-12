import secrets
from datetime import datetime, timedelta

from .connection import db

users_col = db["verified_users"]
tokens_col = db["verified_tokens"]

async def create_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(16)
    await tokens_col.delete_many({"user_id": user_id})  # Remove old tokens
    await tokens_col.insert_one({
        "user_id": user_id,
        "token": token,
        "used": False,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=30)
    })
    return token

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