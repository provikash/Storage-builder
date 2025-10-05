
"""
Start Command Handlers
Centralized start command handling for both mother and clone bots
"""

# This module serves as the central import point for all start-related functionality
# The actual implementation is in bot/plugins/start_handler.py
# This ensures clean module organization while maintaining backwards compatibility

from bot.plugins.start_handler import (
    start_command,
    is_clone_bot_instance_async,
    is_clone_admin,
    get_start_keyboard_for_clone_user,
    get_start_keyboard,
    get_user_settings,
    update_user_setting
)

__all__ = [
    'start_command',
    'is_clone_bot_instance_async', 
    'is_clone_admin',
    'get_start_keyboard_for_clone_user',
    'get_start_keyboard',
    'get_user_settings',
    'update_user_setting'
]
