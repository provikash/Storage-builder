
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from bot.domains.clone.repositories import CloneRepository
from bot.domains.clone.entities import Clone, CloneStatus
from bot.database.mongo_db import MongoDB
from bot.logging import LOGGER

logger = LOGGER(__name__)

class MongoCloneRepository(CloneRepository):
    """MongoDB implementation of clone repository"""
    
    def __init__(self):
        self.db = MongoDB()
        self.collection: AsyncIOMotorCollection = self.db.clones
    
    async def create(self, clone: Clone) -> Clone:
        """Create a new clone"""
        clone_data = {
            "_id": clone.bot_id,
            "owner_id": clone.owner_id,
            "bot_token": clone.bot_token,
            "username": clone.username,
            "status": clone.status.value,
            "created_at": clone.created_at or datetime.now(),
            "last_seen": clone.last_seen,
            "configuration": clone.configuration,
            "metadata": clone.metadata
        }
        
        await self.collection.insert_one(clone_data)
        return clone
    
    async def get_by_id(self, clone_id: str) -> Optional[Clone]:
        """Get clone by ID"""
        data = await self.collection.find_one({"_id": clone_id})
        if not data:
            return None
        
        return Clone(
            bot_id=data["_id"],
            owner_id=data["owner_id"],
            bot_token=data["bot_token"],
            username=data.get("username"),
            status=CloneStatus(data["status"]),
            created_at=data.get("created_at"),
            last_seen=data.get("last_seen"),
            configuration=data.get("configuration", {}),
            metadata=data.get("metadata", {})
        )
    
    async def get_by_owner(self, owner_id: int) -> List[Clone]:
        """Get all clones owned by a user"""
        cursor = self.collection.find({"owner_id": owner_id})
        clones = []
        
        async for data in cursor:
            clone = Clone(
                bot_id=data["_id"],
                owner_id=data["owner_id"],
                bot_token=data["bot_token"],
                username=data.get("username"),
                status=CloneStatus(data["status"]),
                created_at=data.get("created_at"),
                last_seen=data.get("last_seen"),
                configuration=data.get("configuration", {}),
                metadata=data.get("metadata", {})
            )
            clones.append(clone)
        
        return clones
    
    async def update(self, clone: Clone) -> Clone:
        """Update clone information"""
        update_data = {
            "$set": {
                "username": clone.username,
                "status": clone.status.value,
                "last_seen": clone.last_seen or datetime.now(),
                "configuration": clone.configuration,
                "metadata": clone.metadata
            }
        }
        
        await self.collection.update_one({"_id": clone.bot_id}, update_data)
        return clone
    
    async def delete(self, clone_id: str) -> bool:
        """Delete a clone"""
        result = await self.collection.delete_one({"_id": clone_id})
        return result.deleted_count > 0
    
    async def get_active_clones(self) -> List[Clone]:
        """Get all active clones"""
        cursor = self.collection.find({"status": CloneStatus.ACTIVE.value})
        clones = []
        
        async for data in cursor:
            clone = Clone(
                bot_id=data["_id"],
                owner_id=data["owner_id"],
                bot_token=data["bot_token"],
                username=data.get("username"),
                status=CloneStatus(data["status"]),
                created_at=data.get("created_at"),
                last_seen=data.get("last_seen"),
                configuration=data.get("configuration", {}),
                metadata=data.get("metadata", {})
            )
            clones.append(clone)
        
        return clones
