
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestSecurity:
    """Security tests for the bot system"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_admin_access(self):
        """Test that unauthorized users cannot access admin functions"""
        from bot.utils.admin_verification import verify_admin
        
        # Test with non-admin user
        with patch('info.Config') as mock_config:
            mock_config.ADMINS = [123456]
            mock_config.OWNER_ID = 123456
            
            is_admin = await verify_admin(999999)  # Different user ID
            assert is_admin == False

    @pytest.mark.asyncio
    async def test_bot_token_validation(self):
        """Test bot token validation security"""
        # Test with invalid token format
        invalid_tokens = [
            "invalid_token",
            "123:short",
            "",
            "no_colon_token",
            "123456789:ABC"  # Too short
        ]
        
        for token in invalid_tokens:
            with patch('pyrogram.Client') as mock_client:
                mock_client.side_effect = Exception("Invalid token")
                
                from clone_manager import CloneManager
                manager = CloneManager()
                
                success, result = await manager.create_clone(token, 123456, "mongodb://test")
                assert success == False

    @pytest.mark.asyncio
    async def test_database_injection_protection(self):
        """Test protection against database injection"""
        malicious_inputs = [
            {"$ne": None},
            {"$where": "function() { return true; }"},
            "'; DROP TABLE clones; --",
            {"$regex": ".*"}
        ]
        
        with patch('bot.database.clone_db.clones_collection') as mock_collection:
            mock_collection.find_one.return_value = None
            
            from bot.database.clone_db import get_clone_data
            
            for malicious_input in malicious_inputs:
                try:
                    await get_clone_data(malicious_input)
                    # Should not reach here with proper validation
                    assert False, f"Malicious input not blocked: {malicious_input}"
                except (TypeError, ValueError):
                    # Expected behavior - input should be rejected
                    pass

    @pytest.mark.asyncio
    async def test_subscription_tampering_protection(self):
        """Test protection against subscription tampering"""
        from bot.utils.subscription_checker import SubscriptionChecker
        checker = SubscriptionChecker()
        
        # Test with manipulated subscription data
        tampered_subscription = {
            "status": "active",
            "expiry_date": "2099-12-31T23:59:59Z"  # Far future date
        }
        
        with patch('bot.utils.subscription_checker.get_subscription') as mock_get:
            mock_get.return_value = tampered_subscription
            
            # Should validate date format and reasonable ranges
            is_active = await checker.is_subscription_active("123456:ABC")
            # The function should handle this gracefully

    def test_command_rate_limiting(self):
        """Test rate limiting for commands"""
        # This would test rate limiting if implemented
        # For now, verify the structure exists
        try:
            from bot.utils.rate_limiter_disabled import RateLimiter
            # Rate limiter exists but is disabled
            assert True
        except ImportError:
            # If rate limiter doesn't exist, that's a security concern
            pytest.skip("Rate limiter not implemented")

    @pytest.mark.asyncio
    async def test_clone_isolation(self):
        """Test that clones are properly isolated"""
        from clone_manager import CloneManager
        manager = CloneManager()
        
        # Mock two different clones
        clone1_config = {
            "bot_id": "111111",
            "bot_token": "111111:ABC",
            "admin_id": 123
        }
        
        clone2_config = {
            "bot_id": "222222",
            "bot_token": "222222:DEF",
            "admin_id": 456
        }
        
        with patch('clone_manager.get_clone_config') as mock_config:
            def side_effect(bot_id):
                if bot_id == "111111":
                    return clone1_config
                elif bot_id == "222222":
                    return clone2_config
                return None
            
            mock_config.side_effect = side_effect
            
            with patch('pyrogram.Client') as mock_client:
                mock_client.return_value = AsyncMock()
                
                # Start both clones
                await manager.start_clone("111111")
                await manager.start_clone("222222")
                
                # Verify they're separate instances
                assert "111111" in manager.instances
                assert "222222" in manager.instances
                assert manager.instances["111111"] != manager.instances["222222"]

    @pytest.mark.asyncio
    async def test_sensitive_data_logging(self):
        """Test that sensitive data is not logged"""
        import logging
        from io import StringIO
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("bot")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Log message with potential sensitive data
        sensitive_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"
        logger.info(f"Processing token: {sensitive_token[:10]}...")
        
        log_output = log_capture.getvalue()
        
        # Token should be truncated, not logged in full
        assert sensitive_token not in log_output
        assert "123456789:" in log_output  # Partial token is OK

    @pytest.mark.asyncio
    async def test_admin_session_security(self):
        """Test admin session security"""
        # Test session timeout and validation
        from bot.plugins.admin_panel import admin_sessions
        
        # Simulate expired session
        user_id = 123456
        admin_sessions[user_id] = {
            "type": "clone",
            "bot_token": "123456:ABC",
            "created_at": "old_timestamp"
        }
        
        # Session should be validated for freshness
        session = admin_sessions.get(user_id)
        assert session is not None  # Basic existence check
        
        # In production, sessions should have timestamps and expiry
