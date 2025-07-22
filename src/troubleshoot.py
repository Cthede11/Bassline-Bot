#!/usr/bin/env python3
"""
Bassline-Bot Troubleshooting Script
Run this to diagnose common setup issues
"""

import sys
import os
import subprocess
from pathlib import Path

def print_header(title):
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def check_python_version():
    print_header("Python Version Check")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("❌ ERROR: Python 3.8 or higher is required!")
        return False
    elif version >= (3, 11):
        print("✅ Excellent! Using recommended Python version")
    else:
        print("✅ Python version is compatible")
    return True

def check_virtual_environment():
    print_header("Virtual Environment Check")
    
    # Multiple ways to detect virtual environment
    indicators = []
    
    # Method 1: Check for virtual_env environment variable
    if os.environ.get('VIRTUAL_ENV'):
        indicators.append(f"VIRTUAL_ENV: {os.environ['VIRTUAL_ENV']}")
    
    # Method 2: Check sys.prefix vs sys.base_prefix (Python 3.3+)
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        indicators.append(f"sys.prefix differs from base_prefix")
    
    # Method 3: Check for real_prefix (older virtualenv)
    if hasattr(sys, 'real_prefix'):
        indicators.append("real_prefix detected")
    
    # Method 4: Check if pip is installing to user directory
    try:
        import site
        user_site = site.getusersitepackages()
        if sys.prefix not in user_site:
            indicators.append("Non-user site packages")
    except:
        pass
    
    # Method 5: Check command prompt indicator
    # This is a heuristic based on common virtual env naming
    python_executable = sys.executable.lower()
    if any(venv_name in python_executable for venv_name in ['venv', 'virtualenv', '.venv', 'env']):
        indicators.append(f"Python executable in venv path: {sys.executable}")
    
    if indicators:
        print("✅ Running in virtual environment")
        for indicator in indicators:
            print(f"   - {indicator}")
        if hasattr(sys, 'base_prefix'):
            print(f"   - Virtual env path: {sys.prefix}")
            print(f"   - Base Python path: {sys.base_prefix}")
        return True
    else:
        # Even if we can't detect it, check if the user seems to be in one
        if "(venv)" in os.environ.get('PS1', '') or "venv" in sys.executable.lower():
            print("✅ Likely in virtual environment (based on indicators)")
            print("   - Detection methods may not work perfectly on all systems")
            return True
        else:
            print("⚠️  WARNING: Virtual environment not clearly detected")
            print("   - If you see (venv) in your prompt, you're probably fine")
            print("   - Recommended: Create a virtual environment with 'python -m venv venv'")
            return False

def check_dependencies():
    print_header("Dependencies Check")
    
    required_packages = [
        ('discord.py', 'discord'),
        ('yt-dlp', 'yt_dlp'),
        ('SQLAlchemy', 'sqlalchemy'),
        ('aiohttp', 'aiohttp'),
        ('Pydantic', 'pydantic'),
        ('FastAPI', 'fastapi'),
        ('uvicorn', 'uvicorn'),
    ]
    
    missing = []
    for name, module in required_packages:
        try:
            __import__(module)
            print(f"✅ {name} installed")
        except ImportError:
            print(f"❌ {name} missing")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_ffmpeg():
    print_header("FFmpeg Check")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {first_line}")
            return True
        else:
            print("❌ FFmpeg command failed")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("\nInstallation instructions:")
        print("- Windows: Download from https://ffmpeg.org/ and add to PATH")
        print("- macOS: brew install ffmpeg")  
        print("- Ubuntu/Debian: sudo apt install ffmpeg")
        print("- CentOS/RHEL: sudo yum install ffmpeg")
        return False
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg command timed out")
        return False

def check_env_file():
    print_header("Environment File Check")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        print("❌ .env file not found")
        if env_example.exists():
            print("✅ .env.example found")
            print("Action: Copy .env.example to .env and edit it")
        else:
            print("❌ .env.example also missing")
            print("Action: Create .env file with your Discord token")
        return False
    
    print("✅ .env file exists")
    
    # Check if token is configured
    try:
        with open('.env', 'r') as f:
            content = f.read()
            
        if 'DISCORD_TOKEN=' in content:
            print("✅ DISCORD_TOKEN found in .env")
            
            # Check if it's the placeholder
            if 'your_discord_bot_token_here' in content:
                print("⚠️  WARNING: Discord token appears to be placeholder")
                print("Action: Replace with your actual bot token")
                return False
            else:
                print("✅ Discord token appears to be configured")
                return True
        else:
            print("❌ DISCORD_TOKEN not found in .env")
            print("Action: Add DISCORD_TOKEN=your_token_here to .env")
            return False
            
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def check_configuration():
    print_header("Configuration Loading Check")
    
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        from config.settings import settings
        print("✅ Settings loaded successfully")
        
        if settings.discord_token == "your_discord_bot_token_here":
            print("❌ Discord token is still placeholder")
            return False
        
        print(f"✅ Bot name: {settings.bot_name}")
        print(f"✅ Dashboard: {'Enabled' if settings.dashboard_enabled else 'Disabled'}")
        print(f"✅ Log level: {settings.log_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        print("\nThis could be due to:")
        print("- Invalid values in .env file")
        print("- Missing required fields")
        print("- Pydantic validation errors")
        return False

def check_database():
    print_header("Database Check")
    
    try:
        from config.database import init_db, engine
        import sqlalchemy
        
        print("✅ Database modules imported")
        
        # Test database creation
        init_db()
        print("✅ Database tables created/verified")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            if result.fetchone():
                print("✅ Database connection test passed")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_directories():
    print_header("Directory Structure Check")
    
    required_dirs = ['logs', 'data', 'downloads', 'static', 'backups']
    
    for directory in required_dirs:
        path = Path(directory)
        if path.exists():
            print(f"✅ {directory}/ exists")
        else:
            print(f"⚠️  {directory}/ missing (will be created)")
            try:
                path.mkdir(exist_ok=True)
                print(f"✅ Created {directory}/")
            except Exception as e:
                print(f"❌ Failed to create {directory}/: {e}")
                return False
    
    return True

def main():
    print("🔍 Bassline-Bot Troubleshooting Tool")
    print("This tool will help diagnose common setup issues")
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("FFmpeg", check_ffmpeg),
        ("Environment File", check_env_file),
        ("Configuration", check_configuration),
        ("Directory Structure", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All checks passed! Your setup looks good.")
        print("Try running: python -m src.run")
    elif passed >= total - 1:  # Only 1 failure
        failed = [name for name, result in results if not result]
        if "Virtual Environment" in failed and len(failed) == 1:
            print(f"\n✅ Setup looks good! Only virtual environment detection failed.")
            print("Since you see (venv) in your prompt, you're probably fine.")
            print("Try running: python -m src.run")
        else:
            print(f"\n⚠️  {total - passed} minor issue found. You might still be able to run the bot.")
            print(f"Failed checks: {', '.join(failed)}")
    else:
        print(f"\n⚠️  {total - passed} issues found. Please fix the errors above.")
        
        # Show failed checks
        failed = [name for name, result in results if not result]
        print(f"Failed checks: {', '.join(failed)}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Troubleshooting cancelled")
    except Exception as e:
        print(f"\n❌ Troubleshooting tool crashed: {e}")
        import traceback
        traceback.print_exc()