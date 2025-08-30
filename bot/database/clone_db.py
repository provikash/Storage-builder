import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Clone database
clone_client = AsyncIOMotorClient(Config.DATABASE_URL)
clone_db = clone_client[Config.DATABASE_NAME] # Corrected to use Config.DATABASE_DB_NAME
clones_collection = clone_db.clones # Renamed to avoid conflict with the import
clone_configs_collection = clone_db.clone_configs # Renamed for clarity
global_settings_collection = clone_db.global_settings # Renamed for clarity


async def create_clone(clone_data: dict):
    """Create a new clone entry"""
    try:
        await clones_collection.update_one(
            {"_id": clone_data["_id"]},
            {"$set": clone_data},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error creating clone: {e}")
        return False

async def create_clone_with_db(bot_token, admin_id, db_url):
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
            clone_db_instance = clone_db_client[f"clone_{me.id}"]
            # Test connection
            await clone_db_client.admin.command("ping") # Corrected to use admin.command for ping
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
            "bot_token": bot_token,  # Add both for compatibility
            "admin_id": admin_id,
            "db_url": db_url,
            "mongodb_url": db_url,  # Add both for compatibility
            "db_name": f"clone_{me.id}",
            "created_at": datetime.now(),
            "status": "pending_payment",
            "last_seen": datetime.now()
        }

        await clones_collection.update_one(
            {"_id": str(me.id)},
            {"$set": clone_data},
            upsert=True
        )

        # Create default config
        await create_clone_config(str(me.id))

        await test_client.stop()
        return True, clone_data

    except Exception as e:
        logger.error(f"Error creating clone: {e}") # Added logging for the exception
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
            "batch_links": True,
            "random_button": True,
            "recent_button": True,
            "popular_button": True # Added popular button
        },
        "token_settings": {
            "mode": "one_time",  # or "command_limit"
            "command_limit": 100,
            "pricing": 1.0,
            "enabled": True
        },
        "shortener_settings": {
            "enabled": True,
            "api_url": "https://teraboxlinks.com/",
            "api_key": ""
        },
        "time_settings": {
            "auto_delete_time": 600,
            "session_timeout": 3600,
            "cooldown_time": 30
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

    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": default_config},
        upsert=True
    )

async def get_clone(bot_id: str):
    """Get clone data by bot ID"""
    try:
        clone = await clones_collection.find_one({"_id": bot_id}) # Corrected collection name
        return clone
    except Exception as e:
        logger.error(f"Error getting clone {bot_id}: {e}") # Added logging
        return None

async def get_clone_config(clone_id: str):
    """Get clone configuration"""
    try:
        result = await clone_configs_collection.find_one({"_id": clone_id})
        return result
    except Exception as e:
        logger.error(f"Error getting clone config: {e}")
        return None

async def get_clone_by_bot_token(bot_token):
    """Get clone data by bot token"""
    try:
        if not bot_token:
            return None
        
        # Try to find by bot_token first
        result = await clones_collection.find_one({"bot_token": bot_token})
        if result:
            return result
            
        # If not found, try with bot_id extracted from token
        bot_id = int(bot_token.split(':')[0]) if ':' in bot_token else int(bot_token)
        result = await clones_collection.find_one({"bot_id": bot_id})
        return result
    except Exception as e:
        logger.error(f"Error getting clone by bot token: {e}")
        return None

async def update_clone_config(clone_id: str, config_updates: dict):
    """Update clone configuration"""
    config_updates["updated_at"] = datetime.now()
    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": config_updates}
    )

# Clone admin settings functions
async def toggle_clone_feature(clone_id: str, feature: str, enabled: bool):
    """Toggle a specific feature for a clone"""
    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": {f"features.{feature}": enabled, "updated_at": datetime.now()}}
    )

