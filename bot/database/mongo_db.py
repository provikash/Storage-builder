
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
import pymongo

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
