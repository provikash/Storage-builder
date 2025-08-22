import asyncio
import psutil
import time
from datetime import datetime
from bot.logging import LOGGER
from clone_manager import clone_manager

logger = LOGGER(__name__)

class SystemMonitor:
    """Monitor system resources and bot performance"""

    def __init__(self):
        self.check_interval = 300  # Check every 5 minutes
        self.stats = {
            'uptime': datetime.now(),
            'total_memory': 0,
            'used_memory': 0,
            'cpu_percent': 0,
            'running_clones': 0
        }

    async def start_monitoring(self):
        """Start system monitoring"""
        logger.info("🖥️ Starting system monitoring...")

        while True:
            try:
                await self.collect_stats()
                await self.log_stats()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Error in system monitoring: {e}")
                await asyncio.sleep(60)

    async def collect_stats(self):
        """Collect system statistics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            self.stats['total_memory'] = memory.total
            self.stats['used_memory'] = memory.used
            self.stats['memory_percent'] = memory.percent

            # CPU usage
            self.stats['cpu_percent'] = psutil.cpu_percent(interval=1)

            # Running clones
            self.stats['running_clones'] = len(clone_manager.get_running_clones())

            # Uptime
            self.stats['uptime_seconds'] = (datetime.now() - self.stats['uptime']).total_seconds()

        except Exception as e:
            logger.error(f"❌ Error collecting system stats: {e}")

    async def log_stats(self):
        """Log system statistics"""
        try:
            logger.info(
                f"📊 System Stats - "
                f"Memory: {self.stats.get('memory_percent', 0):.1f}% | "
                f"CPU: {self.stats.get('cpu_percent', 0):.1f}% | "
                f"Clones: {self.stats.get('running_clones', 0)} | "
                f"Uptime: {self.stats.get('uptime_seconds', 0)/3600:.1f}h"
            )
        except Exception as e:
            logger.error(f"❌ Error logging stats: {e}")

    def get_stats(self):
        """Get current system statistics"""
        return self.stats.copy()

# Create global instance
system_monitor = SystemMonitor()