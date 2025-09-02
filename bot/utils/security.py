
import hashlib
import hmac
import secrets
import time
import logging
from typing import Optional, Dict, Set
from pyrogram.types import User, Message
from info import Config

logger = logging.getLogger(__name__)

class SecurityManager:
    """Production security manager with rate limiting and access control"""
    
    def __init__(self):
        self.rate_limits: Dict[int, Dict[str, float]] = {}
        self.blocked_users: Set[int] = set()
        self.admin_sessions: Dict[int, float] = {}
        self.failed_attempts: Dict[int, int] = {}
        
        # Rate limit settings
        self.rate_limit_window = 60  # 1 minute
        self.max_requests_per_minute = 20
        self.admin_max_requests = 60
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = 3600  # 1 hour
        self.session_timeout = 7200  # 2 hours
        
    def validate_bot_token(self, token: str) -> bool:
        """Validate bot token format"""
        if not token or not isinstance(token, str):
            return False
            
        parts = token.split(':')
        if len(parts) != 2:
            return False
            
        try:
            bot_id = int(parts[0])
            token_hash = parts[1]
            return len(token_hash) == 35 and bot_id > 0
        except ValueError:
            return False
    
    def validate_api_credentials(self, api_id: str, api_hash: str) -> bool:
        """Validate API credentials format"""
        try:
            api_id_int = int(api_id)
            return (
                api_id_int > 0 and 
                len(api_hash) == 32 and 
                all(c in '0123456789abcdef' for c in api_hash.lower())
            )
        except (ValueError, TypeError):
            return False
    
    def is_rate_limited(self, user_id: int, action: str = "default") -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {}
        
        user_limits = self.rate_limits[user_id]
        
        # Clean old entries
        cutoff_time = current_time - self.rate_limit_window
        user_limits = {k: v for k, v in user_limits.items() if v > cutoff_time}
        self.rate_limits[user_id] = user_limits
        
        # Check limits
        action_key = f"{action}:{int(current_time // self.rate_limit_window)}"
        requests_this_window = sum(1 for k in user_limits.keys() if k.startswith(action))
        
        max_requests = self.admin_max_requests if self.is_admin(user_id) else self.max_requests_per_minute
        
        if requests_this_window >= max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}, action {action}")
            return True
        
        # Record this request
        user_limits[action_key] = current_time
        return False
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in Config.ADMINS
    
    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self.blocked_users
    
    def block_user(self, user_id: int, reason: str = "Security violation"):
        """Block a user"""
        self.blocked_users.add(user_id)
        logger.warning(f"User {user_id} blocked: {reason}")
    
    def unblock_user(self, user_id: int):
        """Unblock a user"""
        self.blocked_users.discard(user_id)
        logger.info(f"User {user_id} unblocked")
    
    def record_failed_attempt(self, user_id: int):
        """Record a failed authentication attempt"""
        self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1
        
        if self.failed_attempts[user_id] >= self.max_failed_attempts:
            self.block_user(user_id, f"Too many failed attempts ({self.failed_attempts[user_id]})")
    
    def sanitize_input(self, text: str, max_length: int = 4096) -> str:
        """Sanitize user input"""
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized
    
    def create_secure_token(self) -> str:
        """Create a secure random token"""
        return secrets.token_urlsafe(32)
    
    def verify_signature(self, data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        try:
            expected = hmac.new(
                secret.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception:
            return False
    
    async def security_check(self, message: Message) -> bool:
        """Perform comprehensive security check"""
        user_id = message.from_user.id
        
        # Check if user is blocked
        if self.is_blocked(user_id):
            logger.warning(f"Blocked user {user_id} attempted access")
            return False
        
        # Check rate limiting
        if self.is_rate_limited(user_id):
            logger.warning(f"Rate limited user {user_id}")
            return False
        
        # Check message content
        if message.text:
            sanitized = self.sanitize_input(message.text)
            if len(sanitized) != len(message.text):
                logger.warning(f"Suspicious input from user {user_id}")
        
        return True
    
    def cleanup_old_data(self):
        """Clean up old security data"""
        current_time = time.time()
        
        # Clean rate limits
        for user_id in list(self.rate_limits.keys()):
            cutoff_time = current_time - self.rate_limit_window
            user_limits = {k: v for k, v in self.rate_limits[user_id].items() if v > cutoff_time}
            if user_limits:
                self.rate_limits[user_id] = user_limits
            else:
                del self.rate_limits[user_id]
        
        # Clean admin sessions
        session_cutoff = current_time - self.session_timeout
        self.admin_sessions = {k: v for k, v in self.admin_sessions.items() if v > session_cutoff}
        
        # Reset failed attempts after lockout period
        lockout_cutoff = current_time - self.lockout_duration
        for user_id in list(self.failed_attempts.keys()):
            if user_id in self.blocked_users:
                # Unblock after lockout period (basic auto-unblock)
                pass  # Keep manual control for now

# Global instance
security_manager = SecurityManager()
