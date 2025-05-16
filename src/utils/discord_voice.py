import time
import discord
import yt_dlp
import asyncio
import functools
import glob
import os

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

async def join_voice_channel(interaction):
    user_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not user_channel:
        await interaction.response.send_message("❌ You must be in a voice channel to use this command.")
        return None

    bot_voice = interaction.guild.voice_client
    if not bot_voice:
        log("VOICE", f"Bot joining channel: {user_channel.name}", LogColors.GREEN)
        return await user_channel.connect()

    if bot_voice.channel != user_channel:
        log("VOICE", f"Bot moving from {bot_voice.channel.name} to {user_channel.name}", LogColors.YELLOW)
        await bot_voice.move_to(user_channel)

    return bot_voice

async def play_song(voice_client, search_query, return_source=False, bass_boost=False, download_first=False):
    import os
    import uuid

    start = time.time()

    # Ensure downloads folder exists
    if download_first:
        os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'cookiefile': 'src/utils/cookies.txt',
        'restrictfilenames': True,
        'forcejson': True,
    }

    if download_first:
        ydl_opts['outtmpl'] = 'downloads/%(title)s.%(ext)s'

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await loop.run_in_executor(
                None,
                functools.partial(
                    ydl.extract_info,
                    f"{search_query} full song",
                    not download_first  # download=False if streaming, True if downloading
                )
            )
        except Exception as e:
            if 'DRM' in str(e).upper():
                raise Exception("🚫 The selected track is DRM-protected and cannot be played.")
            raise Exception(f"❌ yt_dlp error: {str(e)}")

        entries = info.get('entries') or [info]
        selected = next((e for e in entries if e.get("duration", 0) >= 20), None)
        if not selected:
            raise Exception(f"No suitable result for: {search_query}")

        if download_first:
            stream_url = ydl.prepare_filename(selected)
        else:
            stream_url = selected['url']

        title = selected.get("title", "Unknown")
        duration = selected.get("duration", 0)

        log("PLAY", f"Title: {title}", LogColors.BLUE)
        log("PLAY", f"Duration: {duration}s", LogColors.BLUE)
        log("PLAY", f"{'File path' if download_first else 'Stream URL'}: {stream_url}", LogColors.BLUE)

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' if not download_first else '',
            'options': '',
        }

        if bass_boost:
            eq_filter = 'bass=g=6:f=80:w=0.8'
            ffmpeg_options['options'] = f"-vn -af {eq_filter}"
        else:
            ffmpeg_options['options'] = '-vn'

        log("FFMPEG", f"Using filter: {ffmpeg_options['options']}", LogColors.YELLOW)

        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)

        elapsed = time.time() - start
        log("TIME", f"Operation took {elapsed:.2f} seconds", LogColors.GREEN)

        return source if return_source else voice_client.play(source)
