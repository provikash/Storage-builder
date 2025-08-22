
import asyncio
from datetime import datetime
from bot.database.clone_db import get_all_clones, get_clone_statistics
from bot.database.subscription_db import get_subscription_stats
from clone_manager import clone_manager
from bot.logging import LOGGER

logger = LOGGER(__name__)

class HealthChecker:
    """Monitor overall system health"""
    
    def __init__(self):
        self.check_interval = 600  # Check every 10 minutes
        self.last_check = None
        self.status = "unknown"
    
    async def start_monitoring(self):
        """Start health monitoring"""
        logger.info("🏥 Starting health monitoring...")
        
        while True:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def perform_health_check(self):
        """Perform comprehensive health check"""
        try:
            self.last_check = datetime.now()
            issues = []
            
            # Check database connectivity
            try:
                clone_stats = await get_clone_statistics()
                subscription_stats = await get_subscription_stats()
            except Exception as e:
                issues.append(f"Database connectivity: {e}")
            
            # Check clone manager
            try:
                running_clones = clone_manager.get_running_clones()
                all_clones = await get_all_clones()
                active_clones = [c for c in all_clones if c.get('status') == 'active']
                
                if len(running_clones) != len(active_clones):
                    issues.append(f"Clone sync issue: {len(running_clones)}/{len(active_clones)} running")
            except Exception as e:
                issues.append(f"Clone manager: {e}")
            
            # Set status
            if not issues:
                self.status = "healthy"
                logger.info("✅ System health check passed")
            else:
                self.status = "degraded"
                logger.warning(f"⚠️ Health issues detected: {'; '.join(issues)}")
            
        except Exception as e:
            self.status = "critical"
            logger.error(f"❌ Health check failed: {e}")
    
    def get_status(self):
        """Get current health status"""
        return {
            "status": self.status,
            "last_check": self.last_check,
            "uptime": datetime.now() - (self.last_check or datetime.now())
        }

# Create global instance
health_checker = HealthChecker()
