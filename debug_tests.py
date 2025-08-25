
#!/usr/bin/env python3
"""
Simple test debugger to identify issues
"""

import sys
import os
import importlib.util
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print(f"🐍 Python version: {sys.version}")
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        return False
    print("✅ Python version OK")
    return True

def check_imports():
    """Check if all required modules can be imported"""
    print("\n📦 Checking imports...")
    
    modules_to_check = [
        "pytest",
        "asyncio", 
        "unittest.mock",
        "motor",
        "pyrogram"
    ]
    
    for module in modules_to_check:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    return True

def check_project_structure():
    """Check if project files exist"""
    print("\n📁 Checking project structure...")
    
    required_files = [
        "main.py",
        "clone_manager.py", 
        "info.py",
        "bot/__init__.py",
        "tests/__init__.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    return True

def test_simple_import():
    """Test importing main project modules"""
    print("\n🔍 Testing module imports...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Test importing main modules
        import info
        print("✅ info.py imported")
        
        # Test clone_manager import
        import clone_manager
        print("✅ clone_manager.py imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def run_single_test():
    """Try running a single test file"""
    print("\n🧪 Running single test...")
    
    import subprocess
    
    try:
        # Run just the database test
        cmd = [sys.executable, "-m", "pytest", "tests/test_database.py::TestCloneDatabase::test_create_clone_success", "-v"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Main debug function"""
    print("🔧 Test Debug Tool")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Module Imports", check_imports),
        ("Project Structure", check_project_structure),
        ("Module Loading", test_simple_import),
        ("Single Test", run_single_test)
    ]
    
    for name, check_func in checks:
        print(f"\n🔍 {name}...")
        if not check_func():
            print(f"❌ {name} failed - stopping here")
            return False
        print(f"✅ {name} passed")
    
    print("\n🎉 All checks passed! Tests should work now.")
    return True

if __name__ == "__main__":
    main()
