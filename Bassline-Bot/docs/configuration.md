# Configuration Guide

Complete configuration reference for Bassline-Bot.

## Environment Variables

### Core Settings

#### Discord Configuration
```env
# Required - Your Discord bot token
DISCORD_TOKEN=your_discord_bot_token_here

# Optional - For OAuth2 integration
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
```

#### Database Configuration
```env
# SQLite (Default - good for small servers)
DATABASE_URL=sqlite:///./data/basslinebot.db

# PostgreSQL (Recommended for production)
DATABASE_URL=postgresql://username:password@localhost:5432/basslinebot

# Connection pool settings (PostgreSQL only)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

#### Redis Configuration (Optional)
```env
# Redis for caching and session storage
REDIS_URL=redis://localhost:6379

# Redis with authentication
REDIS_URL=redis://:password@localhost:6379

# Redis cluster
REDIS_URL=redis://node1:6379,node2:6379,node3:6379
```

### Bot Behavior

#### Basic Settings
```env
# Command prefix for text commands
BOT_PREFIX=!bl

# Bot display name
BOT_NAME=Bassline-Bot

# Maximum songs in queue per guild
MAX_QUEUE_SIZE=100

# Maximum songs in a playlist
MAX_PLAYLIST_SIZE=200

# Auto-disconnect timeout (seconds)
IDLE_TIMEOUT=300
```

#### Audio Settings
```env
# Default volume (0.0 to 1.0)
DEFAULT_VOLUME=0.5

# Maximum song length (seconds)
MAX_SONG_DURATION=3600

# Enable downloading instead of streaming
DOWNLOAD_ENABLED=true

# Enable bass boost feature
BASS_BOOST_ENABLED=true

# Audio quality preference
AUDIO_QUALITY=best
```

### Logging Configuration
```env
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Main log file location
LOG_FILE=logs/basslinebot.log

# Enable verbose logging (development)
VERBOSE_LOGGING=false

# Log rotation settings
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

### Web Dashboard
```env
# Enable web dashboard
DASHBOARD_ENABLED=true

# Dashboard server settings
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080

# Security key for sessions
SECRET_KEY=your-secret-key-change-this

# Dashboard authentication (optional)
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=secure_password
```

### Monitoring & Metrics
```env
# Enable Prometheus metrics
METRICS_ENABLED=true

# Enable health check endpoint
HEALTH_CHECK_ENABLED=true

# Prometheus metrics port
PROMETHEUS_PORT=9090

# Metrics collection interval (seconds)
METRICS_INTERVAL=60
```

### Commercial Features
```env
# Enable multi-tenant mode
MULTI_TENANT=false

# Default user tier
DEFAULT_TIER=free

# Enable billing integration
BILLING_ENABLED=false

# Stripe integration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
WEBHOOK_SECRET=whsec_...

# Subscription tiers
TIER_FREE_QUEUE_LIMIT=10
TIER_PREMIUM_QUEUE_LIMIT=50
TIER_PRO_QUEUE_LIMIT=200
```

### External APIs
```env
# YouTube API (optional - for enhanced features)
YOUTUBE_API_KEY=your_youtube_api_key

# Spotify integration (optional)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Last.fm integration (optional)
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_API_SECRET=your_lastfm_api_secret
```

### Performance Tuning
```env
# Maximum concurrent downloads
MAX_CONCURRENT_DOWNLOADS=3

# Download timeout (seconds)
DOWNLOAD_TIMEOUT=30

# Search cache TTL (seconds)
SEARCH_CACHE_TTL=3600

# Maximum search results
MAX_SEARCH_RESULTS=10

# YouTube-DL options
YTDL_SOCKET_TIMEOUT=10
YTDL_RETRIES=3
```

## Advanced Configuration

### Database Optimization

#### SQLite Settings
```env
DATABASE_URL=sqlite:///./data/basslinebot.db?timeout=20&check_same_thread=False
```

#### PostgreSQL Settings
```env
# Full PostgreSQL configuration
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require&pool_size=20&max_overflow=30
```

### Custom Audio Processing
```env
# FFmpeg custom options
FFMPEG_BEFORE_OPTIONS=-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5
FFMPEG_OPTIONS=-vn -b:a 128k

# Bass boost filter settings
BASS_BOOST_GAIN=4
BASS_BOOST_FREQUENCY=70
BASS_BOOST_WIDTH=0.4
```

### Security Settings
```env
# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CALLS=5
RATE_LIMIT_PERIOD=60

# Input validation
MAX_INPUT_LENGTH=500
SANITIZE_INPUTS=true

# CORS settings
CORS_ENABLED=true
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

## Guild-Specific Settings

Settings can be customized per Discord server through the dashboard or database:

### Database Configuration
```sql
-- Update guild settings
UPDATE guilds SET 
    max_queue_size = 50,
    auto_disconnect_timeout = 600,
    bass_boost_enabled = true
WHERE id = 'guild_id_here';
```

### API Configuration
```python
# Update via API
POST /api/guilds/{guild_id}/settings
{
    "max_queue_size": 50,
    "auto_disconnect_timeout": 600,
    "bass_boost_enabled": true
}
```

## Configuration Validation

### Environment Validation Script
```bash
# Check configuration
python scripts/validate_config.py

# Test database connection
python scripts/test_database.py

# Validate Discord token
python scripts/test_discord.py
```

### Docker Configuration
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  bot:
    environment:
      - LOG_LEVEL=DEBUG
      - VERBOSE_LOGGING=true
    volumes:
      - ./custom-config:/app/config
```

## Configuration Examples

### Development Setup
```env
DISCORD_TOKEN=your_dev_token
DATABASE_URL=sqlite:///./data/dev.db
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
DASHBOARD_ENABLED=true
METRICS_ENABLED=false
DOWNLOAD_ENABLED=false
```

### Production Setup
```env
DISCORD_TOKEN=your_prod_token
DATABASE_URL=postgresql://bassline:password@db:5432/basslinebot
LOG_LEVEL=INFO
VERBOSE_LOGGING=false
DASHBOARD_ENABLED=true
METRICS_ENABLED=true
DOWNLOAD_ENABLED=true
REDIS_URL=redis://redis:6379
```

### Commercial Hosting
```env
DISCORD_TOKEN=your_token
DATABASE_URL=postgresql://user:pass@db-cluster:5432/basslinebot
MULTI_TENANT=true
BILLING_ENABLED=true
STRIPE_SECRET_KEY=sk_live_...
DASHBOARD_ENABLED=true
METRICS_ENABLED=true
DEFAULT_TIER=free
```

## Troubleshooting Configuration

### Common Issues

**Invalid Token**
```bash
# Test Discord token
python -c "
import discord
import asyncio
async def test():
    client = discord.Client()
    await client.login('YOUR_TOKEN')
    print('Token valid!')
asyncio.run(test())
"
```

**Database Connection**
```bash
# Test database
python -c "
from config.database import engine
with engine.connect() as conn:
    result = conn.execute('SELECT 1').fetchone()
    print('Database connected!')
"
```

**Missing Dependencies**
```bash
# Verify all dependencies
pip check
python -c "import discord, yt_dlp, fastapi, sqlalchemy; print('All imports successful!')"
```

## Best Practices

1. Use environment files instead of hardcoding values
2. Separate dev/staging/prod configurations
3. Rotate secrets regularly (tokens, keys)
4. Monitor configuration changes in production
5. Backup configuration with your database
6. Validate configuration before deployment
7. Use strong secrets for production
8. Enable monitoring in production
9. Set appropriate log levels for environment
10. Test configuration changes in staging first