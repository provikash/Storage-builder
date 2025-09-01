
import os
import glob
import asyncio
from pathlib import Path
from bot.logging import LOGGER

logger = LOGGER(__name__)

class SessionCleanup:
    """Handle session file cleanup to prevent locks"""
    
    @staticmethod
    async def cleanup_session_files():
        """Clean up locked session files"""
        try:
            # Remove journal files that cause locks
            journal_files = glob.glob("*.session-journal") + glob.glob("temp_sessions/*.session-journal")
            for journal_file in journal_files:
                try:
                    os.remove(journal_file)
                    logger.info(f"✅ Removed journal file: {journal_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {journal_file}: {e}")
            
            # Remove WAL files
            wal_files = glob.glob("*.session-wal") + glob.glob("temp_sessions/*.session-wal")
            for wal_file in wal_files:
                try:
                    os.remove(wal_file)
                    logger.info(f"✅ Removed WAL file: {wal_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {wal_file}: {e}")
            
            # Remove .session-shm files
            shm_files = glob.glob("*.session-shm") + glob.glob("temp_sessions/*.session-shm")
            for shm_file in shm_files:
                try:
                    os.remove(shm_file)
                    logger.info(f"✅ Removed SHM file: {shm_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {shm_file}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error cleaning session files: {e}")
    
    @staticmethod
    async def cleanup_on_start():
        """Cleanup before starting bots"""
        logger.info("🧹 Cleaning up session files...")
        await SessionCleanup.cleanup_session_files()
        
        # Ensure directories exist
        Path("temp_sessions").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        # Wait for file system sync
        await asyncio.sleep(1)
        logger.info("✅ Session cleanup completed")

session_cleanup = SessionCleanup()
