import re
from os import getenv, environ
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

    # Bot Configuration - Load from environment
    API_ID = getenv("API_ID")
    API_HASH = getenv("API_HASH")
    BOT_TOKEN = getenv("BOT_TOKEN")
    BOT_WORKERS = int(getenv("BOT_WORKERS", "4"))

    # Validate required environment variables
    if not API_ID or not API_HASH or not BOT_TOKEN:
        raise ValueError("Missing required environment variables: API_ID, API_HASH, or BOT_TOKEN")

    # Convert API_ID to int after validation
    try:
        API_ID = int(API_ID)
    except ValueError:
        raise ValueError("API_ID must be a valid integer")

    # Webhook settings
    WEB_MODE = getenv("WEB_MODE", "False").lower() in ("true", "1", "yes")
    PORT = int(getenv("PORT", "5000"))
    HOST = getenv("HOST", "0.0.0.0")

    # Channel Configuration - Load from environment
    CHANNEL_ID = getenv("CHANNEL_ID")
    INDEX_CHANNEL_ID = getenv("INDEX_CHANNEL_ID")
    OWNER_ID = getenv("OWNER_ID")

    # Validate and convert channel/owner IDs
    if not CHANNEL_ID or not INDEX_CHANNEL_ID or not OWNER_ID:
        raise ValueError("Missing required environment variables: CHANNEL_ID, INDEX_CHANNEL_ID, or OWNER_ID")

    try:
        CHANNEL_ID = int(CHANNEL_ID)
        INDEX_CHANNEL_ID = int(INDEX_CHANNEL_ID)
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        raise ValueError("CHANNEL_ID, INDEX_CHANNEL_ID, and OWNER_ID must be valid integers")

    # Database - Load from environment
    DATABASE_URL = getenv("DATABASE_URL")
    DATABASE_NAME = getenv("DATABASE_NAME", "Cluster0")

    # Force Subscription - Handle both channel IDs and usernames
    FORCE_SUB_CHANNEL_RAW = getenv("FORCE_SUB_CHANNEL", "").strip()
    FORCE_SUB_CHANNEL = []
    if FORCE_SUB_CHANNEL_RAW:
        for ch in FORCE_SUB_CHANNEL_RAW.split():
            ch = ch.strip()
            if ch and ch != "...":  # Skip empty and invalid entries
                if ch.lstrip('-').isdigit():  # Channel ID
                    FORCE_SUB_CHANNEL.append(int(ch))
                else:  # Username
                    FORCE_SUB_CHANNEL.append(ch)
    print(f"DEBUG: Loaded FORCE_SUB_CHANNEL: {FORCE_SUB_CHANNEL}")

    # Request channels (admin approval required) - Handle both channel IDs and usernames
    REQUEST_CHANNEL_RAW = getenv("REQUEST_CHANNEL", "").strip()
    REQUEST_CHANNEL = []
    if REQUEST_CHANNEL_RAW:
        for ch in REQUEST_CHANNEL_RAW.split():
            ch = ch.strip()
            if ch and ch != "...":  # Skip empty and invalid entries
                if ch.lstrip('-').isdigit():  # Channel ID
                    REQUEST_CHANNEL.append(int(ch))
                else:  # Username
                    REQUEST_CHANNEL.append(ch)
    print(f"DEBUG: Loaded REQUEST_CHANNEL: {REQUEST_CHANNEL}")
    JOIN_REQUEST_ENABLE = getenv("JOIN_REQUEST_ENABLED", "False").lower() in ("true", "1", "yes")

    # Messages - Load from environment
    START_PIC = getenv("START_PIC", "")
    START_MSG = getenv("START_MESSAGE", "👋 Hello {mention},\n\nThis bot helps you store private files in a secure channel and generate special access links for sharing. 🔐📁\n\n Only admins can upload files and generate links. Just send the file here to get started.")
    FORCE_MSG = getenv("FORCE_SUB_MESSAGE", "👋 Hello {mention}, \n\n <b>You need to join our updates channel before using this bot.</b>\n\n 📢 Please join the required channel, then try again.")
    CUSTOM_CAPTION = getenv("CUSTOM_CAPTION", None)

    # ✅ Secure ADMINS - Load from environment as immutable tuple
    admins = getenv("ADMINS", "").split()
    _admin_list = list(set(
        [int(x) for x in admins if x.isdigit()] + [OWNER_ID]
    ))
    ADMINS = tuple(_admin_list)  # Immutable tuple prevents runtime modification

    # Security Configuration - Load from environment
    PROTECT_CONTENT = getenv("PROTECT_CONTENT", "False") == "True"
    DISABLE_CHANNEL_BUTTON = getenv("DISABLE_CHANNEL_BUTTON", "False") == "True"

    # Auto Delete Configuration - Load from environment
    AUTO_DELETE_TIME = int(getenv("AUTO_DELETE_TIME", "600"))
    AUTO_DELETE_MSG = getenv("AUTO_DELETE_MSG", "This file will be automatically deleted in {time}.")
    AUTO_DEL_SUCCESS_MSG = getenv("AUTO_DEL_SUCCESS_MSG", "✅ File deleted successfully.")

    # Token Verification (Shortlink) - Load from environment
    VERIFY_MODE = getenv("VERIFY_MODE", "True").lower() in ("true", "1", "yes")
    SHORTLINK_API = getenv("SHORTLINK_API")
    SHORTLINK_URL = getenv("SHORTLINK_URL", "https://teraboxlinks.com/")
    TUTORIAL = getenv("TUTORIAL","https://t.me/alfhamovies/13")

    # Bot Messages - Load from environment
    BOT_STATS_TEXT = getenv("BOT_STATS_TEXT", "<b>BOT UPTIME</b>\n{uptime}")
    USER_REPLY_TEXT = getenv("USER_REPLY_TEXT", "❌ I'm a bot — please don't DM me!")

    # Premium Settings - Load from environment
    PREMIUM_ENABLED = getenv("PREMIUM_ENABLED", "True").lower() in ("true", "1", "yes")
    PAYMENT_UPI = getenv("PAYMENT_UPI", "your_actual_upi@paytm")
    PAYMENT_PHONE = getenv("PAYMENT_PHONE", "+911234567890")
    ADMIN_USERNAME = getenv("ADMIN_USERNAME", "termuxro")

    # Cryptocurrency Payment Options
    CRYPTO_ENABLED = getenv("CRYPTO_ENABLED", "True").lower() in ("true", "1", "yes")
    BITCOIN_ADDRESS = getenv("BITCOIN_ADDRESS", "")
    ETHEREUM_ADDRESS = getenv("ETHEREUM_ADDRESS", "")
    USDT_TRC20_ADDRESS = getenv("USDT_TRC20_ADDRESS", "")
    USDT_ERC20_ADDRESS = getenv("USDT_ERC20_ADDRESS", "")