
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_clone_creation_workflow(self):
        """Test complete clone creation workflow"""
        # Mock successful bot validation
        with patch('pyrogram.Client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.get_me.return_value = MagicMock(id=123456, username="test_bot")
            
            # Mock database operations
            with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_motor:
                mock_db_client = AsyncMock()
                mock_motor.return_value = mock_db_client
                mock_db_client.admin.command.return_value = {"ok": 1}
                
                # Mock clone database
                with patch('bot.database.clone_db.clones_collection') as mock_clones:
                    mock_clones.find_one.return_value = None
                    mock_clones.insert_one.return_value = AsyncMock()
                    
                    # Mock subscription creation
                    with patch('bot.database.subscription_db.subscriptions_collection') as mock_subs:
                        mock_subs.insert_one.return_value = AsyncMock()
                        
                        # Import and test
                        from clone_manager import CloneManager
                        manager = CloneManager()
                        
                        success, result = await manager.create_clone(
                            "123456:ABC", 789, "mongodb://test", "monthly"
                        )
                        
                        assert success == True
                        assert "bot_id" in result

    @pytest.mark.asyncio
    async def test_subscription_expiry_workflow(self):
        """Test subscription expiry handling workflow"""
        from bot.utils.subscription_checker import SubscriptionChecker
        from clone_manager import CloneManager
        
        checker = SubscriptionChecker()
        manager = CloneManager()
        
        # Setup expired subscription
        with patch('bot.utils.subscription_checker.check_expired_subscriptions') as mock_check:
            mock_check.return_value = ["123456"]
            
            with patch('bot.utils.subscription_checker.deactivate_clone') as mock_deactivate:
                mock_deactivate.return_value = True
                
                with patch.object(manager, 'stop_clone') as mock_stop:
                    mock_stop.return_value = True
                    
                    # Patch the clone_manager import in subscription_checker
                    with patch('bot.utils.subscription_checker.clone_manager', manager):
                        await checker.check_subscriptions()
                        
                        mock_deactivate.assert_called_with("123456")
                        mock_stop.assert_called_with("123456")

    @pytest.mark.asyncio
    async def test_health_monitoring_workflow(self):
        """Test health monitoring workflow"""
        from bot.utils.health_check import HealthChecker
        
        checker = HealthChecker()
        
        # Mock healthy system
        with patch('bot.utils.health_check.get_clone_statistics') as mock_stats:
            mock_stats.return_value = {"total": 5}
            
            with patch('bot.utils.health_check.get_subscription_stats') as mock_sub_stats:
                mock_sub_stats.return_value = {"active": 3}
                
                with patch('bot.utils.health_check.clone_manager') as mock_manager:
                    mock_manager.get_running_clones.return_value = ["123", "456"]
                    
                    with patch('bot.utils.health_check.get_all_clones') as mock_all:
                        mock_all.return_value = [
                            {"status": "active"}, 
                            {"status": "active"}
                        ]
                        
                        await checker.perform_health_check()
                        
                        status = checker.get_status()
                        assert status["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_system_startup_workflow(self):
        """Test system startup workflow"""
        # Mock all required components
        with patch('bot.database.subscription_db.init_pricing_tiers') as mock_init:
            mock_init.return_value = None
            
            with patch('bot.database.clone_db.get_global_about') as mock_about:
                mock_about.return_value = "Default about"
                
                with patch('pyrogram.Client') as mock_client:
                    mock_instance = AsyncMock()
                    mock_client.return_value = mock_instance
                    mock_instance.get_me.return_value = MagicMock(username="test_bot")
                    
                    # Import main functions
                    from main import check_requirements, initialize_databases
                    
                    # Test requirements check
                    with patch('pathlib.Path.exists') as mock_exists:
                        mock_exists.return_value = True
                        
                        result = await check_requirements()
                        assert result == True
                    
                    # Test database initialization
                    result = await initialize_databases()
                    assert result == True
