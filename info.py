import re
import os
from dotenv import load_dotenv

load_dotenv()

id_pattern = re.compile(r'^.\d+$')

class Config(object):
    _PROTECTED_ATTRS = frozenset(['ADMINS', 'OWNER_ID', 'API_ID', 'API_HASH', 'BOT_TOKEN'])

    def __setattr__(self, name, value):
        if name in self._PROTECTED_ATTRS and hasattr(self, name):
            raise AttributeError(f"Cannot modify {name} at runtime for security reasons")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in self._PROTECTED_ATTRS:
            raise AttributeError(f"Cannot delete {name} for security reasons")
        super().__delattr__(name)

    # Bot Configuration - REQUIRED
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # Database Configuration - REQUIRED
    DATABASE_URI = os.environ.get("DATABASE_URI", "")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "mother_bot")

    # Admin Configuration - REQUIRED
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split() if x.isdigit()]

    # Optional Configurations
    CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
    FORCE_SUB_CHANNELS = [int(x) for x in os.environ.get("FORCE_SUB_CHANNELS", "").split() if x.isdigit()]

    # Security Settings
    MAX_CLONE_REQUESTS_PER_DAY = int(os.environ.get("MAX_CLONE_REQUESTS_PER_DAY", "5"))
    CLONE_REQUEST_COOLDOWN_HOURS = int(os.environ.get("CLONE_REQUEST_COOLDOWN_HOURS", "24"))

    # Production Settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
    MAX_REQUESTS_PER_MINUTE = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", "20"))

    # Monitoring
    HEALTH_CHECK_ENABLED = os.environ.get("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    SYSTEM_MONITORING_ENABLED = os.environ.get("SYSTEM_MONITORING_ENABLED", "true").lower() == "true"

    # Web Interface
    WEB_SERVER_ENABLED = os.environ.get("WEB_SERVER_ENABLED", "true").lower() == "true"
    WEB_SERVER_PORT = int(os.environ.get("WEB_SERVER_PORT", "5000"))

    # Error Handling
    DETAILED_ERRORS = os.environ.get("DETAILED_ERRORS", "false").lower() == "true"
    ERROR_LOGS_ENABLED = os.environ.get("ERROR_LOGS_ENABLED", "true").lower() == "true"

    # Validate critical configuration
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []

        if not cls.API_ID or cls.API_ID == 0:
            errors.append("API_ID is required")

        if not cls.API_HASH:
            errors.append("API_HASH is required")

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")

        if not cls.DATABASE_URI:
            errors.append("DATABASE_URI is required")

        if not cls.ADMINS:
            errors.append("At least one ADMIN is required")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

# Validate configuration on import
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your environment variables!")