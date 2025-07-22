#!/usr/bin/env python3
"""
Database schema fix script
Run this to update existing database with missing columns
"""

import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_database_schema():
    """Fix database schema issues."""
    
    print("🔧 Fixing database schema...")
    
    try:
        from config.database import engine
        import sqlalchemy
        
        # Get current table info
        inspector = sqlalchemy.inspect(engine)
        
        # Check if guilds table exists and what columns it has
        if inspector.has_table('guilds'):
            columns = [col['name'] for col in inspector.get_columns('guilds')]
            print(f"Current guilds table columns: {columns}")
            
            # Add missing columns to guilds table
            missing_guild_columns = []
            expected_columns = ['is_active', 'created_at', 'updated_at']
            
            for col in expected_columns:
                if col not in columns:
                    missing_guild_columns.append(col)
            
            if missing_guild_columns:
                print(f"Adding missing columns to guilds table: {missing_guild_columns}")
                
                with engine.connect() as conn:
                    # Use transaction to ensure all changes are applied together
                    trans = conn.begin()
                    try:
                        if 'is_active' not in columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE guilds ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                            print("✓ Added is_active column")
                        
                        if 'created_at' not in columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE guilds ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                            print("✓ Added created_at column")
                        
                        if 'updated_at' not in columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE guilds ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                            print("✓ Added updated_at column")
                        
                        trans.commit()
                        print("✅ Guilds table updated successfully")
                        
                    except Exception as e:
                        trans.rollback()
                        print(f"❌ Failed to update guilds table: {e}")
                        raise
            else:
                print("✅ Guilds table already has all required columns")
        
        # Check users table
        if inspector.has_table('users'):
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            print(f"Current users table columns: {user_columns}")
            
            # Add missing columns to users table
            missing_user_columns = []
            expected_user_columns = ['discriminator', 'bass_boost_enabled', 'default_volume', 'total_songs_played', 'total_commands_used', 'tier', 'created_at', 'updated_at', 'last_seen']
            
            for col in expected_user_columns:
                if col not in user_columns:
                    missing_user_columns.append(col)
            
            if missing_user_columns:
                print(f"Adding missing columns to users table: {missing_user_columns}")
                
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        if 'discriminator' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN discriminator VARCHAR(4)"))
                        
                        if 'total_songs_played' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN total_songs_played INTEGER DEFAULT 0"))
                        
                        if 'total_commands_used' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN total_commands_used INTEGER DEFAULT 0"))
                        
                        if 'default_volume' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN default_volume REAL DEFAULT 0.5"))
                            print("✓ Added default_volume column")
                        
                        if 'bass_boost_enabled' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN bass_boost_enabled BOOLEAN DEFAULT FALSE"))
                            print("✓ Added bass_boost_enabled column")
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                        
                        if 'updated_at' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                        
                        if 'last_seen' not in user_columns:
                            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN last_seen DATETIME DEFAULT CURRENT_TIMESTAMP"))
                        
                        trans.commit()
                        print("✅ Users table updated successfully")
                        
                    except Exception as e:
                        trans.rollback()
                        print(f"❌ Failed to update users table: {e}")
                        raise
            else:
                print("✅ Users table already has all required columns")
        
        # Test the fixes
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM guilds"))
            guild_count = result.fetchone()[0]
            print(f"✅ Database test passed. Found {guild_count} guilds.")
        
        print("🎉 Database schema fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database schema fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 Bassline-Bot Database Schema Fix")
    print("="*50)
    
    if fix_database_schema():
        print("\n✅ Database fix completed!")
        print("You can now restart the bot: python -m src.run")
    else:
        print("\n❌ Database fix failed!")
        print("You may need to delete the database and start fresh.")
        print("To reset: delete data/basslinebot.db and run the bot again.")

if __name__ == "__main__":
    main()