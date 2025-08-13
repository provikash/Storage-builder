
import asyncio
import psutil
import time
from datetime import datetime
from bot.logging import LOGGER
from clone_manager import clone_manager
from bot.database.subscription_db import get_subscription_stats
from bot.database.clone_db import get_clone_statistics

logger = LOGGER(__name__)

class SystemMonitor:
    """Monitor system health and performance"""
    
    def __init__(self):
        self.monitor_interval = 300  # 5 minutes
        self.start_time = datetime.now()
        
    async def start_monitoring(self):
        """Start system monitoring"""
        logger.info("📊 Starting system monitoring...")
        
        while True:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"❌ Error in system monitoring: {e}")
                await asyncio.sleep(60)
    
    async def collect_metrics(self):
        """Collect system metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Application metrics
            running_clones = len(clone_manager.get_running_clones())
            clone_stats = await get_clone_statistics()
            subscription_stats = await get_subscription_stats()
            
            # Uptime
            uptime = datetime.now() - self.start_time
            
            # Log metrics
            logger.info(
                f"📊 System Metrics - "
                f"CPU: {cpu_percent}%, "
                f"Memory: {memory.percent}%, "
                f"Disk: {disk.percent}%, "
                f"Uptime: {uptime.days}d {uptime.seconds//3600}h"
            )
            
            logger.info(
                f"🤖 Bot Metrics - "
                f"Running Clones: {running_clones}, "
                f"Total Clones: {clone_stats['total']}, "
                f"Active Subs: {subscription_stats['active']}, "
                f"Revenue: ${subscription_stats['total_revenue']}"
            )
            
            # Check for critical conditions
            if cpu_percent > 80:
                logger.warning(f"⚠️ High CPU usage: {cpu_percent}%")
            if memory.percent > 80:
                logger.warning(f"⚠️ High memory usage: {memory.percent}%")
            if disk.percent > 90:
                logger.warning(f"⚠️ High disk usage: {disk.percent}%")
                
        except Exception as e:
            logger.error(f"❌ Error collecting metrics: {e}")
    
    def get_system_info(self):
        """Get current system information"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "uptime": str(datetime.now() - self.start_time),
                "running_clones": len(clone_manager.get_running_clones())
            }
        except Exception as e:
            logger.error(f"❌ Error getting system info: {e}")
            return {}

# Global system monitor
system_monitor = SystemMonitor()
