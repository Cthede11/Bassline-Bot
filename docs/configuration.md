# Configuration Guide

This guide covers all the settings you can adjust to customize BasslineBot for your server.

## Basic Configuration

All settings are stored in your `.env` file. After installation, copy `.env.example` to `.env` and edit it with your preferred settings.

### Required Settings

```env
# Your Discord bot token (required)
DISCORD_TOKEN=your_discord_bot_token_here
```

### Basic Bot Settings

```env
# Bot display name
BOT_NAME=BasslineBot

# How many songs can be queued at once
MAX_QUEUE_SIZE=100

# How long to wait before leaving empty voice channels (seconds)
IDLE_TIMEOUT=300

# Default volume level (0.0 to 1.0)
DEFAULT_VOLUME=0.5
```

### Database Settings

By default, BasslineBot uses SQLite which works fine for most servers:

```env
DATABASE_URL=sqlite:///./data/basslinebot.db
```

For larger servers or multiple bot instances, PostgreSQL is recommended:

```env
DATABASE_URL=postgresql://username:password@hostname:5432/database_name
```

### Web Dashboard

The web dashboard lets you monitor your bot through a web browser:

```env
# Enable the web dashboard
DASHBOARD_ENABLED=true

# What port to run the dashboard on
DASHBOARD_PORT=8080

# Secret key for sessions (change this!)
SECRET_KEY=change-this-secret-key-in-production
```

Visit http://localhost:8080 (or whatever port you set) to access the dashboard.

### Audio Settings

```env
# Allow users to download and cache songs for faster playback
DOWNLOAD_ENABLED=true

# Allow users to toggle bass boost
BASS_BOOST_ENABLED=true

# Maximum song length in seconds (0 for no limit)
MAX_SONG_DURATION=3600
```

### Logging

```env
# How detailed should the logs be?
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Where to save log files
LOG_FILE=logs/basslinebot.log

# Show extra debugging information
VERBOSE_LOGGING=false
```

## 🔐 Security Configuration

### Basic Security

```env
# Change these in production!
SECRET_KEY=your_very_long_random_secret_key_minimum_32_characters
WEBHOOK_SECRET=your_webhook_secret_if_using_webhooks

# Session security
SESSION_TIMEOUT=3600
SECURE_COOKIES=true
HTTPONLY_COOKIES=true
```

### Rate Limiting

```env
# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10
```

### Access Control

```env
# IP whitelisting (optional)
ALLOWED_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16

# Admin users (Discord user IDs)
ADMIN_USERS=123456789012345678,987654321098765432

# Trusted domains
TRUSTED_DOMAINS=yourdomain.com,*.yourdomain.com
```

## ⚡ Performance Tuning

### Connection Pooling

```env
# Database connection pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO=false
```

### Caching Configuration

```env
# Redis caching
CACHE_TTL=3600
CACHE_PREFIX=basslinebot:
CACHE_ENABLED=true

# Memory limits
MEMORY_LIMIT=2GB
MEMORY_WARNING_THRESHOLD=1.5GB
```

### Concurrency Settings

```env
# Async settings
MAX_CONCURRENT_DOWNLOADS=5
MAX_CONCURRENT_STREAMS=10
WORKER_THREADS=4

# Queue processing
QUEUE_BATCH_SIZE=10
QUEUE_TIMEOUT=30
```

## 🚀 Advanced Features

### Multi-Tenancy & Commercial Features

```env
# Multi-tenant support
MULTI_TENANT=false
DEFAULT_TIER=free

# Billing integration
BILLING_ENABLED=false
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Usage limits per tier
FREE_TIER_QUEUE_LIMIT=50
PREMIUM_TIER_QUEUE_LIMIT=200
PRO_TIER_QUEUE_LIMIT=500
```

### Development Settings

```env
# Development mode
DEBUG_MODE=false
RELOAD_ON_CHANGE=false
DEVELOPMENT_MODE=false

# Testing
TESTING=false
TEST_DATABASE_URL=sqlite:///./test.db
MOCK_DISCORD_API=false
```

### Feature Flags

```env
# Feature toggles
ENABLE_PLAYLISTS=true
ENABLE_DOWNLOADS=true
ENABLE_BASS_BOOST=true
ENABLE_VOLUME_CONTROL=true
ENABLE_QUEUE_HISTORY=true
ENABLE_USER_STATISTICS=true
ENABLE_ADVANCED_SEARCH=true
```

## 📁 Configuration File Examples

### Development Configuration
```env
# .env.development
DISCORD_TOKEN=your_dev_bot_token
DATABASE_URL=sqlite:///./data/dev.db
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
DASHBOARD_ENABLED=true
METRICS_ENABLED=false
DOWNLOAD_ENABLED=false
TESTING=true
```

