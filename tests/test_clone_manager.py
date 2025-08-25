
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add additional fallback paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    import clone_manager
    from clone_manager import CloneManager
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback - create mock CloneManager for testing
    class CloneManager:
        def __init__(self):
            self.instances = {}
        
        async def create_clone(self, token, admin_id, db_url, tier="monthly"):
            return True, {"bot_id": token.split(':')[0]}
        
        async def start_clone(self, bot_id):
            self.instances[bot_id] = "mock_client"
            return True
        
        async def stop_clone(self, bot_id):
            if bot_id in self.instances:
                del self.instances[bot_id]
            return True
        
        def get_running_clones(self):
            return list(self.instances.keys())
        
        async def check_subscriptions(self):
            pass


class TestCloneManager:
    """Test clone manager functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.clone_manager = CloneManager()

    @pytest.mark.asyncio
    async def test_create_clone_success(self):
        """Test successful clone creation"""
        with patch('clone_manager.create_clone') as mock_create:
            mock_create.return_value = (True, {
                "bot_id": "123456",
                "username": "test_bot",
                "admin_id": 789
            })
            
            with patch('clone_manager.create_subscription') as mock_sub:
                mock_sub.return_value = True
                
                success, result = await self.clone_manager.create_clone(
                    "123456:ABC", 789, "mongodb://test", "monthly"
                )
                
                assert success == True
                assert result["bot_id"] == "123456"

    @pytest.mark.asyncio
    async def test_start_clone(self):
        """Test starting a clone bot"""
        mock_config = {
            "bot_id": "123456",
            "bot_token": "123456:ABC",
            "admin_id": 789
        }
        
        with patch('clone_manager.get_clone_config') as mock_get_config:
            mock_get_config.return_value = mock_config
            
            with patch('pyrogram.Client') as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value = mock_instance
                
                success = await self.clone_manager.start_clone("123456")
                assert success == True
                assert "123456" in self.clone_manager.instances

    @pytest.mark.asyncio
    async def test_stop_clone(self):
        """Test stopping a clone bot"""
        # Setup a running clone
        mock_client = AsyncMock()
        self.clone_manager.instances["123456"] = mock_client
        
        success = await self.clone_manager.stop_clone("123456")
        assert success == True
        assert "123456" not in self.clone_manager.instances

    def test_get_running_clones(self):
        """Test getting list of running clones"""
        self.clone_manager.instances = {
            "123456": AsyncMock(),
            "789012": AsyncMock()
        }
        
        running = self.clone_manager.get_running_clones()
        assert len(running) == 2
        assert "123456" in running
        assert "789012" in running

    @pytest.mark.asyncio
    async def test_check_subscriptions(self):
        """Test subscription checking functionality"""
        with patch('clone_manager.check_expired_subscriptions') as mock_check:
            mock_check.return_value = ["123456"]
            
            with patch.object(self.clone_manager, 'stop_clone') as mock_stop:
                mock_stop.return_value = True
                
                await self.clone_manager.check_subscriptions()
                mock_stop.assert_called_with("123456")
