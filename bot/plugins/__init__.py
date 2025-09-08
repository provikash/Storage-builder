
# Bot plugins package
"""Bot plugins initialization"""

# Import all plugins to ensure they register their handlers
try:
    from . import (
        start_handler,
        genlink,
        admin,
        admin_commands,
        admin_panel,
        balance_management,
        premium,
        stats,
        broadcast,
        enhanced_about,
        debug_commands,
        callback_handlers,
        channel,
        clone_admin,
        clone_admin_commands,
        clone_force_commands,
        clone_token_commands,
        debug_callbacks,
        force_sub_commands,
        index,
        missing_callbacks,
        missing_commands,
        referral_program,
        simple_file_sharing,
        token,
        auto_post,
        clone_random_files
    )
except ImportError as e:
    print(f"Warning: Could not import some plugins: {e}")
