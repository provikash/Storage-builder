
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import tempfile
import os

from clone_manager import CloneManager
from bot.database.connection_manager import DatabaseManager
from bot.utils.security import SecurityManager
from bot.utils.file_manager import FileManager
from info import Config

class TestIntegration:
    """Integration tests for the Storage Builder system"""
    
    @pytest.fixture
    async def setup_environment(self):
        """Set up test environment"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.temp_dir, "storage")
        self.temp_storage_dir = os.path.join(self.temp_dir, "temp")
        
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.temp_storage_dir, exist_ok=True)
        
        # Mock configuration
        Config.STORAGE_PATH = self.storage_dir
        Config.TEMP_PATH = self.temp_storage_dir
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.clone_manager = CloneManager()
        self.security_manager = SecurityManager()
        self.file_manager = FileManager()
        
        yield
        
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_database_connection_and_retry(self, setup_environment):
        """Test database connection with retry logic"""
        # Mock connection failure then success
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            # First call fails, second succeeds
            mock_instance = Mock()
            mock_instance.admin.command = AsyncMock(side_effect=[
                Exception("Connection failed"),
                {"ok": 1}  # Success response
            ])
            mock_client.return_value = mock_instance
            
            # Should eventually succeed after retry
            result = await self.db_manager.connect()
            assert result is True
            assert mock_instance.admin.command.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_clone_lifecycle(self, setup_environment):
        """Test complete clone lifecycle"""
        bot_id = "test_clone_123"
        
        # Mock database operations
        with patch('clone_manager.get_clone') as mock_get_clone, \
             patch('clone_manager.get_subscription') as mock_get_subscription, \
             patch('clone_manager.start_clone_in_db') as mock_start_db, \
             patch('pyrogram.Client') as mock_client:
            
            # Setup mocks
            mock_get_clone.return_value = {
                '_id': bot_id,
                'bot_token': 'test_token',
                'owner_id': 123456
            }
            
            mock_get_subscription.return_value = {
                'bot_id': bot_id,
                'status': 'active',
                'expires_at': datetime.now() + timedelta(days=30)
            }
            
            mock_client_instance = Mock()
            mock_client_instance.start = AsyncMock()
            mock_client_instance.get_me = AsyncMock(return_value=Mock(username='test_bot'))
            mock_client_instance.is_connected = True
            mock_client.return_value = mock_client_instance
            
            # Test clone start
            success, message = await self.clone_manager.start_clone(bot_id)
            assert success is True
            assert bot_id in self.clone_manager.active_clones
            
            # Test clone stop
            success, message = await self.clone_manager.stop_clone(bot_id)
            assert success is True
            assert bot_id not in self.clone_manager.active_clones
    
    @pytest.mark.asyncio
    async def test_security_rate_limiting(self, setup_environment):
        """Test security rate limiting functionality"""
        user_id = 12345
        action = "test_action"
        
        # Test normal usage (should not be rate limited)
        for i in range(Config.MAX_REQUESTS_PER_MINUTE - 1):
            assert not self.security_manager.is_rate_limited(user_id, action)
        
        # Next request should trigger rate limit
        assert self.security_manager.is_rate_limited(user_id, action)
        
        # Test user blocking
        self.security_manager.block_user(user_id, 1)  # Block for 1 minute
        assert self.security_manager.is_blocked(user_id)
    
    @pytest.mark.asyncio
    async def test_file_management_workflow(self, setup_environment):
        """Test file upload and management workflow"""
        # Mock message with file
        mock_message = Mock()
        mock_message.id = 123
        mock_message.document = Mock()
        mock_message.document.file_name = "test_file.txt"
        mock_message.document.file_size = 1024
        mock_message.document.mime_type = "text/plain"
        mock_message.caption = "Test file description"
        mock_message.download = AsyncMock(return_value="temp_file_path")
        
        # Mock file content
        test_content = b"Test file content"
        
        with patch('aiofiles.open', mock_open_async(test_content)), \
             patch('os.rename') as mock_rename:
            
            # Test file storage
            result = await self.file_manager.store_file(mock_message, 12345)
            assert result is not None
            assert 'file_id' in result
            assert result['filename'] == "test_file.txt"
            assert result['owner_id'] == 12345
    
    @pytest.mark.asyncio
    async def test_subscription_validation(self, setup_environment):
        """Test subscription validation logic"""
        # Test active subscription
        subscription = {
            'status': 'active',
            'expires_at': datetime.now() + timedelta(days=10),
            'payment_verified': True
        }
        
        is_valid, message = await self.clone_manager._validate_subscription(subscription, "test_bot")
        assert is_valid is True
        
        # Test expired subscription
        subscription['expires_at'] = datetime.now() - timedelta(days=1)
        is_valid, message = await self.clone_manager._validate_subscription(subscription, "test_bot")
        assert is_valid is False
        assert "expired" in message.lower()
        
        # Test pending subscription with payment verification
        subscription = {
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(days=10),
            'payment_verified': True
        }
        
        is_valid, message = await self.clone_manager._validate_subscription(subscription, "test_bot")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_environment):
        """Test error handling and recovery mechanisms"""
        bot_id = "error_test_bot"
        
        with patch('clone_manager.get_clone') as mock_get_clone:
            # Test database error handling
            mock_get_clone.side_effect = Exception("Database error")
            
            success, message = await self.clone_manager.start_clone(bot_id)
            assert success is False
            assert "error" in message.lower()
        
        # Test invalid bot token handling
        with patch('clone_manager.get_clone') as mock_get_clone, \
             patch('clone_manager.get_subscription') as mock_get_subscription:
            
            mock_get_clone.return_value = {'_id': bot_id, 'bot_token': 'invalid_token'}
            mock_get_subscription.return_value = {'status': 'active', 'expires_at': datetime.now() + timedelta(days=30)}
            
            success, message = await self.clone_manager.start_clone(bot_id)
            assert success is False
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, setup_environment):
        """Test concurrent operations handling"""
        bot_ids = ["concurrent_bot_1", "concurrent_bot_2", "concurrent_bot_3"]
        
        # Mock successful operations
        with patch('clone_manager.get_clone'), \
             patch('clone_manager.get_subscription'), \
             patch('pyrogram.Client'), \
             patch('clone_manager.start_clone_in_db'):
            
            # Start multiple clones concurrently
            tasks = [self.clone_manager.start_clone(bot_id) for bot_id in bot_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that all operations completed (success or failure, no exceptions)
            for result in results:
                assert not isinstance(result, Exception)
    
    def test_configuration_validation(self, setup_environment):
        """Test configuration validation"""
        # Save original values
        original_api_id = Config.API_ID
        original_api_hash = Config.API_HASH
        
        try:
            # Test invalid configuration
            Config.API_ID = 0
            Config.API_HASH = ""
            
            assert not Config.validate()
            
            # Test valid configuration
            Config.API_ID = 123456
            Config.API_HASH = "valid_hash"
            Config.BOT_TOKEN = "123456:ABC-DEF"
            Config.DATABASE_URL = "mongodb://localhost:27017"
            Config.OWNER_ID = 123456
            
            assert Config.validate()
            
        finally:
            # Restore original values
            Config.API_ID = original_api_id
            Config.API_HASH = original_api_hash

# Helper function for async file mocking
def mock_open_async(content):
    """Create async mock for file operations"""
    async def mock_aenter(self):
        return self
    
    async def mock_aexit(self, exc_type, exc_val, exc_tb):
        pass
    
    async def mock_read(self):
        return content
    
    async def mock_write(self, data):
        pass
    
    mock = Mock()
    mock.__aenter__ = mock_aenter
    mock.__aexit__ = mock_aexit
    mock.read = mock_read
    mock.write = mock_write
    
    return lambda *args, **kwargs: mock

if __name__ == "__main__":
    pytest.main([__file__])
