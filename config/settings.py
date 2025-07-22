import os
from typing import Optional, List
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
    
    # Database connection pool settings
    db_pool_size: int = 20
    db_max_overflow: int = 30
    
    # Bot Configuration
    bot_prefix: str = "!bl"
    bot_name: str = "Bassline-Bot"
    max_queue_size: int = 100
    max_playlist_size: int = 200
    idle_timeout: int = 300
    
    # Audio Configuration
    default_volume: float = 0.5
    max_song_duration: int = 3600
    download_enabled: bool = True
    bass_boost_enabled: bool = True
    audio_quality: str = "best"
    
    # FFmpeg Configuration
    ffmpeg_before_options: str = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ffmpeg_options: str = "-vn -b:a 128k"
    
    # Bass boost settings
    bass_boost_gain: int = 4
    bass_boost_frequency: int = 70
    bass_boost_width: float = 0.4
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/basslinebot.log"
    verbose_logging: bool = False
    log_max_size: int = 10485760  # 10MB
    log_backup_count: int = 5
    
    # Dashboard Configuration
    dashboard_enabled: bool = True
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    secret_key: str = "change-this-secret-key-in-production"
    
    # Dashboard authentication (optional)
    dashboard_username: Optional[str] = None
    dashboard_password: Optional[str] = None
    
    # CORS settings
    cors_enabled: bool = True
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    
    # Commercial Features
    billing_enabled: bool = False
    stripe_public_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # Monitoring
    metrics_enabled: bool = True
    health_check_enabled: bool = True
    prometheus_port: int = 9090
    metrics_interval: int = 60
    
    # Performance settings
    max_concurrent_downloads: int = 3
    download_timeout: int = 30
    search_cache_ttl: int = 3600
    max_search_results: int = 10
    
    # YouTube-DL settings
    ytdl_socket_timeout: int = 10
    ytdl_retries: int = 3
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_calls: int = 5
    rate_limit_period: int = 60
    
    # Input validation
    max_input_length: int = 500
    sanitize_inputs: bool = True
    
    # Multi-tenancy
    multi_tenant: bool = False
    default_tier: str = "free"
    
    # Subscription tier limits
    tier_free_queue_limit: int = 10
    tier_premium_queue_limit: int = 50
    tier_pro_queue_limit: int = 200
    
    # External APIs
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None
    lastfm_api_key: Optional[str] = None
    lastfm_api_secret: Optional[str] = None
    
    # Security settings
    api_rate_limit: int = 100
    max_request_size: int = 10485760
    allowed_file_types: str = "mp3,wav,ogg,m4a"
    session_timeout: int = 60
    
    # Development settings
    debug: bool = False
    hot_reload: bool = False
    mock_youtube: bool = False
    mock_discord: bool = False
    test_guild_id: Optional[str] = None
    
    # Docker settings
    tz: str = "UTC"
    puid: int = 1000
    pgid: int = 1000
    
    # Backup settings
    auto_backup: bool = True
    backup_interval: int = 24
    backup_retention: int = 7
    backup_path: str = "./backups"
    
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
    
    @field_validator('bass_boost_width')
    @classmethod
    def validate_bass_width(cls, v):
        if not 0.1 <= v <= 2.0:
            raise ValueError('bass_boost_width must be between 0.1 and 2.0')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields in case there are additional env vars
        extra = "ignore"

# Create settings instance
settings = Settings()

# Ensure required directories exist
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("downloads").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path(settings.backup_path).mkdir(exist_ok=True)