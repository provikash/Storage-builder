import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Subscription database
subscription_client = AsyncIOMotorClient(Config.DATABASE_URL)
subscription_db = subscription_client[Config.DATABASE_NAME]
subscriptions = subscription_db.subscriptions
pricing_tiers = subscription_db.pricing_tiers

# Pricing tiers
PRICING_TIERS = {
    "monthly": {"price": 3, "duration_days": 30, "name": "Monthly Plan"},
    "quarterly": {"price": 8, "duration_days": 90, "name": "3 Months Plan"},
    "semi_annual": {"price": 15, "duration_days": 180, "name": "6 Months Plan"},
    "yearly": {"price": 26, "duration_days": 365, "name": "Yearly Plan"}
}

async def init_pricing_tiers():
    """Initialize pricing tiers in database"""
    try:
        for tier_id, tier_data in PRICING_TIERS.items():
            await pricing_tiers.update_one(
                {"_id": tier_id},
                {"$set": tier_data},
                upsert=True
            )
        logger.info("✅ Pricing tiers initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing pricing tiers: {e}")

async def create_subscription(clone_id: str, admin_id: int, tier: str, payment_verified: bool = False):
    """Create a new subscription for a clone"""
    try:
        tier_data = PRICING_TIERS.get(tier, PRICING_TIERS["monthly"])

        expiry_date = datetime.now() + timedelta(days=tier_data["duration_days"])

        subscription_data = {
            "_id": clone_id,
            "admin_id": admin_id,
            "tier": tier,
            "price": tier_data["price"],
            "created_at": datetime.now(),
            "expiry_date": expiry_date,
            "payment_verified": payment_verified,
            "status": "active" if payment_verified else "pending",
            "auto_renewal": False,
            "total_paid": tier_data["price"] if payment_verified else 0
        }

        await subscriptions.update_one(
            {"_id": clone_id},
            {"$set": subscription_data},
            upsert=True
        )

        logger.info(f"✅ Created subscription for clone {clone_id}: {tier} - ${tier_data['price']}")
        return subscription_data

    except Exception as e:
        logger.error(f"❌ Error creating subscription for clone {clone_id}: {e}")
        return None

async def get_subscription(clone_id: str):
    """Get subscription details for a clone"""
    try:
        return await subscriptions.find_one({"_id": clone_id})
    except Exception as e:
        logger.error(f"❌ Error getting subscription for clone {clone_id}: {e}")
        return None

async def activate_subscription(clone_id: str):
    """Activate a pending subscription (payment verified)"""
    try:
        await subscriptions.update_one(
            {"_id": clone_id},
            {"$set": {
                "payment_verified": True,
                "status": "active",
                "activated_at": datetime.now()
            }}
        )
        logger.info(f"✅ Activated subscription for clone {clone_id}")
    except Exception as e:
        logger.error(f"❌ Error activating subscription for clone {clone_id}: {e}")

async def check_expired_subscriptions():
    """Check and deactivate expired subscriptions"""
    try:
        expired_subs = await subscriptions.find({
            "expiry_date": {"$lt": datetime.now()},
            "status": "active"
        }).to_list(None)

        expired_ids = []
        for sub in expired_subs:
            await subscriptions.update_one(
                {"_id": sub["_id"]},
                {"$set": {"status": "expired", "expired_at": datetime.now()}}
            )
            expired_ids.append(sub["_id"])

        if expired_ids:
            logger.info(f"⚠️ Expired {len(expired_ids)} subscriptions: {expired_ids}")

        return expired_ids

    except Exception as e:
        logger.error(f"❌ Error checking expired subscriptions: {e}")
        return []

async def extend_subscription(clone_id: str, months: int, additional_price: float):
    """Extend subscription by specified months"""
    try:
        subscription = await get_subscription(clone_id)
        if not subscription:
            raise Exception("Subscription not found")

        # Extend from current expiry date or now (whichever is later)
        current_expiry = subscription.get('expiry_date', datetime.now())
        if current_expiry < datetime.now():
            current_expiry = datetime.now()

        new_expiry = current_expiry + timedelta(days=months * 30)

        await subscriptions.update_one(
            {"_id": clone_id},
            {"$set": {
                "expiry_date": new_expiry,
                "status": "active",
                "last_extended": datetime.now()
            },
            "$inc": {"total_paid": additional_price}}
        )

        logger.info(f"✅ Extended subscription for clone {clone_id} by {months} months (+${additional_price})")

    except Exception as e:
        logger.error(f"❌ Error extending subscription for clone {clone_id}: {e}")
        raise

