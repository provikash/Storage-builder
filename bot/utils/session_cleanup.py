import os
import glob
import asyncio
import time
from pathlib import Path
from bot.logging import LOGGER

logger = LOGGER(__name__)

class SessionCleanup:
    """Handle session file cleanup to prevent storage issues"""

    def __init__(self):
        self.session_dirs = [
            "temp_sessions",
            "sessions", 
            ".",  # Current directory for any .session files
        ]
        self.max_session_age = 24 * 3600  # 24 hours in seconds

    async def cleanup_on_start(self):
        """Clean up session files on bot startup"""
        try:
            logger.info("🧹 Starting session cleanup...")

            cleaned_files = 0
            current_time = time.time()

            for session_dir in self.session_dirs:
                if os.path.exists(session_dir):
                    # Clean old .session files
                    session_files = glob.glob(os.path.join(session_dir, "*.session"))
                    for file_path in session_files:
                        try:
                            # Check file age
                            file_age = current_time - os.path.getmtime(file_path)
                            if file_age > self.max_session_age:
                                os.remove(file_path)
                                cleaned_files += 1
                                logger.debug(f"Removed old session file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not remove {file_path}: {e}")

                    # Clean .session-journal files (always remove these)
                    journal_files = glob.glob(os.path.join(session_dir, "*.session-journal"))
                    for file_path in journal_files:
                        try:
                            os.remove(file_path)
                            cleaned_files += 1
                            logger.debug(f"Removed journal file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not remove {file_path}: {e}")

                    # Clean any lock files
                    lock_files = glob.glob(os.path.join(session_dir, "*.lock"))
                    for file_path in lock_files:
                        try:
                            os.remove(file_path)
                            cleaned_files += 1
                            logger.debug(f"Removed lock file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not remove {file_path}: {e}")

            logger.info(f"✅ Session cleanup completed. Removed {cleaned_files} files")

        except Exception as e:
            logger.error(f"❌ Session cleanup failed: {e}")

    async def periodic_cleanup(self):
        """Run periodic session cleanup"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_on_start()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

# Global instance
session_cleanup = SessionCleanup()