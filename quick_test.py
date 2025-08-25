
#!/usr/bin/env python3
"""
Quick test runner to check test functionality
"""

import sys
import os
import subprocess

def run_simple_test():
    """Run a single test to check setup"""
    print("🧪 Running simple test...")
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        # Try importing our modules
        import clone_manager
        import info
        print("✅ Module imports successful")
        
        # Run a single test
        cmd = [sys.executable, "-m", "pytest", "tests/test_database.py::TestCloneDatabase::test_database_connection", "-v"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("OUTPUT:", result.stdout)
        if result.stderr:
            print("ERRORS:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    run_simple_test()
