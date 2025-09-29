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

async def create_clone_indexes():
    """Create enhanced indexes for clone databases"""
    try:
        # Enhanced indexes for better search performance
        indexes = [
            # Basic file indexes
            ("file_name", "text"),  # Text index for search
            ("caption", "text"),    # Text index for caption search
            ("keywords", 1),        # Array index for keywords
            ("file_type", 1),
            ("file_size", 1),
            ("file_extension", 1),
            ("quality", 1),
            ("duration", 1),
            ("mime_type", 1),
            ("date", -1),
            ("indexed_at", -1),
            ("access_count", -1),
            ("last_accessed", -1),

            # Chat and message indexes
            ("chat_id", 1),
            ("message_id", 1),
            ("user_id", 1),

            # Compound indexes for complex queries
            [("file_type", 1), ("quality", 1), ("file_size", -1)],
            [("file_type", 1), ("date", -1)],
            [("keywords", 1), ("file_type", 1)],
            [("access_count", -1), ("date", -1)],
            [("file_size", -1), ("date", -1)],
            [("quality", 1), ("duration", -1)],

            # Geospatial index if location data is available
            # ("location", "2dsphere"),  # Uncomment if adding location features
        ]

        # Create text index for full-text search
        text_index = [
            ("file_name", "text"),
            ("caption", "text"),
            ("keywords", "text")
        ]

        for index in indexes:
            if isinstance(index, list):
                await files_collection.create_index(index)
                logger.info(f"Created compound index: {index}")
            elif isinstance(index, tuple) and index[1] == "text":
                # Skip individual text indexes as we'll create a compound one
                continue
            else:
                await files_collection.create_index([index])
                logger.info(f"Created index: {index}")

        # Create compound text index
        await files_collection.create_index(text_index)
        logger.info(f"Created text search index: {text_index}")

        # Create sparse indexes for optional fields
        sparse_indexes = [
            ("duration", 1),
            ("width", 1),
            ("height", 1),
            ("last_accessed", -1)
        ]

        for index in sparse_indexes:
            await files_collection.create_index([index], sparse=True)
            logger.info(f"Created sparse index: {index}")

        # Create TTL index for cleanup if needed
        # await files_collection.create_index([("indexed_at", 1)], expireAfterSeconds=31536000)  # 1 year

    except Exception as e:
        logger.error(f"Error creating enhanced clone indexes: {e}")

async def create_analytics_indexes():
    """Create indexes for analytics and statistics"""
    try:
        analytics_indexes = [
            ("file_type", 1),
            ("access_count", -1),
            ("download_count", -1),
            ("date", -1),
            ("user_id", 1),
            [("file_type", 1), ("access_count", -1)],
            [("date", -1), ("access_count", -1)],
            [("user_id", 1), ("date", -1)]
        ]

        for index in analytics_indexes:
            if isinstance(index, list):
                await analytics_collection.create_index(index)
            else:
                await analytics_collection.create_index([index])

        logger.info("Created analytics indexes")

    except Exception as e:
        logger.error(f"Error creating analytics indexes: {e}")

async def optimize_database_performance():
    """Optimize database performance settings"""
    try:
        # Enable profiling for slow queries
        await db.command("profile", 2, slowms=100)

        # Set read preference for better performance
        # This would be set at connection level in production

        logger.info("Database performance optimization applied")

    except Exception as e:
        logger.error(f"Error optimizing database performance: {e}")


if __name__ == "__main__":
    asyncio.run(create_indexes())