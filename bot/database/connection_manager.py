
import asyncio
from typing import Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bot.logging import get_context_logger
from bot.utils.error_handler import ErrorRecoveryConfig, safe_execute_async
from info import Config

logger = get_context_logger(__name__)

class DatabaseConnectionManager:
    """Manages database connections with automatic recovery"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.connection_config = ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=2.0,
            exponential_backoff=True,
            log_errors=True,
            raise_on_final_failure=True
        )
    
    async def connect(self) -> AsyncIOMotorDatabase:
        """Establish database connection with retry logic"""
        if self.client and self.database:
            try:
                # Test existing connection
                await self.database.admin.command('ping')
                return self.database
            except Exception as e:
                logger.warning("Existing connection failed, reconnecting", error=str(e))
                await self.disconnect()
        
        async def _connect():
            logger.debug("Establishing database connection")
            self.client = AsyncIOMotorClient(Config.DATABASE_URI)
            self.database = self.client[Config.DATABASE_URI.split('/')[-1]]
            
            # Test connection
            await self.database.admin.command('ping')
            logger.info("Database connection established successfully")
            return self.database
        
        return await safe_execute_async(
            _connect,
            config=self.connection_config,
            context={"operation": "database_connect"}
        )
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            try:
                self.client.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning("Error closing database connection", error=str(e))
            finally:
                self.client = None
                self.database = None
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute database operation with automatic retry"""
        async def _execute():
            db = await self.connect()
            return await operation(db, *args, **kwargs)
        
        return await safe_execute_async(
            _execute,
            config=self.connection_config,
            context={"operation": "database_operation"}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            db = await self.connect()
            start_time = asyncio.get_event_loop().time()
            await db.admin.command('ping')
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }

# Global instance
db_manager = DatabaseConnectionManager()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance with connection management"""
    return await db_manager.connect()
