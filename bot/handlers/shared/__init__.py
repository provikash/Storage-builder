
"""
Shared Handlers Package
Contains handlers used by both motherbot and clonebot
"""

from bot.handlers.shared.commands import *
from bot.handlers.shared.premium import *
from bot.handlers.shared.verification import *

__all__ = [
    "commands",
    "premium",
    "verification",
]