async def update_clone_shortener(clone_id: str, api_url: str, api_key: str):
    """Update clone shortener settings"""
    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": {
            "shortener_settings.api_url": api_url,
            "shortener_settings.api_key": api_key,
            "updated_at": datetime.now()
        }}
    )

async def update_clone_token_verification(clone_id: str, mode: str, command_limit: int = None, pricing: float = None, enabled: bool = None):
    """Update clone token verification settings"""
    update_data = {"token_settings.mode": mode, "updated_at": datetime.now()}
    if command_limit is not None:
        update_data["token_settings.command_limit"] = command_limit
    if pricing is not None:
        update_data["token_settings.pricing"] = pricing
    if enabled is not None:
        update_data["token_settings.enabled"] = enabled
    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": update_data}
    )

async def update_clone_time_settings(clone_id: str, setting: str, value: int):
    """Update clone time-based settings"""
    await clone_configs_collection.update_one(
        {"_id": clone_id},
        {"$set": {
            f"time_settings.{setting}": value,
            "updated_at": datetime.now()
        }}
    )

async def get_clone_admin_id(clone_id: str):
    """Get the admin ID for a specific clone"""
    clone = await clones_collection.find_one({"_id": clone_id})
    return clone.get("admin_id") if clone else None

async def get_all_clones():
    """Get all clones"""
    try:
        clones_list = await clones_collection.find({}).to_list(None)
        return clones_list
    except Exception as e:
        logger.error(f"ERROR: Error getting all clones: {e}")
        return []

async def deactivate_clone(clone_id: str):
    """Deactivate a clone"""
    await clones_collection.update_one(
        {"_id": clone_id},
        {"$set": {"status": "deactivated", "deactivated_at": datetime.now()}}
    )

async def activate_clone(clone_id: str):
    """Activate a clone"""
    await clones_collection.update_one(
        {"_id": clone_id},
        {"$set": {"status": "active", "activated_at": datetime.now()}}
    )
    return True

# Global settings
async def set_global_setting(key: str, value):
    """Set a global setting"""
    await global_settings_collection.update_one(
        {"_id": key},
        {"$set": {"value": value, "updated_at": datetime.now()}},
        upsert=True
    )

async def get_global_setting(key: str, default=None):
    """Get a global setting"""
    setting = await global_settings_collection.find_one({"_id": key})
    return setting["value"] if setting else default

async def get_global_force_channels():
    """Get global force channels"""
    return await get_global_setting("global_force_channels", [])

async def set_global_force_channels(channels: list):
    """Set global force channels"""
    await set_global_setting("global_force_channels", channels)

async def get_global_about():
    """Get global about message"""
    try:
        settings = await global_settings_collection.find_one({"key": "global_about"})
        return settings.get("value", "") if settings else ""
    except Exception as e:
        logger.error(f"❌ Error getting global about: {e}")
        return ""

async def set_global_about(about_text: str):
    """Set global about message"""
    try:
        await global_settings_collection.update_one(
            {"key": "global_about"},
            {"$set": {"value": about_text, "updated_at": datetime.now()}},
            upsert=True
        )
        logger.info(f"✅ Global about message updated")
        return True
    except Exception as e:
        logger.error(f"❌ Error setting global about: {e}")
        return False

async def get_user_clones(user_id: int):
    """Get all clones belonging to a user"""
    try:
        clones = await clones_collection.find({"admin_id": user_id}).to_list(None)
        return clones
    except Exception as e:
        logger.error(f"❌ Error getting user clones for {user_id}: {e}")
        return []

async def get_total_subscriptions():
    """Get total number of subscriptions"""
    try:
        from bot.database.premium_db import premium_collection
        return await premium_collection.count_documents({})
    except Exception as e: # Added exception handling
        logger.error(f"Error getting total subscriptions: {e}")
        return 0

