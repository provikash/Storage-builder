
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
        'callback_fix',          # Emergency handler fixes FIRST
        'start_handler',         # Core /start command
        'callback_handlers',     # Core callback system
        'missing_callbacks',     # Missing callback handlers
        'missing_commands'       # Missing command handlers
    ]
    
    # Feature plugins
    feature_plugins = [
        'admin_commands',
        'admin_panel', 
        'balance_management',
        'premium',
        'stats',
        'broadcast',
        'enhanced_about',
        'channel',
        'clone_admin',
        'clone_admin_commands',
        'clone_force_commands',
        'clone_token_commands',
        'force_sub_commands',
        'genlink',
        'index',
        'referral_program',
        'simple_file_sharing',
        'search',
        'token',
        'auto_post',
        'clone_random_files'
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
            __import__(f'bot.plugins.{plugin_name}')
            plugins_loaded.append(plugin_name)
        except ImportError as e:
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
load_plugins() {e}")
