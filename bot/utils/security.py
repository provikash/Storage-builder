import re
import html
from typing import Any, Union

class SecurityValidator:
    """Security validation and sanitization utilities"""

    # Dangerous patterns that should be rejected
    SQL_INJECTION_PATTERNS = [
        r"(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(\$ne|\$regex|\$where|\$or|\$and)",
        r"(javascript:|<script|</script>)",
        r"(--|#|/\*|\*/)",
        r"('|\"|;|\\)"
    ]

    # File path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/",
        r"\\windows\\",
        r"system32"
    ]

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """Sanitize search query to prevent injection attacks"""
        if not isinstance(query, str):
            raise ValueError("Query must be a string")

        # Remove null bytes and control characters
        query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)

        # Check for dangerous patterns
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous query pattern detected")

        # Limit query length
        if len(query) > 100:
            raise ValueError("Query too long")

        # HTML encode for safety
        return html.escape(query.strip())

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal and XSS"""
        if not isinstance(filename, str):
            raise ValueError("Filename must be a string")

        # Remove null bytes and control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

        # Check for path traversal attempts
        for pattern in SecurityValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                raise ValueError("Path traversal attempt detected in filename")

        # Remove or replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Limit filename length
        if len(filename) > 255:
            filename = filename[:255]

        return html.escape(filename.strip())

    @staticmethod
    def validate_user_id(user_id):
        """Validate user ID to prevent injection attacks"""
        if user_id is None:
            return None

        try:
            user_id = int(user_id)
            # Telegram user IDs are positive integers
            if user_id <= 0 or user_id > 2**63 - 1:  # Max 64-bit signed integer
                raise ValueError("Invalid user ID range")
            return user_id
        except (ValueError, TypeError):
            print(f"WARNING: Invalid user_id format: {user_id}")
            return None

    @staticmethod
    def validate_file_size(file_size):
        """Validate file size to prevent overflow attacks"""
        if file_size is None:
            return 0

        try:
            file_size = int(file_size)
            if file_size < 0:
                return 0
            # Max file size 2GB (Telegram limit)
            if file_size > 2147483648:
                print(f"WARNING: File size {file_size} exceeds maximum limit")
                return 2147483648
            return file_size
        except (ValueError, TypeError):
            print(f"WARNING: Invalid file_size format: {file_size}")
            return 0