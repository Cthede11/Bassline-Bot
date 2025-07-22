# 🎵 Bassline-Bot

> **A professional, feature-rich Discord music bot with a beautiful web dashboard**

[![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2+-blue.svg)](https://discordpy.readthedocs.io/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](docker-compose.yml)

**Bassline-Bot** is a  Discord music bot that brings high-quality audio streaming, advanced queue management, and real-time monitoring to your Discord server. Built with modern Python and featuring a sleek web dashboard, it's designed for both casual use and more professional deployments.

## ✨ Features

### 🎶 **Core Music Features**
- **High-quality audio streaming** from YouTube with FFmpeg processing
- **Advanced queue management** with shuffle, loop modes, and position control
- **Bass boost and volume control** with per-user preferences
- **Multiple loop modes**: Off, Single Song, and Queue looping
- **Smart auto-disconnect** to save resources when inactive

### 📝 **Playlist System (Being Reworked)**
- **Custom Discord channel-based playlists** - Turn any text channel into a playlist!
- **Easy playlist creation** with `/setupplaylists` and `/createplaylist`
- **Collaborative playlist building** - Let your community add songs
- **Playlist management** with play counts and organization

### 👑 **Admin & Permissions (Being Reworked)**
- **DJ role system** - Set specific roles that can control music playback
- **Comprehensive server settings** - Customize queue limits, timeouts, and features
- **Usage statistics and analytics** - Track bot performance and popular commands
- **Flexible permission system** - Admins have full control, DJs control playback

### 🌐 **Web Dashboard**
- **Beautiful, responsive web interface** accessible at `http://localhost:8080`
- **Real-time statistics** showing active connections, songs played, and server metrics
- **Live data updates** with automatic refresh every 15 seconds
- **Performance monitoring** with success rates and response times
- **Quick access links** to health checks and API endpoints

### 🐳 **Production Ready**
- **Docker support** with docker-compose for easy deployment
- **Database integration** with SQLAlchemy (SQLite/PostgreSQL)
- **Comprehensive logging** with rotation and error tracking
- **Health monitoring** with Prometheus metrics on port 9090
- **Error handling and recovery** for stable 24/7 operation

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (3.11 recommended)
- **FFmpeg** installed and in your system PATH
- **Discord bot token** ([Create one here](https://discord.com/developers/applications))

### 1. Clone and Setup
```bash
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Discord bot token
# DISCORD_TOKEN=your_bot_token_here
```

### 3. Run the Bot
```bash
# Initialize database
python scripts/migrate.py

# Start the bot
python -m src.bot
```

### 4. Access the Dashboard
Open your browser and visit: **http://localhost:8080**

## 🐳 Docker Deployment

For production deployments, use Docker:

```bash
# Update .env with your bot token
cp .env.example .env

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f bot
```

## 🎯 Commands

### Music Commands
| Command | Description |
|---------|-------------|
| `/play <song>` | Play a song or add to queue |
| `/queue` | Show current queue and now playing |
| `/skip` | Skip current song (DJ/Admin) |
| `/pause` / `/resume` | Control playback (DJ/Admin) |
| `/stop` | Stop and clear queue (DJ/Admin) |
| `/loop <mode>` | Set loop mode: Off/Single/Queue (DJ/Admin) |
| `/shuffle` | Shuffle current queue (DJ/Admin) |
| `/clear` | Clear the queue (DJ/Admin) |
| `/nowplaying` | Show detailed current song info |
| `/volume <0.0-1.0>` | Set your personal volume |
| `/bassboost` | Toggle bass boost for yourself |

### Playlist Commands (Currently Unavailable)
| Command | Description |
|---------|-------------|
| `/setupplaylists` | Create playlist category (Admin) |
| `/createplaylist <name>` | Create a new playlist (Admin) |
| `/playlist <name>` | Play songs from a playlist |
| `/listplaylists` | Show all server playlists |

### Admin Commands (Currently Unavailable)
| Command | Description |
|---------|-------------|
| `/setdjrole <role>` | Set DJ role (Admin) |
| `/settings` | View/update bot settings (Admin) |
| `/stats` | Show comprehensive bot statistics (Admin) |
| `/cleanup` | Clean up bot messages (Admin) |

### Utility Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all commands and help |
| `/ping` | Check bot latency |
| `/info` | Display bot information and stats |

## 🔧 Configuration

### Environment Variables

Key settings in your `.env` file:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token_here

# Optional customization
BOT_PREFIX=!bl
BOT_NAME=Bassline-Bot
MAX_QUEUE_SIZE=100
DEFAULT_VOLUME=0.5
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8080
```

### Advanced Configuration

For production deployments, see:
- [`docs/configuration.md`](docs/configuration.md) - Complete configuration guide
- [`docs/deployment.md`](docs/deployment.md) - Production deployment options

## 📊 Monitoring (Being Updated)

### Web Dashboard
- **Main Dashboard**: `http://localhost:8080`
- **Health Check**: `http://localhost:8080/health`
- **API Stats**: `http://localhost:8080/api/stats`

### Prometheus Metrics
- **Metrics Endpoint**: `http://localhost:9090`
- Track command usage, performance, and system resources

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

Please ensure your code follows a similar style/is readable and includes appropriate tests.

## 📁 Project Structure

```
basslinebot-pro/
├── src/
│   ├── commands/         # Discord slash commands
│   ├── core/            # Core bot logic and managers
│   ├── database/        # Database models and migrations
│   ├── monitoring/      # Health checks and metrics
│   ├── utils/           # Utilities and helpers
│   ├── web/             # Web dashboard and API
│   └── bot.py           # Main bot entry point
├── config/              # Configuration and settings
├── scripts/             # Utility scripts
├── templates/           # Web dashboard templates
├── docs/                # Documentation
├── tests/               # Test suite
├── docker-compose.yml   # Docker configuration
├── requirements.txt     # Python dependencies
└── README.md           # You Are Here ↓
```

## 🆘 Support

### Getting Help
- **Documentation**: Check the [`docs/`](docs/) folder for detailed guides
- **Issues**: [Create an issue](https://github.com/Cthede11/bassline-bot/issues) for bugs or feature requests
- **Discussions**: Join our [GitHub Discussions](https://github.com/Cthede11/bassline-bot/discussions) for questions

### Troubleshooting
- **FFmpeg not found**: Install FFmpeg and add to your system PATH
- **Bot won't connect**: Check your Discord token in `.env`
- **Dashboard not loading**: Ensure port 8080 isn't blocked
- **Music not playing**: Verify FFmpeg installation and bot voice permissions

## 📋 Requirements

### System Requirements
- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.8 or higher (3.11 recommended)
- **Memory**: 512MB RAM minimum (2GB recommended for production)
- **Disk Space**: 1GB available space

### Discord Permissions
Your bot needs these permissions in Discord servers:
- **Read Messages** and **Send Messages**
- **Connect** and **Speak** in voice channels
- **Use Slash Commands**
- **Manage Messages** (for cleanup commands)

## 📜 License

This project is licensed under the **BSD 3-Clause License** - see the [LICENSE](LICENSE.txt) file for details.

### Additional Terms
- Must comply with Discord's Terms of Service
- Users responsible for music copyright compliance
- Commercial hosting requires permission
- Attribution required for public deployments

## 🙏 Acknowledgments

- **Discord.py** - The amazing Discord API wrapper
- **FFmpeg** - High-quality audio processing
- **FastAPI** - Modern web framework for the dashboard
- **yt-dlp** - YouTube audio extraction
- **All contributors** who helped make this project awesome!

## Feel Free To Reach Out To Me:
- **Github** - https://github.com/Cthede11
- **Email** - thedechristian11@gmail.com

---

<div align="center">

**🎵 Built with ❤️ for the Discord community**

[⭐ Star this repo](https://github.com/Cthede11/bassline-bot) • [🐛 Report Bug](https://github.com/Cthede11/bassline-bot/issues) • [💡 Request Feature](https://github.com/Cthede11/bassline-bot/issues)

</div>