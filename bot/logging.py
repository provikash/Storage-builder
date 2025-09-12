import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from contextlib import contextmanager
import threading

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # Add exception info
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data, default=str)

class ColorFormatter(logging.Formatter):
    """Add colors to log messages"""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"

        # Add context if available
        context_info = getattr(record, 'context', {})
        if context_info:
            context_str = ' | '.join([f"{k}={v}" for k, v in context_info.items()])
            record.msg = f"[{context_str}] {record.msg}"

        return super().format(record)

class ContextLogger:
    """Logger with context support"""

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context = {}

    def add_context(self, **kwargs) -> 'ContextLogger':
        """Add context to logger"""
        new_context = {**self._context, **kwargs}
        new_logger = ContextLogger(self._logger)
        new_logger._context = new_context
        return new_logger

    def _log_with_context(self, level, msg, *args, **kwargs):
        """Log message with context"""
        extra = kwargs.get('extra', {})
        extra['context'] = self._context
        kwargs['extra'] = extra
        getattr(self._logger, level)(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log_with_context('debug', msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log_with_context('info', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log_with_context('warning', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log_with_context('error', msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._log_with_context('critical', msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

# Thread-local storage for request context
_context = threading.local()

def setup_logging():
    """Setup enhanced logging configuration"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    file_formatter = logging.Formatter(
        '[%(asctime)s - %(levelname)s] - %(name)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S'
    )

    structured_formatter = StructuredFormatter()
    console_formatter = ColorFormatter(
        '[%(asctime)s - %(levelname)s] - %(name)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S'
    )

    # File handlers
    main_handler = logging.FileHandler(log_dir / "mother_bot.log")
    main_handler.setFormatter(file_formatter)

    structured_handler = logging.FileHandler(log_dir / "structured.log")
    structured_handler.setFormatter(structured_formatter)

    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    access_handler = logging.FileHandler(log_dir / "access.log")
    access_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[main_handler, structured_handler, error_handler, console_handler]
    )

    # Suppress noisy loggers
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)

    startup_logger = logging.getLogger("startup")
    startup_logger.info("🚀 Logging system initialized - " + datetime.now().isoformat())
    startup_logger.info(f"📁 Log directory: {log_dir.absolute()}")
    startup_logger.info(f"📝 Main log: {log_dir / 'mother_bot.log'}")
    startup_logger.info(f"🚨 Error log: {log_dir / 'errors.log'}")
    startup_logger.info(f"🌐 Access log: {log_dir / 'access.log'}")

    return startup_logger

def LOGGER(name: str) -> logging.Logger:
    """Get logger for module"""
    return logging.getLogger(name)

def get_context_logger(name: str) -> ContextLogger:
    """Get context-aware logger"""
    return ContextLogger(logging.getLogger(name))

@contextmanager
def log_context(**kwargs):
    """Context manager for adding context to logs"""
    old_context = getattr(_context, 'data', {})
    _context.data = {**old_context, **kwargs}
    try:
        yield
    finally:
        _context.data = old_context

# Ensure logs directory exists
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log files
LOG_FILE_NAME = LOG_DIR / "mother_bot.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"
ACCESS_LOG_FILE = LOG_DIR / "access.log"
STRUCTURED_LOG_FILE = LOG_DIR / "structured.log"

# Initialize logging
startup_logger = setup_logging()

# Create specialized loggers
# security_logger = logging.getLogger("security") # This was commented out in the original, keeping it commented.
# access_logger = setup_access_logging() # This function is no longer directly called here, setup_logging handles it.

# Log startup
startup_logger.info(f"🚀 Logging system initialized - {datetime.now()}")
startup_logger.info(f"📁 Log directory: {LOG_DIR.absolute()}")
startup_logger.info(f"📝 Main log: {LOG_FILE_NAME}")
startup_logger.info(f"🚨 Error log: {ERROR_LOG_FILE}")
startup_logger.info(f"🌐 Access log: {ACCESS_LOG_FILE}")
startup_logger.info(f"📊 Structured log: {STRUCTURED_LOG_FILE}")