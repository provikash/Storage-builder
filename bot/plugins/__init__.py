import glob
from pathlib import Path

# Import core handlers first to avoid conflicts
from . import start_handler
from . import missing_commands
from . import debug_start

# Import other plugins
from . import callback_handlers
from . import admin_commands
from . import clone_admin_settings
from . import channel
from . import stats
from . import broadcast
from . import mother_admin
from . import enhanced_about

# Set plugin loading order
__all__ = [
    "start_handler",
    "missing_commands",
    "debug_start",
    "callback_handlers",
    "admin_commands",
    "clone_admin_settings",
    "channel",
    "stats", 
    "broadcast",
    "mother_admin",
    "enhanced_about"
]