import asyncio
from datetime import datetime, timedelta
from bot.database import get_user_command_count, increment_command_count, is_verified, is_premium_user
from bot.database.premium_db import use_premium_token
from bot.database.command_usage_db import reset_command_count
from info import Config
from pyrogram import Client
from loguru import logger
from bot.utils import clone_config_loader

# User locks to prevent race conditions
_user_locks = {}

async def check_command_limit(user_id: int, client=None) -> tuple[bool, int]:
    """
    Check if user has exceeded command limit using new token verification system
    Returns: (needs_verification, remaining_commands)
    """
    try:
        if client:
            # Use new token verification system
            from bot.utils.token_verification import TokenVerificationManager
            needs_verification, remaining, mode = await TokenVerificationManager.check_token_verification_needed(client, user_id)
            return needs_verification, remaining
        else:
            # Fallback to legacy logic
            # Skip verification for admins and owner only
            if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
                print(f"DEBUG: User {user_id} has unlimited access (admin/owner)")
                return False, -1  # -1 means unlimited

            # Check if user is premium and get their token count
            if await is_premium_user(user_id):
                from bot.database.premium_db import get_premium_info
                premium_info = await get_premium_info(user_id)

                if premium_info:
                    tokens_remaining = premium_info.get('tokens_remaining', 0)

                    if tokens_remaining == -1:  # Unlimited plan
                        print(f"DEBUG: Premium user {user_id} has unlimited access")
                        return False, -1
                    elif tokens_remaining > 0:  # Token-based plan
                        print(f"DEBUG: Premium user {user_id} has {tokens_remaining} tokens remaining")
                        return False, tokens_remaining
                    else:  # No tokens left
                        print(f"DEBUG: Premium user {user_id} has no tokens left")
                        return True, 0
                else:
                    print(f"DEBUG: Premium user {user_id} has no premium info - treating as expired")
                    return True, 0

            # Handle regular free users
            command_count = await get_user_command_count(user_id)
            print(f"DEBUG: User {user_id} command count check: {command_count}/3")

            # Every user gets exactly 3 commands before needing verification
            max_commands = 3

            if command_count >= max_commands:
                return True, 0  # Need verification to get next 3 commands

            remaining = max_commands - command_count
            return False, remaining
    except Exception as e:
        print(f"Error in check_command_limit: {e}")
        return True, 0

async def reset_user_commands(user_id: int) -> bool:
    """Reset user command count - alias for reset_command_count"""
    try:
        await reset_command_count(user_id)
        return True
    except Exception:
        return False

async def use_command(user_id: int, client=None) -> bool:
    """
    Use a command for the user. Returns True if successful, False if limit reached.
    Thread-safe implementation to prevent race conditions.
    """
    try:
        if client:
            # Use new token verification system
            from bot.utils.token_verification import TokenVerificationManager
            return await TokenVerificationManager.use_verification_token(client, user_id)
        else:
            # Fallback to legacy logic
            # Skip limits entirely for admins and owner - no counting at all
            if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
                print(f"DEBUG: User {user_id} has unlimited access (admin/owner)")
                return True

            # Get or create user-specific lock
            if user_id not in _user_locks:
                _user_locks[user_id] = asyncio.Lock()

            async with _user_locks[user_id]:
                # Check if user is premium and handle token deduction
                if await is_premium_user(user_id):
                    from bot.database.premium_db import use_premium_token
                    if await use_premium_token(user_id):
                        print(f"DEBUG: Premium user {user_id} used a token successfully")
                        return True
                    else:
                        print(f"DEBUG: Premium user {user_id} has no tokens left - premium expired")
                        return False

                # Handle regular users with free commands
                current_count = await get_user_command_count(user_id)
                print(f"DEBUG: User {user_id} current command count: {current_count}")

                # Check if user has reached the limit (3 free commands)
                if current_count >= 3:
                    print(f"DEBUG: User {user_id} reached command limit")
                    return False

                # Increment command count atomically for regular users
                await increment_command_count(user_id)
                print(f"DEBUG: Incremented command count for user {user_id} to {current_count + 1}")
                return True

    except Exception as e:
        print(f"Error in use_command: {e}")
        return False

async def reset_user_commands(user_id):
    """Reset user command count"""
    try:
        from bot.database.connection import db
        from info import Config
        collection = db[Config.COMMAND_USAGE_COLLECTION]
        await collection.delete_one({'user_id': user_id})
        return True
    except Exception as e:
        logger.error(f"Error resetting user commands: {e}")
        return False

async def verify_token_access(client: Client, user_id: int, command_type: str) -> bool:
    """
    Verify token access for a specific command type.
    This is a placeholder and should be implemented based on your token verification logic.
    """
    # Dummy implementation: always return True for now
    # In a real scenario, this would involve checking user's tokens, subscription status, etc.
    return True

async def check_command_access(client: Client, user_id: int, command_type: str) -> bool:
    """Check if user has access to a specific command type"""
    try:
        # Get bot configuration
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is a clone bot
        if bot_token == Config.BOT_TOKEN:
            # Mother bot - these features are disabled
            return False

        config = await clone_config_loader.get_bot_config(bot_token)

        # Check if command type feature is enabled in clone settings
        features = config.get('features', {})
        if not features.get(f"{command_type}_button", True):
            return False

        # Also check clone data settings
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)
        if clone_data:
            # Check specific mode settings
            mode_key = f"{command_type}_mode"
            if not clone_data.get(mode_key, True):
                return False

        # If token verification is disabled, allow access
        token_settings = config.get('token_settings', {})
        if not token_settings.get('enabled', True):
            return True

        # Check token verification
        return await verify_token_access(client, user_id, command_type)

    except Exception as e:
        logger.error(f"Error checking command access: {e}")
        return False