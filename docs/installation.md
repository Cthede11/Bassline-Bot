## Setting Up Your Discord Bot

Before you can use BasslineBot, you need to create a Discord application and get a bot token.

### 1. Create a Discord Application
- Go to https://discord.com/developers/applications
- Click "New Application" and give it a name
- Go to the "Bot" section and click "Add Bot"
- Copy the bot token (you'll need this for your .env file)
- Enable "Message Content Intent" under Privileged Gateway Intents

### 2. Invite Your Bot to Your Server
- Go to OAuth2 > URL Generator
- Select "bot" and "applications.commands" scopes
- Select these permissions:
  - View Channels
  - Send Messages
  - Use Slash Commands
  - Connect (to voice channels)
  - Speak (in voice channels)
  - Manage Messages (for cleanup commands)
- Use the generated URL to invite your bot to your server

## Configuration

After installation, you need to configure the bot by editing your `.env` file:

```env
# Required - get this from Discord Developer Portal
DISCORD_TOKEN=your_discord_bot_token_here

# Basic settings
BOT_NAME=BasslineBot
MAX_QUEUE_SIZE=100
DEFAULT_VOLUME=0.5

# Database (SQLite is fine for most users)
DATABASE_URL=sqlite:///./data/basslinebot.db

# Web dashboard
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8080
```

## Testing Your Installation

After setting up everything:

1. Start the bot using command: `python -m src.bot`
2. Check that it shows as online in Discord
3. Try the `/help` command in your Discord server
4. Visit http://localhost:8080 to see the web dashboard
5. Test music by joining a voice channel and using `/play Never Gonna Give You Up`

## Troubleshooting

### FFmpeg Not Found
If you get an error about FFmpeg:
- **Linux**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from ffmpeg.org and add to your PATH

### Bot Won't Start
- Check that your Discord token is correct in the .env file
- Make sure Python 3.8 or newer is installed
- Verify that all dependencies installed without errors

### Music Won't Play
- Make sure FFmpeg is installed and working (`ffmpeg -version`)
- Check that the bot has permission to join and speak in voice channels
- Ensure you're in a voice channel when using `/play`

### Dashboard Not Loading
- Check if port 8080 is already in use by another program
- Try changing `DASHBOARD_PORT=8081` in your .env file
- Make sure your firewall isn't blocking the port

### Permission Errors
If you get permission errors on Linux/macOS:
```bash
chmod +x scripts/*.sh
chown -R $USER:$USER .
```

## Production Setup

For running the bot 24/7 on a server, you'll want to:

1. Use PostgreSQL instead of SQLite:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/basslinebot
   ```

2. Set up the bot as a system service:
   ```bash
   # Create a systemd service file
   sudo nano /etc/systemd/system/basslinebot.service
   ```

3. Use a reverse proxy like Nginx for the web dashboard

Check out the [deployment guide](deployment.md) for detailed production setup instructions.

## Getting Help

If you run into issues:
- Check the [troubleshooting section](#troubleshooting) above
- Look at existing [GitHub issues](https://github.com/Cthede11/bassline-bot/issues)
- Create a new issue with details about your problem
- Make sure to include your operating system, Python version, and error messages
- Feel free to reach out to me at: thedechristian11@gmail.com

## What's Next?

Once your bot is running:
- Set up playlists with `/setupplaylists`
- Configure a DJ role with `/setdjrole`
- Check out all the commands with `/help`
- Monitor your bot through the web dashboard

The bot will create all the necessary files and folders automatically when it starts, so you don't need to worry about setting up the database or creating directories manually.# 📦 Installation Guide

This comprehensive guide covers different installation methods for Bassline-Bot, from quick setup to production deployment.

## 🔑 Discord Bot Setup

### Creating Your Discord Bot

1. **Visit Discord Developer Portal**
   - Go to [https://discord.com/developers/applications](https://discord.com/developers/applications)
   - Click "New Application" and give it a name

2. **Configure Bot Settings**
   - Go to the "Bot" section
   - Click "Add Bot"
   - Copy the bot token (keep this secret!)
   - Enable "Message Content Intent" under Privileged Gateway Intents

3. **Generate Invite Link**
   - Go to OAuth2 > URL Generator
   - Select "bot" and "applications.commands" scopes
   - Select required permissions (see below)
   - Use the generated URL to invite your bot

### Required Discord Permissions {#permissions}

Your bot needs these permissions in Discord servers:

| Permission | Purpose |
|------------|---------|
| **View Channels** | Read channel messages and structure |
| **Send Messages** | Send command responses and now playing messages |
| **Use Slash Commands** | Enable slash command functionality |
| **Connect** | Join voice channels for music playback |
| **Speak** | Play audio in voice channels |
| **Manage Messages** | Delete bot messages with cleanup commands |
| **Manage Channels** | Create playlist channels (admin feature) |
| **Embed Links** | Send rich embeds with music info |
| **Read Message History** | Access playlist channel history |

**Minimum Permission Integer**: `3148800`
**Recommended Permission Integer**: `8795715584`

### Invite URL Template
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=8795715584&scope=bot%20applications.commands
```

## 🚀 First Run & Setup

### Initial Startup Process

1. **Start the Bot**
   ```bash
   python -m src.bot
   ```

2. **Verify Startup**
   - Check console output for "Bot is online!" message
   - Look for any error messages
   - Verify bot shows as online in Discord
   - I have found that I will show ([CRITICAL] src.monitoring.health: CRITICAL: 1 systems unhealthy) message a lot due to discord latency, you shouldn't need to worry about this.

3. **Test Basic Commands**
   ```bash
   # In Discord, try these commands:
   /help           # Should show all available commands
   /ping           # Should show bot latency
   /info           # Should display bot information
   ```

4. **Setup Playlist System (Optional)**
   ```bash
   # In Discord (as server admin):
   /setupplaylists     # Creates playlist category
   /createplaylist PlaylistName  # Creates first playlist
   ```

### Dashboard Access

1. **Open Web Dashboard**
   - Navigate to `http://localhost:8080`
   - You should see the Bassline-Bot dashboard

2. **Dashboard Features**
   - Real-time bot statistics
   - Server connection status
   - Performance metrics
   - Health monitoring

### First Music Test

1. **Join a Voice Channel** in Discord
2. **Use Play Command**:
   ```
   /play Never Gonna Give You Up
   ```
3. **Verify Playback**:
   - Bot should join your voice channel
   - Music should start playing
   - Dashboard should show active connection

## 📊 Monitoring & Maintenance

### Log Management

**Log Locations:**
- Main log: `logs/basslinebot.log`
- Error log: `logs/error.log`
- Access log: `logs/access.log`

**Log Monitoring:**
```bash
# View real-time logs
tail -f logs/basslinebot.log

# Search for errors
grep -i error logs/basslinebot.log

# Check log size
du -h logs/

# Rotate logs (if needed)
python scripts/rotate_logs.py
```

### Database Maintenance

**Regular Maintenance Tasks:**
```bash
# Backup database
python scripts/backup_db.py

# Optimize database
python scripts/optimize_db.py

# Clean old usage data (90+ days)
python scripts/cleanup_old_data.py --days 90

# Check database integrity
python scripts/check_db_integrity.py
```

### System Monitoring

**Health Check Endpoints:**
- `http://localhost:8080/health` - Basic health status
- `http://localhost:8080/api/stats` - Detailed statistics
- `http://localhost:8080/api/system` - System resource usage

**Prometheus Metrics:**
- `http://localhost:9090/metrics` - Prometheus format metrics

### Update Process

**Updating the Bot:**
```bash
# 1. Stop the bot
pkill -f "python -m src.bot"

# 2. Backup current installation
cp -r bassline-bot bassline-bot.backup

# 3. Pull latest changes
cd bassline-bot
git pull origin main

# 4. Update dependencies
pip install -r requirements.txt --upgrade

# 5. Run database migrations
python scripts/migrate.py

# 6. Restart bot
python -m src.bot
```

## 🐳 Docker Advanced Configuration

### Custom Docker Setup

**Create custom docker-compose.override.yml:**
```yaml
version: '3.8'
services:
  bot:
    environment:
      - LOG_LEVEL=DEBUG
      - VERBOSE_LOGGING=true
    volumes:
      - ./custom-config:/app/config:ro
    ports:
      - "8081:8080"  # Custom port mapping
```

### Multi-Container Production Setup

**docker-compose.prod.yml:**
```yaml
version: '3.8'
services:
  bot:
    build: .
    restart: unless-stopped
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://bassline:${DB_PASSWORD}@db:5432/basslinebot
      - REDIS_URL=redis://redis:6379
    volumes:
      - bot_data:/app/data
      - bot_logs:/app/logs

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_DB=basslinebot
      - POSTGRES_USER=bassline
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - bot

volumes:
  bot_data:
  bot_logs:
  postgres_data:
  redis_data:
```

### Docker Monitoring

**Monitor Docker containers:**
```bash
# View container status
docker-compose ps

# View logs
docker-compose logs -f bot

# Monitor resource usage
docker stats

# Execute commands in container
docker-compose exec bot python scripts/migrate.py
```

## 🔧 Advanced Configuration

### Custom Commands

**Add custom commands in src/commands/custom_commands.py:**
```python
from discord.ext import commands
from discord import app_commands

class CustomCommands(commands.Cog):
    @app_commands.command(name="mycommand", description="My custom command")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello from custom command!")
```

### Environment-Specific Configurations

**Development (.env.dev):**
```env
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
DASHBOARD_ENABLED=true
METRICS_ENABLED=false
DOWNLOAD_ENABLED=false
```

**Production (.env.prod):**
```env
LOG_LEVEL=WARNING
VERBOSE_LOGGING=false
DASHBOARD_ENABLED=true
METRICS_ENABLED=true
DOWNLOAD_ENABLED=true
DATABASE_URL=postgresql://...
```

**Testing (.env.test):**
```env
DATABASE_URL=sqlite:///./test.db
LOG_LEVEL=ERROR
DASHBOARD_ENABLED=false
```

## 🆘 Getting Help

### Support Channels

1. **Documentation**: Check all files in the `docs/` directory
2. **GitHub Issues**: [Create an issue](https://github.com/Cthede11/bassline-bot/issues) for bugs
3. **GitHub Discussions**: [Ask questions](https://github.com/Cthede11/bassline-bot/discussions)
4. **Discord Server**: Join our support community

### Before Asking for Help

**Include this information in your support request:**

1. **System Information:**
   ```bash
   # Run this command and include output
   python -c "
   import sys, platform, discord
   print(f'Python: {sys.version}')
   print(f'OS: {platform.system()} {platform.release()}')
   print(f'Discord.py: {discord.__version__}')
   "
   ```

2. **Bot Configuration** (remove sensitive data):
   - Your `.env` file contents (without tokens, nobody needs to see that!)
   - Relevant log entries
   - Error messages (full traceback)

3. **Steps to Reproduce**:
   - What you were trying to do
   - What you expected to happen  
   - What actually happened

### Common Solutions

**"Command not working"**
- Check bot has required permissions
- Verify bot is in voice channel (for music commands)
- Check console logs for errors

**"Bot offline"**
- Verify Discord token is correct
- Check internet connection
- Review error logs

**"Database errors"**
- Run `python scripts/migrate.py`
- Check database file permissions
- Verify database URL format

**"Performance issues"**
- Monitor system resources
- Check log file sizes
- Consider upgrading hardware

---

## 📚 Next Steps

After successful installation:

1. **[Configuration Guide](configuration.md)** - Detailed configuration options
2. **[Deployment Guide](deployment.md)** - Production deployment strategies  
3. **[API Documentation](api.md)** - Integration and automation
4. **[Contributing Guide](../CONTRIBUTING.md)** - Help improve the bot

---

*Installation complete! Your Bassline-Bot should now be running and ready to play music in your Discord server. Enjoy! 🎵*🔧 Prerequisites

### System Requirements
- **Python 3.8+** (Python 3.11 recommended for best performance)
- **FFmpeg** (for audio processing - essential!)
- **Git** (for cloning the repository)
- **4GB RAM minimum** (8GB recommended for production)
- **2GB disk space** (more recommended for downloads and logs)

### Discord Prerequisites
1. **Discord Bot Application** - Create at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Bot Token** - Generate and copy the bot token
3. **Server Permissions** - Invite bot with required permissions (see [Permissions](#permissions) section)

## 🚀 Installation Methods

### Method 1: Automated Setup (Recommended for Beginners)

This method uses our setup script to handle most of the installation automatically.

#### Linux/macOS
```bash
# 1. Clone the repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# 2. Run the automated setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Configure your bot token
cp .env.example .env
nano .env  # Add your Discord token here

# 4. Start the bot
python -m src.bot
```

#### Windows
```cmd
REM 1. Clone the repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

REM 2. Run the setup script
scripts\setup.bat

REM 3. Configure your bot token
copy .env.example .env
notepad .env

REM 4. Start the bot
python -m src.bot
```

### Method 2: Docker Installation (Recommended for Production)

Docker provides the easiest way to deploy in production environments.

#### Quick Docker Setup
```bash
# 1. Clone repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# 2. Configure environment
cp .env.example .env
# Edit .env with your Discord token and settings

# 3. Start with Docker Compose
docker-compose up -d

# 4. View logs
docker-compose logs -f bot

# 5. Access dashboard
open http://localhost:8080
```

#### Docker Production Setup
```bash
# Use production docker-compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale bot instances if needed
docker-compose scale bot=3

# Update bot
docker-compose pull
docker-compose up -d --no-deps bot
```

### Method 3: Manual Installation (For Advanced Users)

This method gives you full control over the installation process.

#### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
                    python3-pip ffmpeg git curl wget \
                    build-essential libffi-dev libssl-dev

# Optional: Install PostgreSQL and Redis
sudo apt install -y postgresql postgresql-contrib redis-server
```

**CentOS/RHEL/Fedora:**
```bash
# Install EPEL repository (for CentOS/RHEL)
sudo yum install -y epel-release  # CentOS/RHEL
# OR for Fedora
sudo dnf install -y python3.11 python3-pip ffmpeg git

# Install development tools
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3-devel libffi-devel openssl-devel
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 ffmpeg git postgresql redis

# Update PATH to use correct Python version
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
1. **Python 3.11**: Download and install from [python.org](https://python.org)
2. **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH
3. **Git**: Download from [git-scm.com](https://git-scm.com)
4. **Visual Studio Build Tools**: Install for Python package compilation

#### Step 2: Clone and Setup Python Environment
```bash
# 1. Clone the repository
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# 2. Create virtual environment
python3.11 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate.bat     # Windows

# 4. Upgrade pip
pip install --upgrade pip setuptools wheel

# 5. Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Configuration
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit configuration file
nano .env  # Linux/macOS
# notepad .env  # Windows
```

**Minimum required configuration:**
```env
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=sqlite:///./data/basslinebot.db
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8080
```

#### Step 4: Database Setup
```bash
# Create necessary directories
mkdir -p logs data downloads static

# Initialize database
python scripts/migrate.py

# Verify database creation
ls -la data/basslinebot.db
```

#### Step 5: Test Installation
```bash
# Test bot startup (should show no errors)
python -m src.bot --test

# If successful, start normally
python -m src.bot
```

## ✅ Verification & Testing

### Basic Functionality Tests

1. **Bot Status**: Verify bot appears online in Discord
2. **Slash Commands**: Test `/help` command
3. **Voice Connection**: Try joining a voice channel with `/play`
4. **Web Dashboard**: Visit `http://localhost:8080`
5. **Database**: Check that bot responds to commands

### Health Checks
```bash
# Check bot health via API
curl http://localhost:8080/health

# View logs for errors
tail -f logs/basslinebot.log

# Check system resources
curl http://localhost:8080/api/system
```

## 🔧 Configuration Details

### Environment Variables Explained

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | *Required* | Your Discord bot token |
| `DATABASE_URL` | SQLite | Database connection string |
| `DASHBOARD_PORT` | 8080 | Web dashboard port |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `MAX_QUEUE_SIZE` | 100 | Maximum songs in queue |
| `DOWNLOAD_ENABLED` | true | Enable audio caching |

### Database Configuration Options

**SQLite (Default - Single Server):**
```env
DATABASE_URL=sqlite:///./data/basslinebot.db
```

**PostgreSQL (Recommended for Production):**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/basslinebot
```

**MySQL (Alternative):**
```env
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/basslinebot
```

### Optional Services Setup

**PostgreSQL Setup:**
```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE basslinebot;
CREATE USER bassline WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE basslinebot TO bassline;
\q

# Update .env
DATABASE_URL=postgresql://bassline:your_password@localhost:5432/basslinebot
```

**Redis Setup (for caching):**
```bash
# Start Redis service
sudo systemctl start redis-server

# Update .env
REDIS_URL=redis://localhost:6379/0
```

## 🚨 Troubleshooting

### Common Installation Issues

#### FFmpeg Not Found
**Error**: `ffmpeg not found in PATH`

**Solutions:**
```bash
# Check if FFmpeg is installed
ffmpeg -version

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download from ffmpeg.org and add to PATH
```

#### Python Version Issues
**Error**: `Python 3.8+ required`

**Solutions:**
```bash
# Check Python version
python3 --version

# Install correct version
sudo apt install python3.11  # Ubuntu
brew install python@3.11     # macOS

# Use specific Python version
python3.11 -m venv venv
```

#### Permission Errors
**Error**: `Permission denied when creating files`

**Solutions:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh

# Create directories manually
mkdir -p logs data downloads static
```

#### Database Connection Issues
**Error**: `Database connection failed`

**Solutions:**
```bash
# For SQLite - check directory exists
mkdir -p data
ls -la data/

# For PostgreSQL - test connection
psql -h localhost -U bassline -d basslinebot -c "SELECT 1;"

# Reset database if corrupted
rm data/basslinebot.db  # SQLite only
python scripts/migrate.py
```

#### Port Already in Use
**Error**: `Port 8080 already in use`

**Solutions:**
```bash
# Find what's using the port
sudo netstat -tulpn | grep :8080
# OR
sudo lsof -i :8080

# Kill the process or change port in .env
DASHBOARD_PORT=8080
```

### Performance Issues

#### High Memory Usage
```bash
# Monitor memory usage
htop
# OR
ps aux | grep python

# Reduce memory usage in .env
MAX_QUEUE_SIZE=50
DOWNLOAD_ENABLED=false
LOG_LEVEL=WARNING
```

#### Slow Response Times
```bash
# Check system resources
curl http://localhost:8080/api/system

# Optimize database
python scripts/optimize_db.py

# Enable Redis caching
REDIS_URL=redis://localhost:6379
```

## 🔐 Security Configuration

### Production Security Checklist

- [ ] Change `SECRET_KEY` to a strong random string
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS with reverse proxy (nginx/Apache)
- [ ] Restrict `CORS_ORIGINS` to your domain
- [ ] Use strong database passwords
- [ ] Enable monitoring and logging
- [ ] Keep dependencies updated
- [ ] Use non-root user for bot process

### Recommended Production Settings
```env
# Security
SECRET_KEY=your_very_long_random_secret_key_here
CORS_ORIGINS=https://yourdomain.com

# Performance
DATABASE_URL=postgresql://bassline:strong_password@localhost:5432/basslinebot
REDIS_URL=redis://localhost:6379
LOG_LEVEL=WARNING
METRICS_ENABLED=true

# Reliability
HEALTH_CHECK_ENABLED=true
PROMETHEUS_PORT=9090
```

##