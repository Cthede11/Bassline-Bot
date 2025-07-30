# config/settings.py - Fixed version to handle environment variable parsing

import os
from pathlib import Path
from typing import Optional

def safe_int(value: str, default: int) -> int:
    """Safely convert string to int, handling comments and invalid values."""
    if not value:
        return default
    
    # Remove comments from the value
    value = value.split('#')[0].strip().strip("'\"")
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: str, default: float) -> float:
    """Safely convert string to float, handling comments and invalid values."""
    if not value:
        return default
    
    # Remove comments from the value
    value = value.split('#')[0].strip().strip("'\"")
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_bool(value: str, default: bool = False) -> bool:
    """Safely convert string to bool, handling comments and invalid values."""
    if not value:
        return default
    
    # Remove comments from the value
    value = value.split('#')[0].strip().strip("'\"").lower()
    
    return value in ('true', '1', 'yes', 'on', 'enabled')

class Settings:
    """Configuration settings for the Discord bot with sharding support."""
    
    # Core Bot Settings
    bot_name: str = os.getenv('BOT_NAME', 'Bassline-Bot')
    bot_prefix: str = os.getenv('BOT_PREFIX', '!')
    discord_token: str = os.getenv('DISCORD_TOKEN', '')
    
    # Sharding Configuration
    # If both are None, automatic sharding will be used
    shard_id: Optional[int] = None if os.getenv('SHARD_ID') is None else safe_int(os.getenv('SHARD_ID', ''), None)
    shard_count: Optional[int] = None if os.getenv('SHARD_COUNT') is None else safe_int(os.getenv('SHARD_COUNT', ''), None)
    
    # Sharding behavior settings
    auto_shard: bool = safe_bool(os.getenv('AUTO_SHARD', 'true'))
    chunk_guilds_at_startup: bool = safe_bool(os.getenv('CHUNK_GUILDS_AT_STARTUP', 'false'))
    member_cache_enabled: bool = safe_bool(os.getenv('MEMBER_CACHE_ENABLED', 'false'))
    
    # Database Configuration
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./data/basslinebot.db')
    
    # Performance settings adjusted for sharding
    max_queue_size: int = safe_int(os.getenv('MAX_QUEUE_SIZE', '100'), 100)
    max_concurrent_downloads: int = safe_int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '3'), 3)
    download_timeout: int = safe_int(os.getenv('DOWNLOAD_TIMEOUT', '30'), 30)
    
    # Dashboard Configuration
    dashboard_enabled: bool = safe_bool(os.getenv('DASHBOARD_ENABLED', 'true'))
    download_enabled: bool = True
    bass_boost_enabled: bool = False
    auto_disconnect_timeout: int = 300
    max_concurrent_downloads: int = 3
    download_timeout: int = 30
    cache_ttl: int = 3600
    dashboard_host: str = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    dashboard_port: int = safe_int(os.getenv('DASHBOARD_PORT', '8080'), 8080)
    
    # Only start dashboard on specific shard (usually shard 0)
    dashboard_shard_id: int = safe_int(os.getenv('DASHBOARD_SHARD_ID', '0'), 0)
    
    # Monitoring & Health Checks
    health_check_enabled: bool = safe_bool(os.getenv('HEALTH_CHECK_ENABLED', 'true'))
    metrics_enabled: bool = safe_bool(os.getenv('METRICS_ENABLED', 'true'))
    
    # Shard-specific health check settings
    shard_health_check_interval: int = safe_int(os.getenv('SHARD_HEALTH_CHECK_INTERVAL', '30'), 30)
    shard_reconnect_attempts: int = safe_int(os.getenv('SHARD_RECONNECT_ATTEMPTS', '5'), 5)
    
    # Logging Configuration
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', 'logs/basslinebot.log')
    verbose_logging: bool = safe_bool(os.getenv('VERBOSE_LOGGING', 'false'))
    
    # Shard-specific logging
    log_shard_events: bool = safe_bool(os.getenv('LOG_SHARD_EVENTS', 'true'))
    
    # Redis Configuration (recommended for multi-shard setups)
    redis_url: str = os.getenv('REDIS_URL', '')
    redis_enabled: bool = bool(redis_url)
    
    # Cache settings for sharded environment
    cache_enabled: bool = safe_bool(os.getenv('CACHE_ENABLED', str(redis_enabled)))
    cache_ttl: int = safe_int(os.getenv('CACHE_TTL', '3600'), 3600)
    
    # Inter-shard communication settings
    ipc_enabled: bool = safe_bool(os.getenv('IPC_ENABLED', 'false'))
    ipc_port: int = safe_int(os.getenv('IPC_PORT', '8765'), 8765)
    ipc_secret: str = os.getenv('IPC_SECRET', 'your_ipc_secret_here')
    
    # Audio & Voice Settings (per shard)
    ffmpeg_options: str = os.getenv('FFMPEG_OPTIONS', '-nostdin -loglevel panic')
    ytdl_format: str = os.getenv('YTDL_FORMAT', 'bestaudio/best')
    
    # Voice connection limits per shard
    max_voice_connections_per_shard: int = safe_int(os.getenv('MAX_VOICE_CONNECTIONS_PER_SHARD', '10'), 10)
    voice_timeout: int = safe_int(os.getenv('VOICE_TIMEOUT', '300'), 300)
    
    # Security Settings
    command_cooldown: float = safe_float(os.getenv('COMMAND_COOLDOWN', '2.0'), 2.0)
    max_user_queues: int = safe_int(os.getenv('MAX_USER_QUEUES', '5'), 5)
    
    # Development & Debug Settings
    debug_mode: bool = safe_bool(os.getenv('DEBUG_MODE', 'false'))
    testing_mode: bool = safe_bool(os.getenv('TESTING_MODE', 'false'))
    
    # Shard debugging - FIXED: This was causing the error
    debug_shards: bool = safe_bool(os.getenv('DEBUG_SHARDS', 'false'))
    shard_startup_delay: int = safe_int(os.getenv('SHARD_STARTUP_DELAY', '5'), 5)  # Fixed parsing
    
    # Resource Management
    memory_limit_mb: int = safe_int(os.getenv('MEMORY_LIMIT_MB', '512'), 512)
    cpu_limit_percent: int = safe_int(os.getenv('CPU_LIMIT_PERCENT', '50'), 50)
    
    # Scaling Configuration
    auto_scaling_enabled: bool = safe_bool(os.getenv('AUTO_SCALING_ENABLED', 'false'))
    guilds_per_shard_threshold: int = safe_int(os.getenv('GUILDS_PER_SHARD_THRESHOLD', '1000'), 1000)
    scale_up_threshold: float = safe_float(os.getenv('SCALE_UP_THRESHOLD', '0.8'), 0.8)
    scale_down_threshold: float = safe_float(os.getenv('SCALE_DOWN_THRESHOLD', '0.3'), 0.3)
    
    # Error Handling & Recovery
    max_reconnect_attempts: int = safe_int(os.getenv('MAX_RECONNECT_ATTEMPTS', '5'), 5)
    reconnect_delay: int = safe_int(os.getenv('RECONNECT_DELAY', '10'), 10)
    shard_failure_threshold: int = safe_int(os.getenv('SHARD_FAILURE_THRESHOLD', '3'), 3)
    
    # Startup Configuration
    startup_timeout: int = safe_int(os.getenv('STARTUP_TIMEOUT', '120'), 120)
    graceful_shutdown_timeout: int = safe_int(os.getenv('GRACEFUL_SHUTDOWN_TIMEOUT', '30'), 30)
    
    @property
    def is_sharded(self) -> bool:
        """Check if the bot is configured for sharding."""
        return self.shard_count is not None and self.shard_count > 1
    
    @property
    def is_auto_sharded(self) -> bool:
        """Check if the bot uses automatic sharding."""
        return self.auto_shard and (self.shard_id is None or self.shard_count is None)
    
    @property
    def should_start_dashboard(self) -> bool:
        """Check if this instance should start the dashboard."""
        if not self.dashboard_enabled:
            return False
        
        # If not sharded, always start dashboard
        if not self.is_sharded:
            return True
        
        # If sharded, only start on designated shard
        return self.shard_id == self.dashboard_shard_id or self.shard_id is None
    
    def get_shard_info(self) -> dict:
        """Get current shard configuration info."""
        return {
            'shard_id': self.shard_id,
            'shard_count': self.shard_count,
            'auto_shard': self.auto_shard,
            'is_sharded': self.is_sharded,
            'is_auto_sharded': self.is_auto_sharded,
        }
    
    def validate_sharding_config(self) -> list:
        """Validate sharding configuration and return any issues."""
        issues = []
        
        # Check for invalid shard configuration
        if self.shard_id is not None and self.shard_count is not None:
            if self.shard_id < 0:
                issues.append("SHARD_ID cannot be negative")
            
            if self.shard_count <= 0:
                issues.append("SHARD_COUNT must be positive")
            
            if self.shard_id >= self.shard_count:
                issues.append(f"SHARD_ID ({self.shard_id}) must be less than SHARD_COUNT ({self.shard_count})")
        
        # Check dashboard configuration
        if self.dashboard_enabled and self.dashboard_shard_id >= (self.shard_count or 1):
            issues.append(f"DASHBOARD_SHARD_ID ({self.dashboard_shard_id}) must be less than SHARD_COUNT")
        
        # Resource limit checks
        if self.max_voice_connections_per_shard <= 0:
            issues.append("MAX_VOICE_CONNECTIONS_PER_SHARD must be positive")
        
        if self.guilds_per_shard_threshold <= 0:
            issues.append("GUILDS_PER_SHARD_THRESHOLD must be positive")
        
        return issues


# Global settings instance
settings = Settings()

# Validate configuration on import
config_issues = settings.validate_sharding_config()
if config_issues:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Sharding configuration issues found:")
    for issue in config_issues:
        logger.warning(f"  - {issue}")