from .connection import db
from datetime import datetime
from typing import List, Dict, Optional
import re
from info import Config
from ..utils.helper import get_collection_name, get_readable_file_size
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

async def get_popular_files(limit: int = 20, offset: int = 0, clone_id: str = None) -> List[Dict]:
    """Enhanced popular files with advanced popularity scoring algorithm"""
    try:
        print(f"DEBUG: Starting get_popular_files with limit={limit}, offset={offset}, clone_id={clone_id}")

        # Base match criteria for popular files
        match_criteria = {
            "file_type": {"$in": ["video", "document", "photo", "audio", "animation"]},
            "file_name": {"$exists": True, "$ne": None, "$ne": ""},
            "_id": {"$exists": True, "$ne": None, "$ne": ""},
            "file_size": {"$gt": 1024},
            "access_count": {"$gte": 1}  # Must have at least 1 view to be popular
        }
        
        # Add clone filter if specified
        if clone_id:
            match_criteria["clone_id"] = clone_id

        # Advanced popularity scoring pipeline
        pipeline = [
            {"$match": match_criteria},
            {
                "$addFields": {
                    # Advanced popularity algorithm
                    "popularity_score": {
                        "$add": [
                            # Base popularity from views (60% weight)
                            {"$multiply": [{"$ifNull": ["$access_count", 0]}, 0.6]},
                            
                            # Download count (25% weight)
                            {"$multiply": [{"$ifNull": ["$download_count", 0]}, 0.25]},
                            
                            # File size factor (10% weight) - larger files often more valuable
                            {"$multiply": [
                                {"$cond": [
                                    {"$gte": ["$file_size", 104857600]},  # 100MB+
                                    10,
                                    {"$cond": [
                                        {"$gte": ["$file_size", 52428800]},  # 50MB+
                                        5,
                                        {"$cond": [
                                            {"$gte": ["$file_size", 10485760]},  # 10MB+
                                            2,
                                            1
                                        ]}
                                    ]}
                                ]}, 0.1
                            ]},
                            
                            # File type bonus (5% weight)
                            {"$multiply": [
                                {"$cond": [
                                    {"$eq": ["$file_type", "video"]},
                                    3,
                                    {"$cond": [
                                        {"$eq": ["$file_type", "animation"]},
                                        2,
                                        {"$cond": [
                                            {"$eq": ["$file_type", "document"]},
                                            1.5,
                                            1
                                        ]}
                                    ]}
                                ]}, 0.05
                            ]}
                        ]
                    },
                    
                    # Calculate engagement rate (views per day since indexed)
                    "engagement_rate": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$indexed_at", null]},
                                {"$gt": ["$access_count", 0]}
                            ]},
                            {"$divide": [
                                "$access_count",
                                {"$max": [
                                    {"$divide": [
                                        {"$subtract": [datetime.utcnow(), "$indexed_at"]},
                                        86400000  # Convert to days
                                    ]},
                                    1  # Minimum 1 day to avoid division by zero
                                ]}
                            ]},
                            0
                        ]
                    },
                    
                    # Calculate viral coefficient (rapid growth indicator)
                    "viral_coefficient": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$indexed_at", null]},
                                {"$gt": ["$access_count", 10]}
                            ]},
                            {"$multiply": [
                                "$engagement_rate",
                                {"$sqrt": "$access_count"}
                            ]},
                            0
                        ]
                    }
                }
            },
            {
                "$sort": {
                    "popularity_score": -1,
                    "viral_coefficient": -1,
                    "engagement_rate": -1,
                    "access_count": -1
                }
            },
            {"$skip": offset},
            {"$limit": limit}
        ]

        try:
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Enhanced popularity query returned {len(results)} results")
        except Exception as agg_error:
            print(f"ERROR: Enhanced popularity aggregation failed: {agg_error}")
            
            # Fallback to simple access count sorting
            cursor = collection.find(match_criteria).sort("access_count", -1).skip(offset).limit(limit)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Fallback popularity query returned {len(results)} results")

        # Validate and enhance results
        valid_results = []
        for idx, doc in enumerate(results):
            try:
                if not isinstance(doc, dict):
                    continue

                file_id = str(doc.get('_id', ''))
                file_name = doc.get('file_name', 'Unknown')
                access_count = doc.get('access_count', 0)
                popularity_score = doc.get('popularity_score', access_count)
                engagement_rate = doc.get('engagement_rate', 0)

                if not file_id or access_count < 1:
                    continue

                # Add popularity rank
                doc['popularity_rank'] = idx + 1 + offset
                
                # Add trending indicator
                doc['is_trending'] = engagement_rate > 5  # More than 5 views per day
                
                # Add popularity tier
                if popularity_score >= 100:
                    doc['popularity_tier'] = 'viral'
                elif popularity_score >= 50:
                    doc['popularity_tier'] = 'hot'
                elif popularity_score >= 20:
                    doc['popularity_tier'] = 'popular'
                else:
                    doc['popularity_tier'] = 'rising'

                # Ensure required fields
                doc['file_name'] = file_name
                doc['download_count'] = doc.get('download_count', 0)
                
                valid_results.append(doc)
                print(f"DEBUG: Validated popular file #{doc['popularity_rank']}: {file_name} "
                      f"(Score: {popularity_score:.1f}, Views: {access_count}, Tier: {doc['popularity_tier']})")

            except Exception as validation_error:
                print(f"ERROR: Popular file validation failed: {validation_error}")
                continue

        print(f"DEBUG: get_popular_files returning {len(valid_results)} validated results")
        return valid_results

    except Exception as e:
        print(f"ERROR: get_popular_files failed: {e}")
        return []

