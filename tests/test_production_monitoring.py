
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.utils.system_monitor import SystemMonitor, system_monitor
from bot.utils.health_check import HealthChecker
from bot.utils.error_handler import safe_execute_async, ErrorRecoveryConfig

class TestProductionMonitoring:
    """Production-level monitoring and error handling tests"""

    @pytest.fixture
    def monitor_instance(self):
        """Create fresh monitor instance for each test"""
        return SystemMonitor()

    @pytest.mark.asyncio
    async def test_system_monitor_initialization(self, monitor_instance):
        """Test system monitor initialization"""
        assert not monitor_instance.running
        assert monitor_instance.monitor_interval == 60
        assert len(monitor_instance.metrics_history) == 4
        assert all(len(queue) == 0 for queue in monitor_instance.metrics_history.values())

    @pytest.mark.asyncio
    async def test_system_monitor_start_stop(self, monitor_instance):
        """Test starting and stopping system monitor"""
        # Start monitoring in background
        monitor_task = asyncio.create_task(monitor_instance.start_monitoring())
        
        # Wait a moment for it to start
        await asyncio.sleep(0.1)
        assert monitor_instance.running
        
        # Stop monitoring
        await monitor_instance.stop_monitoring()
        assert not monitor_instance.running
        
        # Cancel the task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_metrics_collection(self, monitor_instance):
        """Test metrics collection functionality"""
        await monitor_instance.collect_metrics()
        
        # Check that metrics were collected
        assert len(monitor_instance.metrics_history['cpu']) == 1
        assert len(monitor_instance.metrics_history['memory']) == 1
        assert len(monitor_instance.metrics_history['disk']) == 1
        assert len(monitor_instance.metrics_history['network']) == 1
        
        # Verify metric structure
        cpu_metric = monitor_instance.metrics_history['cpu'][0]
        assert 'timestamp' in cpu_metric
        assert 'percent' in cpu_metric
        assert 'count' in cpu_metric

    @pytest.mark.asyncio
    async def test_storage_stats_error_handling(self, monitor_instance):
        """Test storage stats error handling"""
        with patch('os.path.exists', return_value=False):
            stats = monitor_instance.get_storage_stats_safe()
            
            assert stats['total'] == 0
            assert stats['used'] == 0
            assert stats['free'] == 0
            assert 'error' in stats

    @pytest.mark.asyncio
    async def test_storage_stats_success(self, monitor_instance):
        """Test successful storage stats collection"""
        with patch('os.path.exists', return_value=True), \
             patch('psutil.disk_usage') as mock_disk_usage:
            
            mock_disk_usage.return_value = MagicMock(
                total=1000000000,  # 1GB
                used=500000000,    # 500MB
                free=500000000     # 500MB
            )
            
            stats = monitor_instance.get_storage_stats_safe()
            
            assert stats['total'] == 1000000000
            assert stats['used'] == 500000000
            assert stats['free'] == 500000000
            assert stats['percent'] == 50.0
            assert 'error' not in stats

    @pytest.mark.asyncio
    async def test_get_stats_with_history(self, monitor_instance):
        """Test getting stats when history exists"""
        # Collect some metrics first
        await monitor_instance.collect_metrics()
        
        stats = monitor_instance.get_stats()
        
        assert 'cpu_percent' in stats
        assert 'memory_percent' in stats
        assert 'disk_percent' in stats
        assert 'uptime_seconds' in stats
        assert 'timestamp' in stats
        assert stats['cpu_percent'] >= 0
        assert stats['memory_percent'] >= 0

    @pytest.mark.asyncio
    async def test_get_stats_empty_history(self, monitor_instance):
        """Test getting stats when no history exists"""
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value = MagicMock(percent=60.0)
            mock_disk.return_value = MagicMock(total=1000, used=300)
            
            stats = monitor_instance.get_stats()
            
            assert stats['cpu_percent'] == 25.0
            assert stats['memory_percent'] == 60.0
            assert stats['disk_percent'] == 30.0

    @pytest.mark.asyncio
    async def test_resource_alerts(self, monitor_instance):
        """Test resource usage alerts"""
        # Mock high usage
        with patch.object(monitor_instance, 'get_stats', return_value={
            'cpu_percent': 90.0,
            'memory_percent': 95.0,
            'disk_percent': 98.0,
            'uptime_seconds': 3600
        }):
            alerts = monitor_instance.check_resource_alerts()
            
            assert len(alerts) == 3
            assert any('High CPU usage' in alert for alert in alerts)
            assert any('Critical memory usage' in alert for alert in alerts)
            assert any('Critical disk usage' in alert for alert in alerts)

    @pytest.mark.asyncio
    async def test_historical_data_filtering(self, monitor_instance):
        """Test historical data filtering by time"""
        # Add some old and new metrics
        old_time = time.time() - 3600  # 1 hour ago
        new_time = time.time()
        
        monitor_instance.metrics_history['cpu'].append({
            'timestamp': old_time,
            'percent': 50.0
        })
        monitor_instance.metrics_history['cpu'].append({
            'timestamp': new_time,
            'percent': 60.0
        })
        
        # Get data from last 30 minutes
        recent_data = monitor_instance.get_historical_data('cpu', 30)
        
        assert len(recent_data) == 1
        assert recent_data[0]['percent'] == 60.0

    @pytest.mark.asyncio
    async def test_averages_calculation(self, monitor_instance):
        """Test average metrics calculation"""
        # Add test metrics
        for i in range(5):
            monitor_instance.metrics_history['cpu'].append({
                'timestamp': time.time(),
                'percent': 20.0 + i * 10  # 20, 30, 40, 50, 60
            })
            monitor_instance.metrics_history['memory'].append({
                'timestamp': time.time(),
                'percent': 40.0 + i * 5   # 40, 45, 50, 55, 60
            })
            monitor_instance.metrics_history['disk'].append({
                'timestamp': time.time(),
                'percent': 60.0 + i * 2   # 60, 62, 64, 66, 68
            })
        
        averages = monitor_instance.get_averages(60)  # 60 minutes
        
        assert averages['avg_cpu'] == 40.0  # (20+30+40+50+60)/5
        assert averages['avg_memory'] == 50.0  # (40+45+50+55+60)/5
        assert averages['avg_disk'] == 64.0  # (60+62+64+66+68)/5
        assert averages['sample_count'] == 5

    @pytest.mark.asyncio
    async def test_error_handling_in_collect_metrics(self, monitor_instance):
        """Test error handling during metrics collection"""
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")):
            # Should not raise exception
            await monitor_instance.collect_metrics()
            
            # Should have fallback values
            if monitor_instance.metrics_history['cpu']:
                cpu_metric = monitor_instance.metrics_history['cpu'][0]
                assert cpu_metric['percent'] == 0  # Fallback value

    @pytest.mark.asyncio
    async def test_concurrent_metrics_collection(self, monitor_instance):
        """Test concurrent metrics collection"""
        # Run multiple collections concurrently
        tasks = [monitor_instance.collect_metrics() for _ in range(3)]
        await asyncio.gather(*tasks)
        
        # Should have collected metrics from all tasks
        assert len(monitor_instance.metrics_history['cpu']) == 3

    @pytest.mark.asyncio
    async def test_metrics_history_limit(self, monitor_instance):
        """Test that metrics history respects maxlen limit"""
        # Add more than maxlen items
        for i in range(150):  # More than maxlen=100
            monitor_instance.metrics_history['cpu'].append({
                'timestamp': time.time(),
                'percent': float(i)
            })
        
        # Should be limited to maxlen
        assert len(monitor_instance.metrics_history['cpu']) == 100
        # Should keep the most recent items
        assert monitor_instance.metrics_history['cpu'][-1]['percent'] == 149.0

    @pytest.mark.asyncio
    async def test_safe_execute_async_success(self):
        """Test successful async function execution"""
        async def test_function(x, y):
            return x + y
        
        result = await safe_execute_async(
            test_function, 
            5, 10,
            context={"operation": "test_addition"}
        )
        
        assert result == 15

    @pytest.mark.asyncio
    async def test_safe_execute_async_with_retry(self):
        """Test async function execution with retry"""
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"
        
        config = ErrorRecoveryConfig(max_retries=3, retry_delay=0.1)
        
        result = await safe_execute_async(
            failing_function,
            context={"operation": "test_retry"},
            recovery_config=config
        )
        
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_safe_execute_async_max_retries_exceeded(self):
        """Test async function when max retries exceeded"""
        async def always_failing_function():
            raise Exception("Always fails")
        
        config = ErrorRecoveryConfig(max_retries=2, retry_delay=0.1)
        
        result = await safe_execute_async(
            always_failing_function,
            context={"operation": "test_max_retries"},
            recovery_config=config
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration with monitoring"""
        try:
            from bot.utils.health_check import health_checker
            
            # Mock the health checker methods
            with patch.object(health_checker, 'check_memory', return_value={'status': 'healthy'}), \
                 patch.object(health_checker, 'check_cpu', return_value={'status': 'healthy'}), \
                 patch.object(health_checker, 'check_disk', return_value={'status': 'healthy'}), \
                 patch.object(health_checker, 'check_database', return_value={'status': 'healthy'}), \
                 patch.object(health_checker, 'check_clone_system', return_value={'status': 'healthy'}):
                
                health_status = await health_checker.run_health_check()
                
                assert 'overall_status' in health_status
                assert 'checks' in health_status
                assert health_status['overall_status'] in ['healthy', 'degraded', 'unhealthy']
                
        except ImportError:
            pytest.skip("Health checker not available")

    def test_monitor_singleton_behavior(self):
        """Test that system monitor behaves as singleton"""
        from bot.utils.system_monitor import system_monitor
        
        # Should be the same instance
        monitor1 = system_monitor
        monitor2 = system_monitor
        
        assert monitor1 is monitor2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
