
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log files
LOG_FILE_NAME = LOG_DIR / "mother_bot.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"
ACCESS_LOG_FILE = LOG_DIR / "access.log"

class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logging():
    """Setup production-ready logging configuration"""
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Main log file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_NAME,
        maxBytes=50_000_000,  # 50MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Error log file handler
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    # Production logging adjustments
    if os.environ.get("ENVIRONMENT") == "production":
        # Reduce console logging in production
        console_handler.setLevel(logging.WARNING)
        
        # Add security logger for audit trails
        security_logger = logging.getLogger("security")
        security_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "security.log",
            maxBytes=10_000_000,
            backupCount=10,
            encoding="utf-8"
        )
        security_handler.setFormatter(file_formatter)
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.INFO)

def LOGGER(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)

class ContextLogger:
    """Logger with context support for debugging"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.context = {}
    
    def add_context(self, **kwargs):
        """Add context to logger"""
        self.context.update(kwargs)
        return self
    
    def _format_message(self, msg: str) -> str:
        """Format message with context"""
        if self.context:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"[{context_str}] {msg}"
        return msg
    
    def debug(self, msg: str, **kwargs):
        temp_context = {**self.context, **kwargs}
        if temp_context:
            context_str = " | ".join([f"{k}={v}" for k, v in temp_context.items()])
            msg = f"[{context_str}] {msg}"
        self.logger.debug(msg)
    
    def info(self, msg: str, **kwargs):
        temp_context = {**self.context, **kwargs}
        if temp_context:
            context_str = " | ".join([f"{k}={v}" for k, v in temp_context.items()])
            msg = f"[{context_str}] {msg}"
        self.logger.info(msg)
    
    def warning(self, msg: str, **kwargs):
        temp_context = {**self.context, **kwargs}
        if temp_context:
            context_str = " | ".join([f"{k}={v}" for k, v in temp_context.items()])
            msg = f"[{context_str}] {msg}"
        self.logger.warning(msg)
    
    def error(self, msg: str, **kwargs):
        temp_context = {**self.context, **kwargs}
        if temp_context:
            context_str = " | ".join([f"{k}={v}" for k, v in temp_context.items()])
            msg = f"[{context_str}] {msg}"
        self.logger.error(msg)

def get_context_logger(name: str) -> ContextLogger:
    """Get context logger instance"""
    return ContextLogger(name)

def setup_access_logging():
    """Setup access logging for web interface"""
    access_logger = logging.getLogger("access")
    access_handler = logging.handlers.RotatingFileHandler(
        ACCESS_LOG_FILE,
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    access_formatter = logging.Formatter(
        "%(asctime)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    access_handler.setFormatter(access_formatter)
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    return access_logger

# Initialize logging
setup_logging()

# Create specialized loggers
security_logger = logging.getLogger("security")
access_logger = setup_access_logging()

# Log startup
startup_logger = LOGGER("startup")
startup_logger.info(f"🚀 Logging system initialized - {datetime.now()}")
startup_logger.info(f"📁 Log directory: {LOG_DIR.absolute()}")
startup_logger.info(f"📝 Main log: {LOG_FILE_NAME}")
startup_logger.info(f"🚨 Error log: {ERROR_LOG_FILE}")
startup_logger.info(f"🌐 Access log: {ACCESS_LOG_FILE}")
