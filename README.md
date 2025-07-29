# BasslineBot

A Discord music bot that plays high-quality audio and manages playlists for your server. Simple to set up, easy to use, and packed with features your community will love.

[![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2+-blue.svg)](https://discordpy.readthedocs.io/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](docker-compose.yml)

BasslineBot brings music to your Discord server with features like playlist management, queue controls, and a web dashboard to monitor everything. It's built with Python and designed to be reliable and easy to use.

## Features

### Music Commands
- High-quality audio streaming from YouTube
- Queue management with shuffle and loop modes
- Personal volume and bass boost controls
- Smart auto-disconnect when not in use
- Download caching for faster repeated songs

### Playlist System
- Create playlists using Discord text channels
- Add songs by posting YouTube links or song names in playlist channels
- Play entire playlists with one command
- Share playlists with your server members

### Admin Tools
- Set DJ roles to control who can manage music
- Server settings for queue limits and timeouts
- Usage statistics to see what's popular
- Message cleanup commands

### Web Dashboard
- Real-time bot statistics at http://localhost:8080
- Monitor server connections and performance
- View what's playing across all servers
- Health checks and system information

## Quick Start

You'll need Python 3.8 or higher and FFmpeg installed on your system. You'll also need a Discord bot token from the Discord Developer Portal.

### 1. Download and Setup
```bash
git clone https://github.com/Cthede11/bassline-bot.git
cd bassline-bot

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Or install manually
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 2. Configure the Bot
```bash
cp .env.example .env
# Edit .env and add your Discord bot token
```

### 3. Start the Bot
```bash
python scripts/migrate.py  # Set up the database
python -m src.bot          # Start the bot
```

### 4. Check the Dashboard
Open http://localhost:8080 in your browser to see the web dashboard.

## Docker Setup

If you prefer using Docker:

```bash
cp .env.example .env
# Edit .env with your bot token
docker-compose up -d
```

## 🎯 Commands

### 🎵 Music Commands
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
| `/storagestats` | View download cache statistics |
| `/cleandownloads` | Clean up old cached files |

### 📝 Playlist Commands
| Command | Description |
|---------|-------------|
| `/setupplaylists` | Create playlist category (Admin) |
| `/createplaylist <name>` | Create a new playlist channel (Admin) |
| `/listplaylists` | Show all server playlists |
| `/myplaylists` | View your personal playlists |
| `/addtoplaylist <playlist> [song]` | Add song to playlist |
| `/playplaylist <name>` | Play all songs from a playlist |
| `/playlistinfo <name>` | Show detailed playlist information |
| `/deleteplaylist <name>` | Delete your playlist |

### ⚙️ Admin Commands
| Command | Description |
|---------|-------------|
| `/setdjrole <role>` | Set DJ role (Admin) |
| `/cleardjrole` | Clear DJ role (Admin) |
| `/checkdjrole` | Check current DJ role status |
| `/stats` | Show comprehensive bot statistics (Admin) |
| `/settings` | View/update bot settings (Admin) |
| `/cleanup <count>` | Clean up bot messages (Admin) |

### 🔧 Utility Commands
| Command | Description |
|---------|-------------|
| `/help [command]` | Show all commands or specific command help |
| `/ping` | Check bot latency |
| `/info` | Display bot information and stats |
| `/search <query>` | Search for songs on YouTube |

## Configuration

The main settings are in your `.env` file:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token_here

# Basic settings
BOT_NAME=BasslineBot
MAX_QUEUE_SIZE=100
DEFAULT_VOLUME=0.5

# Database (SQLite by default)
DATABASE_URL=sqlite:///./data/basslinebot.db

# Web dashboard
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8080
```

For more configuration options, check out the [configuration guide](docs/configuration.md).

## Project Structure

```
bassline-bot/
├── src/
│   ├── commands/         # Discord slash commands
│   ├── core/            # Bot logic and managers
│   ├── database/        # Database models
│   ├── web/             # Web dashboard
│   └── bot.py           # Main bot file
├── config/              # Settings and configuration
├── scripts/             # Setup and utility scripts
├── docs/                # Documentation
└── requirements.txt     # Python dependencies
```

## Getting Help

- Check the [installation guide](docs/installation.md) for detailed setup instructions
- Look at [troubleshooting](docs/installation.md#troubleshooting) for common issues
- Create an [issue on GitHub](https://github.com/Cthede11/bassline-bot/issues) for bugs
- Join discussions for questions and ideas
- Feel free to reach out to me at: thedechristian11@gmail.com

## Common Issues

**FFmpeg not found**: Install FFmpeg and make sure it's in your system PATH
**Bot won't connect**: Check your Discord token in the .env file
**Music not playing**: Make sure the bot has voice permissions in your Discord server
**Dashboard not loading**: Check that port 8080 isn't blocked by your firewall

## Requirements

- Python 3.8 or higher
- FFmpeg for audio processing
- Discord bot token
- At least 512MB RAM (more recommended for busy servers)

## Discord Permissions

Your bot needs these permissions in Discord:
- Read Messages and Send Messages
- Connect and Speak in voice channels
- Use Slash Commands
- Manage Messages (for cleanup commands)

## License

This project uses the BSD 3-Clause License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Thanks to the developers of Discord.py, FFmpeg, FastAPI, and yt-dlp for making this bot possible.

---

Made by the BasslineBot community. Happy listening! 🎵