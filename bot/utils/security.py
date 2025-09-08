import time
import hashlib
import hmac
import secrets
from typing import Dict, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.types import Message
from info import Config

class SecurityManager:
    """Enhanced security management system"""

    def __init__(self):
        self.rate_limits: Dict[str, Dict[str, float]] = {}
        self.blocked_users: Dict[int, datetime] = {}
        self.failed_attempts: Dict[int, int] = {}
        self.active_sessions: Dict[int, str] = {}

    def generate_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)

    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)

        hashed = hashlib.pbkdf2_hmac('sha256',
                                   password.encode('utf-8'),
                                   salt.encode('utf-8'),
                                   100000)
        return hashed.hex(), salt

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        new_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(new_hash, hashed)

    def is_rate_limited(self, user_id: int, action: str = "default") -> bool:
        """Check if user is rate limited for specific action"""
        key = f"{user_id}_{action}"
        now = time.time()

        if key not in self.rate_limits:
            self.rate_limits[key] = {"count": 0, "reset_time": now + 60}
            return False

        rate_data = self.rate_limits[key]

        # Reset counter if time window passed
        if now >= rate_data["reset_time"]:
            rate_data["count"] = 0
            rate_data["reset_time"] = now + 60

        # Check rate limit
        if rate_data["count"] >= Config.MAX_REQUESTS_PER_MINUTE:
            return True

        rate_data["count"] += 1
        return False

    def block_user(self, user_id: int, duration_minutes: int = 60):
        """Block user for specified duration"""
        self.blocked_users[user_id] = datetime.now() + timedelta(minutes=duration_minutes)

    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        if user_id not in self.blocked_users:
            return False

        if datetime.now() >= self.blocked_users[user_id]:
            del self.blocked_users[user_id]
            return False

        return True

    def record_failed_attempt(self, user_id: int):
        """Record failed authentication attempt"""
        self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1

        # Block after 5 failed attempts
        if self.failed_attempts[user_id] >= 5:
            self.block_user(user_id, 60)

    def clear_failed_attempts(self, user_id: int):
        """Clear failed attempts for user"""
        if user_id in self.failed_attempts:
            del self.failed_attempts[user_id]

    def validate_file_path(self, file_path: str) -> bool:
        """Validate file path for security"""
        # Prevent directory traversal
        if ".." in file_path or file_path.startswith("/"):
            return False

        # Check file extension
        allowed_extensions = ['.txt', '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3']
        if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
            return False

        return True

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        import re
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')

        return filename

# Global security manager instance
security_manager = SecurityManager()

def admin_required(func):
    """Decorator to require admin privileges"""
    @wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if not Config.is_admin(message.from_user.id):
            await message.reply("❌ Admin access required.")
            return
        return await func(client, message, *args, **kwargs)
    return wrapper

def rate_limit(action: str = "default"):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            user_id = message.from_user.id

            if security_manager.is_blocked(user_id):
                await message.reply("❌ You are temporarily blocked. Please try again later.")
                return

            if security_manager.is_rate_limited(user_id, action):
                await message.reply("⚠️ Rate limit exceeded. Please slow down.")
                return

            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator

def validate_user_input(max_length: int = 1000):
    """Decorator to validate user input"""
    def decorator(func):
        @wraps(func)
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            if message.text and len(message.text) > max_length:
                await message.reply("❌ Input too long.")
                return
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator