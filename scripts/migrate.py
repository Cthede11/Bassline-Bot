#!/usr/bin/env python3
"""
Complete database initialization and verification script.
This will create all tables if they don't exist and verify the setup.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import engine, SessionLocal, Base
from config.logging import logger

def initialize_database():
    """Initialize all database tables."""
    try:
        print("🔄 Initializing database tables...")
        
        # Import all models to ensure they're registered
        from src.database.models import Guild, User, Playlist, Song, Usage
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def check_database_structure():
    """Check that all expected tables and columns exist."""
    try:
        print("🔍 Checking database structure...")
        
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # Check tables exist
        tables = inspector.get_table_names()
        expected_tables = ['guilds', 'users', 'playlists', 'songs', 'usage']
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print(f"✅ All tables exist: {tables}")
        
        # Check songs table structure (most complex)
        songs_columns = inspector.get_columns('songs')
        songs_column_names = [col['name'] for col in songs_columns]
        
        expected_song_columns = [
            'id', 'title', 'url', 'duration', 'thumbnail', 'uploader',
            'playlist_id', 'position', 'added_by', 'local_path', 'file_size',
            'is_downloaded', 'download_date', 'play_count', 'last_played',
            'first_played', 'last_requested_by', 'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in expected_song_columns if col not in songs_column_names]
        if missing_columns:
            print(f"❌ Missing columns in songs table: {missing_columns}")
            return False
        
        print(f"✅ Songs table has all expected columns: {len(songs_column_names)} columns")
        return True
        
    except Exception as e:
        print(f"❌ Database structure check failed: {e}")
        return False

def test_database_operations():
    """Test basic database operations."""
    session = SessionLocal()
    try:
        print("🧪 Testing database operations...")
        
        from src.database.models import Song, Guild, User
        from datetime import datetime
        
        # Test creating a global song (no playlist)
        test_song = Song(
            title="Test Migration Song",
            url=f"https://test.com/migration_test_{int(time.time())}",
            play_count=1,
            first_played=datetime.utcnow(),
            is_downloaded=False
        )
        session.add(test_song)
        session.commit()
        print("✅ Can create global songs")
        
        # Test querying
        all_songs = session.query(Song).all()
        print(f"✅ Can query songs: {len(all_songs)} songs found")
        
        # Test updating
        test_song.play_count = 2
        test_song.last_played = datetime.utcnow()
        session.commit()
        print("✅ Can update song records")
        
        # Clean up
        session.delete(test_song)
        session.commit()
        print("✅ Can delete song records")
        
        print("🎉 All database operations working!")
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def main():
    """Main initialization and verification function."""
    print("🎵 Bassline-Bot Database Setup & Verification")
    print("=" * 50)
    
    try:
        # Step 1: Initialize database
        if not initialize_database():
            print("❌ Database initialization failed")
            return False
        
        # Step 2: Check structure
        if not check_database_structure():
            print("❌ Database structure check failed")
            return False
        
        # Step 3: Test operations
        if not test_database_operations():
            print("❌ Database operations test failed")
            return False
        
        # Success!
        print()
        print("🎉 Database setup completed successfully!")
        print()
        print("✅ Your database is ready for:")
        print("   • Database-first song management")
        print("   • Smart caching and play count tracking")
        print("   • Global song database")
        print("   • Enhanced analytics")
        print()
        print("📝 Next steps:")
        print("   1. Start your bot: python -m src.bot")
        print("   2. Test with /play command")
        print("   3. Check analytics with /songstats (after implementing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed with unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)