async def update_clone_setting(bot_id: str, setting_key: str, setting_value):
    """Update a specific setting for a clone"""
    try:
        await clones_collection.update_one(
            {"bot_id": bot_id},
            {"$set": {setting_key: setting_value, "updated_at": datetime.now()}}
        )
        logger.info(f"✅ Updated {setting_key} for clone {bot_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating clone setting {setting_key}: {e}")
        return False

async def get_clone_user_count(bot_id: str):
    """Get user count for a specific clone"""
    try:
        # This would need to be implemented based on your user tracking system
        # For now, return a placeholder
        return await clones_collection.count_documents({"bot_id": bot_id})
    except Exception as e:
        logger.error(f"Error getting user count for clone {bot_id}: {e}")
        return 0

async def get_clone_file_count(bot_id: str):
    """Get file count for a specific clone"""
    try:
        # This would need to be implemented based on your file tracking system
        # For now, return a placeholder
        return 0
    except Exception as e:
        logger.error(f"Error getting file count for clone {bot_id}: {e}")
        return 0

async def get_clone_by_bot_token(bot_token: str):
    """Get clone data by bot token"""
    try:
        return await clones_collection.find_one({"bot_token": bot_token})
    except Exception as e:
        logger.error(f"❌ Error getting clone by token: {e}")
        return None

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
    except Exception as e: # Added exception handling
        logger.error(f"Error getting active subscriptions: {e}")
        return 0

async def get_total_clones_count():
    """Get total number of clones"""
    try:
        return await clones_collection.count_documents({})
    except Exception as e: # Added exception handling
        logger.error(f"Error getting total clones count: {e}")
        return 0

async def get_active_clones_count():
    """Get number of active clones"""
    try:
        return await clones_collection.count_documents({"status": "active"})
    except Exception as e: # Added exception handling
        logger.error(f"Error getting active clones count: {e}")
        return 0

async def get_total_users_count():
    """Get total number of users"""
    try:
        from bot.database.users import collection as users_collection
        return await users_collection.count_documents({})
    except Exception as e: # Added exception handling
        logger.error(f"Error getting total users count: {e}")
        return 0

async def get_total_files_count():
    """Get total number of indexed files"""
    try:
        from bot.database.index_db import collection as files_collection
        return await files_collection.count_documents({})
    except Exception as e: # Added exception handling
        logger.error(f"Error getting total files count: {e}")
        return 0

# Missing helper functions for mother admin panel
async def get_clone_by_id_from_db(clone_id: str):
    """Get a specific clone by its ID from the database"""
    try:
        return await clones_collection.find_one({"_id": clone_id})
    except Exception as e:
        logger.error(f"❌ Error getting clone {clone_id}: {e}")
        return None

async def stop_clone_in_db(clone_id: str):
    """Update clone status to stopped in the database"""
    try:
        await clones_collection.update_one(
            {"_id": clone_id},
            {"$set": {"status": "stopped", "stopped_at": datetime.now()}}
        )
        logger.info(f"✅ Marked clone {clone_id} as stopped in database")
    except Exception as e:
        logger.error(f"❌ Error stopping clone {clone_id} in DB: {e}")

async def start_clone_in_db(clone_id: str):
    """Update clone status to running in the database"""
    try:
        await clones_collection.update_one(
            {"_id": clone_id},
            {"$set": {"status": "active", "started_at": datetime.now()}}
        )
        logger.info(f"✅ Marked clone {clone_id} as active in database")
    except Exception as e:
        logger.error(f"❌ Error starting clone {clone_id} in DB: {e}")

async def get_clone_statistics():
    """Get comprehensive clone statistics"""
    try:
        total_clones = await clones_collection.count_documents({})
        active_clones = await clones_collection.count_documents({"status": "active"})
        pending_clones = await clones_collection.count_documents({"status": "pending_payment"})
        deactivated_clones = await clones_collection.count_documents({"status": "deactivated"})

        return {
            "total": total_clones,
            "active": active_clones,
            "pending": pending_clones,
            "deactivated": deactivated_clones
        }
    except Exception as e:
        logger.error(f"❌ Error getting clone statistics: {e}")
        return {"total": 0, "active": 0, "pending": 0, "deactivated": 0}

