
import asyncio
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from bot.database.clone_db import get_clone_config
from bot.database.verify_db import get_verification_token, delete_verification_token, create_verification_token
from bot.database import get_user_command_count, increment_command_count, is_verified, is_premium_user
from bot.database.premium_db import use_premium_token
from bot.database.command_usage_db import reset_command_count
from info import Config
import logging

logger = logging.getLogger(__name__)

# User locks to prevent race conditions
_user_locks = {}

class TokenVerificationManager:
    """Manages token verification for clone bots with different modes"""
    
    @staticmethod
    async def get_clone_token_settings(client) -> Dict[str, Any]:
        """Get token verification settings for current clone"""
        try:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            
            # Extract bot_id from token
            if ':' in bot_token:
                bot_id = bot_token.split(':')[0]
            else:
                bot_id = bot_token
            
            config = await get_clone_config(bot_id)
            if not config:
                # Return default settings
                return {
                    "verification_mode": "command_limit",
                    "command_limit": 3,
                    "time_duration": 24,
                    "enabled": True
                }
            
            return config.get('token_settings', {
                "verification_mode": "command_limit",
                "command_limit": 3,
                "time_duration": 24,
                "enabled": True
            })
        except Exception as e:
            logger.error(f"Error getting clone token settings: {e}")
            return {
                "verification_mode": "command_limit",
                "command_limit": 3,
                "time_duration": 24,
                "enabled": True
            }

    @staticmethod
    async def check_token_verification_needed(client, user_id: int) -> Tuple[bool, int, str]:
        """
        Check if user needs token verification based on clone settings
        Returns: (needs_verification, remaining_count, verification_mode)
        """
        try:
            # Skip verification for admins and owner
            if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
                logger.info(f"User {user_id} has unlimited access (admin/owner)")
                return False, -1, "admin"

            # Check if user is premium
            if await is_premium_user(user_id):
                from bot.database.premium_db import get_premium_info
                premium_info = await get_premium_info(user_id)
                
                if premium_info:
                    tokens_remaining = premium_info.get('tokens_remaining', 0)
                    
                    if tokens_remaining == -1:  # Unlimited plan
                        logger.info(f"Premium user {user_id} has unlimited access")
                        return False, -1, "premium_unlimited"
                    elif tokens_remaining > 0:  # Token-based plan
                        logger.info(f"Premium user {user_id} has {tokens_remaining} tokens remaining")
                        return False, tokens_remaining, "premium_tokens"
                    else:  # No tokens left
                        logger.info(f"Premium user {user_id} has no tokens left")
                        return True, 0, "premium_expired"

            # Get clone token settings
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')
            
            if not token_settings.get('enabled', True):
                logger.info(f"Token verification disabled for clone")
                return False, -1, "disabled"

            if verification_mode == "command_limit":
                return await TokenVerificationManager._check_command_limit_mode(user_id, token_settings)
            elif verification_mode == "time_based":
                return await TokenVerificationManager._check_time_based_mode(user_id, token_settings)
            else:
                logger.error(f"Unknown verification mode: {verification_mode}")
                return await TokenVerificationManager._check_command_limit_mode(user_id, token_settings)

        except Exception as e:
            logger.error(f"Error in check_token_verification_needed: {e}")
            # Fallback to command limit mode
            command_count = await get_user_command_count(user_id)
            max_commands = 3
            if command_count >= max_commands:
                return True, 0, "command_limit"
            return False, max_commands - command_count, "command_limit"

    @staticmethod
    async def _check_command_limit_mode(user_id: int, token_settings: Dict) -> Tuple[bool, int, str]:
        """Check verification for command limit mode"""
        command_limit = token_settings.get('command_limit', 3)
        command_count = await get_user_command_count(user_id)
        
        logger.info(f"Command limit mode - User {user_id}: {command_count}/{command_limit}")
        
        if command_count >= command_limit:
            return True, 0, "command_limit"
        
        remaining = command_limit - command_count
        return False, remaining, "command_limit"

    @staticmethod
    async def _check_time_based_mode(user_id: int, token_settings: Dict) -> Tuple[bool, int, str]:
        """Check verification for time-based mode"""
        try:
            # Check if user has a valid time-based token
            from bot.database.verify_db import get_user_time_token
            time_token = await get_user_time_token(user_id)
            
            if not time_token:
                logger.info(f"Time-based mode - User {user_id} has no token")
                return True, 0, "time_based"
            
            # Check if token is still valid
            expires_at = time_token.get('expires_at')
            if not expires_at or datetime.now() > expires_at:
                logger.info(f"Time-based mode - User {user_id} token expired")
                # Clean up expired token
                await delete_verification_token(user_id)
                return True, 0, "time_based"
            
            # Calculate remaining time in hours
            remaining_time = expires_at - datetime.now()
            remaining_hours = int(remaining_time.total_seconds() / 3600)
            
            logger.info(f"Time-based mode - User {user_id} has {remaining_hours} hours remaining")
            return False, remaining_hours, "time_based"
            
        except Exception as e:
            logger.error(f"Error in time-based verification check: {e}")
            return True, 0, "time_based"

    @staticmethod
    async def use_verification_token(client, user_id: int) -> bool:
        """Use a verification token based on current mode"""
        try:
            # Skip for admins and owner
            if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
                return True

            # Handle premium users
            if await is_premium_user(user_id):
                from bot.database.premium_db import use_premium_token
                return await use_premium_token(user_id)

            # Get clone token settings
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            if verification_mode == "command_limit":
                return await TokenVerificationManager._use_command_limit_token(user_id, token_settings)
            elif verification_mode == "time_based":
                return await TokenVerificationManager._use_time_based_token(user_id, token_settings)
            else:
                logger.error(f"Unknown verification mode: {verification_mode}")
                return await TokenVerificationManager._use_command_limit_token(user_id, token_settings)

        except Exception as e:
            logger.error(f"Error in use_verification_token: {e}")
            return False

    @staticmethod
    async def _use_command_limit_token(user_id: int, token_settings: Dict) -> bool:
        """Use token in command limit mode"""
        try:
            # Get or create user-specific lock
            if user_id not in _user_locks:
                _user_locks[user_id] = asyncio.Lock()

            async with _user_locks[user_id]:
                current_count = await get_user_command_count(user_id)
                command_limit = token_settings.get('command_limit', 3)
                
                if current_count >= command_limit:
                    logger.info(f"User {user_id} reached command limit")
                    return False

                # Increment command count
                await increment_command_count(user_id)
                logger.info(f"Incremented command count for user {user_id} to {current_count + 1}")
                return True

        except Exception as e:
            logger.error(f"Error in command limit token usage: {e}")
            return False

    @staticmethod
    async def _use_time_based_token(user_id: int, token_settings: Dict) -> bool:
        """Use token in time-based mode"""
        try:
            # Check if user has valid time token
            from bot.database.verify_db import get_user_time_token
            time_token = await get_user_time_token(user_id)
            
            if not time_token:
                logger.info(f"User {user_id} has no time token")
                return False
            
            # Check if token is still valid
            expires_at = time_token.get('expires_at')
            if not expires_at or datetime.now() > expires_at:
                logger.info(f"User {user_id} time token expired")
                await delete_verification_token(user_id)
                return False
            
            logger.info(f"User {user_id} used time-based token successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in time-based token usage: {e}")
            return False

    @staticmethod
    async def create_verification_token_for_mode(client, user_id: int) -> Optional[str]:
        """Create verification token based on current mode"""
        try:
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')
            
            if verification_mode == "command_limit":
                # Reset command count and create token
                await reset_command_count(user_id)
                token = await create_verification_token(user_id)
                logger.info(f"Created command-limit token for user {user_id}")
                return token
                
            elif verification_mode == "time_based":
                # Create time-based token
                duration_hours = token_settings.get('time_duration', 24)
                expires_at = datetime.now() + timedelta(hours=duration_hours)
                
                from bot.database.verify_db import create_time_based_token
                token = await create_time_based_token(user_id, expires_at)
                logger.info(f"Created time-based token for user {user_id} valid for {duration_hours} hours")
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating verification token: {e}")
            return None

