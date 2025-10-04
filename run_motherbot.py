
#!/usr/bin/env python3
"""
Mother Bot Entry Point
Starts the main mother bot instance
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup uvloop if available
from shared.utils.uvloop_compat import setup_event_loop
setup_event_loop()

# Import and run mother bot
from motherbot.main import run_mother_bot

if __name__ == "__main__":
    print("🚀 Starting Mother Bot...")
    run_mother_bot()
