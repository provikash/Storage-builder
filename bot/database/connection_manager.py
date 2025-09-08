
import asyncio
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from info import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Enhanced database connection manager with retry logic and health checks"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.is_connected: bool = False
        self.connection_retries: int = 0
        self.max_retries: int = 5
        
    async def connect(self) -> bool:
        """Connect to MongoDB with retry logic"""
        if self.is_connected and await self.health_check():
            return True
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{self.max_retries})")
                
                # Create client with proper configuration
                self.client = AsyncIOMotorClient(
                    Config.DATABASE_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                    retryWrites=True,
                    retryReads=True,
                    maxPoolSize=50,
                    minPoolSize=5
                )
                
                # Test connection
                await self.client.admin.command('ping')
                
                # Set database
                self.database = self.client[Config.DATABASE_NAME]
                self.is_connected = True
                self.connection_retries = 0
                
                logger.info("✅ Successfully connected to MongoDB")
                
                # Initialize collections and indexes
                await self.initialize_collections()
                
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff with max 30s
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("❌ Failed to connect to MongoDB after all retries")
                    
        self.is_connected = False
        return False
    
    async def disconnect(self):
        """Safely disconnect from MongoDB"""
        if self.client:
            try:
                self.client.close()
                self.is_connected = False
                logger.info("✅ Disconnected from MongoDB")
            except Exception as e:
                logger.error(f"Error disconnecting from MongoDB: {e}")
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        if not self.client:
            return False
        
        try:
            await asyncio.wait_for(self.client.admin.command('ping'), timeout=5)
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self.is_connected = False
            return False
    
    async def reconnect(self) -> bool:
        """Reconnect to database"""
        logger.info("Attempting to reconnect to database...")
        await self.disconnect()
        return await self.connect()
    
    async def initialize_collections(self):
        """Initialize database collections with indexes"""
        try:
            # Users collection indexes
            await self.database.users.create_index("user_id", unique=True)
            await self.database.users.create_index("created_at")
            
            # Clones collection indexes
            await self.database.clones.create_index("owner_id")
            await self.database.clones.create_index("status")
            await self.database.clones.create_index("created_at")
            
            # Files collection indexes
            await self.database.files.create_index("file_id", unique=True)
            await self.database.files.create_index("owner_id")
            await self.database.files.create_index("created_at")
            await self.database.files.create_index([("filename", "text"), ("caption", "text")])
            
            # Subscriptions collection indexes
            await self.database.subscriptions.create_index("user_id", unique=True)
            await self.database.subscriptions.create_index("expires_at")
            await self.database.subscriptions.create_index("status")
            
            # Sessions collection indexes (for user sessions)
            await self.database.sessions.create_index("user_id")
            await self.database.sessions.create_index("expires_at")
            
            # Logs collection with TTL index (auto-delete after 30 days)
            await self.database.logs.create_index("timestamp", expireAfterSeconds=30*24*3600)
            
            logger.info("✅ Database collections and indexes initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database collections: {e}")
    
    def get_database(self) -> Optional[AsyncIOMotorDatabase]:
        """Get database instance"""
        return self.database if self.is_connected else None
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute database operation with automatic retry on connection failure"""
        for attempt in range(3):
            try:
                if not self.is_connected or not await self.health_check():
                    if not await self.reconnect():
                        raise ConnectionFailure("Failed to reconnect to database")
                
                return await operation(*args, **kwargs)
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                raise
            except Exception as e:
                logger.error(f"Database operation error: {e}")
                raise

# Global database manager instance
db_manager = DatabaseManager()

# Convenience function to get database
def get_database() -> Optional[AsyncIOMotorDatabase]:
    return db_manager.get_database()

# Initialize database connection
async def init_database():
    """Initialize database connection"""
    return await db_manager.connect()

# Cleanup database connection
async def cleanup_database():
    """Cleanup database connection"""
    await db_manager.disconnect()
