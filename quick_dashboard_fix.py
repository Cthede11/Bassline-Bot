#!/usr/bin/env python3
"""
Quick Dashboard Fix for Bassline Bot
====================================

This script will patch your existing dashboard to fix the API endpoint errors.
Run this file from your bassline-bot root directory.

Usage: python quick_dashboard_fix.py
"""

import os
import sys
import json
import time
import psutil
import logging
from pathlib import Path

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

def create_mock_api_responses():
    """Create a simple mock API module to handle missing endpoints."""
    
    api_code = '''
# Auto-generated API fixes for dashboard
import time
import json
import psutil
import logging
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

def add_dashboard_api_routes(app):
    """Add missing API routes for dashboard functionality."""
    
    @app.get("/api/stats")
    async def api_stats():
        """Bot statistics endpoint."""
        try:
            # Try to get real bot data
            from src.web.dashboard import get_bot_instance
            bot = get_bot_instance()
            
            if bot and hasattr(bot, 'is_ready') and bot.is_ready():
                guild_count = len(bot.guilds) if hasattr(bot, 'guilds') and bot.guilds else 0
                user_count = sum(g.member_count for g in bot.guilds) if hasattr(bot, 'guilds') and bot.guilds else 0
                latency = round(bot.latency * 1000, 1) if hasattr(bot, 'latency') else 0
                status = "online"
            else:
                guild_count = 0
                user_count = 0
                latency = 0
                status = "offline"
                
            return {
                "status": status,
                "uptime": int(time.time() - 1640995200),  # Mock uptime
                "guild_count": guild_count,
                "user_count": user_count,
                "commands_today": 0,  # Implement real command tracking
                "songs_played": 0,    # Implement real song tracking
                "latency": latency
            }
        except Exception as e:
            logger.error(f"API stats error: {e}")
            return {
                "status": "error",
                "uptime": 0,
                "guild_count": 0,
                "user_count": 0,
                "commands_today": 0,
                "songs_played": 0,
                "latency": 0
            }
    
    @app.get("/api/guilds")
    async def api_guilds():
        """Guild information endpoint."""
        try:
            from src.web.dashboard import get_bot_instance
            bot = get_bot_instance()
            
            if bot and hasattr(bot, 'guilds') and bot.guilds:
                return [
                    {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count,
                        "active_voice_connections": 1 if hasattr(guild, 'voice_client') and guild.voice_client else 0,
                        "queue_length": 0,  # Implement queue tracking
                        "active": bool(hasattr(guild, 'voice_client') and guild.voice_client)
                    }
                    for guild in bot.guilds
                ]
            else:
                return []
        except Exception as e:
            logger.error(f"API guilds error: {e}")
            return []
    
    @app.get("/api/system")
    async def api_system():
        """System information endpoint."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_used": memory.used,
                "memory_total": memory.total,
                "memory_percent": memory.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "disk_percent": round((disk.used / disk.total) * 100, 1),
                "discord_latency": 45.0,  # Mock value
                "uptime": int(time.time() - 1640995200)
            }
        except Exception as e:
            logger.error(f"API system error: {e}")
            return {
                "cpu_percent": 0, "memory_used": 0, "memory_total": 0, "memory_percent": 0,
                "disk_used": 0, "disk_total": 0, "disk_percent": 0, "discord_latency": 0, "uptime": 0
            }
    
    @app.get("/health")
    async def api_health():
        """Health check endpoint."""
        try:
            from src.web.dashboard import get_bot_instance
            bot = get_bot_instance()
            is_healthy = bot and hasattr(bot, 'is_ready') and bot.is_ready()
            
            return {
                "overall_score": 100 if is_healthy else 50,
                "status": "healthy" if is_healthy else "unhealthy",
                "system_health": "healthy",
                "issues": [] if is_healthy else [{"title": "Bot Offline", "description": "Bot is not connected"}],
                "recommendations": [] if is_healthy else ["Check bot connection", "Verify Discord token"],
                "checks": {
                    "bot": {"healthy": is_healthy},
                    "database": {"healthy": True},
                    "memory": {"healthy": psutil.virtual_memory().percent < 90},
                    "disk": {"healthy": True}
                }
            }
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {"overall_score": 0, "status": "unhealthy", "system_health": "unhealthy", "issues": [], "recommendations": [], "checks": {}}
    
    # Add simple mock endpoints for missing routes
    mock_endpoints = {
        "/api/guilds/distribution": {"labels": ["Small", "Medium", "Large"], "values": [1, 1, 1]},
        "/api/usage/24h": {"labels": [f"{i:02d}:00" for i in range(24)], "commands": [0]*24, "music_commands": [0]*24},
        "/api/performance": {"avg_response_time": 45.0, "success_rate": 99.5, "commands_per_minute": 5.0, "music_latency": 120.0, "resources": {"cpu_load": 0, "memory_usage": 0, "network_io": 0, "disk_io": 0}},
        "/api/performance/trends": {"labels": [f"{i:02d}:00" for i in range(30)], "response_times": [45]*30, "cpu_usage": [10]*30},
        "/api/database/stats": {"labels": ["Guilds", "Users", "Playlists", "Songs", "Logs"], "values": [0, 0, 0, 0, 0]},
        "/api/diagnostics": {"issues": []},
        "/api/health/database": {"status": "healthy", "response_time": 5.0},
        "/api/logs/errors": {"recent_errors": []},
        "/api/music/activity": {"hourly": [0]*24, "daily": [0]*7, "genres": {}, "top_songs": []}
    }
    
    for endpoint, response_data in mock_endpoints.items():
        @app.get(endpoint)
        async def mock_endpoint(data=response_data):
            return data

    print("✅ Dashboard API routes added successfully!")
'''
    
    return api_code

