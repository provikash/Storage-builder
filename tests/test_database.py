
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot.database.clone_db import *
from bot.database.subscription_db import *
from bot.database.users import *


class TestCloneDatabase:
    """Test clone database operations"""
    
    @pytest.mark.asyncio
    async def test_create_clone_success(self):
        """Test successful clone creation"""
        with patch('bot.database.clone_db.Client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.get_me.return_value = MagicMock(id=123456, username="test_bot")
            
            with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_motor:
                mock_db_client = AsyncMock()
                mock_motor.return_value = mock_db_client
                mock_db_client.admin.command.return_value = {"ok": 1}
                
                with patch('bot.database.clone_db.clones_collection') as mock_collection:
                    mock_collection.find_one.return_value = None
                    mock_collection.insert_one.return_value = AsyncMock()
                    
                    success, result = await create_clone("123456:ABC", 789, "mongodb://test")
                    assert success == True
                    assert "bot_id" in result

    @pytest.mark.asyncio
    async def test_create_clone_duplicate(self):
        """Test creating duplicate clone"""
        with patch('bot.database.clone_db.clones_collection') as mock_collection:
            mock_collection.find_one.return_value = {"bot_id": "123456"}
            
            success, result = await create_clone("123456:ABC", 789, "mongodb://test")
            assert success == False
            assert "already exists" in result

    @pytest.mark.asyncio
    async def test_get_clone_config(self):
        """Test retrieving clone configuration"""
        mock_config = {
            "bot_id": "123456",
            "admin_id": 789,
            "features": {"search": True, "upload": True}
        }
        
        with patch('bot.database.clone_db.clone_configs_collection') as mock_collection:
            mock_collection.find_one.return_value = mock_config
            
            config = await get_clone_config("123456")
            assert config["bot_id"] == "123456"
            assert config["admin_id"] == 789


class TestSubscriptionDatabase:
    """Test subscription database operations"""
    
    @pytest.mark.asyncio
    async def test_create_subscription(self):
        """Test creating new subscription"""
        with patch('bot.database.subscription_db.subscriptions_collection') as mock_collection:
            mock_collection.insert_one.return_value = AsyncMock()
            
            success = await create_subscription("123456", "monthly", 30)
            assert success == True

    @pytest.mark.asyncio
    async def test_check_expired_subscriptions(self):
        """Test checking for expired subscriptions"""
        expired_sub = {
            "bot_id": "123456",
            "expiry_date": datetime.now() - timedelta(days=1),
            "status": "active"
        }
        
        with patch('bot.database.subscription_db.subscriptions_collection') as mock_collection:
            mock_collection.find.return_value.to_list.return_value = [expired_sub]
            mock_collection.update_one.return_value = AsyncMock()
            
            expired_list = await check_expired_subscriptions()
            assert "123456" in expired_list

    @pytest.mark.asyncio
    async def test_get_subscription_stats(self):
        """Test getting subscription statistics"""
        with patch('bot.database.subscription_db.subscriptions_collection') as mock_collection:
            mock_collection.count_documents.return_value = 5
            
            stats = await get_subscription_stats()
            assert "total_subscriptions" in stats


class TestUserDatabase:
    """Test user database operations"""
    
    @pytest.mark.asyncio
    async def test_add_user(self):
        """Test adding new user"""
        with patch('bot.database.users.users') as mock_collection:
            mock_collection.find_one.return_value = None
            mock_collection.insert_one.return_value = AsyncMock()
            
            result = await add_user(123456, "testuser")
            assert result == True

    @pytest.mark.asyncio
    async def test_present_user(self):
        """Test checking if user exists"""
        with patch('bot.database.users.users') as mock_collection:
            mock_collection.find_one.return_value = {"user_id": 123456}
            
            result = await present_user(123456)
            assert result == True
