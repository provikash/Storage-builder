
import re
import html
import hashlib
import hmac
import time
from typing import Any, Union, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Enhanced security validation and sanitization utilities"""

    # Dangerous patterns that should be rejected
    SQL_INJECTION_PATTERNS = [
        r"(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(\$ne|\$regex|\$where|\$or|\$and)",
        r"(javascript:|<script|</script>)",
        r"(--|#|/\*|\*/)",
        r"('|\"|;|\\)",
        r"(eval\(|setTimeout\(|setInterval\()",
        r"(document\.|window\.|location\.)"
    ]

    # File path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/",
        r"\\windows\\",
        r"system32",
        r"/proc/",
        r"/sys/",
        r"passwd",
        r"shadow"
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*="
    ]

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        import secrets
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt using PBKDF2"""
        if salt is None:
            import os
            salt = os.urandom(32)
        elif isinstance(salt, str):
            salt = salt.encode('utf-8')
        
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt, 
                                      100000)  # 100k iterations
        return pwdhash, salt

    @staticmethod
    def verify_password(password: str, stored_hash: bytes, salt: bytes) -> bool:
        """Verify password against stored hash"""
        pwdhash, _ = SecurityValidator.hash_password(password, salt)
        return hmac.compare_digest(pwdhash, stored_hash)

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """Enhanced search query sanitization"""
        if not isinstance(query, str):
            raise ValueError("Query must be a string")

        # Remove null bytes and control characters
        query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)

        # Check for dangerous patterns
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potentially dangerous query pattern detected: {pattern}")
                raise ValueError(f"Query contains potentially dangerous content")

        # Check for XSS patterns
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"XSS pattern detected in query: {pattern}")
                raise ValueError(f"Query contains potentially dangerous content")

        # Limit query length
        if len(query) > 100:
            raise ValueError("Query too long (max 100 characters)")

        # Remove excessive whitespace
        query = ' '.join(query.split())

        # HTML encode for safety
        return html.escape(query.strip())

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Enhanced filename sanitization"""
        if not isinstance(filename, str):
            raise ValueError("Filename must be a string")

        # Remove null bytes and control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

        # Check for path traversal attempts
        for pattern in SecurityValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                logger.warning(f"Path traversal attempt detected: {pattern}")
                raise ValueError("Filename contains potentially dangerous path elements")

        # Remove or replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Ensure filename isn't empty
        if not filename:
            filename = "unnamed_file"

        # Limit filename length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 250 - len(ext) - 1 if ext else 250
            filename = name[:max_name_length] + ('.' + ext if ext else '')

        return html.escape(filename)

    @staticmethod
    def validate_user_id(user_id) -> Optional[int]:
        """Enhanced user ID validation"""
        if user_id is None:
            return None

        try:
            user_id = int(user_id)
            # Telegram user IDs are positive integers within specific range
            if user_id <= 0 or user_id > 2**53 - 1:  # JavaScript safe integer limit
                logger.warning(f"User ID out of valid range: {user_id}")
                raise ValueError("Invalid user ID range")
            return user_id
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid user_id format: {user_id} - {e}")
            return None

    @staticmethod
    def validate_file_size(file_size) -> int:
        """Enhanced file size validation"""
        if file_size is None:
            return 0

        try:
            file_size = int(file_size)
            if file_size < 0:
                return 0
            # Max file size 2GB (Telegram limit)
            if file_size > 2147483648:
                logger.warning(f"File size {file_size} exceeds maximum limit")
                return 2147483648
            return file_size
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid file_size format: {file_size} - {e}")
            return 0

    @staticmethod
    def validate_message_id(message_id) -> Optional[int]:
        """Validate Telegram message ID"""
        if message_id is None:
            return None

        try:
            message_id = int(message_id)
            if message_id <= 0:
                return None
            return message_id
        except (ValueError, TypeError):
            return None

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """Check if URL is safe (basic validation)"""
        if not isinstance(url, str):
            return False
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'vbscript:', 'data:', 'file:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                return False
        
        # Check for valid HTTP/HTTPS
        return url.startswith(('http://', 'https://'))

def rate_limit_decorator(max_calls: int = 10, time_window: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        calls = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            # Get user_id from args or kwargs
            user_id = None
            if args and hasattr(args[1], 'from_user'):
                user_id = args[1].from_user.id
            elif 'message' in kwargs and hasattr(kwargs['message'], 'from_user'):
                user_id = kwargs['message'].from_user.id
            
            if user_id:
                # Clean old entries
                calls[user_id] = [call_time for call_time in calls.get(user_id, []) 
                                if now - call_time < time_window]
                
                # Check rate limit
                if len(calls.get(user_id, [])) >= max_calls:
                    logger.warning(f"Rate limit exceeded for user {user_id}")
                    return
                
                # Record this call
                calls.setdefault(user_id, []).append(now)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Global security instance
security = SecurityValidator()
