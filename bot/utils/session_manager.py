
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from bot.logging import LOGGER

logger = LOGGER(__name__)

class SessionManager:
    """Manage user sessions for clone creation process"""
    
    def __init__(self):
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.session_timeout = 7200  # 2 hours for clone creation
    
    def create_session(self, user_id: int, session_data: Dict[str, Any]) -> None:
        """Create a new session for a user"""
        session_data['created_at'] = datetime.now()
        session_data['last_activity'] = datetime.now()
        self.sessions[user_id] = session_data
        logger.info(f"Created session for user {user_id}")
    
    def get_session(self, user_id: int, default: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get session data for a user"""
        session = self.sessions.get(user_id, default)
        if session:
            # Update last activity
            session['last_activity'] = datetime.now()
            self.sessions[user_id] = session
        return session
    
    def update_session(self, user_id: int, session_data: Dict[str, Any]) -> None:
        """Update session data for a user"""
        if user_id in self.sessions:
            session_data['last_activity'] = datetime.now()
            # Preserve created_at if it exists
            if 'created_at' not in session_data and 'created_at' in self.sessions[user_id]:
                session_data['created_at'] = self.sessions[user_id]['created_at']
            self.sessions[user_id] = session_data
            logger.debug(f"Updated session for user {user_id}")
    
    def delete_session(self, user_id: int) -> bool:
        """Delete session for a user"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Deleted session for user {user_id}")
            return True
        return False
    
    def has_session(self, user_id: int) -> bool:
        """Check if user has an active session"""
        return user_id in self.sessions
    
    def is_session_expired(self, user_id: int) -> bool:
        """Check if user's session has expired"""
        session = self.sessions.get(user_id)
        if not session:
            return True
        
        last_activity = session.get('last_activity', session.get('created_at'))
        if not last_activity:
            return True
        
        elapsed = (datetime.now() - last_activity).total_seconds()
        return elapsed > self.session_timeout
    
    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions"""
        expired_users = []
        current_time = datetime.now()
        
        for user_id, session in self.sessions.items():
            last_activity = session.get('last_activity', session.get('created_at'))
            if last_activity:
                elapsed = (current_time - last_activity).total_seconds()
                if elapsed > self.session_timeout:
                    expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")
        
        return len(expired_users)
    
    def get_all_sessions(self) -> Dict[int, Dict[str, Any]]:
        """Get all active sessions (for debugging)"""
        return self.sessions.copy()
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.sessions)
    
    async def start_cleanup_task(self):
        """Start background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                self.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
