
import time
import discord
import yt_dlp

# ANSI color codes
class LogColors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    CYAN = "\033[96m"

def log(tag, message, color=LogColors.RESET):
    print(f"{color}[{tag}]{LogColors.RESET} {message}")

async def join_voice_channel(ctx):
    user_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not user_channel:
        await ctx.send("❌ You must be in a voice channel to use this command.")
        return None

    bot_voice = ctx.guild.voice_client
    if not bot_voice:
        log("VOICE", f"Bot joining channel: {user_channel.name}", LogColors.GREEN)
        return await user_channel.connect()

    if bot_voice.channel != user_channel:
        log("VOICE", f"Bot moving from {bot_voice.channel.name} to {user_channel.name}", LogColors.YELLOW)
        await bot_voice.move_to(user_channel)

    return bot_voice

async def play_song(voice_client, search_query, return_source=False):
    start = time.time()

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch10',
        'noplaylist': True,
        'extract_flat': False,
        'cookiefile': 'src/utils/cookies.txt',
        'restrictfilenames': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"{search_query} full song", download=False)
        except yt_dlp.utils.DownloadError as e:
            log("ERROR", f"yt_dlp failed: {e}", LogColors.RED)
            raise Exception(f"❌ yt_dlp error: {str(e)}")

        entries = info.get('entries') or [info]
        playlist_detected = 'entries' in info
        if playlist_detected:
            log("QUEUE", f"Playlist detected: {len(entries)} tracks", LogColors.CYAN)

        selected = next((e for e in entries if e.get("duration", 0) >= 90), None)
        if not selected:
            raise Exception(f"No suitable result for: {search_query}")

        stream_url = selected['url']
        title = selected.get("title", "Unknown")
        duration = selected.get("duration", 0)

        log("PLAY", f"Title: {title}", LogColors.BLUE)
        log("PLAY", f"Duration: {duration}s", LogColors.BLUE)
        log("PLAY", f"Stream URL: {stream_url}", LogColors.BLUE)

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)

        elapsed = time.time() - start
        log("TIME", f"Operation took {elapsed:.2f} seconds", LogColors.GREEN)

        return source if return_source else voice_client.play(source)
