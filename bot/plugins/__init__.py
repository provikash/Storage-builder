
# Bot plugins package
"""Bot plugins initialization"""

# Import plugins in specific order to prevent handler conflicts
# Core handlers first, then specialized handlers
try:
    from . import (
        start_handler,          # MUST be first - core /start command
        callback_handlers,      # Core callback system
        admin_commands,         # Admin commands
        clone_admin_commands,   # Clone admin commands
        genlink,
        admin_panel,
        balance_management,
        premium,
        stats,
        broadcast,
        enhanced_about,
        channel,
        clone_admin,
        clone_force_commands,
        clone_token_commands,
        force_sub_commands,
        index,
        referral_program,
        simple_file_sharing,
        token,
        auto_post,
        clone_random_files,
        # Debug and fallback handlers LAST to avoid conflicts
        debug_commands,
        debug_callbacks,
        missing_callbacks,
        missing_commands
    )
    print("✅ All plugins imported successfully in correct order")
except ImportError as e:
    print(f"⚠️  Warning: Could not import some plugins: {e}")
