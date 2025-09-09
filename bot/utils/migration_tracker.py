
"""
Migration tracker to help with file organization
"""
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Mapping of old file locations to new locations
MIGRATION_MAP = {
    # Handlers moved to bot/handlers/
    'bot/plugins/callback_handlers.py': 'bot/handlers/callback.py',
    'bot/plugins/start_handler.py': 'bot/handlers/start.py',
    'bot/plugins/simple_start.py': 'bot/handlers/start.py',
    'bot/plugins/debug_start.py': 'bot/handlers/start.py',
    'bot/plugins/search.py': 'bot/handlers/search.py',
    
    # Clone programs moved to bot/programs/
    'bot/plugins/clone_admin.py': 'bot/programs/clone_admin.py',
    'bot/plugins/clone_admin_commands.py': 'bot/programs/clone_admin.py',
    'bot/plugins/clone_admin_settings.py': 'bot/programs/clone_admin.py',
    'bot/plugins/clone_index.py': 'bot/programs/clone_indexing.py',
    'bot/plugins/clone_management.py': 'bot/programs/clone_management.py',
    'bot/plugins/clone_random_files.py': 'bot/programs/clone_random_files.py',
    'bot/plugins/clone_force_commands.py': 'bot/programs/clone_admin.py',
    'bot/plugins/clone_token_commands.py': 'bot/programs/clone_admin.py',
}

def log_migration_status():
    """Log the current migration status"""
    logger.info("🔄 File Migration Status:")
    logger.info("📁 Handlers moved to: bot/handlers/")
    logger.info("🤖 Clone programs moved to: bot/programs/")
    logger.info("✅ Architecture improved for better organization")

def get_new_location(old_path: str) -> str:
    """Get the new location for a migrated file"""
    return MIGRATION_MAP.get(old_path, old_path)
