
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config

# Subscription database
subscription_client = AsyncIOMotorClient(Config.DATABASE_URL)
subscription_db = subscription_client[Config.DATABASE_NAME]
subscriptions = subscription_db.subscriptions

async def create_subscription(clone_id: str, admin_id: int, tier: str, payment_verified: bool = False):
    """Create a new subscription"""
    pricing = {
        "monthly": {"months": 1, "price": 3.0},
        "quarterly": {"months": 3, "price": 8.0},
        "semi_annual": {"months": 6, "price": 15.0},
        "yearly": {"months": 12, "price": 26.0}
    }
    
    tier_data = pricing.get(tier, pricing["monthly"])
    
    subscription_data = {
        "_id": clone_id,
        "admin_id": admin_id,
        "tier": tier,
        "price": tier_data["price"],
        "created_at": datetime.now(),
        "expiry_date": datetime.now() + timedelta(days=tier_data["months"] * 30),
        "status": "active" if payment_verified else "pending",
        "payment_verified": payment_verified,
        "auto_renew": False
    }
    
    await subscriptions.update_one(
        {"_id": clone_id},
        {"$set": subscription_data},
        upsert=True
    )
    
    return subscription_data

async def get_subscription(clone_id: str):
    """Get subscription details"""
    return await subscriptions.find_one({"_id": clone_id})

async def activate_subscription(clone_id: str):
    """Activate a pending subscription"""
    await subscriptions.update_one(
        {"_id": clone_id},
        {"$set": {
            "status": "active",
            "payment_verified": True,
            "activated_at": datetime.now()
        }}
    )

async def extend_subscription(clone_id: str, months: int, additional_price: float):
    """Extend subscription by specified months"""
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

async def get_all_subscriptions():
    """Get all subscriptions"""
    return await subscriptions.find({}).to_list(None)

async def check_expired_subscriptions():
    """Check and update expired subscriptions"""
    expired = await subscriptions.find({
        "expiry_date": {"$lt": datetime.now()},
        "status": "active"
    }).to_list(None)
    
    for sub in expired:
        await subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": "expired"}}
        )
    
    return len(expired)


import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config

# Subscription database
sub_client = AsyncIOMotorClient(Config.DATABASE_URL)
sub_db = sub_client[Config.DATABASE_NAME]
subscriptions = sub_db.subscriptions
pricing_tiers = sub_db.pricing_tiers

# Pricing tiers
PRICING_TIERS = {
    "monthly": {"price": 3, "duration_days": 30, "name": "Monthly Plan"},
    "quarterly": {"price": 8, "duration_days": 90, "name": "3 Months Plan"},
    "semi_annual": {"price": 15, "duration_days": 180, "name": "6 Months Plan"},
    "yearly": {"price": 26, "duration_days": 365, "name": "Yearly Plan"}
}

async def init_pricing_tiers():
    """Initialize pricing tiers in database"""
    for tier_id, tier_data in PRICING_TIERS.items():
        await pricing_tiers.update_one(
            {"_id": tier_id},
            {"$set": tier_data},
            upsert=True
        )

async def create_subscription(clone_id: str, admin_id: int, tier: str, payment_verified: bool = False):
    """Create a new subscription for a clone"""
    tier_data = PRICING_TIERS.get(tier)
    if not tier_data:
        return False
    
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
        "auto_renewal": False
    }
    
    await subscriptions.update_one(
        {"_id": clone_id},
        {"$set": subscription_data},
        upsert=True
    )
    return True

async def get_subscription(clone_id: str):
    """Get subscription details for a clone"""
    return await subscriptions.find_one({"_id": clone_id})

async def verify_payment(clone_id: str):
    """Verify payment for a subscription"""
    await subscriptions.update_one(
        {"_id": clone_id},
        {"$set": {"payment_verified": True, "status": "active"}}
    )

async def check_expired_subscriptions():
    """Check and deactivate expired subscriptions"""
    expired_subs = await subscriptions.find({
        "expiry_date": {"$lt": datetime.now()},
        "status": "active"
    }).to_list(None)
    
    for sub in expired_subs:
        await subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": "expired"}}
        )
    
    return [sub["_id"] for sub in expired_subs]

async def extend_subscription(clone_id: str, tier: str):
    """Extend an existing subscription"""
    tier_data = PRICING_TIERS.get(tier)
    if not tier_data:
        return False
    
    current_sub = await get_subscription(clone_id)
    if not current_sub:
        return False
    
    # Extend from current expiry or now, whichever is later
    base_date = max(current_sub["expiry_date"], datetime.now())
    new_expiry = base_date + timedelta(days=tier_data["duration_days"])
    
    await subscriptions.update_one(
        {"_id": clone_id},
        {"$set": {
            "expiry_date": new_expiry,
            "status": "active",
            "last_extended": datetime.now()
        }}
    )
    return True

async def get_all_subscriptions():
    """Get all subscriptions for admin panel"""
    return await subscriptions.find({}).to_list(None)
