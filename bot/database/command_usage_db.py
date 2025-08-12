from datetime import datetime
from .connection import db
from info import Config

command_usage_col = db["command_usage"]

async def get_user_command_count(user_id: int) -> int:
    """Get current command count for user"""
    try:
        user_data = await command_usage_col.find_one({"_id": user_id})
        return user_data.get("command_count", 0) if user_data else 0
    except Exception as e:
        print(f"Error getting command count for {user_id}: {e}")
        return 0

async def increment_command_count(user_id: int):
    """Increment command count for user"""
    await command_usage_col.update_one(
        {"_id": user_id},
        {
            "$inc": {"command_count": 1},
            "$set": {"last_command_at": datetime.utcnow()}
        },
        upsert=True
    )

async def reset_command_count(user_id: int):
    """Reset command count for a user"""
    try:
        await command_usage_col.update_one(
            {"_id": user_id},
            {"$set": {"command_count": 0}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error resetting command count for {user_id}: {e}")
        return False

async def get_command_stats(user_id: int) -> dict:
    """Get detailed command usage stats for user"""
    user_data = await command_usage_col.find_one({"_id": user_id})
    if not user_data:
        return {"command_count": 0, "last_command_at": None, "last_reset": None}
    return {
        "command_count": user_data.get("command_count", 0),
        "last_command_at": user_data.get("last_command_at"),
        "last_reset": user_data.get("last_reset")
    }