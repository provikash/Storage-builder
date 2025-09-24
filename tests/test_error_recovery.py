
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.utils.error_handler import (
    safe_execute_async, safe_execute, ErrorRecoveryConfig,
    ProductionErrorHandler, error_handler
)

class TestErrorRecovery:
    """Production-level error recovery tests"""

    @pytest.mark.asyncio
    async def test_database_connection_recovery(self):
        """Test database connection recovery scenarios"""
        call_count = 0
        
        async def mock_database_operation():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise ConnectionError("Database connection lost")
            elif call_count == 2:
                raise TimeoutError("Database timeout")
            else:
                return {"status": "success", "data": "retrieved"}
        
        config = ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=0.1,
            exponential_backoff=True
        )
        
        result = await safe_execute_async(
            mock_database_operation,
            context={"operation": "database_query", "table": "users"},
            recovery_config=config
        )
        
        assert result == {"status": "success", "data": "retrieved"}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_telegram_api_flood_wait_recovery(self):
        """Test Telegram API FloodWait error recovery"""
        call_count = 0
        
        async def mock_telegram_api_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Simulate FloodWait error
                from pyrogram.errors import FloodWait
                raise FloodWait(value=1)  # 1 second wait
            else:
                return {"message_id": 12345}
        
        config = ErrorRecoveryConfig(
            max_retries=5,
            retry_delay=0.1,
            handle_flood_wait=True
        )
        
        result = await safe_execute_async(
            mock_telegram_api_call,
            context={"operation": "send_message", "chat_id": 12345},
            recovery_config=config
        )
        
        assert result == {"message_id": 12345}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_session_recovery_after_failure(self):
        """Test session recovery after connection failure"""
        from bot.utils.session_manager import create_session, get_session, user_sessions
        
        # Clear any existing sessions
        user_sessions.clear()
        
        user_id = 12345
        session_data = {"step": 1, "data": "important"}
        
        # Create session successfully
        await create_session(user_id, "test_recovery", session_data)
        
        # Simulate session corruption
        user_sessions[user_id]['expires_at'] = None  # Corrupt the session
        
        # Try to get session - should handle corruption gracefully
        session = await get_session(user_id)
        assert session is None  # Should return None due to corruption
        assert user_id not in user_sessions  # Should clean up corrupted session

    @pytest.mark.asyncio
    async def test_file_system_error_recovery(self):
        """Test file system operation error recovery"""
        call_count = 0
        
        async def mock_file_operation():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise PermissionError("Permission denied")
            elif call_count == 2:
                raise FileNotFoundError("File not found")
            else:
                return "file_content_here"
        
        config = ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=0.1
        )
        
        result = await safe_execute_async(
            mock_file_operation,
            context={"operation": "read_file", "file_path": "/tmp/test.txt"},
            recovery_config=config
        )
        
        assert result == "file_content_here"

    @pytest.mark.asyncio
    async def test_network_timeout_recovery(self):
        """Test network timeout recovery"""
        call_count = 0
        
        async def mock_network_request():
            nonlocal call_count
            call_count += 1
            
            if call_count < 4:
                raise asyncio.TimeoutError("Network timeout")
            else:
                return {"status": 200, "data": "success"}
        
        config = ErrorRecoveryConfig(
            max_retries=5,
            retry_delay=0.2,
            exponential_backoff=True
        )
        
        result = await safe_execute_async(
            mock_network_request,
            context={"operation": "api_request", "url": "https://api.example.com"},
            recovery_config=config
        )
        
        assert result == {"status": 200, "data": "success"}

    @pytest.mark.asyncio
    async def test_memory_error_recovery(self):
        """Test memory error handling"""
        async def mock_memory_intensive_operation():
            raise MemoryError("Out of memory")
        
        config = ErrorRecoveryConfig(
            max_retries=2,
            retry_delay=0.1
        )
        
        result = await safe_execute_async(
            mock_memory_intensive_operation,
            context={"operation": "large_data_processing"},
            recovery_config=config
        )
        
        # Should fail gracefully
        assert result is None

    @pytest.mark.asyncio
    async def test_critical_error_no_retry(self):
        """Test that critical errors are not retried"""
        call_count = 0
        
        async def mock_critical_operation():
            nonlocal call_count
            call_count += 1
            raise SystemExit("Critical system error")
        
        config = ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=0.1
        )
        
        result = await safe_execute_async(
            mock_critical_operation,
            context={"operation": "critical_system_call"},
            recovery_config=config
        )
        
        # Should not retry SystemExit
        assert result is None
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_error_recovery(self):
        """Test error recovery under concurrent load"""
        results = []
        
        async def mock_unstable_operation(task_id):
            if task_id % 3 == 0:  # Every 3rd task fails initially
                raise ConnectionError(f"Task {task_id} connection failed")
            return f"Task {task_id} completed"
        
        config = ErrorRecoveryConfig(
            max_retries=2,
            retry_delay=0.05
        )
        
        # Run 10 concurrent tasks
        tasks = []
        for i in range(10):
            task = safe_execute_async(
                mock_unstable_operation,
                i,
                context={"operation": "concurrent_task", "task_id": i},
                recovery_config=config
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All tasks should eventually succeed or return None
        assert len(results) == 10
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) >= 7  # Most should succeed

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff timing"""
        call_times = []
        
        async def mock_operation():
            call_times.append(asyncio.get_event_loop().time())
            raise Exception("Always fails")
        
        config = ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=0.1,
            exponential_backoff=True,
            max_delay=1.0
        )
        
        await safe_execute_async(
            mock_operation,
            context={"operation": "backoff_test"},
            recovery_config=config
        )
        
        # Check that delays increase exponentially
        assert len(call_times) == 4  # Initial + 3 retries
        
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # Second delay should be roughly double the first
            assert delay2 > delay1 * 1.5

    @pytest.mark.asyncio
    async def test_context_preservation_across_retries(self):
        """Test that context is preserved across retries"""
        contexts_received = []
        
        async def mock_operation_with_context(**context):
            contexts_received.append(context.copy())
            if len(contexts_received) < 3:
                raise ValueError("Retry needed")
            return "success"
        
        config = ErrorRecoveryConfig(max_retries=3, retry_delay=0.1)
        
        result = await safe_execute_async(
            mock_operation_with_context,
            context={
                "operation": "context_test",
                "user_id": 12345,
                "session_data": {"important": "value"}
            },
            recovery_config=config
        )
        
        assert result == "success"
        assert len(contexts_received) == 3
        
        # All contexts should be identical
        for ctx in contexts_received:
            assert ctx["user_id"] == 12345
            assert ctx["session_data"]["important"] == "value"

    def test_synchronous_error_recovery(self):
        """Test synchronous error recovery"""
        call_count = 0
        
        def mock_sync_operation():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                raise ConnectionError("Sync connection failed")
            return "sync_success"
        
        config = ErrorRecoveryConfig(max_retries=3, retry_delay=0.1)
        
        result = safe_execute(
            mock_sync_operation,
            context={"operation": "sync_test"},
            recovery_config=config
        )
        
        assert result == "sync_success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_error_handler_class_methods(self):
        """Test ProductionErrorHandler class methods"""
        async def test_function():
            raise ValueError("Test error")
        
        result = await error_handler.safe_execute(
            test_function,
            context="test_operation"
        )
        
        assert result is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
