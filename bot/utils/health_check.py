
import asyncio
import logging
import time
from typing import Dict, Any
from pyrogram import Client
from bot.database.connection import Database

logger = logging.getLogger(__name__)

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check = time.time()
        self.health_status = {
            'bot': False,
            'database': False,
            'clone_manager': False
        }
    
    async def check_bot_health(self, client: Client) -> bool:
        """Check if bot is responsive"""
        try:
            me = await client.get_me()
            return me is not None
        except Exception as e:
            logger.error(f"Bot health check failed: {e}")
            return False
    
    async def check_database_health(self) -> bool:
        """Check database connectivity"""
        try:
            database = Database()
            # Simple ping to check connection
            await database.total_users_count()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_clone_manager_health(self) -> bool:
        """Check clone manager status"""
        try:
            from clone_manager import clone_manager
            return hasattr(clone_manager, 'instances')
        except Exception as e:
            logger.error(f"Clone manager health check failed: {e}")
            return False
    
    async def perform_health_check(self, client: Client = None) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        self.last_check = time.time()
        
        # Check bot health
        if client:
            self.health_status['bot'] = await self.check_bot_health(client)
        
        # Check database health
        self.health_status['database'] = await self.check_database_health()
        
        # Check clone manager health
        self.health_status['clone_manager'] = await self.check_clone_manager_health()
        
        uptime = self.last_check - self.start_time
        
        return {
            'status': 'healthy' if all(self.health_status.values()) else 'unhealthy',
            'uptime': uptime,
            'components': self.health_status,
            'timestamp': self.last_check
        }
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return all(self.health_status.values())

# Global health checker instance
health_checker = HealthChecker()
