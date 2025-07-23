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
    db_pool_size: int = 20
    db_max_overflow: int = 30
    
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
    audio_quality: str = "best"
    
    # FFmpeg Configuration
    ffmpeg_before_options: str = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ffmpeg_options: str = "-vn -b:a 128k"
    
    # Bass Boost Settings
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
    dashboard_port: int = 8000
    secret_key: str = "change-this-secret-key-in-production"
    
    # CORS Settings
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
    
    # Multi-tenancy
    multi_tenant: bool = False
    default_tier: str = "free"
    
    # External APIs
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None
    
    # Download Settings
    max_concurrent_downloads: int = 3
    download_timeout: int = 30
    
    # Search and Cache Settings
    search_cache_ttl: int = 3600
    max_search_results: int = 10
    
    # YouTube-DL Settings
    ytdl_socket_timeout: int = 10
    ytdl_retries: int = 3
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_calls: int = 5
    rate_limit_period: int = 60
    
    # Input Validation
    max_input_length: int = 500
    sanitize_inputs: bool = True
    
    # Tier Limits
    tier_free_queue_limit: int = 10
    tier_premium_queue_limit: int = 50
    tier_pro_queue_limit: int = 200
    
    # API Settings
    api_rate_limit: int = 100
    max_request_size: int = 10485760  # 10MB
    allowed_file_types: str = "mp3,wav,ogg,m4a"
    
    # Session Settings
    session_timeout: int = 60
    
    # Development Settings
    debug: bool = False
    hot_reload: bool = False
    mock_youtube: bool = False
    mock_discord: bool = False
    
    # System Settings
    tz: str = "UTC"
    puid: int = 1000
    pgid: int = 1000
    
    # Backup Settings
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
    
    @field_validator('audio_quality')
    @classmethod
    def validate_audio_quality(cls, v):
        valid_qualities = ['worst', 'best', 'bestaudio', 'worstaudio']
        if v not in valid_qualities:
            raise ValueError(f'audio_quality must be one of {valid_qualities}')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()

# Ensure required directories exist
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("downloads").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path(settings.backup_path).mkdir(exist_ok=True)