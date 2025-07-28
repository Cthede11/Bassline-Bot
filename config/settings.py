import os
from typing import Optional
from pathlib import Path

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import field_validator
except ImportError:
    # Pydantic v1 (fallback)
    from pydantic import BaseSettings
    from pydantic import validator as field_validator

class Settings(BaseSettings):
    # Discord Configuration
    discord_token: str
    discord_client_id: Optional[str] = None
    discord_client_secret: Optional[str] = None
    
    # Database Configuration
    database_url: str = "sqlite:///./data/basslinebot.db"
    redis_url: Optional[str] = None
    
    # Bot Configuration
    bot_prefix: str = "!bl"
    bot_name: str = "BasslineBot Pro"
    max_queue_size: int = 100
    max_playlist_size: int = 200
    idle_timeout: int = 300
    
    # Audio Configuration
    default_volume: float = 0.5
    max_song_duration: int = 3600
    download_enabled: bool = True
    bass_boost_enabled: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/basslinebot.log"
    verbose_logging: bool = False
    
    # Dashboard Configuration
    dashboard_enabled: bool = True
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    secret_key: str = "change-this-secret-key-in-production"
    
    # Commercial Features
    billing_enabled: bool = False
    stripe_public_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # Monitoring
    metrics_enabled: bool = True
    health_check_enabled: bool = True
    prometheus_port: int = 9090
    
    # Multi-tenancy
    multi_tenant: bool = False
    default_tier: str = "free"
    
    # External APIs
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('default_volume')
    @classmethod
    def validate_volume(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('default_volume must be between 0.0 and 1.0')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Ensure required directories exist
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("downloads").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)