# Legacy compatibility functions
async def check_command_limit(user_id: int, client=None) -> Tuple[bool, int]:
    """Legacy function - redirects to new token verification system"""
    try:
        if client:
            needs_verification, remaining, mode = await TokenVerificationManager.check_token_verification_needed(client, user_id)
            return needs_verification, remaining
        else:
            # Fallback to original command limit logic
            command_count = await get_user_command_count(user_id)
            max_commands = 3
            if command_count >= max_commands:
                return True, 0
            return False, max_commands - command_count
    except Exception as e:
        logger.error(f"Error in legacy check_command_limit: {e}")
        return True, 0

async def use_command(user_id: int, client=None) -> bool:
    """Legacy function - redirects to new token verification system"""
    try:
        if client:
            return await TokenVerificationManager.use_verification_token(client, user_id)
        else:
            # Fallback to original logic
            if user_id in Config.ADMINS or user_id == Config.OWNER_ID:
                return True
            
            if await is_premium_user(user_id):
                from bot.database.premium_db import use_premium_token
                return await use_premium_token(user_id)
            
            current_count = await get_user_command_count(user_id)
            if current_count >= 3:
                return False
            
            await increment_command_count(user_id)
            return True
    except Exception as e:
        logger.error(f"Error in legacy use_command: {e}")
        return False
