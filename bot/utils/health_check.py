import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psutil

logger = logging.getLogger(__name__)

class HealthChecker:
    """Production health monitoring system"""

    def __init__(self):
        self.status = "unknown"
        self.last_check = None
        self.checks = {}
        self.alert_thresholds = {
            'memory_percent': 85.0,
            'cpu_percent': 80.0,
            'disk_percent': 90.0,
            'response_time': 5.0  # seconds
        }
        self.check_interval = 60  # seconds
        self.running = False

    async def start_monitoring(self):
        """Start health monitoring"""
        self.running = True
        logger.info("🏥 Health monitoring started")

        while self.running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.check_interval)

    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        logger.info("🏥 Health monitoring stopped")

    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        start_time = time.time()

        try:
            # System resource check
            memory_check = await self.check_memory()
            cpu_check = await self.check_cpu()
            disk_check = await self.check_disk()

            # Database connectivity check
            db_check = await self.check_database()

            # Clone system check
            clone_check = await self.check_clone_system()

            # Calculate response time
            response_time = time.time() - start_time

            # Overall health status
            all_checks = [memory_check, cpu_check, disk_check, db_check, clone_check]

            if all(check['status'] == 'healthy' for check in all_checks):
                self.status = "healthy"
            elif any(check['status'] == 'critical' for check in all_checks):
                self.status = "critical"
            else:
                self.status = "degraded"

            self.last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            health_report = {
                'overall_status': self.status,
                'last_check': self.last_check,
                'response_time': response_time,
                'checks': {
                    'memory': memory_check,
                    'cpu': cpu_check,
                    'disk': disk_check,
                    'database': db_check,
                    'clone_system': clone_check
                }
            }

            # Log critical issues
            if self.status == "critical":
                logger.critical(f"Critical health issues detected: {health_report}")
            elif self.status == "degraded":
                logger.warning(f"System performance degraded: {health_report}")

            self.checks = health_report
            return health_report

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.status = "critical"
            return {
                'overall_status': 'critical',
                'error': str(e),
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    async def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            percent = memory.percent

            if percent > self.alert_thresholds['memory_percent']:
                status = 'critical'
            elif percent > (self.alert_thresholds['memory_percent'] - 15):
                status = 'degraded'
            else:
                status = 'healthy'

            return {
                'status': status,
                'percent': percent,
                'available_gb': round(memory.available / (1024**3), 2),
                'total_gb': round(memory.total / (1024**3), 2)
            }
        except Exception as e:
            return {'status': 'critical', 'error': str(e)}

    async def check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent > self.alert_thresholds['cpu_percent']:
                status = 'critical'
            elif cpu_percent > (self.alert_thresholds['cpu_percent'] - 20):
                status = 'degraded'
            else:
                status = 'healthy'

            return {
                'status': status,
                'percent': cpu_percent,
                'cores': psutil.cpu_count()
            }
        except Exception as e:
            return {'status': 'critical', 'error': str(e)}

    async def check_disk(self) -> Dict[str, Any]:
        """Check disk usage"""
        try:
            disk = psutil.disk_usage('/')
            percent = (disk.used / disk.total) * 100

            if percent > self.alert_thresholds['disk_percent']:
                status = 'critical'
            elif percent > (self.alert_thresholds['disk_percent'] - 15):
                status = 'degraded'
            else:
                status = 'healthy'

            return {
                'status': status,
                'percent': round(percent, 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'total_gb': round(disk.total / (1024**3), 2)
            }
        except Exception as e:
            return {'status': 'critical', 'error': str(e)}

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity with enhanced error detection"""
        from bot.logging import get_context_logger

        context_logger = get_context_logger(__name__).add_context(check_type="database")
        start_time = time.time()

        try:
            # Test database connection
            from bot.database.connection import db
            if db is not None:
                # Try a simple operation - correct method call
                try:
                    result = await db.command("ping")
                    return {
                        'status': 'healthy',
                        'connected': True,
                        'response_time': time.time() - start_time
                    }
                except Exception as ping_error:
                    raise Exception(f"Database ping failed: {ping_error}")
            else:
                raise Exception("Database connection is None")
        except Exception as e:
            error_msg = str(e)
            context_logger.error("Database health check exception", error=error_msg, error_type=type(e).__name__)
            return {
                'status': 'critical',
                'connected': False,
                'error': error_msg,
                'error_type': type(e).__name__
            }

    async def check_clone_system(self) -> Dict[str, Any]:
        """Check clone system health"""
        try:
            from clone_manager import clone_manager

            running_clones = len(clone_manager.get_running_clones())
            total_clones = len(clone_manager.active_clones)

            # Check if clone manager is responding
            start_time = time.time()
            clone_status = clone_manager.get_running_clones()
            response_time = time.time() - start_time

            if response_time > 2.0:
                status = 'degraded'
            else:
                status = 'healthy'

            return {
                'status': status,
                'running_clones': running_clones,
                'total_clones': total_clones,
                'response_time': round(response_time, 3)
            }
        except Exception as e:
            logger.error(f"Clone system health check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e)
            }

    def get_status(self) -> str:
        """Get current health status"""
        return self.status

    def get_last_check(self) -> Optional[str]:
        """Get last check timestamp"""
        return self.last_check

    def get_full_report(self) -> Dict[str, Any]:
        """Get full health report"""
        return self.checks

# Global instance
health_checker = HealthChecker()