async def get_recent_files(limit=10, offset=0, clone_id: str = None):
    """Enhanced recent files retrieval with better date-based sorting"""
    try:
        print(f"DEBUG: Starting get_recent_files with limit={limit}, offset={offset}, clone_id={clone_id}")

        # Base match criteria for recent files
        match_criteria = {
            "file_type": {"$in": ["video", "document", "photo", "audio", "animation"]},
            "file_name": {"$exists": True, "$ne": None, "$ne": ""},
            "_id": {"$exists": True, "$ne": None, "$ne": ""},
            "file_size": {"$gt": 1024},
            "indexed_at": {"$exists": True}
        }
        
        # Add clone filter if specified
        if clone_id:
            match_criteria["clone_id"] = clone_id

        # Enhanced pipeline with recency scoring
        pipeline = [
            {"$match": match_criteria},
            {
                "$addFields": {
                    "recency_score": {
                        "$add": [
                            # Primary: Days since indexed (more recent = higher score)
                            {"$divide": [
                                {"$subtract": [datetime.utcnow(), "$indexed_at"]},
                                86400000  # Convert to days
                            ]},
                            # Bonus for larger files
                            {"$cond": [
                                {"$gte": ["$file_size", 10485760]},  # 10MB+
                                2,
                                1
                            ]}
                        ]
                    }
                }
            },
            {"$sort": {"indexed_at": -1, "recency_score": 1}},  # Most recent first
            {"$skip": offset},
            {"$limit": limit}
        ]

        try:
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Enhanced recent query returned {len(results)} results")
        except Exception as agg_error:
            print(f"ERROR: Enhanced recent aggregation failed: {agg_error}")
            
            # Fallback to simple sort
            cursor = collection.find(match_criteria).sort("indexed_at", -1).skip(offset).limit(limit)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Fallback recent query returned {len(results)} results")

        # Validate and enhance results
        valid_results = []
        for doc in results:
            try:
                if not isinstance(doc, dict):
                    continue

                file_id = str(doc.get('_id', ''))
                file_name = doc.get('file_name', 'Unknown')
                indexed_at = doc.get('indexed_at')

                if not file_id:
                    continue

                # Calculate age for display
                if indexed_at:
                    age = datetime.utcnow() - indexed_at
                    doc['age_days'] = age.days
                    doc['age_hours'] = age.seconds // 3600
                else:
                    doc['age_days'] = 0
                    doc['age_hours'] = 0

                # Ensure required fields
                doc['file_name'] = file_name
                doc['access_count'] = doc.get('access_count', 0)
                
                valid_results.append(doc)
                print(f"DEBUG: Validated recent file: {file_name} (Age: {doc['age_days']}d {doc['age_hours']}h)")

            except Exception as validation_error:
                print(f"ERROR: Recent file validation failed: {validation_error}")
                continue

        print(f"DEBUG: get_recent_files returning {len(valid_results)} validated results")
        return valid_results

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