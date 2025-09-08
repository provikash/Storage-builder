from .connection import db
from datetime import datetime
from typing import List, Dict, Optional
import re
from info import Config
from ..utils.helper import get_collection_name, get_readable_file_size
from ..utils.security import security_manager
import logging

logger = logging.getLogger(__name__)

collection = db["file_index"]

async def add_to_index(file_id: str, file_name: str, file_type: str, file_size: int, caption: str = "", user_id: int = None):
    """Add a file to the search index"""

    # Sanitize and validate inputs
    file_name = security_manager.sanitize_filename(file_name)
    caption = security_manager.sanitize_filename(caption) if caption else ""
    user_id = int(user_id) if user_id and str(user_id).isdigit() else None
    file_size = max(0, int(file_size)) if file_size and str(file_size).isdigit() else 0

    # Sanitize file_id and file_type
    file_id = str(file_id)[:100]  # Limit length
    file_type = str(file_type)[:50] if file_type else "unknown"

    # Extract keywords from filename and caption
    keywords = extract_keywords(file_name, caption)

    document = {
        "_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "file_size": file_size,
        "caption": caption,
        "keywords": keywords,
        "user_id": user_id,
        "indexed_at": datetime.utcnow(),
        "access_count": 0
    }

    await collection.replace_one({"_id": file_id}, document, upsert=True)

