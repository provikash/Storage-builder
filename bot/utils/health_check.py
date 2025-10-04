import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psutil

from bot.logging import LOGGER

logger = LOGGER(__name__)

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
        """Check database connectivity and performance"""
        try:
            start_time = time.time()

            # Database connection test with proper error handling
            from bot.database.connection import get_database
            
            try:
                db = await asyncio.wait_for(get_database(), timeout=5.0)
                if db is None:
                    return {
                        'status': 'unhealthy',
                        'connected': False,
                        'error': 'Failed to get database connection'
                    }
            except asyncio.TimeoutError:
                return {
                    'status': 'unhealthy',
                    'connected': False,
                    'error': 'Database connection timeout'
                }

            # Test database operations with multiple checks
            checks = []
            
            # 1. List collections test
            try:
                collections = await asyncio.wait_for(db.list_collection_names(), timeout=10.0)
                checks.append(('collections_list', True, len(collections)))
            except asyncio.TimeoutError:
                checks.append(('collections_list', False, 'timeout'))
            except Exception as e:
                checks.append(('collections_list', False, str(e)))
            
            # 2. Simple query test
            try:
                result = await asyncio.wait_for(
                    db.clones.count_documents({}), 
                    timeout=5.0
                )
                checks.append(('count_query', True, result))
            except asyncio.TimeoutError:
                checks.append(('count_query', False, 'timeout'))
            except Exception as e:
                checks.append(('count_query', False, str(e)))
            
            # 3. Write test (if possible)
            try:
                test_doc = {'_id': 'health_check', 'timestamp': time.time()}
                await asyncio.wait_for(
                    db.health_checks.replace_one(
                        {'_id': 'health_check'}, 
                        test_doc, 
                        upsert=True
                    ), 
                    timeout=5.0
                )
                checks.append(('write_test', True, 'success'))
            except asyncio.TimeoutError:
                checks.append(('write_test', False, 'timeout'))
            except Exception as e:
                checks.append(('write_test', False, str(e)))

            response_time = time.time() - start_time
            
            # Determine overall status
            failed_checks = [c for c in checks if not c[1]]
            if len(failed_checks) >= 2:
                status = 'unhealthy'
            elif len(failed_checks) == 1:
                status = 'degraded'
            else:
                status = 'healthy'

            if response_time > 5.0:
                return {
                    'status': 'degraded',
                    'connected': True,
                    'response_time': response_time,
                    'warning': 'Slow database response'
                }
            elif response_time > 2.0:
                return {
                    'status': 'degraded',
                    'connected': True,
                    'response_time': response_time,
                    'warning': 'Moderate database response time'
                }
            else:
                return {
                    'status': 'healthy',
                    'connected': True,
                    'response_time': response_time
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e),
                'response_time': 0
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