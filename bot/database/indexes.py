
```python
"""Database indexes for optimal performance"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

async def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        client = AsyncIOMotorClient(Config.DATABASE_URI)
        db = client[Config.DATABASE_NAME]
        
        # Clone collection indexes
        clones_collection = db.clones
        await clones_collection.create_index("bot_id", unique=True)
        await clones_collection.create_index("admin_id")
        await clones_collection.create_index("status")
        await clones_collection.create_index("created_at")
        await clones_collection.create_index([("status", 1), ("admin_id", 1)])
        
        # Subscription collection indexes
        subscriptions_collection = db.subscriptions
        await subscriptions_collection.create_index("bot_id", unique=True)
        await subscriptions_collection.create_index("status")
        await subscriptions_collection.create_index("expiry_date")
        await subscriptions_collection.create_index([("status", 1), ("expiry_date", 1)])
        
        # Users collection indexes
        users_collection = db.users
        await users_collection.create_index("user_id", unique=True)
        await users_collection.create_index("created_at")
        
        # Files collection indexes (if exists)
        files_collection = db.files
        await files_collection.create_index("owner_id")
        await files_collection.create_index("file_type")
        await files_collection.create_index("created_at")
        await files_collection.create_index([("owner_id", 1), ("created_at", -1)])
        
        # TTL index for logs cleanup
        logs_collection = db.logs
        await logs_collection.create_index("timestamp", expireAfterSeconds=2592000)  # 30 days
        
        logger.info("✅ Database indexes created successfully")
        client.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to create database indexes: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_indexes())
```