async def update_clone_last_seen(clone_id: str):
    """Update clone's last seen timestamp"""
    try:
        await clones_collection.update_one(
            {"_id": clone_id},
            {"$set": {"last_seen": datetime.now()}}
        )
    except Exception as e:
        logger.error(f"❌ Error updating last seen for clone {clone_id}: {e}")

async def delete_clone(bot_id: str):
    """Delete a clone completely"""
    try:
        result = await clones_collection.delete_one({"_id": bot_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"ERROR: Error deleting clone {bot_id}: {e}")
        return False

async def update_clone_status(bot_id: str, status: str):
    """Update clone status"""
    try:
        await clones_collection.update_one(
            {"_id": bot_id},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
        return True
    except Exception as e:
        logger.error(f"ERROR: Error updating clone status {bot_id}: {e}")
        return False

async def delete_clone_config(bot_id: str):
    """Delete clone configuration"""
    try:
        result = await clone_configs_collection.delete_one({"_id": bot_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"ERROR: Error deleting clone config {bot_id}: {e}")
        return False

# Create clone requests collection
clone_requests_collection = clone_db.clone_requests

async def get_all_clone_requests(status: str = None):
    """Get all clone requests, optionally filtered by status"""
    try:
        filter_dict = {}
        if status:
            filter_dict["status"] = status

        requests = await clone_requests_collection.find(filter_dict).to_list(length=None)
        return requests
    except Exception as e:
        logger.error(f"Error getting clone requests: {e}")
        return []

async def approve_clone_request(request_id: str):
    """Approve a clone request"""
    try:
        result = await clone_requests_collection.update_one(
            {"request_id": request_id},
            {"$set": {"status": "approved", "approved_at": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error approving request {request_id}: {e}")
        return False

async def reject_clone_request(request_id: str):
    """Reject a clone request"""
    try:
        result = await clone_requests_collection.update_one(
            {"request_id": request_id},
            {"$set": {"status": "rejected", "rejected_at": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error rejecting request {request_id}: {e}")
        return False

async def create_clone_request(request_data):
    """Create a new clone request"""
    try:
        await clone_requests_collection.insert_one(request_data)
        logger.info(f"SUCCESS: Created clone request {request_data['request_id']}")
        return True
    except Exception as e:
        logger.error(f"ERROR: Error creating clone request: {e}")
        return False

async def get_clone_request(request_id: str):
    """Get clone request by ID - alias for compatibility"""
    try:
        request = await clone_requests_collection.find_one({"request_id": request_id})
        return request
    except Exception as e:
        logger.error(f"Error getting clone request {request_id}: {e}")
        return None

async def get_clone_request_by_id(request_id: str):
    """Get a specific clone request by ID"""
    try:
        request = await clone_requests_collection.find_one({"request_id": request_id})
        return request
    except Exception as e:
        logger.error(f"ERROR: Error getting clone request {request_id}: {e}")
        return None

async def get_clone_by_token(bot_token: str):
    """Get clone by bot token"""
    try:
        clone = await clones_collection.find_one({"bot_token": bot_token})
        return clone
    except Exception as e:
        logger.error(f"ERROR: Error getting clone by token: {e}")
        return None

async def get_user_clones(user_id: int):
    """Get all clones for a specific user"""
    try:
        clones = await clones_collection.find({"admin_id": user_id}).to_list(None)
        return clones
    except Exception as e:
        logger.error(f"ERROR: Error getting user clones for {user_id}: {e}")
        return []

async def get_pending_clone_request(user_id: int):
    """Get pending clone request for user"""
    try:
        return await clone_requests_collection.find_one({
            "user_id": user_id,
            "status": "pending"
        })
    except Exception as e:
        logger.error(f"Error getting pending request for user {user_id}: {e}")
        return None