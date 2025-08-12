
import asyncio
from datetime import datetime, timedelta
from bot.database.clone_db import get_clone_config, get_global_force_channels, get_clone
from bot.database.subscription_db import get_subscription
from info import Config

class CloneConfigLoader:
    """Advanced configuration loader for dynamic bot behavior"""
    
    def __init__(self):
        self.config_cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    async def get_bot_config(self, bot_token: str):
        """Get comprehensive configuration for a specific bot"""
        # Extract bot ID from token
        bot_id = bot_token.split(':')[0]
        
        # Check cache first
        cache_key = f"config_{bot_id}"
        if cache_key in self.config_cache:
            cached_data = self.config_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_timeout):
                return cached_data['config']
        
        # Load configuration from database
        config = await self._load_bot_config(bot_id, bot_token)
        
        # Cache the configuration
        self.config_cache[cache_key] = {
            'config': config,
            'timestamp': datetime.now()
        }
        
        return config
    
    async def _load_bot_config(self, bot_id: str, bot_token: str):
        """Load configuration from database"""
        # Check if this is the mother bot
        if bot_token == Config.BOT_TOKEN:
            return await self._get_mother_bot_config()
        
        # Get clone-specific configuration
        clone_config = await get_clone_config(bot_id)
        clone_data = await get_clone(bot_id)
        subscription = await get_subscription(bot_id)
        
        if not clone_config or not clone_data:
            # Return restricted config for unregistered bots
            return await self._get_restricted_config()
        
        # Check subscription status
        subscription_active = (
            subscription and 
            subscription['status'] == 'active' and 
            subscription['expiry_date'] > datetime.now()
        )
        
        # Build comprehensive configuration
        config = {
            "bot_info": {
                "bot_id": bot_id,
                "token": bot_token,
                "admin_id": clone_data['admin_id'],
                "is_clone": True,
                "is_mother_bot": False
            },
            "subscription": {
                "active": subscription_active,
                "tier": subscription['tier'] if subscription else None,
                "expiry": subscription['expiry_date'] if subscription else None,
                "status": subscription['status'] if subscription else 'inactive'
            },
            "features": clone_config.get('features', self._get_default_features()),
            "token_settings": clone_config.get('token_settings', self._get_default_token_settings()),
            "channels": await self._get_channel_config(clone_config),
            "custom_messages": clone_config.get('custom_messages', {}),
            "url_shortener": clone_config.get('url_shortener', self._get_default_shortener()),
            "permissions": self._get_clone_permissions(subscription_active)
        }
        
        return config
    
    async def _get_mother_bot_config(self):
        """Get configuration for mother bot"""
        return {
            "bot_info": {
                "bot_id": Config.BOT_TOKEN.split(':')[0],
                "token": Config.BOT_TOKEN,
                "admin_id": Config.OWNER_ID,
                "is_clone": False,
                "is_mother_bot": True
            },
            "subscription": {
                "active": True,
                "tier": "unlimited",
                "expiry": None,
                "status": "active"
            },
            "features": {
                "search": True,
                "upload": True,
                "token_verification": True,
                "premium": True,
                "auto_delete": True,
                "batch_links": True,
                "clone_creation": True,
                "admin_panel": True
            },
            "token_settings": {
                "mode": "unlimited",
                "command_limit": -1,
                "pricing": 0.0,
                "enabled": False
            },
            "channels": {
                "force_channels": await get_global_force_channels(),
                "request_channels": getattr(Config, 'REQUEST_CHANNELS', [])
            },
            "custom_messages": {},
            "url_shortener": {
                "service": getattr(Config, 'SHORTLINK_API_URL', ''),
                "api_key": getattr(Config, 'SHORTLINK_API', '')
            },
            "permissions": {
                "can_create_clones": True,
                "can_manage_global_settings": True,
                "unlimited_access": True
            }
        }
    
    async def _get_restricted_config(self):
        """Get restricted configuration for inactive/unregistered bots"""
        return {
            "bot_info": {
                "is_clone": True,
                "is_mother_bot": False,
                "restricted": True
            },
            "subscription": {
                "active": False,
                "status": "inactive"
            },
            "features": {
                "search": False,
                "upload": False,
                "token_verification": False,
                "premium": False,
                "auto_delete": False,
                "batch_links": False
            },
            "permissions": {
                "can_use_bot": False,
                "restriction_message": "⚠️ This bot clone is inactive. Contact the admin to renew subscription."
            }
        }
    
    async def _get_channel_config(self, clone_config):
        """Get channel configuration combining global and local channels"""
        global_channels = await get_global_force_channels()
        local_channels = clone_config.get('channels', {}).get('force_channels', [])
        request_channels = clone_config.get('channels', {}).get('request_channels', [])
        
        return {
            "force_channels": list(set(global_channels + local_channels)),
            "request_channels": request_channels,
            "global_force_channels": global_channels,
            "local_force_channels": local_channels
        }
    
    def _get_default_features(self):
        """Get default feature configuration for clones"""
        return {
            "search": True,
            "upload": True,
            "token_verification": True,
            "premium": True,
            "auto_delete": True,
            "batch_links": True,
            "clone_creation": False,  # Only mother bot can create clones
            "admin_panel": False
        }
    
    def _get_default_token_settings(self):
        """Get default token verification settings"""
        return {
            "mode": "one_time",  # or "command_limit"
            "command_limit": 100,
            "pricing": 1.0,
            "enabled": True
        }
    
    def _get_default_shortener(self):
        """Get default URL shortener settings"""
        return {
            "service": "",
            "api_key": "",
            "enabled": False
        }
    
    def _get_clone_permissions(self, subscription_active):
        """Get permissions based on subscription status"""
        if subscription_active:
            return {
                "can_use_bot": True,
                "can_upload": True,
                "can_search": True,
                "can_generate_tokens": True,
                "unlimited_access": False
            }
        else:
            return {
                "can_use_bot": False,
                "restriction_message": "⚠️ Subscription expired. Please renew to continue using this bot."
            }
    
    async def is_feature_enabled(self, bot_token: str, feature: str):
        """Check if a specific feature is enabled for a bot"""
        config = await self.get_bot_config(bot_token)
        return config.get('features', {}).get(feature, False)
    
    async def can_user_access(self, bot_token: str, user_id: int):
        """Check if user can access the bot"""
        config = await self.get_bot_config(bot_token)
        
        # Mother bot - check admin status
        if config['bot_info'].get('is_mother_bot', False):
            return user_id in [Config.OWNER_ID] + list(Config.ADMINS)
        
        # Clone bot - check subscription and permissions
        permissions = config.get('permissions', {})
        if not permissions.get('can_use_bot', False):
            return False, permissions.get('restriction_message', 'Bot access restricted')
        
        return True, None
    
    async def get_force_channels(self, bot_token: str):
        """Get all force channels (global + local) for a bot"""
        config = await self.get_bot_config(bot_token)
        return config.get('channels', {}).get('force_channels', [])
    
    async def get_request_channels(self, bot_token: str):
        """Get request channels for a bot"""
        config = await self.get_bot_config(bot_token)
        return config.get('channels', {}).get('request_channels', [])
    
    async def get_token_settings(self, bot_token: str):
        """Get token verification settings for a bot"""
        config = await self.get_bot_config(bot_token)
        return config.get('token_settings', {})
    
    async def get_custom_messages(self, bot_token: str):
        """Get custom messages for a bot"""
        config = await self.get_bot_config(bot_token)
        return config.get('custom_messages', {})
    
    def clear_cache(self, bot_token: str = None):
        """Clear configuration cache"""
        if bot_token:
            bot_id = bot_token.split(':')[0]
            cache_key = f"config_{bot_id}"
            self.config_cache.pop(cache_key, None)
        else:
            self.config_cache.clear()
    
    async def reload_config(self, bot_token: str):
        """Force reload configuration for a bot"""
        self.clear_cache(bot_token)
        return await self.get_bot_config(bot_token)

# Global instance
clone_config_loader = CloneConfigLoader()
