
import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging():
    """Set up logging configuration"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s - %(levelname)s] - %(name)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class LOGGER:
    """Enhanced logger wrapper with proper error handling"""
    
    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(name)
        
    def _log_with_context(self, level: str, msg: str, *args, **kwargs):
        """Log with context, filtering out invalid kwargs"""
        # Remove any invalid kwargs that logging doesn't accept
        valid_kwargs = {k: v for k, v in kwargs.items() 
                       if k in ['exc_info', 'stack_info', 'stacklevel', 'extra']}
        
        getattr(self._logger, level)(msg, *args, **valid_kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message"""
        self._log_with_context('info', msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message"""
        self._log_with_context('debug', msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message"""
        self._log_with_context('warning', msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message"""
        self._log_with_context('error', msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log critical message"""
        self._log_with_context('critical', msg, *args, **kwargs)

# Setup logging on import
setup_logging()
