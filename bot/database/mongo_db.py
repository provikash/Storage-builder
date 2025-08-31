import asyncio
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import Config
from bot.logging import LOGGER
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import pymongo

# MongoDB Connection
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(Config.DATABASE_URL)
db = mongo_client[Config.DATABASE_NAME]
collection = db['files']

logger = LOGGER(__name__)

# Dictionary to store clone-specific MongoDB clients and collections
clone_clients = {}
clone_dbs = {}
clone_collections = {}

async def get_clone_files_collection(clone_id):
    """Get the files collection for a specific clone, creating it if it doesn't exist."""
    if clone_id in clone_collections:
        return clone_collections[clone_id]

    # Assuming Config.CLONE_DB_URL_FORMAT can be used to construct URLs or fetch them
    # For now, we'll simulate fetching a URL based on clone_id
    # In a real scenario, you'd fetch this from a configuration or a database that maps clone_ids to URLs
    # Example: clone_db_url = Config.CLONE_DB_URL_FORMAT.format(clone_id=clone_id)
    # For demonstration, we'll use a placeholder and assume it works.
    # In a real implementation, you would need a mechanism to get the actual MongoDB URL for each clone.
    # This might involve querying a central database or using a predefined mapping.
    # As a placeholder, we'll create a new client for each unique clone_id.
    # IMPORTANT: In a production environment, manage client lifecycles carefully to avoid resource exhaustion.

    try:
        # This is a placeholder. You need to fetch the actual MongoDB URL for the clone.
        # For example, if you have a way to get clone details:
        # clone_details = await get_clone_details(clone_id) # Assume this function exists
        # clone_db_url = clone_details['mongodb_url']
        # For now, we'll use a dummy URL, assuming it's accessible and valid.
        # You should replace this with actual logic to get the clone's DB URL.
        clone_db_url = Config.DATABASE_URL # Placeholder: Use the main DB URL for demonstration
                                          # Replace with actual clone-specific URL fetching logic

        if not clone_db_url:
            logger.error(f"No MongoDB URL found for clone ID: {clone_id}")
            return None

        clone_clients[clone_id] = AsyncIOMotorClient(clone_db_url)
        # Use a database name specific to the clone, e.g., by appending the clone_id
        clone_db_name = f"clone_db_{clone_id}"
        clone_dbs[clone_id] = clone_clients[clone_id][clone_db_name]
        clone_collections[clone_id] = clone_dbs[clone_id]['files']
        logger.info(f"Initialized collection for clone ID: {clone_id}")
        return clone_collections[clone_id]
    except Exception as e:
        logger.error(f"Error initializing collection for clone {clone_id}: {e}")
        return None


async def get_random_files(limit=10, clone_id=None):
    """Get random files from the database"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return []
        else:
            files_collection = collection

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

        cursor = files_collection.aggregate(pipeline)
        files = await cursor.to_list(length=limit)

        logger.info(f"Retrieved {len(files)} random files for {'clone ' + clone_id if clone_id else 'mother bot'}")
        return files

    except Exception as e:
        logger.error(f"Error getting random files: {e}")
        return []

async def get_recent_files(limit=10, clone_id=None):
    """Get recent files from the database"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return []
        else:
            files_collection = collection

        # Get files sorted by creation date (newest first)
        cursor = files_collection.find(
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

        logger.info(f"Retrieved {len(files)} recent files for {'clone ' + clone_id if clone_id else 'mother bot'}")
        return files

    except Exception as e:
        logger.error(f"Error getting recent files: {e}")
        return []

async def get_popular_files(limit=10, clone_id=None):
    """Get popular files based on download count"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return []
        else:
            files_collection = collection

        # Get files sorted by download count (highest first)
        cursor = files_collection.find(
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
            files = await get_recent_files(limit, clone_id)

        logger.info(f"Retrieved {len(files)} popular files for {'clone ' + clone_id if clone_id else 'mother bot'}")
        return files

    except Exception as e:
        logger.error(f"Error getting popular files: {e}")
        return []

async def get_file_by_id(file_id, clone_id=None):
    """Get a specific file by its ID"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return None
        else:
            files_collection = collection

        # Try to convert to ObjectId if it's a valid ObjectId string
        try:
            object_id = ObjectId(file_id)
            file_data = await files_collection.find_one({"_id": object_id})
        except:
            # If not a valid ObjectId, search by file_id field
            file_data = await files_collection.find_one({"file_id": file_id})

        if file_data:
            logger.info(f"Retrieved file: {file_data.get('file_name', 'Unknown')} for {'clone ' + clone_id if clone_id else 'mother bot'}")

        return file_data

    except Exception as e:
        logger.error(f"Error getting file by ID {file_id} for {'clone ' + clone_id if clone_id else 'mother bot'}: {e}")
        return None

async def increment_download_count(file_id, clone_id=None):
    """Increment download count for a file"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return False
        else:
            files_collection = collection

        # Try to increment by ObjectId first
        try:
            object_id = ObjectId(file_id)
            result = await files_collection.update_one(
                {"_id": object_id},
                {"$inc": {"download_count": 1}}
            )
        except:
            # If not ObjectId, try by file_id field
            result = await files_collection.update_one(
                {"file_id": file_id},
                {"$inc": {"download_count": 1}}
            )

        if result.modified_count > 0:
            logger.info(f"Incremented download count for file {file_id} for {'clone ' + clone_id if clone_id else 'mother bot'}")
            return True
        else:
            logger.warning(f"File {file_id} not found for download count increment for {'clone ' + clone_id if clone_id else 'mother bot'}")
            return False

    except Exception as e:
        logger.error(f"Error incrementing download count for {file_id} for {'clone ' + clone_id if clone_id else 'mother bot'}: {e}")
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
            raise Exception(f"MongoDB connection failed: {e}")

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

    def close_clone_connections(self):
        """Close all clone MongoDB connections."""
        for client in clone_clients.values():
            client.close()
        clone_clients.clear()
        clone_dbs.clear()
        clone_collections.clear()
        logger.info("All clone MongoDB connections closed.")