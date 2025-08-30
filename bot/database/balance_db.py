import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from info import Config
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Balance database
balance_client = AsyncIOMotorClient(Config.DATABASE_URL)
balance_db = balance_client[Config.DATABASE_NAME]
user_balances = balance_db.user_balances
balance_transactions = balance_db.balance_transactions
referral_codes = balance_db.referral_codes
referral_rewards = balance_db.referral_rewards

async def create_user_profile(user_id: int, username: str = None, first_name: str = None):
    """Create user profile with default balance"""
    try:
        # Check if user already exists
        existing_user = await user_balances.find_one({"_id": user_id})
        if existing_user:
            return existing_user

        # Create new user with $5 default balance
        user_profile = {
            "_id": user_id,
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "balance": 5.00,  # $5 default balance
            "total_spent": 0.00,
            "total_earned": 5.00,  # Default balance counts as earned
            "created_at": datetime.now(),
            "last_transaction": datetime.now(),
            "status": "active"
        }

        await user_balances.insert_one(user_profile)

        # Log transaction for default balance
        await log_transaction(
            user_id=user_id,
            amount=5.00,
            transaction_type="credit",
            description="Default signup balance",
            admin_id=None
        )

        logger.info(f"✅ Created user profile for {user_id} with $5 default balance")
        return user_profile

    except Exception as e:
        logger.error(f"❌ Error creating user profile {user_id}: {e}")
        return None

async def get_user_balance(user_id: int):
    """Get user's current balance"""
    try:
        user = await user_balances.find_one({"_id": user_id})
        return user['balance'] if user else 0.00
    except Exception as e:
        logger.error(f"❌ Error getting balance for {user_id}: {e}")
        return 0.00

async def get_user_profile(user_id: int):
    """Get complete user profile"""
    try:
        return await user_balances.find_one({"_id": user_id})
    except Exception as e:
        logger.error(f"❌ Error getting profile for {user_id}: {e}")
        return None

async def update_balance(user_id: int, amount: float, transaction_type: str, description: str, admin_id: int = None):
    """Update user balance and log transaction"""
    try:
        current_balance = await get_user_balance(user_id)

        if transaction_type == "debit" and current_balance < amount:
            return False, "Insufficient balance"

        new_balance = current_balance + amount if transaction_type == "credit" else current_balance - amount

        # Update balance
        update_data = {
            "balance": new_balance,
            "last_transaction": datetime.now()
        }

        if transaction_type == "credit":
            update_data["total_earned"] = current_balance + amount
        else:
            update_data["total_spent"] = (await user_balances.find_one({"_id": user_id})).get("total_spent", 0) + amount

        await user_balances.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )

        # Log transaction
        await log_transaction(user_id, amount, transaction_type, description, admin_id)

        logger.info(f"✅ Updated balance for {user_id}: ${current_balance} -> ${new_balance}")
        return True, f"Balance updated successfully. New balance: ${new_balance:.2f}"

    except Exception as e:
        logger.error(f"❌ Error updating balance for {user_id}: {e}")
        return False, str(e)

async def deduct_balance(user_id: int, amount: float, description: str):
    """Deduct balance for purchase"""
    return await update_balance(user_id, amount, "debit", description)

async def add_balance(user_id: int, amount: float, description: str, admin_id: int):
    """Add balance (admin function)"""
    return await update_balance(user_id, amount, "credit", description, admin_id)

async def log_transaction(user_id: int, amount: float, transaction_type: str, description: str, admin_id: int = None):
    """Log balance transaction"""
    try:
        transaction = {
            "user_id": user_id,
            "amount": amount,
            "type": transaction_type,
            "description": description,
            "admin_id": admin_id,
            "timestamp": datetime.now(),
            "balance_after": await get_user_balance(user_id)
        }

        await balance_transactions.insert_one(transaction)

    except Exception as e:
        logger.error(f"❌ Error logging transaction: {e}")

async def get_user_transactions(user_id: int, limit: int = 10):
    """Get user transaction history"""
    try:
        transactions = await balance_transactions.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit).to_list(None)

        return transactions

    except Exception as e:
        logger.error(f"❌ Error getting transactions for {user_id}: {e}")
        return []

async def get_all_user_balances():
    """Get all user balances (admin function)"""
    try:
        users = await user_balances.find({}).sort("balance", -1).to_list(None)
        return users
    except Exception as e:
        logger.error(f"❌ Error getting all balances: {e}")
        return []

async def check_sufficient_balance(user_id: int, required_amount: float):
    """Check if user has sufficient balance"""
    current_balance = await get_user_balance(user_id)
    return current_balance >= required_amount

# Referral Program Functions

async def generate_referral_code(user_id: int):
    """Generate a unique referral code for a user"""
    try:
        referral_code = f"REF-{user_id}-{asyncio.get_running_loop().time():.0f}"
        await referral_codes.insert_one({
            "_id": referral_code,
            "user_id": user_id,
            "created_at": datetime.now()
        })
        logger.info(f"✅ Generated referral code: {referral_code} for user: {user_id}")
        return referral_code
    except Exception as e:
        logger.error(f"❌ Error generating referral code for {user_id}: {e}")
        return None

async def get_referral_code_owner(referral_code: str):
    """Get the user ID associated with a referral code"""
    try:
        code_data = await referral_codes.find_one({"_id": referral_code})
        return code_data['user_id'] if code_data else None
    except Exception as e:
        logger.error(f"❌ Error getting owner of referral code {referral_code}: {e}")
        return None

async def process_referral_reward(referred_user_id: int, referrer_user_id: int, purchase_amount: float):
    """Process referral reward for premium plan purchase"""
    try:
        # Define reward amount for premium plan purchase
        reward_amount = 0.10  # $0.10 reward

        # Check if the purchase qualifies for a referral reward
        # For simplicity, we assume any premium plan purchase triggers the reward
        # In a real scenario, you might want to check the specific plan or amount

        if purchase_amount > 0:  # Ensure a purchase was made
            # Add reward to referrer's balance
            success, message = await add_balance(
                user_id=referrer_user_id,
                amount=reward_amount,
                description=f"Referral reward from {referred_user_id}",
                admin_id=None  # Referral rewards are not from admin
            )

            if success:
                # Log the referral reward transaction
                await referral_rewards.insert_one({
                    "referrer_id": referrer_user_id,
                    "referred_id": referred_user_id,
                    "reward_amount": reward_amount,
                    "purchase_amount": purchase_amount,
                    "timestamp": datetime.now()
                })
                logger.info(f"✅ Awarded ${reward_amount} to referrer {referrer_user_id} for referral from {referred_user_id}")
            else:
                logger.error(f"❌ Failed to award referral reward to {referrer_user_id}: {message}")
    except Exception as e:
        logger.error(f"❌ Error processing referral reward: {e}")