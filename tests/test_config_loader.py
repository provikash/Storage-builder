
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.clone_config_loader import CloneConfigLoader


class TestCloneConfigLoader:
    """Test clone configuration loading"""
    
    def setup_method(self):
        """Setup for each test"""
        self.config_loader = CloneConfigLoader()

    @pytest.mark.asyncio
    async def test_get_mother_bot_config(self):
        """Test getting mother bot configuration"""
        with patch('info.Config') as mock_config:
            mock_config.BOT_TOKEN = "123456:ABC"
            mock_config.ADMINS = [789]
            
            config = await self.config_loader.get_mother_bot_config()
            
            assert config["bot_info"]["is_mother_bot"] == True
            assert config["permissions"]["can_create_clones"] == True

    @pytest.mark.asyncio
    async def test_get_clone_config_active_subscription(self):
        """Test getting clone config with active subscription"""
        mock_clone_config = {
            "bot_id": "123456",
            "admin_id": 789,
            "features": {"search": True, "upload": True}
        }
        
        mock_subscription = {
            "status": "active",
            "tier": "monthly",
            "expiry_date": datetime.now() + timedelta(days=30)
        }
        
        with patch('bot.utils.clone_config_loader.get_clone_config') as mock_get_config:
            mock_get_config.return_value = mock_clone_config
            
            with patch('bot.utils.clone_config_loader.get_subscription') as mock_get_sub:
                mock_get_sub.return_value = mock_subscription
                
                with patch('bot.utils.clone_config_loader.get_clone_data') as mock_get_data:
                    mock_get_data.return_value = {"admin_id": 789}
                    
                    config = await self.config_loader.get_bot_config("123456:ABC")
                    
                    assert config["subscription"]["active"] == True
                    assert config["permissions"]["can_use_bot"] == True

    @pytest.mark.asyncio
    async def test_get_clone_config_expired_subscription(self):
        """Test getting clone config with expired subscription"""
        mock_subscription = {
            "status": "expired",
            "tier": "monthly",
            "expiry_date": datetime.now() - timedelta(days=1)
        }
        
        with patch('bot.utils.clone_config_loader.get_subscription') as mock_get_sub:
            mock_get_sub.return_value = mock_subscription
            
            with patch('bot.utils.clone_config_loader.get_clone_config') as mock_get_config:
                mock_get_config.return_value = None
                
            with patch('bot.utils.clone_config_loader.get_clone_data') as mock_get_data:
                mock_get_data.return_value = None
                
                config = await self.config_loader.get_bot_config("123456:ABC")
                
                assert config["subscription"]["active"] == False
                assert config["permissions"]["can_use_bot"] == False

    def test_get_default_features(self):
        """Test getting default features"""
        features = self.config_loader._get_default_features()
        
        assert features["search"] == True
        assert features["upload"] == True
        assert features["clone_creation"] == False
        assert features["admin_panel"] == False

    def test_get_clone_permissions_active(self):
        """Test getting permissions for active subscription"""
        permissions = self.config_loader._get_clone_permissions(True)
        
        assert permissions["can_use_bot"] == True
        assert permissions["can_upload"] == True
        assert permissions["unlimited_access"] == False

    def test_get_clone_permissions_inactive(self):
        """Test getting permissions for inactive subscription"""
        permissions = self.config_loader._get_clone_permissions(False)
        
        assert permissions["can_use_bot"] == False
