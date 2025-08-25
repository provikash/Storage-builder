
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration for tests"""
    with patch('info.Config') as mock:
        mock.BOT_TOKEN = "123456789:ABCDEFGHIJKLMNOP"
        mock.API_ID = 123456
        mock.API_HASH = "abcdef123456"
        mock.DATABASE_URL = "mongodb://localhost:27017"
        mock.DATABASE_NAME = "test_db"
        mock.ADMINS = [123456789]
        mock.OWNER_ID = 123456789
        yield mock


@pytest.fixture
def mock_database():
    """Mock database collections"""
    with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        
        # Mock collections
        mock_db.clones = AsyncMock()
        mock_db.clone_configs = AsyncMock()
        mock_db.subscriptions = AsyncMock()
        mock_db.global_settings = AsyncMock()
        
        yield mock_db


@pytest.fixture
def mock_pyrogram_client():
    """Mock Pyrogram client"""
    with patch('pyrogram.Client') as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value = mock_instance
        
        # Mock bot info
        mock_instance.get_me.return_value = MagicMock(
            id=123456789,
            username="test_bot",
            first_name="Test Bot"
        )
        
        yield mock_instance


@pytest.fixture
def mock_clone_manager():
    """Mock clone manager"""
    with patch('clone_manager.clone_manager') as mock_manager:
        mock_manager.instances = {}
        mock_manager.get_running_clones.return_value = []
        mock_manager.start_clone = AsyncMock(return_value=True)
        mock_manager.stop_clone = AsyncMock(return_value=True)
        mock_manager.create_clone = AsyncMock(return_value=(True, {"bot_id": "123456"}))
        
        yield mock_manager


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests"""
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)


# Test data fixtures
@pytest.fixture
def sample_clone_data():
    """Sample clone data for testing"""
    return {
        "bot_id": "123456789",
        "bot_token": "123456789:ABCDEFGHIJKLMNOP",
        "admin_id": 987654321,
        "username": "test_clone_bot",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_subscription_data():
    """Sample subscription data for testing"""
    from datetime import datetime, timedelta
    return {
        "bot_id": "123456789",
        "tier": "monthly",
        "status": "active",
        "expiry_date": datetime.now() + timedelta(days=30),
        "created_at": datetime.now()
    }


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing"""
    return {
        "bot_id": "123456789",
        "features": {
            "search": True,
            "upload": True,
            "token_verification": True,
            "premium": True,
            "auto_delete": True,
            "batch_links": True,
            "clone_creation": False,
            "admin_panel": False
        },
        "token_settings": {
            "mode": "one_time",
            "command_limit": 100,
            "pricing": 1.0,
            "enabled": True
        },
        "channels": {
            "force_channels": [],
            "request_channels": []
        }
    }
