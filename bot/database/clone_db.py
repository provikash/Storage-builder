import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config

# Clone database
clone_client = AsyncIOMotorClient(Config.DATABASE_URL)
clone_db = clone_client[Config.DATABASE_NAME]
clones = clone_db.clones
clone_configs = clone_db.clone_configs
global_settings = clone_db.global_settings

async def create_clone(bot_token: str, admin_id: int, db_url: str):
    """Create a new clone entry with separate database"""
    from pyrogram import Client
    from motor.motor_asyncio import AsyncIOMotorClient
    try:
        # Validate bot token
        test_client = Client(
            name=f"test_{bot_token[:10]}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=bot_token
        )

        await test_client.start()
        me = await test_client.get_me()

        # Test clone's database connection
        try:
            clone_db_client = AsyncIOMotorClient(db_url)
            clone_db = clone_db_client[f"clone_{me.id}"]
            # Test connection
            await clone_db.command("ping")
            clone_db_client.close()
        except Exception as db_e:
            await test_client.stop()
            return False, f"Database connection failed: {str(db_e)}"

        clone_data = {
            "_id": str(me.id),
            "bot_id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "token": bot_token,
            "admin_id": admin_id,
            "db_url": db_url,
            "db_name": f"clone_{me.id}",
            "created_at": datetime.now(),
            "status": "pending_payment",
            "last_seen": datetime.now()
        }

        await clones.update_one(
            {"_id": str(me.id)},
            {"$set": clone_data},
            upsert=True
        )

        # Create default config
        await create_clone_config(str(me.id))

        await test_client.stop()
        return True, clone_data

    except Exception as e:
        return False, str(e)

async def create_clone_config(clone_id: str):
    """Create default configuration for a clone"""
    default_config = {
        "_id": clone_id,
        "features": {
            "search": True,
            "upload": True,
            "token_verification": True,
            "premium": True,
            "auto_delete": True,
            "batch_links": True
        },
        "token_settings": {
            "mode": "one_time",  # or "command_limit"
            "command_limit": 100,
            "pricing": 1.0,
            "enabled": True
        },
        "channels": {
            "force_channels": [],
            "request_channels": []
        },
        "custom_messages": {
            "start_message": "",
            "help_message": "",
            "about_message": ""
        },
        "updated_at": datetime.now()
    }

    await clone_configs.update_one(
        {"_id": clone_id},
        {"$set": default_config},
        upsert=True
    )

async def get_clone(clone_id: str):
    """Get clone details"""
    return await clones.find_one({"_id": clone_id})

async def get_clone_config(clone_id: str):
    """Get clone configuration"""
    return await clone_configs.find_one({"_id": clone_id})

async def update_clone_config(clone_id: str, config_updates: dict):
    """Update clone configuration"""
    config_updates["updated_at"] = datetime.now()
    await clone_configs.update_one(
        {"_id": clone_id},
        {"$set": config_updates}
    )

async def get_all_clones():
    """Get all clones for admin panel"""
    return await clones.find({}).to_list(None)

async def deactivate_clone(clone_id: str):
    """Deactivate a clone"""
    await clones.update_one(
        {"_id": clone_id},
        {"$set": {"status": "deactivated", "deactivated_at": datetime.now()}}
    )

async def activate_clone(clone_id: str):
    """Activate a clone"""
    await clones.update_one(
        {"_id": clone_id},
        {"$set": {"status": "active"}}
    )

# Global settings
async def set_global_setting(key: str, value):
    """Set a global setting"""
    await global_settings.update_one(
        {"_id": key},
        {"$set": {"value": value, "updated_at": datetime.now()}},
        upsert=True
    )

async def get_global_setting(key: str, default=None):
    """Get a global setting"""
    setting = await global_settings.find_one({"_id": key})
    return setting["value"] if setting else default

async def get_global_force_channels():
    """Get global force channels"""
    return await get_global_setting("global_force_channels", [])

async def set_global_force_channels(channels: list):
    """Set global force channels"""
    await set_global_setting("global_force_channels", channels)

async def get_global_about():
    """Get global about page content"""
    result = await global_settings.find_one({"_id": "global_about"})
    return result.get('about_text', '') if result else ''

async def set_global_about(about_text: str):
    """Set global about page content"""
    await global_settings.update_one(
        {"_id": "global_about"},
        {"$set": {"about_text": about_text, "updated_at": datetime.now()}},
        upsert=True
    )

async def get_total_subscriptions():
    """Get total number of subscriptions"""
    try:
        from bot.database.premium_db import premium_collection
        return await premium_collection.count_documents({})
    except:
        return 0

async def get_active_subscriptions():
    """Get number of active subscriptions"""
    try:
        from bot.database.premium_db import premium_collection
        from datetime import datetime
        return await premium_collection.count_documents({
            "$or": [
                {"tokens": {"$gt": 0}},
                {"tokens": -1}  # unlimited
            ]
        })
    except:
        return 0

async def get_total_clones_count():
    """Get total number of clones"""
    try:
        return await clones.count_documents({})
    except:
        return 0

async def get_active_clones_count():
    """Get number of active clones"""
    try:
        return await clones.count_documents({"status": "active"})
    except:
        return 0

async def get_total_users_count():
    """Get total number of users"""
    try:
        from bot.database.users import collection as users_collection
        return await users_collection.count_documents({})
    except:
        return 0

async def get_total_files_count():
    """Get total number of indexed files"""
    try:
        from bot.database.index_db import collection as files_collection
        return await files_collection.count_documents({})
    except:
        return 0