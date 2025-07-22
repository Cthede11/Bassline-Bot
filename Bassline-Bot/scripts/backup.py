#!/usr/bin/env python3
"""Database backup script."""

import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from config.logging import logger

def backup_sqlite(db_path: str, backup_dir: str) -> str:
    """Backup SQLite database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"basslinebot_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"SQLite backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup SQLite database: {e}")
        raise

def backup_postgresql(backup_dir: str) -> str:
    """Backup PostgreSQL database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"basslinebot_backup_{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Extract connection details from DATABASE_URL
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(settings.database_url)
        
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed.password
        
        cmd = [
            'pg_dump',
            '-h', parsed.hostname,
            '-p', str(parsed.port or 5432),
            '-U', parsed.username,
            '-d', parsed.path[1:],  # Remove leading slash
            '-f', backup_path,
            '--verbose'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"PostgreSQL backup created: {backup_path}")
            return backup_path
        else:
            raise Exception(f"pg_dump failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Failed to backup PostgreSQL database: {e}")
        raise

def cleanup_old_backups(backup_dir: str, keep_days: int = 7):
    """Remove backup files older than specified days."""
    try:
        current_time = datetime.now()
        
        for file_path in Path(backup_dir).glob("basslinebot_backup_*"):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            age_days = (current_time - file_time).days
            
            if age_days > keep_days:
                file_path.unlink()
                logger.info(f"Removed old backup: {file_path}")
                
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}")

def main():
    """Main backup function."""
    try:
        # Create backup directory
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        logger.info("Starting database backup...")
        
        # Determine database type and backup accordingly
        if settings.database_url.startswith("sqlite"):
            # Extract SQLite database path
            db_path = settings.database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                backup_path = backup_sqlite(db_path, backup_dir)
            else:
                logger.error(f"SQLite database not found: {db_path}")
                sys.exit(1)
        
        elif settings.database_url.startswith("postgresql"):
            backup_path = backup_postgresql(backup_dir)
        
        else:
            logger.error(f"Unsupported database type: {settings.database_url}")
            sys.exit(1)
        
        # Cleanup old backups
        cleanup_old_backups(backup_dir)
        
        logger.info("✅ Backup completed successfully")
        print(f"Backup created: {backup_path}")
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()