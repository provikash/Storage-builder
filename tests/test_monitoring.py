
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.system_monitor import SystemMonitor
from bot.utils.health_check import HealthChecker
from bot.utils.subscription_checker import SubscriptionChecker


class TestSystemMonitor:
    """Test system monitoring functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.monitor = SystemMonitor()

    @pytest.mark.asyncio
    async def test_collect_stats(self):
        """Test system stats collection"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                total=1000000000,
                used=300000000,
                percent=30.0
            )
            
            with patch('psutil.cpu_percent') as mock_cpu:
                mock_cpu.return_value = 25.5
                
                with patch('clone_manager.clone_manager') as mock_clone_manager:
                    mock_clone_manager.get_running_clones.return_value = ["123", "456"]
                    
                    await self.monitor.collect_stats()
                    
                    assert self.monitor.stats['memory_percent'] == 30.0
                    assert self.monitor.stats['cpu_percent'] == 25.5
                    assert self.monitor.stats['running_clones'] == 2

    def test_get_stats(self):
        """Test getting current stats"""
        self.monitor.stats = {
            'memory_percent': 30.0,
            'cpu_percent': 25.5,
            'running_clones': 2
        }
        
        stats = self.monitor.get_stats()
        assert stats['memory_percent'] == 30.0
        assert stats['cpu_percent'] == 25.5
        assert stats['running_clones'] == 2


class TestHealthChecker:
    """Test health checking functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.health_checker = HealthChecker()

    @pytest.mark.asyncio
    async def test_perform_health_check_healthy(self):
        """Test health check when system is healthy"""
        with patch('bot.utils.health_check.get_clone_statistics') as mock_stats:
            mock_stats.return_value = {"total": 5}
            
            with patch('bot.utils.health_check.get_subscription_stats') as mock_sub_stats:
                mock_sub_stats.return_value = {"active": 3}
                
                with patch('bot.utils.health_check.clone_manager') as mock_clone_manager:
                    mock_clone_manager.get_running_clones.return_value = ["123", "456"]
                    
                    with patch('bot.utils.health_check.get_all_clones') as mock_all_clones:
                        mock_all_clones.return_value = [
                            {"status": "active"}, 
                            {"status": "active"}
                        ]
                        
                        await self.health_checker.perform_health_check()
                        
                        assert self.health_checker.status == "healthy"

    @pytest.mark.asyncio
    async def test_perform_health_check_degraded(self):
        """Test health check when system has issues"""
        with patch('bot.utils.health_check.get_clone_statistics') as mock_stats:
            mock_stats.side_effect = Exception("Database error")
            
            await self.health_checker.perform_health_check()
            
            assert self.health_checker.status == "degraded"

    def test_get_status(self):
        """Test getting health status"""
        self.health_checker.status = "healthy"
        self.health_checker.last_check = datetime.now()
        
        status = self.health_checker.get_status()
        assert status["status"] == "healthy"
        assert "last_check" in status


class TestSubscriptionChecker:
    """Test subscription checking functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.sub_checker = SubscriptionChecker()

    @pytest.mark.asyncio
    async def test_check_subscriptions(self):
        """Test subscription checking"""
        with patch('bot.utils.subscription_checker.check_expired_subscriptions') as mock_check:
            mock_check.return_value = ["123456"]
            
            with patch.object(self.sub_checker, 'handle_expired_subscription') as mock_handle:
                mock_handle.return_value = None
                
                await self.sub_checker.check_subscriptions()
                mock_handle.assert_called_with("123456")

    @pytest.mark.asyncio
    async def test_handle_expired_subscription(self):
        """Test handling expired subscription"""
        with patch('bot.utils.subscription_checker.deactivate_clone') as mock_deactivate:
            mock_deactivate.return_value = True
            
            with patch('bot.utils.subscription_checker.clone_manager') as mock_clone_manager:
                mock_clone_manager.stop_clone.return_value = True
                
                await self.sub_checker.handle_expired_subscription("123456")
                mock_deactivate.assert_called_with("123456")

    @pytest.mark.asyncio
    async def test_is_subscription_active(self):
        """Test checking if subscription is active"""
        mock_subscription = {
            "status": "active",
            "expiry_date": datetime.now().replace(year=2025)
        }
        
        with patch('bot.utils.subscription_checker.get_subscription') as mock_get:
            mock_get.return_value = mock_subscription
            
            is_active = await self.sub_checker.is_subscription_active("123456:ABC")
            assert is_active == True
