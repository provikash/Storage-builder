from .connection import db
from datetime import datetime
from typing import List, Dict, Optional
import re
from info import Config
from ..utils.helper import get_collection_name
from ..utils.security import SecurityValidator

collection = db["file_index"]

async def add_to_index(file_id: str, file_name: str, file_type: str, file_size: int, caption: str = "", user_id: int = None):
    """Add a file to the search index"""

    # Sanitize and validate inputs
    file_name = SecurityValidator.sanitize_filename(file_name)
    caption = SecurityValidator.sanitize_filename(caption) if caption else ""
    user_id = SecurityValidator.validate_user_id(user_id)
    file_size = SecurityValidator.validate_file_size(file_size)

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
    sanitized_query = SecurityValidator.sanitize_search_query(query)

    # Create search pattern
    search_terms = sanitized_query.strip().split()
    regex_patterns = []

    for term in search_terms:
        regex_patterns.append({"keywords": {"$regex": re.escape(term), "$options": "i"}})

    search_filter = {"$or": regex_patterns}

    cursor = collection.find(search_filter).sort("indexed_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def get_popular_files(limit: int = 20, offset: int = 0) -> List[Dict]:
    """Get most accessed files with offset support"""
    try:
        print(f"DEBUG: Starting get_popular_files with limit={limit}, offset={offset}")

        # Get files sorted by access count (most popular first) with offset
        cursor = collection.find({}).sort("access_count", -1).skip(offset).limit(limit)

        results = []
        async for doc in cursor:
            # Validate document structure
            if not isinstance(doc, dict):
                print(f"WARNING: Invalid document type: {type(doc)}")
                continue

            file_id = str(doc.get('_id', ''))
            file_name = doc.get('file_name', 'Unknown')
            file_type = doc.get('file_type', 'unknown')
            access_count = doc.get('access_count', 0)

            if not file_id:
                print(f"WARNING: Document missing _id: {doc}")
                continue

            print(f"DEBUG: Validated popular file: {file_name} (ID: {file_id}, Views: {access_count})")
            results.append(doc)

        print(f"DEBUG: get_popular_files returning {len(results)} results with offset {offset}")
        return results

    except Exception as e:
        print(f"ERROR: get_popular_files failed: {e}")
        return []

async def get_recent_files(limit=10, offset=0):
    """Get recent files from database with offset support"""
    try:
        print(f"DEBUG: Starting get_recent_files with limit={limit}, offset={offset}")

        # Get files sorted by insertion order (most recent first) with offset
        cursor = collection.find({}).sort([("_id", -1)]).skip(offset).limit(limit)

        results = []
        async for doc in cursor:
            # Validate document structure
            if not isinstance(doc, dict):
                print(f"WARNING: Invalid document type: {type(doc)}")
                continue

            file_id = str(doc.get('_id', ''))
            file_name = doc.get('file_name', 'Unknown')
            file_type = doc.get('file_type', 'unknown')

            if not file_id:
                print(f"WARNING: Document missing _id: {doc}")
                continue

            print(f"DEBUG: Validated recent file: {file_name} (ID: {file_id})")
            results.append(doc)

        print(f"DEBUG: get_recent_files returning {len(results)} results with offset {offset}")
        return results

    except Exception as e:
        print(f"ERROR: get_recent_files failed: {e}")
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

async def get_random_files(limit: int = 10) -> List[Dict]:
    """Get random files from the index with proper validation and comprehensive error handling"""
    print(f"DEBUG: Starting get_random_files with limit={limit}")

    try:
        # Check if collection exists and has documents
        total_docs = await collection.count_documents({})
        print(f"DEBUG: Total documents in collection: {total_docs}")

        if total_docs == 0:
            print("WARNING: No documents found in collection")
            return []

        pipeline = [
            {
                "$match": {
                    # Ensure required fields exist and are valid
                    "file_type": {"$exists": True, "$ne": None, "$ne": "", "$nin": ["text", "sticker"]},
                    "file_name": {"$exists": True, "$ne": None, "$ne": ""},
                    "_id": {"$exists": True, "$ne": None, "$ne": ""},
                    "file_size": {"$exists": True, "$gt": 100},  # At least 100 bytes
                    # Ensure it's not a deleted or invalid entry
                    "indexed_at": {"$exists": True},
                    # Only include media files
                    "$or": [
                        {"file_type": "video"},
                        {"file_type": "document"},
                        {"file_type": "photo"},
                        {"file_type": "audio"},
                        {"file_type": "animation"}
                    ]
                }
            },
            {"$sample": {"size": limit}}
        ]

        print(f"DEBUG: Executing aggregation pipeline with {len(pipeline)} stages")

        try:
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Aggregation returned {len(results)} results")

        except Exception as agg_error:
            print(f"ERROR: Aggregation pipeline failed: {agg_error}")

            # Fallback to simple find query
            print("DEBUG: Trying fallback method with simple find query")
            try:
                cursor = collection.find({
                    "file_type": {"$exists": True, "$ne": None, "$ne": ""},
                    "file_name": {"$exists": True, "$ne": None, "$ne": ""},
                    "_id": {"$exists": True, "$ne": None, "$ne": ""},
                    "indexed_at": {"$exists": True}
                }).limit(limit * 2)  # Get more docs to compensate for filtering

                results = await cursor.to_list(length=limit * 2)
                print(f"DEBUG: Fallback query returned {len(results)} results")

                # Manually randomize since $sample failed
                import random
                if len(results) > limit:
                    results = random.sample(results, min(limit, len(results)))
                    print(f"DEBUG: Randomly selected {len(results)} from fallback results")

            except Exception as fallback_error:
                print(f"ERROR: Fallback query also failed: {fallback_error}")
                return []

        # Additional validation to ensure _id is properly formatted
        valid_results = []
        invalid_count = 0

        for idx, result in enumerate(results):
            try:
                if not isinstance(result, dict):
                    print(f"ERROR: Result {idx} is not a dict: {type(result)}")
                    invalid_count += 1
                    continue

                file_id = result.get('_id')
                if file_id is None:
                    print(f"ERROR: Result {idx} has no _id field")
                    invalid_count += 1
                    continue

                file_id_str = str(file_id)
                file_name = result.get('file_name', 'Unknown')
                file_type = result.get('file_type', 'unknown')

                # Validate file_id format
                if not file_id_str:
                    print(f"ERROR: Empty file_id for {file_name}")
                    invalid_count += 1
                    continue

                # Check if it's a valid format (either numeric or contains underscore)
                is_valid_format = (
                    file_id_str.isdigit() or
                    ('_' in file_id_str and file_id_str.replace('_', '').replace('-', '').isdigit())
                )

                if not is_valid_format:
                    print(f"ERROR: Invalid file_id format '{file_id_str}' for {file_name}")
                    invalid_count += 1
                    continue

                # Additional field validation
                if not file_name or file_name.strip() == '':
                    print(f"WARNING: Empty file_name for file_id {file_id_str}")
                    result['file_name'] = f"File_{file_id_str}"

                if not file_type or file_type.strip() == '':
                    print(f"WARNING: Empty file_type for {file_name}")
                    result['file_type'] = 'unknown'

                valid_results.append(result)
                print(f"DEBUG: Validated file {len(valid_results)}: {file_name} (ID: {file_id_str})")

            except Exception as validation_error:
                print(f"ERROR: Validation failed for result {idx}: {validation_error}")
                invalid_count += 1
                continue

        print(f"DEBUG: Validation complete - Valid: {len(valid_results)}, Invalid: {invalid_count}")

        if len(valid_results) == 0 and len(results) > 0:
            print("ERROR: All results failed validation - checking database integrity")

            # Sample a few documents to check their structure
            try:
                sample_docs = await collection.find({}).limit(3).to_list(length=3)
                print("DEBUG: Sample documents structure:")
                for i, doc in enumerate(sample_docs):
                    print(f"  Doc {i}: keys={list(doc.keys())}, _id={doc.get('_id')}")
            except Exception as sample_error:
                print(f"ERROR: Could not sample documents: {sample_error}")

        return valid_results

    except Exception as main_error:
        print(f"CRITICAL ERROR in get_random_files: {main_error}")
        print(f"ERROR TYPE: {type(main_error).__name__}")

        # Try to get basic info about the collection as a last resort
        try:
            collection_stats = await collection.count_documents({})
            print(f"DEBUG: Collection still accessible, total docs: {collection_stats}")
        except Exception as stats_error:
            print(f"ERROR: Cannot access collection at all: {stats_error}")

        return []

async def add_file_to_index(file_id, file_name, file_size, file_type, message_id, channel_id, caption="", user_id=None):
    """Add file to index with all required parameters"""
    try:
        # Sanitize and validate inputs for add_file_to_index
        file_name = SecurityValidator.sanitize_filename(file_name)
        caption = SecurityValidator.sanitize_filename(caption) if caption else ""
        user_id = SecurityValidator.validate_user_id(user_id)
        file_size = SecurityValidator.validate_file_size(file_size)

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