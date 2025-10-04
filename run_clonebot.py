
#!/usr/bin/env python3
"""
Clone Bot Entry Point
Starts the clone bot manager and all active clones
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup uvloop if available
from shared.utils.uvloop_compat import setup_event_loop
setup_event_loop()

# Import and run clone manager
from clonebot.main import run_clone_system

if __name__ == "__main__":
    print("🚀 Starting Clone Bot System...")
    run_clone_system()
