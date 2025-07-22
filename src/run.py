#!/usr/bin/env python3
"""
Bassline-Bot Startup Script
Run this file to start the bot: python -m src.run
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def setup_environment():
    """Set up the environment and check requirements."""
    
    # Create necessary directories
    directories = ['logs', 'data', 'downloads', 'backups', 'static']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created/verified directory: {directory}")
    
    # Check for .env file
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ ERROR: .env file not found!")
        print("Please copy .env.example to .env and add your Discord bot token.")
        print("\nSteps:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env and add your DISCORD_TOKEN")
        print("3. Run this script again")
        sys.exit(1)
    
    # Load environment variables
    try:
        from config.settings import settings
        if not settings.discord_token or settings.discord_token == "your_discord_bot_token_here":
            print("❌ ERROR: Discord token not configured!")
            print("Please edit your .env file and set a valid DISCORD_TOKEN")
            sys.exit(1)
        print("✓ Environment configuration loaded")
        return settings
    except Exception as e:
        print(f"❌ ERROR: Failed to load configuration: {e}")
        print("\nThis might be a Pydantic validation error.")
        print("Check your .env file for invalid values or typos.")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are installed."""
    
    missing_deps = []
    
    # Critical dependencies
    try:
        import discord
        print("✓ discord.py installed")
    except ImportError:
        missing_deps.append("discord.py")
    
    try:
        import yt_dlp
        print("✓ yt-dlp installed")
    except ImportError:
        missing_deps.append("yt-dlp")
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy installed")
    except ImportError:
        missing_deps.append("sqlalchemy")
    
    try:
        import aiohttp
        print("✓ aiohttp installed")
    except ImportError:
        missing_deps.append("aiohttp")
    
    try:
        import pydantic_settings
        print("✓ pydantic-settings installed")
    except ImportError:
        try:
            import pydantic
            print("✓ pydantic installed (legacy mode)")
        except ImportError:
            missing_deps.append("pydantic")
    
    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ FFmpeg is installed")
        else:
            print("⚠️  WARNING: FFmpeg may not be working properly")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ ERROR: FFmpeg not found!")
        print("Please install FFmpeg:")
        print("- Windows: Download from https://ffmpeg.org/download.html")
        print("- macOS: brew install ffmpeg")
        print("- Ubuntu/Debian: sudo apt install ffmpeg")
        print("- CentOS/RHEL: sudo yum install ffmpeg")
        missing_deps.append("ffmpeg")
    
    if missing_deps:
        print(f"\n❌ ERROR: Missing dependencies: {', '.join(missing_deps)}")
        print("Please install them with: pip install -r requirements.txt")
        if "ffmpeg" in missing_deps:
            print("And install FFmpeg using your system package manager.")
        sys.exit(1)

def check_database():
    """Initialize database if needed."""
    try:
        from config.database import init_db, engine
        import sqlalchemy
        
        print("🗄️  Initializing database...")
        init_db()
        
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            if result.fetchone():
                print("✓ Database initialized and tested")
        
    except Exception as e:
        print(f"❌ ERROR: Database initialization failed: {e}")
        print("This might be a temporary issue. Continuing...")

def show_startup_info(settings):
    """Show startup information."""
    
    print("\n" + "="*60)
    print(f"🎵 {settings.bot_name}")
    print("="*60)
    print(f"Version: 1.0.0")
    print(f"Dashboard: {'Enabled' if settings.dashboard_enabled else 'Disabled'}")
    if settings.dashboard_enabled:
        print(f"Dashboard URL: http://{settings.dashboard_host}:{settings.dashboard_port}")
    print(f"Log Level: {settings.log_level}")
    print(f"Database: {settings.database_url.split('://')[0].upper()}")
    print("="*60)
    print("Bot is starting up...")
    print("Press Ctrl+C to stop the bot")
    print("="*60 + "\n")

async def main():
    """Main entry point."""
    
    print("🚀 Starting Bassline-Bot...")
    print("Checking environment...")
    
    # Setup and checks
    settings = setup_environment()
    check_dependencies()
    check_database()
    
    # Show startup info
    show_startup_info(settings)
    
    # Import and start the bot
    try:
        from src.bot import main as bot_main
        await bot_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested by user")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        logging.exception("Fatal error occurred")
        sys.exit(1)
    finally:
        print("👋 Bot shutdown completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        sys.exit(1)