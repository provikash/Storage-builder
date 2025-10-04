
"""
uvloop compatibility wrapper
Handles optional uvloop import for Windows compatibility
"""
import sys
import asyncio

def setup_event_loop():
    """
    Setup event loop with uvloop if available and not on Windows
    """
    if sys.platform != "win32":
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            print("✅ Using uvloop for improved performance")
        except ImportError:
            print("⚠️ uvloop not available, using default event loop")
    else:
        print("ℹ️ Running on Windows, using default event loop")
