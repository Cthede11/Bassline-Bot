# 🎵 BasslineBot

BasslineBot is a powerful, self-hosted Discord music bot that plays music from  YouTube searches. It supports preloading, queueing, and gapless playback, offering a smooth music experience in your server. This bot is still a work in progress, so if you have anything you think would be good to add, let me know! 

---


## ⚙️ Features

- 🎵 `/play [YouTube query or URL]` — Plays a song or adds it to the queue instantly.
- 📻 Youtube-based streaming powered by `yt-dlp`.
- ⚡ Preloads the next track for seamless transitions.
- 🎚️ **Playback Control:**
    - `/stop` — Stops the current song and clears the queue, disconnecting the bot.
    - `/skip` — Skips the current song or a specified number of songs in the queue.
    - `/pause` — Pauses the current song.
    - `/resume` — Resumes a paused song.
    - `/loop [off/single/queue]` — Sets the loop mode for the current song or the entire queue.
- 🎶 **Queue Management:**
    - `/queue` — Displays the current song queue.
    - `/shuffle` — Shuffles the songs in the queue.
    - `/clear` — Clears all songs from the queue.
- 🔊 **Audio Enhancements:**
    - `/bassboost` — Toggles bass boost on or off for your user session.
- 🗃️ **Custom Playlist System:**
    - Create and manage custom playlists directly within Discord text channels.
    - `/createplaylist [playlist name]` — Creates a new dedicated text channel for your playlist.
    - `/playplaylist [playlist name]` — Plays a custom playlist.
- 🔐 **DJ Role Control:** Commands like `/stop` and `/skip` can be restricted to users with a designated "DJ" role or server administrators.
- 💤 **Auto Disconnect:** The bot automatically disconnects from the voice channel after a period of inactivity.
- 🔊 **Now Playing Embed:** Rich embeds provide detailed information about the currently playing song.

---

## 📦 Setup Instructions

### 1. Install Dependencies

Install Python packages:

```bash
pip install -r requirements.txt
```

Make sure [FFmpeg](https://ffmpeg.org/download.html) is installed and added to your system PATH.

### 2. Create a `.env` file

Add the following environment variable:

```
DISCORD_TOKEN=your_discord_bot_token
```

### 3. Run the Bot

From the root of the project:

```bash
python -m src.bot
```
Or use the start-bot.bat file updated with your actual file path

---

## 💡 Available Commands

| Command           | Description                                                                                             | Parameters                                               |
| :---------------- | :------------------------------------------------------------------------------------------------------ | :------------------------------------------------------- |
| `/play`           | Plays a song or adds it to the queue instantly. Supports Youtube queries or direct URLs.                | `query_or_url`: Youtube query or URL.                    |
| `/stop`           | Stops the current song, clears the entire queue, and disconnects the bot from the voice channel.        | None                                                     |
| `/skip`           | Skips the current song or a specified number of songs in the queue.                                     | `count`: Defaults to 1.                                  |
| `/pause`          | Pauses the currently playing song.                                                                      | None                                                     |
| `/resume`         | Resumes a paused song.                                                                                  | None                                                     |
| `/loop`           | Sets the loop mode for playback.                                                                        | `mode`: `off`, `single` , or `queue`.                    |
| `/queue`          | Displays the current list of songs in the playback queue.                                               | None                                                     |
| `/shuffle`        | Shuffles the order of songs in the current queue.                                                       | None                                                     |
| `/clear`          | Clears all songs from the playback queue.                                                               | None                                                     |
| `/bassboost`      | Toggles the bass boost audio effect on or off for your user session.                                    | None                                                     |
| `/setupplaylists` | Creates a text channel category for storing custom playlists (Admin only)                               | None                                                     |
| `/createplaylist` | Creates a new dedicated text channel in your server for a custom playlist.                              | `name`: The name for your new playlist.                  |
| `/playplaylist`   | Starts playing a custom playlist from its beginning.                                                    | `playlist_name`: The name of the playlist to play.       |

---

## 📌 Notes

- This bot uses YouTube as the playback source for all songs
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

- Volume Control
- Lyrics fetch command (Toggle on/off?)
- Queue saved locally for continuity through restart

---

## 🙏 Credit

This bot was created by [Cthede11](https://github.com/Cthede11).

If you use or modify this bot, please include proper credit in your documentation or public deployment. A simple mention or link back is appreciated!

---
## 📜 License

MIT — Feel free to fork and build upon this project. But, I would love to hear about what you are up to or what ideas you have come up with!
