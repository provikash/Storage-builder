# Bot plugins package
"""Bot plugins initialization"""

# Import plugins in specific order to prevent handler conflicts
# Core handlers first, then specialized handlers
import logging

logger = logging.getLogger(__name__)

def load_plugins():
    """Load plugins in safe order to prevent conflicts"""
    plugins_loaded = []
    plugins_failed = []

    # Core plugins that must load first
    core_plugins = [
        'start_handler',         # Core /start command FIRST
        'commands_unified',      # Unified commands handler
        'callback_unified',      # Unified callback handler
    ]

    # Feature plugins - Unified versions
    feature_plugins = [
        'clone_admin_unified',   # Unified clone admin
        'clone_indexing_unified', # Unified clone indexing
        'clone_search_unified',  # Unified clone search
        'admin_panel',           # Admin panel
        'balance_management',    # Balance management
        'premium',               # Premium features
        'enhanced_about',        # About page
        'auto_post',             # Auto posting
    ]

    # Debug plugins (load last)
    debug_plugins = [
        'debug_commands',
        'debug_callbacks',
        'debug_start'
    ]

    all_plugins = core_plugins + feature_plugins + debug_plugins

    for plugin_name in all_plugins:
        try:
            # Import the unified callback handler
            if plugin_name == 'callback_unified':
                __import__(f'bot.plugins.{plugin_name}')
            elif plugin_name == 'callback_fix' or plugin_name == 'missing_callbacks' or plugin_name == 'callback_handlers':
                # Skip old callback files if they are merged into callback_unified
                # This part might need adjustment based on how callback_unified is structured
                # and if any specific imports from these are still needed.
                # For now, we assume callback_unified replaces them.
                if plugin_name not in ['callback_fix', 'missing_callbacks', 'callback_handlers']:
                    __import__(f'bot.plugins.{plugin_name}')
            else:
                __import__(f'bot.plugins.{plugin_name}')
            plugins_loaded.append(plugin_name)
        except ImportError as e:
            # If callback_unified fails to import, it's a critical error.
            # If old callback files fail, it's expected if they are merged.
            if plugin_name in ['callback_fix', 'missing_callbacks', 'callback_handlers']:
                logger.debug(f"Skipping import of {plugin_name} as it's likely merged into callback_unified: {e}")
            else:
                plugins_failed.append(f"{plugin_name}: {str(e)}")
                logger.warning(f"Failed to import plugin {plugin_name}: {e}")
        except Exception as e:
            plugins_failed.append(f"{plugin_name}: {str(e)}")
            logger.error(f"Error loading plugin {plugin_name}: {e}")

    logger.info(f"✅ Loaded {len(plugins_loaded)} plugins successfully")
    if plugins_failed:
        logger.warning(f"⚠️ Failed to load {len(plugins_failed)} plugins: {plugins_failed}")

    return plugins_loaded, plugins_failed

# Auto-load plugins when module is imported
load_plugins()