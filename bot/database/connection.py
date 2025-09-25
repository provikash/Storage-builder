from motor.motor_asyncio import AsyncIOMotorClient
from info import Config

client = AsyncIOMotorClient(Config.DATABASE_URI)
db = client[Config.DATABASE_NAME]

async def get_database():
    """Get database instance for health checks"""
    return db
