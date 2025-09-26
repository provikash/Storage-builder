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
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(Config.DATABASE_URI)
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
        
        # Fetch clone info and URL using the new function
        from bot.database.clone_db import get_clone
        clone_info = await get_clone(clone_id)
        if not clone_info or 'mongodb_url' not in clone_info:
            logger.error(f"No MongoDB URL found for clone ID: {clone_id}")
            return None
        clone_db_url = clone_info['mongodb_url']
        clone_db_name = clone_info.get('db_name', f"clone_{clone_id}")

        clone_clients[clone_id] = AsyncIOMotorClient(clone_db_url)
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
    """Get popular files sorted by download count with enhanced metrics"""
    try:
        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return []
        else:
            files_collection = collection

        # Enhanced query with popularity metrics
        pipeline = [
            {
                "$match": {
                    "clone_id": clone_id if clone_id else {"$exists": False},
                    "download_count": {"$gt": 0}  # Only files with downloads
                }
            },
            {
                "$addFields": {
                    "popularity_score": {
                        "$add": [
                            {"$multiply": ["$download_count", 5]},  # Downloads are most important
                            {"$multiply": [{"$ifNull": ["$view_count", 0]}, 1]},
                            {"$multiply": [{"$ifNull": ["$share_count", 0]}, 3]}
                        ]
                    }
                }
            },
            {
                "$sort": {"popularity_score": -1, "download_count": -1}
            },
            {
                "$limit": limit
            }
        ]

        cursor = files_collection.aggregate(pipeline)
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

async def get_file_stats(file_id, clone_id=None):
    """Get detailed statistics for a file"""
    try:
        from bson import ObjectId

        # Determine which collection to use
        if clone_id:
            files_collection = await get_clone_files_collection(clone_id)
            if not files_collection:
                logger.error(f"Could not get collection for clone {clone_id}")
                return {
                    'views': 0,
                    'downloads': 0,
                    'shares': 0,
                    'recent_activity': 0
                }
        else:
            files_collection = collection

        # Try to find by ObjectId first, then by string
        try:
            query = {"_id": ObjectId(file_id)}
        except:
            query = {"file_id": file_id}

        if clone_id:
            query["clone_id"] = clone_id

        file_doc = await files_collection.find_one(query)

        if file_doc:
            return {
                'views': file_doc.get('view_count', 0),
                'downloads': file_doc.get('download_count', 0),
                'shares': file_doc.get('share_count', 0),
                'recent_activity': file_doc.get('recent_downloads', 0),
                'upload_date': file_doc.get('upload_date'),
                'last_downloaded': file_doc.get('last_downloaded')
            }
        else:
            return {
                'views': 0,
                'downloads': 0,
                'shares': 0,
                'recent_activity': 0
            }

    except Exception as e:
        logger.error(f"Error getting file stats: {e}")
        return {
            'views': 0,
            'downloads': 0,
            'shares': 0,
            'recent_activity': 0
        }

# Add clone-specific indexing functions
async def add_file_to_clone_index(file_data, clone_id):
    """Add file to clone-specific index"""
    try:
        # Get clone's database URL
        from bot.database.clone_db import get_clone
        clone_info = await get_clone(clone_id)
        if not clone_info or 'mongodb_url' not in clone_info:
            return False

        # Connect to clone's database
        clone_db_client = AsyncIOMotorClient(clone_info['mongodb_url'])
        clone_db = clone_db_client[clone_info.get('db_name', f"clone_{clone_id}")]
        clone_files_collection = clone_db['files']

        # Add clone_id to file data
        file_data['clone_id'] = clone_id
        file_data['indexed_at'] = datetime.now()

        # Check for duplicates
        existing_file = await clone_files_collection.find_one({
            "$or": [
                {"file_id": file_data["file_id"]},
                {"message_id": file_data.get("message_id"), "chat_id": file_data.get("chat_id")}
            ]
        })

        if existing_file:
            clone_db_client.close()
            return False  # Duplicate found

        # Insert file
        await clone_files_collection.insert_one(file_data)

        clone_db_client.close()
        return True

    except Exception as e:
        logger.error(f"Error adding file to clone index: {e}")
        return False