### Production Configuration
```env
# .env.production
DISCORD_TOKEN=your_prod_bot_token
DATABASE_URL=postgresql://bassline:secure_password@db-server:5432/basslinebot
REDIS_URL=redis://redis-server:6379/0

LOG_LEVEL=WARNING
VERBOSE_LOGGING=false
DASHBOARD_ENABLED=true
METRICS_ENABLED=true
DOWNLOAD_ENABLED=true

SECRET_KEY=your_very_secure_secret_key_for_production
CORS_ORIGINS=https://yourdomain.com
DASHBOARD_SECURE_COOKIES=true

MAX_QUEUE_SIZE=200
IDLE_TIMEOUT=600
```

### Docker Environment
```env
# .env.docker
DATABASE_URL=postgresql://bassline:${DB_PASSWORD}@db:5432/basslinebot
REDIS_URL=redis://redis:6379/0
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

## 🔧 Configuration Validation

### Validation Script
Create `scripts/validate_config.py`:

```python
#!/usr/bin/env python3
"""Configuration validation script."""

import os
import sys
from urllib.parse import urlparse

def validate_discord_token():
    """Validate Discord token format."""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        return False, "DISCORD_TOKEN is required"
    
    # Basic token format validation
    if len(token) < 50:
        return False, "DISCORD_TOKEN appears to be invalid (too short)"
    
    return True, "Discord token format appears valid"

def validate_database_url():
    """Validate database URL format."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return False, "DATABASE_URL is required"
    
    try:
        parsed = urlparse(db_url)
        if not parsed.scheme:
            return False, "DATABASE_URL missing scheme"
        
        supported_schemes = ['sqlite', 'postgresql', 'mysql']
        if parsed.scheme not in supported_schemes:
            return False, f"Unsupported database scheme: {parsed.scheme}"
        
        return True, f"Database URL valid ({parsed.scheme})"
    except Exception as e:
        return False, f"Invalid DATABASE_URL: {e}"

def validate_ports():
    """Validate port configurations."""
    dashboard_port = os.getenv('DASHBOARD_PORT', '8000')
    prometheus_port = os.getenv('PROMETHEUS_PORT', '9090')
    
    try:
        d_port = int(dashboard_port)
        p_port = int(prometheus_port)
        
        if d_port == p_port:
            return False, "Dashboard and Prometheus ports cannot be the same"
        
        if d_port < 1024 or d_port > 65535:
            return False, f"Dashboard port {d_port} out of valid range"
        
        return True, f"Ports valid (Dashboard: {d_port}, Prometheus: {p_port})"
    except ValueError:
        return False, "Port values must be integers"

def main():
    """Run all validations."""
    validations = [
        validate_discord_token,
        validate_database_url,
        validate_ports,
    ]
    
    all_passed = True
    
    print("🔍 Validating Bassline-Bot Configuration")
    print("=" * 50)
    
    for validation in validations:
        passed, message = validation()
        status = "✅" if passed else "❌"
        print(f"{status} {message}")
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All validations passed! Configuration looks good.")
        sys.exit(0)
    else:
        print("❌ Configuration validation failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Testing Configuration

```bash
# Test configuration
python scripts/validate_config.py

# Test database connection
python -c "from config.database import engine; engine.connect(); print('Database connection successful')"

# Test Discord token
python -c "
import discord, asyncio, os
async def test():
    client = discord.Client(intents=discord.Intents.default())
    await client.login(os.getenv('DISCORD_TOKEN'))
    print('Discord token valid!')
    await client.close()
asyncio.run(test())
"
```

## 🔄 Configuration Management

### Environment-Specific Configs

Use different configuration files for different environments:

```bash
# Load development config
cp .env.development .env

# Load production config  
cp .env.production .env

# Use environment-specific files
python -m src.bot --env development
```

### Configuration Hot Reload

Some settings can be reloaded without restarting the bot:

```bash
# Reload configuration (where supported)
curl -X POST http://localhost:8080/api/admin/reload-config
```

### Backup Configuration

```bash
# Backup current configuration
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Create configuration archive
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env config/ logs/
```

---

## 📚 Next Steps

- **[Installation Guide](installation.md)** - Initial setup
- **[Deployment Guide](deployment.md)** - Production deployment  
- **[API Documentation](api.md)** - Integration options
- **[Troubleshooting](troubleshooting.md)** - Common issues

*Need help with configuration? Check our [support channels](installation.md#getting-help) or create an issue on GitHub.*