import asyncio
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

# Clone subscription pricing tiers (for clone creation only)
PRICING_TIERS = {
    "monthly": {"name": "Monthly Plan", "price": 3.00, "duration_days": 30, "features": ["Basic Clone Features", "File Sharing", "Standard Support"]},
    "quarterly": {"name": "3 Months Plan", "price": 8.00, "duration_days": 90, "features": ["Extended Clone Features", "File Sharing", "Priority Support"]},
    "semi_annual": {"name": "6 Months Plan", "price": 15.00, "duration_days": 180, "features": ["Premium Clone Features", "File Sharing", "Advanced Support"]},
    "yearly": {"name": "Yearly Plan", "price": 26.00, "duration_days": 365, "features": ["All Clone Features", "File Sharing", "Premium Support", "Custom Settings"]}
}

# Token verification plans (separate from clone plans)
TOKEN_PLANS = {
    "basic": {"name": "Basic", "price": 5.00, "duration_days": 30, "tokens": 1000, "features": ["Search", "Download", "Basic Support"]},
    "premium": {"name": "Premium", "price": 10.00, "duration_days": 30, "tokens": 5000, "features": ["Search", "Download", "Upload", "Premium Support", "Auto Delete"]},
    "unlimited": {"name": "Unlimited", "price": 20.00, "duration_days": 30, "tokens": -1, "features": ["All Features", "Priority Support", "Custom Channels"]}
}

async def init_pricing_tiers():
    """Initialize pricing tiers in database"""
    try:
        await pricing_collection.update_one(
            {"_id": "pricing_tiers"},
            {"$set": {"tiers": PRICING_TIERS, "updated_at": datetime.now()}},
            upsert=True
        )
        logger.info("✅ Pricing tiers initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing pricing tiers: {e}")

async def create_subscription(bot_id: str, user_id: int, plan: str, payment_verified: bool = False):
    """Create a new subscription"""
    try:
        logger.info(f"Creating subscription for bot_id: {bot_id}, user_id: {user_id}, plan: {plan}")

        # Get plan details
        plan_data = PRICING_TIERS.get(plan)
        if not plan_data:
            logger.error(f"Invalid plan: {plan}")
            return False

        subscription_data = {
            "_id": bot_id,
            "bot_id": bot_id,
            "user_id": user_id,
            "admin_id": user_id,  # For backwards compatibility
            "plan": plan,
            "tier": plan,  # For backwards compatibility
            "plan_data": plan_data,
            "price": plan_data['price'],
            "status": "active" if payment_verified else "pending_payment",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=plan_data['duration_days']),
            "expiry_date": datetime.now() + timedelta(days=plan_data['duration_days']),  # For backwards compatibility
            "payment_verified": payment_verified,
            "tokens": plan_data.get('tokens', 1000),
            "features": plan_data.get('features', []),
            "auto_renewal": False,
            "total_paid": plan_data['price'] if payment_verified else 0
        }

        await subscriptions_collection.update_one(
            {"_id": bot_id},
            {"$set": subscription_data},
            upsert=True
        )

        logger.info(f"✅ Created subscription for bot {bot_id}: {plan} - ${plan_data['price']}")
        return True

    except Exception as e:
        logger.error(f"❌ Error creating subscription for bot {bot_id}: {e}")
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
    """Get available clone pricing tiers"""
    try:
        # Try to get from database first
        pricing_doc = await pricing_collection.find_one({"_id": "pricing_tiers"})
        if pricing_doc:
            return pricing_doc["tiers"]
        else:
            # Insert default tiers
            await init_pricing_tiers()
            return PRICING_TIERS
    except Exception as e:
        logger.error(f"Error getting pricing tiers: {e}")
        return PRICING_TIERS

async def get_token_plans():
    """Get available token verification plans"""
    try:
        # Try to get from database first
        token_doc = await pricing_collection.find_one({"_id": "token_plans"})
        if token_doc:
            return token_doc["plans"]
        else:
            # Insert default token plans
            await pricing_collection.update_one(
                {"_id": "token_plans"},
                {"$set": {"plans": TOKEN_PLANS, "updated_at": datetime.now()}},
                upsert=True
            )
            return TOKEN_PLANS
    except Exception as e:
        logger.error(f"Error getting token plans: {e}")
        return TOKEN_PLANS

async def get_subscription(bot_id: str):
    """Get subscription by bot ID"""
    try:
        return await subscriptions_collection.find_one({"_id": bot_id})
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        return None

async def check_expired_subscriptions():
    """Check and return expired subscription IDs"""
    try:
        expired_subs = await subscriptions_collection.find({
            "$or": [
                {"expires_at": {"$lt": datetime.now()}},
                {"expiry_date": {"$lt": datetime.now()}}
            ],
            "status": "active"
        }).to_list(None)

        expired_ids = []
        for sub in expired_subs:
            # Mark as expired
            await subscriptions_collection.update_one(
                {"_id": sub["_id"]},
                {"$set": {"status": "expired", "expired_at": datetime.now()}}
            )
            expired_ids.append(sub["bot_id"])

        return expired_ids
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}")
        return []

async def get_all_subscriptions():
    """Get all subscriptions"""
    try:
        all_subs = await subscriptions_collection.find({}).to_list(length=None)
        return all_subs
    except Exception as e:
        logger.error(f"Error getting all subscriptions: {e}")
        return []

async def delete_subscription(bot_id: str):
    """Delete a subscription"""
    try:
        result = await subscriptions_collection.delete_one({"_id": bot_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting subscription {bot_id}: {e}")
        return False

async def get_subscription_stats():
    """Get subscription statistics"""
    try:
        total = await subscriptions_collection.count_documents({})
        active = await subscriptions_collection.count_documents({"status": "active"})
        pending = await subscriptions_collection.count_documents({"status": "pending_payment"})
        expired = await subscriptions_collection.count_documents({"status": "expired"})

        # Calculate total revenue
        revenue_pipeline = [
            {"$match": {"payment_verified": True}},
            {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}}
        ]
        revenue_result = await subscriptions_collection.aggregate(revenue_pipeline).to_list(None)
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

async def extend_subscription(clone_id: str, months: int, additional_price: float):
    """Extend subscription by specified months"""
    try:
        subscription = await get_subscription(clone_id)
        if not subscription:
            raise Exception("Subscription not found")

        # Extend from current expiry date or now (whichever is later)
        current_expiry = subscription.get('expires_at') or subscription.get('expiry_date', datetime.now())
        if current_expiry < datetime.now():
            current_expiry = datetime.now()

        new_expiry = current_expiry + timedelta(days=months * 30)

        await subscriptions_collection.update_one(
            {"_id": clone_id},
            {"$set": {
                "expires_at": new_expiry,
                "expiry_date": new_expiry,  # For backwards compatibility
                "status": "active",
                "last_extended": datetime.now()
            },
            "$inc": {"total_paid": additional_price}}
        )

        logger.info(f"✅ Extended subscription for clone {clone_id} by {months} months (+${additional_price})")

    except Exception as e:
        logger.error(f"❌ Error extending subscription for clone {clone_id}: {e}")
        raise