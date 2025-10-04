
"""
Handlers package - organized callback and message handlers
"""

# Import all handler modules to register them
from . import emergency
from . import file_browsing
from . import admin
from . import callback
from . import commands
from . import start
from . import search

__all__ = [
    'emergency',
    'file_browsing', 
    'admin',
    'callback',
    'commands',
    'start',
    'search'
]
"""
Bot Handlers Package
Organized into motherbot, clonebot, and shared handlers
"""

from bot.handlers import motherbot
from bot.handlers import clonebot
from bot.handlers import shared

__all__ = ["motherbot", "clonebot", "shared"]
