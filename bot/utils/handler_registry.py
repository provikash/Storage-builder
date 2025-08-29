
"""
Handler Registry to prevent callback conflicts
"""
from bot.logging import LOGGER

logger = LOGGER(__name__)

class HandlerRegistry:
    def __init__(self):
        self.registered_patterns = set()
        self.handler_groups = {}
    
    def register_pattern(self, pattern, handler_name, group=5):
        """Register a callback pattern to prevent conflicts"""
        if pattern in self.registered_patterns:
            logger.warning(f"Pattern '{pattern}' already registered by {self.handler_groups.get(pattern, 'unknown')}")
            return False
        
        self.registered_patterns.add(pattern)
        self.handler_groups[pattern] = handler_name
        logger.info(f"Registered pattern '{pattern}' for handler '{handler_name}' in group {group}")
        return True
    
    def is_registered(self, pattern):
        """Check if a pattern is already registered"""
        return pattern in self.registered_patterns
    
    def get_handler(self, pattern):
        """Get the handler name for a pattern"""
        return self.handler_groups.get(pattern)

# Global registry instance
handler_registry = HandlerRegistry()

# Register core patterns
handler_registry.register_pattern("back_to_start", "start_handler", 1)
handler_registry.register_pattern("user_profile", "start_handler", 1)
handler_registry.register_pattern("help_menu", "start_handler", 1)
handler_registry.register_pattern("admin_panel", "admin_handlers", 1)
handler_registry.register_pattern("start_clone_creation", "clone_creation", 2)
handler_registry.register_pattern("manage_my_clone", "clone_management", 2)
