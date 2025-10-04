"""
Bot Package
Main bot functionality organized by:
- handlers: Request handlers (motherbot, clonebot, shared)
- programs: Reusable program modules
- plugins: Legacy plugins (being phased out)
- database: Data persistence layer
- utils: Utility functions
"""
__version__ = "2.0.0"

# Import core components
from bot.logging import LOGGER

# Import handlers
from bot import handlers

# Import programs
from bot import programs

__all__ = ["LOGGER", "handlers", "programs"]