async def get_clone_database_stats(clone_id):
    """Get database statistics for a specific clone"""
    try:
        from bot.database.clone_db import get_clone
        clone_info = await get_clone(clone_id)
        if not clone_info or 'mongodb_url' not in clone_info:
            return None

        # Connect to clone's database
        clone_db_client = AsyncIOMotorClient(clone_info['mongodb_url'])
        clone_db = clone_db_client[clone_info.get('db_name', f"clone_{clone_id}")]

        # Get collection stats
        files_collection = clone_db['files']
        users_collection = clone_db['users']

        total_files = await files_collection.count_documents({})
        total_users = await users_collection.count_documents({})

        # Get file type distribution
        pipeline = [
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        file_types = await files_collection.aggregate(pipeline).to_list(length=None)

        # Get total file size
        size_pipeline = [
            {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
        ]
        size_result = await files_collection.aggregate(size_pipeline).to_list(length=1)
        total_size = size_result[0]['total_size'] if size_result else 0

        # Recent activity (files added in last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        recent_files = await files_collection.count_documents({
            "indexed_at": {"$gte": yesterday}
        })

        clone_db_client.close()

        return {
            "total_files": total_files,
            "total_users": total_users,
            "total_size": total_size,
            "recent_files": recent_files,
            "file_types": {item["_id"]: item["count"] for item in file_types},
            "database_name": clone_info.get('db_name', f"clone_{clone_id}")
        }

    except Exception as e:
        logger.error(f"Error getting clone database stats: {e}")
        return None

async def check_clone_database_connection(clone_id):
    """Check if clone database connection is working"""
    try:
        from bot.database.clone_db import get_clone
        clone_info = await get_clone(clone_id)
        if not clone_info or 'mongodb_url' not in clone_info:
            return False, "Clone configuration not found or missing database URL"

        # Test connection
        clone_db_client = AsyncIOMotorClient(clone_info['mongodb_url'], serverSelectionTimeoutMS=5000)
        await clone_db_client.admin.command('ping')
        clone_db_client.close()

        return True, "Database connection successful"

    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


class MongoDB:
    """MongoDB connection handler"""

    def __init__(self):
        self.client = AsyncIOMotorClient(Config.DATABASE_URI)
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

# Clone database connections
clone_clients = {}
clone_dbs = {}
clone_collections = {}

def get_clone_database(clone_id: str, mongodb_url: str):
    """Get clone-specific database connection"""
    if clone_id not in clone_clients:
        clone_clients[clone_id] = AsyncIOMotorClient(mongodb_url)
        clone_dbs[clone_id] = clone_clients[clone_id][f"clone_{clone_id}"]
        clone_collections[clone_id] = clone_dbs[clone_id].files
    
    return clone_dbs[clone_id], clone_collections[clone_id]

def close_clone_connections():
    """Close all clone MongoDB connections."""
    for client in clone_clients.values():
        client.close()
    clone_clients.clear()
    clone_dbs.clear()
    clone_collections.clear()
    logger.info("All clone MongoDB connections closed.")

# Fallback functions using bot.database.connection
async def get_random_files_fallback(limit=10, clone_id=None):
    """Get random files - fallback function"""
    try:
        from bot.database.connection import database

        if clone_id:
            collection = database.clone_files
            query = {'clone_id': clone_id}
        else:
            collection = database.files
            query = {}

        pipeline = [
            {'$match': query},
            {'$sample': {'size': limit}}
        ]

        cursor = collection.aggregate(pipeline)
        files = await cursor.to_list(length=limit)
        return files
    except Exception as e:
        logger.error(f"Error getting random files: {e}")
        return []

async def get_recent_files_fallback(limit=10, clone_id=None):
    """Get recent files - fallback function"""
    try:
        from bot.database.connection import database

        if clone_id:
            collection = database.clone_files
            query = {'clone_id': clone_id}
        else:
            collection = database.files
            query = {}

        cursor = collection.find(query).sort('created_at', -1).limit(limit)
        files = await cursor.to_list(length=limit)
        return files
    except Exception as e:
        logger.error(f"Error getting recent files: {e}")
        return []

async def get_popular_files_fallback(limit=10, clone_id=None):
    """Get popular files - fallback function"""
    try:
        from bot.database.connection import database

        if clone_id:
            collection = database.clone_files
            query = {'clone_id': clone_id}
        else:
            collection = database.files
            query = {}

        cursor = collection.find(query).sort('access_count', -1).limit(limit)
        files = await cursor.to_list(length=limit)
        return files
    except Exception as e:
        logger.error(f"Error getting popular files: {e}")
        return []