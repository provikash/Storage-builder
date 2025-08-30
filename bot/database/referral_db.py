
from datetime import datetime
from .connection import db
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Collections
referrals_collection = db['referrals']
referral_stats_collection = db['referral_stats']

async def create_referral_code(user_id: int):
    """Create or get existing referral code for user"""
    try:
        # Check if user already has a referral code
        existing = await referrals_collection.find_one({"user_id": user_id})
        if existing:
            return existing['referral_code']
        
        # Generate unique referral code
        import hashlib
        import random
        seed = f"{user_id}_{datetime.now().timestamp()}_{random.randint(1000, 9999)}"
        referral_code = hashlib.md5(seed.encode()).hexdigest()[:8].upper()
        
        # Ensure uniqueness
        while await referrals_collection.find_one({"referral_code": referral_code}):
            seed = f"{user_id}_{datetime.now().timestamp()}_{random.randint(1000, 9999)}"
            referral_code = hashlib.md5(seed.encode()).hexdigest()[:8].upper()
        
        # Store referral code
        await referrals_collection.insert_one({
            "user_id": user_id,
            "referral_code": referral_code,
            "created_at": datetime.now(),
            "total_referrals": 0,
            "total_earnings": 0.0,
            "active": True
        })
        
        logger.info(f"✅ Created referral code {referral_code} for user {user_id}")
        return referral_code
        
    except Exception as e:
        logger.error(f"❌ Error creating referral code for user {user_id}: {e}")
        return None

async def get_referral_code(user_id: int):
    """Get user's referral code"""
    try:
        result = await referrals_collection.find_one({"user_id": user_id})
        return result['referral_code'] if result else None
    except Exception as e:
        logger.error(f"❌ Error getting referral code for user {user_id}: {e}")
        return None

async def get_referrer_by_code(referral_code: str):
    """Get referrer user ID by referral code"""
    try:
        result = await referrals_collection.find_one({"referral_code": referral_code, "active": True})
        return result['user_id'] if result else None
    except Exception as e:
        logger.error(f"❌ Error getting referrer for code {referral_code}: {e}")
        return None

async def record_referral(referrer_id: int, referred_id: int, referral_code: str):
    """Record a new referral"""
    try:
        # Check if referral already exists
        existing = await referral_stats_collection.find_one({
            "referrer_id": referrer_id,
            "referred_id": referred_id
        })
        
        if existing:
            logger.info(f"⚠️ Referral already exists: {referrer_id} -> {referred_id}")
            return False
        
        # Record the referral
        await referral_stats_collection.insert_one({
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "referral_code": referral_code,
            "referred_at": datetime.now(),
            "reward_paid": False,
            "premium_purchased": False,
            "reward_amount": 0.0
        })
        
        # Update referrer's total count
        await referrals_collection.update_one(
            {"user_id": referrer_id},
            {"$inc": {"total_referrals": 1}}
        )
        
        logger.info(f"✅ Recorded referral: {referrer_id} -> {referred_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error recording referral: {e}")
        return False

async def process_referral_reward(referred_id: int, premium_amount: float):
    """Process referral reward when referred user buys premium"""
    try:
        # Find the referral record
        referral = await referral_stats_collection.find_one({
            "referred_id": referred_id,
            "premium_purchased": False
        })
        
        if not referral:
            logger.info(f"⚠️ No pending referral found for user {referred_id}")
            return False
        
        referrer_id = referral['referrer_id']
        reward_amount = 0.1  # $0.1 reward
        
        # Update referral record
        await referral_stats_collection.update_one(
            {"_id": referral['_id']},
            {
                "$set": {
                    "premium_purchased": True,
                    "reward_paid": True,
                    "reward_amount": reward_amount,
                    "premium_amount": premium_amount,
                    "reward_paid_at": datetime.now()
                }
            }
        )
        
        # Update referrer's total earnings
        await referrals_collection.update_one(
            {"user_id": referrer_id},
            {"$inc": {"total_earnings": reward_amount}}
        )
        
        # Add reward to referrer's balance
        from bot.database.balance_db import add_balance
        await add_balance(referrer_id, reward_amount, "Referral reward")
        
        logger.info(f"✅ Processed referral reward: ${reward_amount} to user {referrer_id} for referring {referred_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing referral reward: {e}")
        return False

async def get_referral_stats(user_id: int):
    """Get user's referral statistics"""
    try:
        referral_data = await referrals_collection.find_one({"user_id": user_id})
        if not referral_data:
            return None
        
        # Get detailed referral history
        referral_history = await referral_stats_collection.find({
            "referrer_id": user_id
        }).to_list(None)
        
        pending_rewards = len([r for r in referral_history if not r['premium_purchased']])
        paid_rewards = len([r for r in referral_history if r['reward_paid']])
        
        return {
            "referral_code": referral_data['referral_code'],
            "total_referrals": referral_data['total_referrals'],
            "total_earnings": referral_data['total_earnings'],
            "pending_rewards": pending_rewards,
            "paid_rewards": paid_rewards,
            "referral_history": referral_history
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting referral stats for user {user_id}: {e}")
        return None

async def get_top_referrers(limit: int = 10):
    """Get top referrers by total earnings"""
    try:
        top_referrers = await referrals_collection.find({
            "total_referrals": {"$gt": 0}
        }).sort("total_earnings", -1).limit(limit).to_list(None)
        
        return top_referrers
        
    except Exception as e:
        logger.error(f"❌ Error getting top referrers: {e}")
        return []

async def get_referral_analytics():
    """Get overall referral program analytics"""
    try:
        total_referrals = await referral_stats_collection.count_documents({})
        total_rewards_paid = await referral_stats_collection.count_documents({"reward_paid": True})
        
        # Calculate total reward amount
        pipeline = [
            {"$match": {"reward_paid": True}},
            {"$group": {"_id": None, "total_rewards": {"$sum": "$reward_amount"}}}
        ]
        
        result = await referral_stats_collection.aggregate(pipeline).to_list(None)
        total_reward_amount = result[0]['total_rewards'] if result else 0.0
        
        return {
            "total_referrals": total_referrals,
            "total_rewards_paid": total_rewards_paid,
            "total_reward_amount": total_reward_amount,
            "conversion_rate": (total_rewards_paid / total_referrals * 100) if total_referrals > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting referral analytics: {e}")
        return {
            "total_referrals": 0,
            "total_rewards_paid": 0,
            "total_reward_amount": 0.0,
            "conversion_rate": 0
        }
