
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.clone_config_loader import CloneConfigLoader


class TestConfigLoader:
    """Test configuration loading functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.config_loader = CloneConfigLoader()

    @pytest.mark.asyncio
    async def test_load_clone_config(self):
        """Test loading clone configuration"""
        mock_config = {
            "bot_id": "123456",
            "admin_id": 789,
            "features": {
                "search": True,
                "upload": True,
                "token_verification": True
            }
        }
        
        with patch('bot.database.clone_db.get_clone_config') as mock_get:
            mock_get.return_value = mock_config
            
            config = await self.config_loader.load_config("123456")
            assert config["bot_id"] == "123456"
            assert config["admin_id"] == 789

    @pytest.mark.asyncio
    async def test_save_clone_config(self):
        """Test saving clone configuration"""
        config_data = {
            "bot_id": "123456",
            "features": {"search": True}
        }
        
        with patch('bot.database.clone_db.update_clone_config') as mock_update:
            mock_update.return_value = True
            
            result = await self.config_loader.save_config("123456", config_data)
            assert result == True

    def test_validate_config(self):
        """Test configuration validation"""
        valid_config = {
            "bot_id": "123456",
            "admin_id": 789,
            "features": {"search": True}
        }
        
        is_valid = self.config_loader.validate_config(valid_config)
        assert is_valid == True

    def test_get_default_config(self):
        """Test getting default configuration"""
        default_config = self.config_loader.get_default_config()
        
        assert "features" in default_config
        assert "token_settings" in default_config
        assert "channels" in default_config