def patch_dashboard_file():
    """Patch the existing dashboard.py file to include the API routes."""
    
    dashboard_file = Path("src/web/dashboard.py")
    
    if not dashboard_file.exists():
        print(f"❌ Dashboard file not found at {dashboard_file}")
        return False
    
    try:
        # Read the existing file
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already patched
        if "add_dashboard_api_routes" in content:
            print("✅ Dashboard already patched!")
            return True
        
        # Create the API patch
        api_patch = create_mock_api_responses()
        
        # Add the patch at the end of the file
        patched_content = content + "\n\n# === AUTO-GENERATED API PATCH ===\n" + api_patch
        
        # Add the call to integrate the routes
        integration_code = '''
# Auto-integrate the API routes when the module loads
try:
    if 'app' in globals():
        add_dashboard_api_routes(app)
        print("🎉 Dashboard API routes integrated!")
except Exception as e:
    print(f"⚠️ Could not auto-integrate API routes: {e}")
    print("💡 You may need to manually call add_dashboard_api_routes(app)")
'''
        
        patched_content += "\n" + integration_code
        
        # Backup the original file
        backup_file = dashboard_file.with_suffix('.py.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📄 Backup created: {backup_file}")
        
        # Write the patched file
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(patched_content)
        
        print(f"✅ Dashboard patched successfully: {dashboard_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error patching dashboard: {e}")
        return False

def create_static_directories():
    """Create the static directory structure if it doesn't exist."""
    
    static_dirs = [
        "static",
        "static/css",
        "static/js"
    ]
    
    for dir_path in static_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {dir_path}")

def check_dependencies():
    """Check if required dependencies are installed."""
    
    required_packages = ['fastapi', 'psutil', 'uvicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {missing_packages}")
        print(f"💡 Install them with: pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All required dependencies found!")
    return True

def test_dashboard_connection():
    """Test if the dashboard is accessible."""
    
    try:
        import requests
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is accessible at http://localhost:8080")
            return True
        else:
            print(f"⚠️ Dashboard responded with status {response.status_code}")
            return False
    except ImportError:
        print("💡 Install requests to test dashboard: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        print("💡 Make sure your bot is running with the dashboard enabled")
        return False

def main():
    """Main function to run all fixes."""
    
    print("🔧 Bassline Bot Dashboard Quick Fix")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Please run this script from the bassline-bot root directory")
        print("💡 Current directory should contain 'src' folder")
        return False
    
    success = True
    
    # Check dependencies
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        success = False
    
    # Create static directories
    print("\n2. Creating static directories...")
    create_static_directories()
    
    # Patch dashboard file
    print("\n3. Patching dashboard file...")
    if not patch_dashboard_file():
        success = False
    
    # Test dashboard (optional)
    print("\n4. Testing dashboard connection...")
    test_dashboard_connection()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Dashboard fix completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your bot if it's running")
        print("2. Visit http://localhost:8080 to see the dashboard")
        print("3. Check that all tabs load without errors")
        print("\n💡 The dashboard now includes mock data for development.")
        print("   Replace the mock data with real bot data as needed.")
    else:
        print("❌ Some fixes failed. Check the errors above.")
        print("💡 You may need to manually apply some fixes.")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Fix cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Please check the error and try again")