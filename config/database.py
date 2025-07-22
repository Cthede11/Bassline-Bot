from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Database URL handling
if settings.database_url.startswith("sqlite"):
    # SQLite specific configuration
    engine = create_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        echo=settings.log_level == "DEBUG"
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(
        settings.database_url,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.log_level == "DEBUG"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    from src.database.models import Guild, User, Playlist, Song, Usage
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")