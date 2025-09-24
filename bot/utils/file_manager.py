import os
import asyncio
import hashlib
import mimetypes
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
from pyrogram.types import Message
from info import Config
from bot.utils.security import security_manager
from bot.logging import LOGGER

logger = LOGGER(__name__)

class FileManager:
    """Enhanced file management system with security and optimization"""

    def __init__(self):
        self.storage_path = Config.STORAGE_PATH
        self.temp_path = Config.TEMP_PATH
        self.max_file_size = Config.MAX_FILE_SIZE * 1024 * 1024  # Convert MB to bytes
        self.active_downloads = {}
        self.file_cache = {}

    async def validate_file(self, message: Message) -> Tuple[bool, str]:
        """Validate file before processing"""
        if not message.document and not message.photo and not message.video and not message.audio:
            return False, "No file found in message"

        # Get file info
        file_info = None
        if message.document:
            file_info = message.document
        elif message.photo:
            file_info = message.photo
        elif message.video:
            file_info = message.video
        elif message.audio:
            file_info = message.audio

        # Check file size
        if hasattr(file_info, 'file_size') and file_info.file_size:
            if file_info.file_size > self.max_file_size:
                return False, f"File too large. Maximum size: {Config.MAX_FILE_SIZE}MB"

        # Check file name
        filename = getattr(file_info, 'file_name', 'unknown')
        if not security_manager.validate_file_path(filename):
            return False, "Invalid file type or dangerous filename"

        return True, "File validation passed"

    async def generate_file_id(self, file_content: bytes) -> str:
        """Generate unique file ID based on content hash"""
        hasher = hashlib.sha256()
        hasher.update(file_content)
        return hasher.hexdigest()[:16]

    async def store_file(self, message: Message, user_id: int) -> Optional[Dict]:
        """Store file with metadata"""
        try:
            # Validate file
            is_valid, validation_msg = await self.validate_file(message)
            if not is_valid:
                logger.error(f"File validation failed: {validation_msg}")
                return None

            # Download file
            file_path = await self.download_file(message)
            if not file_path:
                return None

            # Read file content for ID generation
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            file_id = await self.generate_file_id(file_content)

            # Get file info
            file_info = self.get_file_info(message)

            # Create storage path
            storage_file_path = self.storage_path / f"{file_id}_{file_info['filename']}"

            # Move file to storage
            os.rename(file_path, storage_file_path)

            # Create file metadata
            metadata = {
                'file_id': file_id,
                'original_message_id': message.id,
                'filename': file_info['filename'],
                'file_size': file_info['file_size'],
                'mime_type': file_info['mime_type'],
                'stored_path': str(storage_file_path),
                'owner_id': user_id,
                'created_at': datetime.now(),
                'download_count': 0,
                'last_accessed': datetime.now(),
                'tags': [],
                'description': message.caption or '',
                'is_public': False
            }

            logger.info(f"File stored successfully: {file_id}")
            return metadata

        except Exception as e:
            logger.error(f"Error storing file: {e}")
            return None

    async def download_file(self, message: Message) -> Optional[str]:
        """Download file from Telegram"""
        try:
            # Generate temporary file path
            temp_filename = f"temp_{message.id}_{int(datetime.now().timestamp())}"
            temp_file_path = self.temp_path / temp_filename

            # Download file
            downloaded_file = await message.download(file_name=str(temp_file_path))

            if downloaded_file:
                logger.info(f"File downloaded: {downloaded_file}")
                return downloaded_file

            return None

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    def get_file_info(self, message: Message) -> Dict:
        """Extract file information from message"""
        file_info = {
            'filename': 'unknown',
            'file_size': 0,
            'mime_type': 'application/octet-stream'
        }

        if message.document:
            file_info['filename'] = message.document.file_name or 'document'
            file_info['file_size'] = message.document.file_size or 0
            file_info['mime_type'] = message.document.mime_type or 'application/octet-stream'
        elif message.photo:
            file_info['filename'] = f"photo_{message.photo.file_id}.jpg"
            file_info['file_size'] = message.photo.file_size or 0
            file_info['mime_type'] = 'image/jpeg'
        elif message.video:
            file_info['filename'] = message.video.file_name or f"video_{message.video.file_id}.mp4"
            file_info['file_size'] = message.video.file_size or 0
            file_info['mime_type'] = message.video.mime_type or 'video/mp4'
        elif message.audio:
            file_info['filename'] = message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
            file_info['file_size'] = message.audio.file_size or 0
            file_info['mime_type'] = message.audio.mime_type or 'audio/mpeg'

        # Sanitize filename
        file_info['filename'] = security_manager.sanitize_filename(file_info['filename'])

        return file_info

    async def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get file path by file ID"""
        try:
            # Search for file in storage
            for file_path in self.storage_path.glob(f"{file_id}_*"):
                if file_path.exists():
                    return file_path
            return None
        except Exception as e:
            logger.error(f"Error getting file path: {e}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from storage"""
        try:
            file_path = await self.get_file_path(file_id)
            if file_path and file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    async def cleanup_temp_files(self):
        """Clean up temporary files older than 1 hour"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            for temp_file in self.temp_path.glob("temp_*"):
                try:
                    file_time = datetime.fromtimestamp(temp_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        temp_file.unlink()
                        logger.debug(f"Cleaned up temp file: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"Error cleaning temp file {temp_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")

    async def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            from pathlib import Path
            import os

            # Ensure storage_path is a Path object
            if isinstance(self.storage_path, str):
                storage_path = Path(self.storage_path)
            else:
                storage_path = self.storage_path

            total_files = 0
            total_size = 0

            if storage_path.exists():
                for file_path in storage_path.rglob('*'):
                    if file_path.is_file():
                        total_files += 1
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            # Skip files that can't be accessed
                            continue

            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'storage_path': str(self.storage_path)
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}

# Global file manager instance
file_manager = FileManager()

# Periodic cleanup task
async def start_cleanup_task():
    """Start periodic cleanup task"""
    while True:
        try:
            await file_manager.cleanup_temp_files()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error