import os
from pathlib import Path
from typing import Optional, List
import logging

class Config:
    """Enhanced configuration management with validation"""

    # Core Bot Configuration
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", os.getenv("DATABASE_URI", ""))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "storage_builder")

    # Admin Configuration
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    ADMIN_IDS: List[int] = []

    # Security Configuration
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "2000"))  # MB

    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
    MAX_CLONES_PER_USER: int = int(os.getenv("MAX_CLONES_PER_USER", "5"))

    # File Storage
    STORAGE_PATH: Path = Path(os.getenv("STORAGE_PATH", "storage"))
    TEMP_PATH: Path = Path(os.getenv("TEMP_PATH", "temp"))

    # Subscription Configuration
    DEFAULT_SUBSCRIPTION_DAYS: int = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))
    PREMIUM_FEATURES_ENABLED: bool = os.getenv("PREMIUM_FEATURES_ENABLED", "true").lower() == "true"

    # Clone Configuration
    CLONE_PREFIX: str = os.getenv("CLONE_PREFIX", "clone_")
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "5"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bot.log")

    # Web Dashboard
    WEB_PORT: int = int(os.getenv("WEB_PORT", "5000"))
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_fields = [
            ("API_ID", cls.API_ID),
            ("API_HASH", cls.API_HASH),
            ("BOT_TOKEN", cls.BOT_TOKEN),
            ("DATABASE_URL", cls.DATABASE_URL),
            ("OWNER_ID", cls.OWNER_ID)
        ]

        missing_fields = []
        for field_name, field_value in required_fields:
            if not field_value or (isinstance(field_value, int) and field_value == 0):
                missing_fields.append(field_name)

        if missing_fields:
            logging.error(f"Missing required configuration: {', '.join(missing_fields)}")
            return False

        # Parse admin IDs
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            try:
                cls.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            except ValueError:
                logging.error("Invalid ADMIN_IDS format")

        # Add owner to admin list
        if cls.OWNER_ID not in cls.ADMIN_IDS:
            cls.ADMIN_IDS.append(cls.OWNER_ID)

        # Create directories
        cls.STORAGE_PATH.mkdir(exist_ok=True)
        cls.TEMP_PATH.mkdir(exist_ok=True)
        Path(cls.LOG_FILE).parent.mkdir(exist_ok=True)

        return True

    @classmethod
    def get_admin_ids(cls) -> List[int]:
        """Get list of admin user IDs"""
        return cls.ADMIN_IDS.copy()

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in cls.ADMIN_IDS or user_id == cls.OWNER_ID

# Validate configuration on import
if not Config.validate():
    raise ValueError("Invalid configuration. Please check your environment variables.")