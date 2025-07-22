#!/usr/bin/env python3
"""Database migration script."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import init_db, engine
from config.logging import logger

def main():
    """Run database migrations."""
    try:
        logger.info("Starting database migration...")
        
        # Initialize database tables
        init_db()
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1").fetchone()
            if result:
                logger.info("✅ Database connection successful")
        
        logger.info("✅ Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()