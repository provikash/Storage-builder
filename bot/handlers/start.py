
"""
Start command handlers
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

# This will import and organize all start-related handlers
# from the existing start_handler.py, simple_start.py, debug_start.py
