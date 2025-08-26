import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Session timeout (6 hours) - Extended for clone creation process
SESSION_TIMEOUT = timedelta(hours=6)

# In-memory storage for user sessions
user_sessions: Dict[int, Dict[str, Any]] = {}

async def create_session(user_id: int, session_type: str, data: dict = None) -> bool:
    """Create a new session for a user"""
    try:
        print(f"🎬 DEBUG SESSION: Creating session for user {user_id}")
        print(f"📋 DEBUG SESSION: Session type: {session_type}")
        print(f"📊 DEBUG SESSION: Session data keys: {list(data.keys()) if data else 'None'}")

        session_data = {
            'user_id': user_id,
            'type': session_type,
            'data': data or {},
            'started_at': datetime.now(),
            'last_activity': datetime.now(),
            'expires_at': datetime.now() + SESSION_TIMEOUT
        }

        # Store in memory
        user_sessions[user_id] = session_data

        print(f"✅ DEBUG SESSION: Session created successfully for user {user_id}")
        print(f"⏰ DEBUG SESSION: Expires at: {session_data['expires_at']}")
        logger.info(f"Created session for user {user_id}")
        return True

    except Exception as e:
        print(f"❌ DEBUG SESSION: Error creating session for user {user_id}: {e}")
        logger.error(f"Error creating session for user {user_id}: {e}")
        return False

async def get_session(user_id: int) -> dict:
    """Get session data for a user"""
    try:
        print(f"🔍 DEBUG SESSION: Getting session for user {user_id}")
        session = user_sessions.get(user_id)

        if not session:
            print(f"❌ DEBUG SESSION: No session found for user {user_id}")
            return None

        print(f"📋 DEBUG SESSION: Session found for user {user_id}, type: {session.get('type', 'unknown')}")
        print(f"⏰ DEBUG SESSION: Session expires at: {session.get('expires_at', 'unknown')}")

        # Check if session has expired
        if datetime.now() > session['expires_at']:
            print(f"⏰ DEBUG SESSION: Session expired for user {user_id}, clearing...")
            await clear_session(user_id)
            return None

        print(f"✅ DEBUG SESSION: Valid session retrieved for user {user_id}")
        return session

    except Exception as e:
        print(f"❌ DEBUG SESSION: Error getting session for user {user_id}: {e}")
        logger.error(f"Error getting session for user {user_id}: {e}")
        return None

async def clear_session(user_id: int) -> bool:
    """Clear session data for a user"""
    try:
        print(f"🧹 DEBUG SESSION: Clearing session for user {user_id}")
        if user_id in user_sessions:
            del user_sessions[user_id]
            print(f"✅ DEBUG SESSION: Session cleared for user {user_id}")
            logger.info(f"Cleared session for user {user_id}")
            return True
        print(f"❌ DEBUG SESSION: No session found to clear for user {user_id}")
        return False
    except Exception as e:
        print(f"❌ DEBUG SESSION: Error clearing session for user {user_id}: {e}")
        logger.error(f"Error clearing session for user {user_id}: {e}")
        return False

async def session_expired(user_id: int) -> bool:
    """Check if user's session has expired"""
    try:
        print(f"⏰ DEBUG SESSION: Checking if session expired for user {user_id}")
        session = user_sessions.get(user_id)

        if not session:
            print(f"❌ DEBUG SESSION: No session found for user {user_id} - considered expired")
            return True

        current_time = datetime.now()
        expires_at = session.get('expires_at')

        if not expires_at:
            print(f"❌ DEBUG SESSION: No expiry time found for user {user_id} - considered expired")
            return True

        is_expired = current_time > expires_at

        print(f"📊 DEBUG SESSION: User {user_id} session status:")
        print(f"   Current time: {current_time}")
        print(f"   Expires at: {expires_at}")
        print(f"   Is expired: {is_expired}")

        return is_expired

    except Exception as e:
        print(f"❌ DEBUG SESSION: Error checking session expiry for user {user_id}: {e}")
        logger.error(f"Error checking session expiry for user {user_id}: {e}")
        return True

async def update_session_activity(user_id: int) -> bool:
    """Update last activity timestamp for a session"""
    try:
        print(f"🔄 DEBUG SESSION: Updating session activity for user {user_id}")
        session = user_sessions.get(user_id)

        if session:
            current_time = datetime.now()
            session['last_activity'] = current_time
            # Extend session by 2 more hours from current activity
            session['expires_at'] = current_time + SESSION_TIMEOUT

            print(f"✅ DEBUG SESSION: Session activity updated for user {user_id}")
            print(f"   New expiry: {session['expires_at']}")
            return True

        print(f"❌ DEBUG SESSION: No session to update for user {user_id}")
        return False

    except Exception as e:
        print(f"❌ DEBUG SESSION: Error updating session activity for user {user_id}: {e}")
        logger.error(f"Error updating session activity for user {user_id}: {e}")
        return False

async def start_cleanup_task():
    """Start background task to cleanup expired sessions"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            cleanup_count = cleanup_expired_sessions()
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired sessions")
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying

def cleanup_expired_sessions() -> int:
    """Remove all expired sessions"""
    expired_user_ids = []
    current_time = datetime.now()

    for user_id, session in user_sessions.items():
        expires_at = session.get('expires_at')
        if expires_at and current_time > expires_at:
            expired_user_ids.append(user_id)

    for user_id in expired_user_ids:
        print(f"🧹 DEBUG SESSION: Auto-cleaning expired session for user {user_id}")
        try:
            del user_sessions[user_id]
        except KeyError:
            pass # Session might have been cleared by another process

    if expired_user_ids:
        logger.info(f"Cleaned up {len(expired_user_ids)} expired sessions")
    return len(expired_user_ids)

def get_all_sessions() -> Dict[int, Dict[str, Any]]:
    """Get all active sessions (for debugging)"""
    print(f"ℹ️ DEBUG SESSION: Retrieving all active sessions ({len(user_sessions)} total)")
    return user_sessions.copy()

def get_session_count() -> int:
    """Get total number of active sessions"""
    count = len(user_sessions)
    print(f"📊 DEBUG SESSION: Current active session count: {count}")
    return count


class SessionManager:
    """Session manager class that wraps the session management functions"""
    
    @staticmethod
    async def create_session(user_id: int, session_type: str, data: dict = None) -> bool:
        """Create a new session for a user"""
        return await create_session(user_id, session_type, data)
    
    @staticmethod
    async def get_session(user_id: int) -> dict:
        """Get session data for a user"""
        return await get_session(user_id)
    
    @staticmethod
    async def clear_session(user_id: int) -> bool:
        """Clear session data for a user"""
        return await clear_session(user_id)
    
    @staticmethod
    async def session_expired(user_id: int) -> bool:
        """Check if user's session has expired"""
        return await session_expired(user_id)
    
    @staticmethod
    async def update_session_activity(user_id: int) -> bool:
        """Update last activity timestamp for a session"""
        return await update_session_activity(user_id)
    
    @staticmethod
    def get_all_sessions() -> Dict[int, Dict[str, Any]]:
        """Get all active sessions"""
        return get_all_sessions()
    
    @staticmethod
    def get_session_count() -> int:
        """Get total number of active sessions"""
        return get_session_count()
    
    @staticmethod
    async def start_cleanup_task():
        """Start background task to cleanup expired sessions"""
        return await start_cleanup_task()
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """Remove all expired sessions"""
        return cleanup_expired_sessions()