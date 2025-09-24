
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.utils.session_manager import (
    create_session, get_session, clear_session, session_expired,
    update_session_activity, cleanup_expired_sessions, user_sessions,
    SessionManager, SESSION_TIMEOUT
)

class TestSessionManager:
    """Production-level session management tests"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up sessions before and after each test"""
        user_sessions.clear()
        yield
        user_sessions.clear()

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Test successful session creation"""
        user_id = 12345
        session_type = "clone_setup"
        data = {"step": 1, "bot_token": "test_token"}

        result = await create_session(user_id, session_type, data)
        
        assert result is True
        assert user_id in user_sessions
        
        session = user_sessions[user_id]
        assert session['user_id'] == user_id
        assert session['type'] == session_type
        assert session['data'] == data
        assert 'started_at' in session
        assert 'expires_at' in session

    @pytest.mark.asyncio
    async def test_create_session_overwrites_existing(self):
        """Test that creating a new session overwrites existing one"""
        user_id = 12345
        
        # Create first session
        await create_session(user_id, "type1", {"data": "old"})
        
        # Create second session (should overwrite)
        await create_session(user_id, "type2", {"data": "new"})
        
        session = user_sessions[user_id]
        assert session['type'] == "type2"
        assert session['data']['data'] == "new"

    @pytest.mark.asyncio
    async def test_get_session_valid(self):
        """Test retrieving a valid session"""
        user_id = 12345
        await create_session(user_id, "test", {"key": "value"})
        
        session = await get_session(user_id)
        
        assert session is not None
        assert session['user_id'] == user_id
        assert session['type'] == "test"

    @pytest.mark.asyncio
    async def test_get_session_nonexistent(self):
        """Test retrieving a non-existent session"""
        user_id = 99999
        
        session = await get_session(user_id)
        
        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """Test retrieving an expired session"""
        user_id = 12345
        await create_session(user_id, "test", {})
        
        # Manually expire the session
        user_sessions[user_id]['expires_at'] = datetime.now() - timedelta(hours=1)
        
        session = await get_session(user_id)
        
        assert session is None
        assert user_id not in user_sessions  # Should be auto-cleaned

    @pytest.mark.asyncio
    async def test_session_expired_check(self):
        """Test session expiry checking"""
        user_id = 12345
        
        # Test non-existent session
        assert await session_expired(user_id) is True
        
        # Test valid session
        await create_session(user_id, "test", {})
        assert await session_expired(user_id) is False
        
        # Test expired session
        user_sessions[user_id]['expires_at'] = datetime.now() - timedelta(hours=1)
        assert await session_expired(user_id) is True
        assert user_id not in user_sessions  # Should be auto-cleaned

    @pytest.mark.asyncio
    async def test_session_activity_update(self):
        """Test session activity updating"""
        user_id = 12345
        await create_session(user_id, "test", {})
        
        original_expires = user_sessions[user_id]['expires_at']
        
        # Wait a moment to ensure timestamp difference
        await asyncio.sleep(0.1)
        
        result = await update_session_activity(user_id)
        
        assert result is True
        assert user_sessions[user_id]['expires_at'] > original_expires

    @pytest.mark.asyncio
    async def test_session_activity_update_nonexistent(self):
        """Test updating activity for non-existent session"""
        user_id = 99999
        
        result = await update_session_activity(user_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_session(self):
        """Test session clearing"""
        user_id = 12345
        await create_session(user_id, "test", {})
        
        assert user_id in user_sessions
        
        result = await clear_session(user_id)
        
        assert result is True
        assert user_id not in user_sessions

    @pytest.mark.asyncio
    async def test_clear_nonexistent_session(self):
        """Test clearing non-existent session"""
        user_id = 99999
        
        result = await clear_session(user_id)
        
        assert result is False

    def test_cleanup_expired_sessions(self):
        """Test bulk cleanup of expired sessions"""
        # Create mix of valid and expired sessions
        valid_session = {
            'user_id': 1,
            'type': 'valid',
            'data': {},
            'started_at': datetime.now(),
            'last_activity': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=1)
        }
        
        expired_session = {
            'user_id': 2,
            'type': 'expired',
            'data': {},
            'started_at': datetime.now() - timedelta(hours=2),
            'last_activity': datetime.now() - timedelta(hours=2),
            'expires_at': datetime.now() - timedelta(hours=1)
        }
        
        user_sessions[1] = valid_session
        user_sessions[2] = expired_session
        
        cleanup_count = cleanup_expired_sessions()
        
        assert cleanup_count == 1
        assert 1 in user_sessions
        assert 2 not in user_sessions

    @pytest.mark.asyncio
    async def test_session_manager_class_methods(self):
        """Test SessionManager class wrapper methods"""
        user_id = 12345
        
        # Test create_session
        result = await SessionManager.create_session(user_id, "test", {"key": "value"})
        assert result is True
        
        # Test get_session
        session = await SessionManager.get_session(user_id)
        assert session is not None
        
        # Test get_all_sessions
        all_sessions = SessionManager.get_all_sessions()
        assert user_id in all_sessions
        
        # Test get_session_count
        count = SessionManager.get_session_count()
        assert count == 1
        
        # Test clear_session
        result = await SessionManager.clear_session(user_id)
        assert result is True
        assert user_id not in user_sessions

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self):
        """Test concurrent session operations for race conditions"""
        user_id = 12345
        
        async def create_and_update():
            await create_session(user_id, "concurrent", {"data": "test"})
            await update_session_activity(user_id)
        
        async def clear_session_task():
            await asyncio.sleep(0.05)  # Small delay
            await clear_session(user_id)
        
        # Run concurrent operations
        await asyncio.gather(
            create_and_update(),
            clear_session_task(),
            return_exceptions=True
        )
        
        # Session should be cleared
        assert user_id not in user_sessions

    @pytest.mark.asyncio
    async def test_session_timeout_configuration(self):
        """Test session timeout configuration"""
        user_id = 12345
        await create_session(user_id, "test", {})
        
        session = user_sessions[user_id]
        created_time = session['started_at']
        expires_time = session['expires_at']
        
        # Check that timeout is correctly set
        expected_expiry = created_time + SESSION_TIMEOUT
        time_diff = abs((expires_time - expected_expiry).total_seconds())
        
        assert time_diff < 1  # Should be within 1 second

    @pytest.mark.asyncio
    async def test_corrupted_session_handling(self):
        """Test handling of corrupted session data"""
        user_id = 12345
        
        # Create corrupted session (missing expires_at)
        user_sessions[user_id] = {
            'user_id': user_id,
            'type': 'corrupted',
            'data': {},
            'started_at': datetime.now()
            # Missing expires_at
        }
        
        # Should handle corrupted session gracefully
        is_expired = await session_expired(user_id)
        assert is_expired is True
        assert user_id not in user_sessions  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_error_handling_with_mock_exception(self):
        """Test error handling in session operations"""
        user_id = 12345
        
        with patch('bot.utils.session_manager.user_sessions', side_effect=Exception("Mock error")):
            # Should handle exceptions gracefully
            result = await create_session(user_id, "test", {})
            assert result is False

    @pytest.mark.asyncio
    async def test_session_persistence_simulation(self):
        """Test session behavior under simulated restart conditions"""
        user_id = 12345
        
        # Create session
        await create_session(user_id, "persistent", {"important": "data"})
        
        # Simulate application restart by clearing and recreating
        saved_session = user_sessions[user_id].copy()
        user_sessions.clear()
        
        # In real scenario, sessions would be lost
        session = await get_session(user_id)
        assert session is None
        
        # This test demonstrates the need for persistent session storage

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
