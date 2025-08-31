import asyncio
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import Config
from bot.logging import LOGGER
import motor.motor_asyncio
from bson import ObjectId

# MongoDB Connection
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(Config.DATABASE_URL)
db = mongo_client[Config.DATABASE_NAME]
collection = db['files']

logger = LOGGER(__name__)

async def get_random_files(limit=10):
    """Get random files from the database"""
    try:
        # Use MongoDB's $sample aggregation to get random documents
        pipeline = [
            {"$sample": {"size": limit}},
            {"$project": {
                "_id": 1,
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "created_at": 1,
                "download_count": {"$ifNull": ["$download_count", 0]}
            }}
        ]

        cursor = collection.aggregate(pipeline)
        files = await cursor.to_list(length=limit)

        logger.info(f"Retrieved {len(files)} random files")
        return files

    except Exception as e:
        logger.error(f"Error getting random files: {e}")
        return []

async def get_recent_files(limit=10):
    """Get recent files from the database"""
    try:
        # Get files sorted by creation date (newest first)
        cursor = collection.find(
            {},
            {
                "_id": 1,
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "created_at": 1,
                "download_count": {"$ifNull": ["$download_count", 0]}
            }
        ).sort("created_at", -1).limit(limit)

        files = await cursor.to_list(length=limit)

        logger.info(f"Retrieved {len(files)} recent files")
        return files

    except Exception as e:
        logger.error(f"Error getting recent files: {e}")
        return []

async def get_popular_files(limit=10):
    """Get popular files based on download count"""
    try:
        # Get files sorted by download count (highest first)
        cursor = collection.find(
            {"download_count": {"$exists": True, "$gt": 0}},
            {
                "_id": 1,
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "created_at": 1,
                "download_count": 1
            }
        ).sort("download_count", -1).limit(limit)

        files = await cursor.to_list(length=limit)

        # If no files with download count, get recent files instead
        if not files:
            files = await get_recent_files(limit)

        logger.info(f"Retrieved {len(files)} popular files")
        return files

    except Exception as e:
        logger.error(f"Error getting popular files: {e}")
        return []

async def get_file_by_id(file_id):
    """Get a specific file by its ID"""
    try:

        # Try to convert to ObjectId if it's a valid ObjectId string
        try:
            object_id = ObjectId(file_id)
            file_data = await collection.find_one({"_id": object_id})
        except:
            # If not a valid ObjectId, search by file_id field
            file_data = await collection.find_one({"file_id": file_id})

        if file_data:
            logger.info(f"Retrieved file: {file_data.get('file_name', 'Unknown')}")

        return file_data

    except Exception as e:
        logger.error(f"Error getting file by ID {file_id}: {e}")
        return None

async def increment_download_count(file_id):
    """Increment download count for a file"""
    try:

        # Try to increment by ObjectId first
        try:
            object_id = ObjectId(file_id)
            result = await collection.update_one(
                {"_id": object_id},
                {"$inc": {"download_count": 1}}
            )
        except:
            # If not ObjectId, try by file_id field
            result = await collection.update_one(
                {"file_id": file_id},
                {"$inc": {"download_count": 1}}
            )

        if result.modified_count > 0:
            logger.info(f"Incremented download count for file {file_id}")
            return True
        else:
            logger.warning(f"File {file_id} not found for download count increment")
            return False

    except Exception as e:
        logger.error(f"Error incrementing download count for {file_id}: {e}")
        return False

class MongoDB:
    """MongoDB connection handler"""

    def __init__(self):
        self.client = AsyncIOMotorClient(Config.DATABASE_URL)
        self.db = self.client[Config.DATABASE_NAME]

    async def test_connection(self):
        """Test MongoDB connection"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            raise pymongo.errors.ConnectionFailure(f"MongoDB connection failed: {e}")

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()