async def search_files(query: str, limit: int = 50) -> List[Dict]:
    """Search files by query"""
    if not query.strip():
        return []

    # Sanitize search query
    sanitized_query = query.strip()[:100]  # Basic sanitization - limit length

    # Create search pattern
    search_terms = sanitized_query.strip().split()
    regex_patterns = []

    for term in search_terms:
        regex_patterns.append({"keywords": {"$regex": re.escape(term), "$options": "i"}})

    search_filter = {"$or": regex_patterns}

    cursor = collection.find(search_filter).sort("indexed_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def get_popular_files(limit=10, clone_id=None):
    """Get most popular files (most accessed)"""
    try:
        if clone_id:
            db_collection = db["clone_files"] # Assuming clone_id maps to a specific collection or a field
        else:
            db_collection = db["files"]  # Mother bot files

        # Find files sorted by access/download count
        cursor = db_collection.find({'clone_id': clone_id} if clone_id else {}).sort('access_count', -1).limit(limit)
        files = await cursor.to_list(length=limit)

        return files
    except Exception as e:
        logger.error(f"Error getting popular files: {e}")
        return []

async def get_recent_files(limit=10, clone_id=None):
    """Get most recently added files"""
    try:
        if clone_id:
            db_collection = db["clone_files"]
        else:
            db_collection = db["files"]  # Mother bot files

        # Find files sorted by creation time (most recent first)
        cursor = db_collection.find({'clone_id': clone_id} if clone_id else {}).sort('created_at', -1).limit(limit)
        files = await cursor.to_list(length=limit)

        return files
    except Exception as e:
        logger.error(f"Error getting recent files: {e}")
        return []

async def get_random_files(limit=10, clone_id=None):
    """Get random files from the database"""
    try:
        if clone_id:
            db_collection = db["clone_files"]
        else:
            db_collection = db["files"]  # Mother bot files

        # Use MongoDB aggregation pipeline to get random documents
        pipeline = [
            {'$match': {'clone_id': clone_id} if clone_id else {}},
            {'$sample': {'size': limit}}
        ]

        cursor = db_collection.aggregate(pipeline)
        files = await cursor.to_list(length=limit)

        return files
    except Exception as e:
        logger.error(f"Error getting random files: {e}")
        return []

async def increment_access_count(file_id: str):
    """Increment access count for a file"""
    await collection.update_one(
        {"_id": file_id},
        {"$inc": {"access_count": 1}}
    )

async def remove_from_index(file_id: str):
    """Remove a file from index"""
    await collection.delete_one({"_id": file_id})

async def get_index_stats() -> Dict:
    """Get indexing statistics"""
    total_files = await collection.count_documents({})

    # Count by file type
    pipeline = [
        {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    type_stats = await collection.aggregate(pipeline).to_list(length=None)

    return {
        "total_files": total_files,
        "file_types": {stat["_id"]: stat["count"] for stat in type_stats}
    }

def extract_keywords(file_name: str, caption: str = "") -> List[str]:
    """Extract searchable keywords from filename and caption"""
    text = f"{file_name} {caption}".lower()

    # Remove special characters and split into words
    words = re.findall(r'\b\w+\b', text)

    # Filter out very short words and common words
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were'}
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]

    # Remove duplicates while preserving order
    return list(dict.fromkeys(keywords))

async def update_file_keywords(file_id: str, new_keywords: List[str]):
    """Update keywords for a file"""
    await collection.update_one(
        {"_id": file_id},
        {"$set": {"keywords": new_keywords}}
    )

async def search_files_by_name(query: str, limit: int = 50) -> List[Dict]:
    """Search files by name - alias for search_files function"""
    return await search_files(query, limit)

async def get_random_files(limit: int = 10, clone_id: str = None) -> List[Dict]:
    """Enhanced random files retrieval with better filtering and clone support"""
    print(f"DEBUG: Starting get_random_files with limit={limit}, clone_id={clone_id}")

    try:
        # Base match criteria
        match_criteria = {
            "file_type": {"$in": ["video", "document", "photo", "audio", "animation"]},
            "file_name": {"$exists": True, "$ne": None, "$ne": ""},
            "_id": {"$exists": True, "$ne": None, "$ne": ""},
            "file_size": {"$gt": 1024},  # At least 1KB
            "indexed_at": {"$exists": True}
        }

        # Add clone filter if specified
        if clone_id:
            match_criteria["clone_id"] = clone_id

        # Enhanced pipeline with quality scoring
        pipeline = [
            {"$match": match_criteria},
            {
                "$addFields": {
                    "quality_score": {
                        "$add": [
                            # Size score (larger files generally better quality)
                            {"$cond": [
                                {"$gte": ["$file_size", 52428800]},  # 50MB+
                                5,
                                {"$cond": [
                                    {"$gte": ["$file_size", 10485760]},  # 10MB+
                                    3,
                                    1
                                ]}
                            ]},
                            # Access count bonus
                            {"$multiply": [{"$ifNull": ["$access_count", 0]}, 0.1]},
                            # File type preference
                            {"$cond": [
                                {"$in": ["$file_type", ["video", "animation"]]},
                                2,
                                {"$cond": [
                                    {"$eq": ["$file_type", "document"]},
                                    1.5,
                                    1
                                ]}
                            ]}
                        ]
                    }
                }
            },
            {"$sample": {"size": limit * 2}},  # Get more samples
            {"$sort": {"quality_score": -1}},   # Sort by quality
            {"$limit": limit}                   # Take top results
        ]

        print(f"DEBUG: Executing enhanced aggregation pipeline")

        try:
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Enhanced aggregation returned {len(results)} results")

        except Exception as agg_error:
            print(f"ERROR: Enhanced aggregation failed: {agg_error}")

            # Simple fallback
            try:
                cursor = collection.find(match_criteria).limit(limit * 2)
                all_results = await cursor.to_list(length=limit * 2)

                import random
                results = random.sample(all_results, min(limit, len(all_results))) if all_results else []
                print(f"DEBUG: Fallback returned {len(results)} random results")

            except Exception as fallback_error:
                print(f"ERROR: Fallback also failed: {fallback_error}")
                return []

        # Enhanced validation
        valid_results = []
        for idx, result in enumerate(results):
            try:
                if not isinstance(result, dict):
                    continue

                file_id = str(result.get('_id', ''))
                file_name = result.get('file_name', '')

                # Validate file_id format
                if not file_id:
                    continue

                # Check if it's a valid message ID format
                is_valid = False
                if '_' in file_id:
                    parts = file_id.split('_')
                    if len(parts) >= 2 and parts[-1].isdigit():
                        is_valid = True
                elif file_id.isdigit():
                    is_valid = True

                if not is_valid:
                    continue

                # Ensure required fields
                result['file_name'] = file_name or f"File_{file_id}"
                result['file_type'] = result.get('file_type', 'unknown')
                result['access_count'] = result.get('access_count', 0)

                valid_results.append(result)
                print(f"DEBUG: Validated random file: {result['file_name']} (Score: {result.get('quality_score', 0):.1f})")

            except Exception as validation_error:
                print(f"ERROR: Validation failed for result {idx}: {validation_error}")
                continue

        print(f"DEBUG: Random files validation complete - Valid: {len(valid_results)}")
        return valid_results

    except Exception as main_error:
        print(f"CRITICAL ERROR in get_random_files: {main_error}")
        return []

async def add_file_to_index(file_id, file_name, file_size, file_type, message_id, channel_id, caption="", user_id=None):
    """Add file to index with all required parameters"""
    try:
        # Sanitize and validate inputs for add_file_to_index
        file_name = security_manager.sanitize_filename(file_name)
        caption = security_manager.sanitize_filename(caption) if caption else ""
        user_id = int(user_id) if user_id and str(user_id).isdigit() else None
        file_size = max(0, int(file_size)) if file_size and str(file_size).isdigit() else 0

        # Sanitize file_id, file_type, message_id, channel_id
        file_id = str(file_id)[:100] if file_id else ""
        file_type = str(file_type)[:50] if file_type else "unknown"
        message_id = str(message_id)[:50] if message_id else ""
        channel_id = str(channel_id)[:50] if channel_id else ""

        file_data = {
            '_id': file_id,
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'message_id': message_id,
            'channel_id': channel_id,
            'caption': caption,
            'user_id': user_id,
            'access_count': 0,
            'date_added': datetime.utcnow()
        }

        collection_name = get_collection_name(channel_id) # Assuming channel_id is used to determine collection
        collection = db[collection_name]
        await collection.insert_one(file_data)
        return True
    except Exception as e:
        print(f"ERROR: Error adding file to index: {e}") # Use print for error logging as logger is not defined here
        return False

async def get_file_by_id(file_id):
    """Get file by ID"""
    try:
        # Sanitize file_id before using it in the query
        sanitized_file_id = str(file_id)[:100] if file_id else ""

        if not sanitized_file_id:
            print("ERROR: file_id is empty or invalid.")
            return None

        collection_name = get_collection_name(None) # Assuming collection name doesn't depend on file_id in this context
        collection = db[collection_name]
        return await collection.find_one({'_id': sanitized_file_id})
    except Exception as e:
        print(f"ERROR: Error getting file by ID: {e}") # Use print for error logging as logger is not defined here
        return None