import asyncio
import logging
import time
import psutil
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Production system monitoring with metrics collection"""

    def __init__(self):
        self.metrics_history = {
            'cpu': deque(maxlen=100),
            'memory': deque(maxlen=100),
            'disk': deque(maxlen=100),
            'network': deque(maxlen=100)
        }
        self.start_time = time.time()
        self.running = False
        self.monitor_interval = 60  # seconds - increased from 30 to reduce CPU usage

    async def start_monitoring(self):
        """Start system monitoring"""
        self.running = True
        logger.info("📊 System monitoring started")

        while self.running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(self.monitor_interval)

    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.running = False
        logger.info("📊 System monitoring stopped")

    async def collect_metrics(self):
        """Collect system metrics with error recovery"""
        from bot.utils.error_handler import safe_execute_async, ErrorRecoveryConfig
        from bot.logging import get_context_logger

        context_logger = get_context_logger(__name__).add_context(operation="collect_metrics")

        try:
            timestamp = time.time()

            # CPU metrics with fallback - reduced interval to lower CPU usage
            async def get_cpu_metrics():
                cpu_percent = psutil.cpu_percent(interval=0.1)  # Reduced from 1 second
                cpu_count = psutil.cpu_count()
                load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
                return cpu_percent, cpu_count, load_avg

            cpu_data = await safe_execute_async(
                get_cpu_metrics,
                config=ErrorRecoveryConfig(
                    max_retries=2,
                    retry_delay=0.5,
                    fallback_value=(0, 1, (0, 0, 0)),
                    log_errors=True
                ),
                context={"metric_type": "cpu"}
            )

            cpu_percent, cpu_count, load_avg = cpu_data

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()

            # Network metrics
            network = psutil.net_io_counters()

            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()

            # Get storage stats safely
            storage_stats = await self.get_storage_stats_safe()

            # Store metrics
            cpu_metric = {
                'timestamp': timestamp,
                'percent': cpu_percent,
                'count': cpu_count,
                'load_avg': load_avg,
                'process_cpu': process_cpu
            }

            memory_metric = {
                'timestamp': timestamp,
                'percent': memory.percent,
                'available': memory.available,
                'total': memory.total,
                'swap_percent': swap.percent,
                'process_memory': process_memory.rss
            }

            disk_metric = {
                'timestamp': timestamp,
                'percent': (disk.used / disk.total) * 100,
                'free': disk.free,
                'total': disk.total,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0
            }

            network_metric = {
                'timestamp': timestamp,
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }

            # Add to history
            self.metrics_history['cpu'].append(cpu_metric)
            self.metrics_history['memory'].append(memory_metric)
            self.metrics_history['disk'].append(disk_metric)
            self.metrics_history['network'].append(network_metric)

            # Log warnings for high usage
            if cpu_percent > 80:
                logger.warning(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 85:
                logger.warning(f"High memory usage: {memory.percent}%")
            if (disk.used / disk.total) * 100 > 90:
                logger.warning(f"High disk usage: {(disk.used / disk.total) * 100:.1f}%")

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

    async def get_storage_stats_safe(self) -> Dict[str, Any]:
        """Get storage statistics with error handling"""
        try:
            from info import Config
            # Try multiple path options in order of preference
            path_options = [
                getattr(Config, 'TEMP_PATH', None),
                getattr(Config, 'STORAGE_PATH', None),
                '/tmp',
                '.'
            ]
            
            storage_path = None
            for path in path_options:
                if path and os.path.exists(path):
                    storage_path = path
                    break
            
            if storage_path:
                storage_usage = psutil.disk_usage(storage_path)
                return {
                    'total': storage_usage.total,
                    'used': storage_usage.used,
                    'free': storage_usage.free,
                    'percent': (storage_usage.used / storage_usage.total) * 100,
                    'path': storage_path
                }
            else:
                return {
                    'total': 0,
                    'used': 0,
                    'free': 0,
                    'percent': 0,
                    'error': 'No valid storage path found'
                }
        except Exception as e:
            logger.warning(f"Could not get storage stats: {e}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent': 0,
                'error': str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            # Get latest metrics or calculate current ones
            if self.metrics_history['cpu']:
                latest_cpu = self.metrics_history['cpu'][-1]
                latest_memory = self.metrics_history['memory'][-1]
                latest_disk = self.metrics_history['disk'][-1]
            else:
                # Calculate current metrics if history is empty
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                latest_cpu = {'percent': cpu_percent}
                latest_memory = {'percent': memory.percent}
                latest_disk = {'percent': (disk.used / disk.total) * 100}

            uptime_seconds = time.time() - self.start_time

            return {
                'cpu_percent': latest_cpu.get('percent', 0),
                'memory_percent': latest_memory.get('percent', 0),
                'disk_percent': latest_disk.get('percent', 0),
                'uptime_seconds': uptime_seconds,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'uptime_seconds': 0,
                'error': str(e)
            }

    def get_historical_data(self, metric_type: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        if metric_type not in self.metrics_history:
            return []

        cutoff_time = time.time() - (minutes * 60)
        return [
            metric for metric in self.metrics_history[metric_type]
            if metric['timestamp'] > cutoff_time
        ]

    def get_averages(self, minutes: int = 30) -> Dict[str, float]:
        """Get average metrics over specified time period"""
        try:
            cutoff_time = time.time() - (minutes * 60)

            cpu_values = [
                m['percent'] for m in self.metrics_history['cpu']
                if m['timestamp'] > cutoff_time
            ]

            memory_values = [
                m['percent'] for m in self.metrics_history['memory']
                if m['timestamp'] > cutoff_time
            ]

            disk_values = [
                m['percent'] for m in self.metrics_history['disk']
                if m['timestamp'] > cutoff_time
            ]

            return {
                'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
                'avg_disk': sum(disk_values) / len(disk_values) if disk_values else 0,
                'sample_count': len(cpu_values)
            }
        except Exception as e:
            logger.error(f"Failed to calculate averages: {e}")
            return {'avg_cpu': 0, 'avg_memory': 0, 'avg_disk': 0, 'sample_count': 0}

    def check_resource_alerts(self) -> List[str]:
        """Check for resource usage alerts"""
        alerts = []

        try:
            current_stats = self.get_stats()

            if current_stats['cpu_percent'] > 85:
                alerts.append(f"⚠️ High CPU usage: {current_stats['cpu_percent']:.1f}%")

            if current_stats['memory_percent'] > 90:
                alerts.append(f"🔴 Critical memory usage: {current_stats['memory_percent']:.1f}%")
            elif current_stats['memory_percent'] > 80:
                alerts.append(f"⚠️ High memory usage: {current_stats['memory_percent']:.1f}%")

            if current_stats['disk_percent'] > 95:
                alerts.append(f"🔴 Critical disk usage: {current_stats['disk_percent']:.1f}%")
            elif current_stats['disk_percent'] > 85:
                alerts.append(f"⚠️ High disk usage: {current_stats['disk_percent']:.1f}%")

        except Exception as e:
            alerts.append(f"❌ Error checking resources: {e}")

        return alerts

# Global instance
system_monitor = SystemMonitor()