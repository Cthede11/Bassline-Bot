# 🎵 BasslineBot

BasslineBot is a powerful, self-hosted Discord music bot that plays music from Spotify playlists and YouTube search. It supports preloading, queueing, and gapless playback, offering a smooth music experience in your server. This bot is still a work in progress, so if you have anything you think would be good to add, let me know! 

---

## ⚙️ Features

- 🔗 `!play [Spotify playlist | YouTube query | song name | custom Discord playlist]` — plays instantly
- 📄 Spotify playlist importing (uses YouTube playback)
- 🎵 Custom Discord playlists with !createplaylist and !playplaylist
- 📻 YouTube search-based streaming (via `yt_dlp`)
- 🎚️ Queue system with `!queue`, `!skip`, `!shuffle`, `!clear`
- ⏯️ `!pause` and `!resume` playback
- 🚀 Preloads next track for nearly seamless transitions

---

## 📦 Setup Instructions

### 1. Install Dependencies

Install Python packages:

```bash
pip install -r requirements.txt
```

Make sure [FFmpeg](https://ffmpeg.org/download.html) is installed and added to your system PATH.

### 2. Create a `.env` file

Add the following environment variables:

```
DISCORD_TOKEN=your_discord_bot_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### 3. Run the Bot

From the root of the project:

```bash
python -m src.bot
```

---

## 💡 Available Commands

| Command                           | Description                                                          |
|-----------------------------------|----------------------------------------------------------------------|
| `!play [song]`                    | Plays a song or Spotify playlist                                     |
| `!queue`                          | Shows the current queue                                              |
| `!skip`                           | Skips the currently playing track                                    |
| `!pause`                          | Pauses playback                                                      |
| `!resume`                         | Resumes playback                                                     |
| `!shuffle`                        | Shuffles the remaining queue                                         |
| `!clear`                          | Clears the queue and stops playback                                  |
| `!setupplaylists`                 | Creates the playlist category to organize custom playlist channels   |
| `!createplaylists` [name]         | Creates a new text channel playlist with the given name              |
| `!playplaylists` [name/#channel]  | Plays songs from the named or mentioned custom playlist channel      |

---

## 📌 Notes

- This bot uses YouTube as the playback source even for Spotify playlists
- Preloading system improves continuity but still depends on YouTube response speed
- You may customize the command prefix and embed style in `bot.py`

---

## 🔐 Required Discord Bot Permissions
To ensure BasslineBot works correctly, please make sure the bot has the following permissions when added to your server:

### ✅ Essential Permissions
Connect – Join voice channels

Speak – Play music in voice channels

Read Messages – See text channel commands and custom playlist entries

Send Messages – Respond with playback messages and feedback

Embed Links – Format messages and show rich embeds (future support for thumbnails)

Use External Emojis (optional) – Enhanced emoji support for visual feedback

Manage Channels (optional but recommended) – Automatically create playlist channels via !createplaylist

View Channel – Access channels required for reading playlist data


## 🛠️ Coming Soon

- Fix to slight playback cut when preloading next song
- Volume Control
- Bass Boost
- Now Playing embed
- Lyrics fetch command (Toggle on/off?)
- Auto Disconnect
- DJ role only control
- Queue saved locally for continuity through restart
- Updated command system (Update to slash commands with auto-complete)

---

## 🙏 Credit

This bot was created by [Cthede11](https://github.com/Cthede11).

If you use or modify this bot, please include proper credit in your documentation or public deployment. A simple mention or link back is appreciated!

---
## 📜 License

MIT — Feel free to fork and build upon this project. But, I would love to hear about what you are up to or what ideas you have come up with!