async def get_all_subscriptions():
    """Get all subscriptions"""
    try:
        all_subs = await subscriptions.find({}).to_list(length=None)
        return all_subs
    except Exception as e:
        print(f"Error getting all subscriptions: {e}")
        return []

async def delete_subscription(bot_id: str):
    """Delete a subscription"""
    try:
        result = await subscriptions.delete_one({"_id": bot_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"ERROR: Error deleting subscription {bot_id}: {e}")
        return False

async def get_subscription_stats():
    """Get subscription statistics"""
    try:
        total = await subscriptions.count_documents({})
        active = await subscriptions.count_documents({"status": "active"})
        pending = await subscriptions.count_documents({"status": "pending"})
        expired = await subscriptions.count_documents({"status": "expired"})

        # Calculate total revenue
        revenue_pipeline = [
            {"$match": {"payment_verified": True}},
            {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}}
        ]
        revenue_result = await subscriptions.aggregate(revenue_pipeline).to_list(None)
        total_revenue = revenue_result[0]["total"] if revenue_result else 0

        return {
            "total": total,
            "active": active,
            "pending": pending,
            "expired": expired,
            "total_revenue": total_revenue
        }
    except Exception as e:
        logger.error(f"❌ Error getting subscription stats: {e}")
        return {"total": 0, "active": 0, "pending": 0, "expired": 0, "total_revenue": 0}
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Subscription database
subscription_client = AsyncIOMotorClient(Config.DATABASE_URL)
subscription_db = subscription_client[Config.DATABASE_NAME]
subscriptions_collection = subscription_db.subscriptions
pricing_collection = subscription_db.pricing

async def create_subscription(bot_id: str, user_id: int, plan: str, payment_verified: bool = False):
    """Create a new subscription"""
    try:
        # Get plan details
        plans = await get_pricing_tiers()
        plan_data = plans.get(plan)
        
        if not plan_data:
            return False
        
        subscription_data = {
            "_id": bot_id,
            "bot_id": bot_id,
            "user_id": user_id,
            "plan": plan,
            "plan_data": plan_data,
            "status": "active" if payment_verified else "pending_payment",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=plan_data['duration_days']),
            "payment_verified": payment_verified,
            "tokens": plan_data.get('tokens', 1000),
            "features": plan_data.get('features', [])
        }
        
        await subscriptions_collection.update_one(
            {"_id": bot_id},
            {"$set": subscription_data},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return False

async def activate_subscription(bot_id: str):
    """Activate a subscription"""
    try:
        await subscriptions_collection.update_one(
            {"_id": bot_id},
            {"$set": {"status": "active", "activated_at": datetime.now()}}
        )
        return True
    except Exception as e:
        logger.error(f"Error activating subscription: {e}")
        return False

async def get_pricing_tiers():
    """Get available pricing tiers"""
    default_tiers = {
        "basic": {
            "name": "Basic",
            "price": 5.00,
            "duration_days": 30,
            "tokens": 1000,
            "features": ["Search", "Download", "Basic Support"]
        },
        "premium": {
            "name": "Premium",
            "price": 10.00,
            "duration_days": 30,
            "tokens": 5000,
            "features": ["Search", "Download", "Upload", "Premium Support", "Auto Delete"]
        },
        "unlimited": {
            "name": "Unlimited",
            "price": 20.00,
            "duration_days": 30,
            "tokens": -1,  # Unlimited
            "features": ["All Features", "Priority Support", "Custom Channels"]
        }
    }
    
    try:
        # Try to get from database first
        pricing_doc = await pricing_collection.find_one({"_id": "pricing_tiers"})
        if pricing_doc:
            return pricing_doc["tiers"]
        else:
            # Insert default tiers
            await pricing_collection.update_one(
                {"_id": "pricing_tiers"},
                {"$set": {"tiers": default_tiers, "updated_at": datetime.now()}},
                upsert=True
            )
            return default_tiers
    except Exception as e:
        logger.error(f"Error getting pricing tiers: {e}")
        return default_tiers

async def get_subscription(bot_id: str):
    """Get subscription by bot ID"""
    try:
        return await subscriptions_collection.find_one({"_id": bot_id})
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        return None
