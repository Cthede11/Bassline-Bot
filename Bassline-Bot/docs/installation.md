# Installation Guide

This guide covers different installation methods for Bassline-Bot.

## Prerequisites

### System Requirements
- **Python 3.8+** (3.11 recommended)
- **FFmpeg** (for audio processing)
- **Git** (for cloning repository)
- **4GB RAM minimum** (8GB recommended for production)
- **2GB disk space** (more for downloads/logs)

### Discord Requirements
- Discord Bot Application with token
- Bot invited to server with appropriate permissions

## Installation Methods

### Method 1: Automated Setup (Recommended)

#### Linux/macOS
```bash
# Clone repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Edit configuration
cp .env.example .env
nano .env  # Add your Discord token

# Start bot
python -m src.bot
```

#### Windows
```cmd
REM Clone repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

REM Run setup script
scripts\setup.bat

REM Edit configuration
copy .env.example .env
notepad .env

REM Start bot
python -m src.bot
```

### Method 2: Docker Installation

#### Quick Start
```bash
# Clone and start
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot
cp .env.example .env
# Edit .env with your Discord token
docker-compose up -d
```

#### Production Setup
```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f bot

# Access dashboard
open http://localhost:8080
```

### Method 3: Manual Installation

#### 1. Install Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip ffmpeg git postgresql redis-server
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip ffmpeg git postgresql-server redis
```

**macOS:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 ffmpeg git postgresql redis
```

**Windows:**
- Install Python 3.11 from python.org
- Install FFmpeg from ffmpeg.org
- Install Git from git-scm.com
- Install PostgreSQL (optional)

#### 2. Clone and Setup
```bash
# Clone repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate.bat  # Windows

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # Linux/macOS
# or
notepad .env  # Windows
```

**Required settings:**
```env
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=sqlite:///./data/basslinebot.db
DASHBOARD_PORT=8080
```

#### 4. Initialize Database
```bash
python scripts/migrate.py
```

#### 5. Start Bot
```bash
python -m src.bot
```

## Verification

### Test Basic Functionality
1. Bot should appear online in Discord
2. Try `/help` command
3. Check bot joins voice channel
4. Verify dashboard at http://localhost:8080

### Check Logs
```bash
# View current logs
tail -f logs/basslinebot.log

# Check for errors
grep ERROR logs/basslinebot.log
```

## Troubleshooting

### Common Issues

**FFmpeg Not Found**
```bash
# Check if FFmpeg is installed
ffmpeg -version

# If not found, install:
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows - download from ffmpeg.org
```

**Python Version Issues**
```bash
# Check Python version
python3 --version

# Install Python 3.11 if needed
# Ubuntu
sudo apt install python3.11

# Use specific version
python3.11 -m venv venv
```

**Permission Errors**
```bash
# Fix file permissions
chmod +x scripts/*.sh
chown -R $USER:$USER .

# Run with proper permissions
sudo -u botuser python -m src.bot
```

**Database Connection Issues**
```bash
# Check SQLite path
ls -la data/basslinebot.db

# Reset database
rm data/basslinebot.db
python scripts/migrate.py

# For PostgreSQL, check connection
psql -h localhost -U bassline -d basslinebot -c "SELECT 1;"
```

## Performance Optimization

### For Production
```bash
# Use PostgreSQL instead of SQLite
DATABASE_URL=postgresql://user:pass@localhost:5432/basslinebot

# Enable Redis caching
REDIS_URL=redis://localhost:6379

# Optimize logging
LOG_LEVEL=WARNING
VERBOSE_LOGGING=false
```

### System Limits
```bash
# Increase file descriptors
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize memory
echo "vm.swappiness=10" >> /etc/sysctl.conf
```

## Next Steps

1. **Configuration Guide** - Detailed settings
2. **Deployment Guide** - Production setup
3. **API Documentation** - Integration details

## Support

- **Issues**: Create GitHub issue
- **Discord**: Join support server
- **Documentation**: Check docs/ folder