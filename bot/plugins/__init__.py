
# Bot plugins package
"""Bot plugins initialization"""

# Import all plugins to ensure they register their handlers
try:
    from . import (
        start_handler,
        genlink,
        search,
        callback,
        command_stats,
        water_about,
        callback_fix,
        clone_index,
        admin,
        admin_commands,
        admin_panel,
        balance_management,
        premium,
        stats,
        broadcast,
        enhanced_about,
        debug_commands
    )
except ImportError as e:
    print(f"Warning: Could not import some plugins: {e}")
