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
    DATABASE_URI = os.environ.get("DATABASE_URL", "")
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

    # Additional Configuration - moved inside Config class
    WEB_MODE = os.environ.get("WEB_MODE", "False").lower() in ("true", "1", "yes")
    PORT = int(os.environ.get("PORT", "5000"))
    HOST = os.environ.get("HOST", "0.0.0.0")

    # Channel Configuration with defaults for missing vars
    INDEX_CHANNEL_ID = int(os.environ.get("INDEX_CHANNEL_ID", "0"))
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

    # Force Subscription - Handle both channel IDs and usernames
    FORCE_SUB_CHANNEL_RAW = os.environ.get("FORCE_SUB_CHANNEL", "").strip()
    FORCE_SUB_CHANNEL = []
    if FORCE_SUB_CHANNEL_RAW:
        for ch in FORCE_SUB_CHANNEL_RAW.split():
            ch = ch.strip()
            if ch and ch != "...":
                if ch.lstrip('-').isdigit():
                    FORCE_SUB_CHANNEL.append(int(ch))
                else:
                    FORCE_SUB_CHANNEL.append(ch)

    # Request channels
    REQUEST_CHANNEL_RAW = os.environ.get("REQUEST_CHANNEL", "").strip()
    REQUEST_CHANNEL = []
    if REQUEST_CHANNEL_RAW:
        for ch in REQUEST_CHANNEL_RAW.split():
            ch = ch.strip()
            if ch and ch != "...":
                if ch.lstrip('-').isdigit():
                    REQUEST_CHANNEL.append(int(ch))
                else:
                    REQUEST_CHANNEL.append(ch)

    # Messages
    START_PIC = os.environ.get("START_PIC", "")
    START_MSG = os.environ.get("START_MESSAGE", "👋 Hello {mention},\n\nThis bot helps you store private files in a secure channel and generate special access links for sharing. 🔐📁\n\n Only admins can upload files and generate links. Just send the file here to get started.")
    FORCE_MSG = os.environ.get("FORCE_SUB_MESSAGE", "👋 Hello {mention}, \n\n <b>You need to join our updates channel before using this bot.</b>\n\n 📢 Please join the required channel, then try again.")
    CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", None)

    # Security Configuration
    PROTECT_CONTENT = os.environ.get("PROTECT_CONTENT", "False") == "True"
    DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", "False") == "True"

    # Auto Delete Configuration
    AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", "600"))
    AUTO_DELETE_MSG = os.environ.get("AUTO_DELETE_MSG", "This file will be automatically deleted in {time}.")
    AUTO_DEL_SUCCESS_MSG = os.environ.get("AUTO_DEL_SUCCESS_MSG", "✅ File deleted successfully.")

    # Token Verification (Shortlink)
    VERIFY_MODE = os.environ.get("VERIFY_MODE", "True").lower() in ("true", "1", "yes")
    SHORTLINK_API = os.environ.get("SHORTLINK_API")
    SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "https://teraboxlinks.com/")
    TUTORIAL = os.environ.get("TUTORIAL","https://t.me/alfhamovies/13")

    # Bot Messages
    BOT_STATS_TEXT = os.environ.get("BOT_STATS_TEXT", "<b>BOT UPTIME</b>\n{uptime}")
    USER_REPLY_TEXT = os.environ.get("USER_REPLY_TEXT", "❌ I'm a bot — please don't DM me!")

    # Premium Settings
    PREMIUM_ENABLED = os.environ.get("PREMIUM_ENABLED", "True").lower() in ("true", "1", "yes")
    PAYMENT_UPI = os.environ.get("PAYMENT_UPI", "your_actual_upi@paytm")
    PAYMENT_PHONE = os.environ.get("PAYMENT_PHONE", "+911234567890")
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "termuxro")

    # Cryptocurrency Payment Options
    CRYPTO_ENABLED = os.environ.get("CRYPTO_ENABLED", "True").lower() in ("true", "1", "yes")
    BITCOIN_ADDRESS = os.environ.get("BITCOIN_ADDRESS", "")
    ETHEREUM_ADDRESS = os.environ.get("ETHEREUM_ADDRESS", "")
    USDT_TRC20_ADDRESS = os.environ.get("USDT_TRC20_ADDRESS", "")
    USDT_ERC20_ADDRESS = os.environ.get("USDT_ERC20_ADDRESS", "")

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

    # Additional config variables that might be missing
    FORCE_SUB_MESSAGE = os.environ.get("FORCE_SUB_MESSAGE", "Please join our channel to use this bot.")
    START_MESSAGE = os.environ.get("START_MESSAGE", "Welcome! I'm your file sharing bot.")

    # Validate configuration on import
    @classmethod
    def validate_extended(cls):
        """Extended validation including additional configs"""
        cls.validate()  # Run basic validation first
        return True

# Validate configuration on import
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your environment variables!")