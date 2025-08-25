
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestPerformance:
    """Performance tests for system components"""
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance"""
        start_time = time.time()
        
        with patch('bot.database.clone_db.clones_collection') as mock_collection:
            mock_collection.find.return_value.to_list.return_value = [
                {"bot_id": f"bot_{i}", "status": "active"} for i in range(100)
            ]
            
            from bot.database.clone_db import get_all_clones
            clones = await get_all_clones()
            
            end_time = time.time()
            query_time = end_time - start_time
            
            assert len(clones) == 100
            assert query_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_clone_manager_bulk_operations(self):
        """Test clone manager handling multiple operations"""
        from clone_manager import CloneManager
        manager = CloneManager()
        
        start_time = time.time()
        
        # Mock multiple clone configs
        with patch('clone_manager.get_clone_config') as mock_config:
            mock_config.return_value = {
                "bot_id": "123456",
                "bot_token": "123456:ABC",
                "admin_id": 789
            }
            
            with patch('pyrogram.Client') as mock_client:
                mock_client.return_value = AsyncMock()
                
                # Start multiple clones
                tasks = []
                for i in range(10):
                    tasks.append(manager.start_clone(f"bot_{i}"))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                operation_time = end_time - start_time
                
                assert operation_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_subscription_checker_performance(self):
        """Test subscription checker performance with many subscriptions"""
        from bot.utils.subscription_checker import SubscriptionChecker
        checker = SubscriptionChecker()
        
        start_time = time.time()
        
        # Mock many expired subscriptions
        with patch('bot.utils.subscription_checker.check_expired_subscriptions') as mock_check:
            mock_check.return_value = [f"bot_{i}" for i in range(50)]
            
            with patch('bot.utils.subscription_checker.deactivate_clone') as mock_deactivate:
                mock_deactivate.return_value = True
                
                with patch('bot.utils.subscription_checker.clone_manager') as mock_manager:
                    mock_manager.stop_clone.return_value = True
                    
                    await checker.check_subscriptions()
                    
                    end_time = time.time()
                    check_time = end_time - start_time
                    
                    assert check_time < 10.0  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Test memory usage doesn't grow excessively"""
        from bot.utils.system_monitor import SystemMonitor
        monitor = SystemMonitor()
        
        with patch('psutil.virtual_memory') as mock_memory:
            initial_memory = 500000000  # 500MB
            mock_memory.return_value = MagicMock(
                total=1000000000,
                used=initial_memory,
                percent=50.0
            )
            
            with patch('psutil.cpu_percent') as mock_cpu:
                mock_cpu.return_value = 25.0
                
                with patch('clone_manager.clone_manager') as mock_manager:
                    mock_manager.get_running_clones.return_value = []
                    
                    # Collect stats multiple times
                    for _ in range(10):
                        await monitor.collect_stats()
                        await asyncio.sleep(0.1)
                    
                    # Memory usage should remain stable
                    assert monitor.stats['memory_percent'] <= 60.0

    def test_concurrent_requests_handling(self):
        """Test handling multiple concurrent requests"""
        async def mock_request():
            await asyncio.sleep(0.1)
            return True
        
        async def test_concurrent():
            start_time = time.time()
            
            # Simulate 20 concurrent requests
            tasks = [mock_request() for _ in range(20)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            assert len(results) == 20
            assert all(results)
            assert total_time < 2.0  # Should handle concurrency efficiently
        
        asyncio.run(test_concurrent())
