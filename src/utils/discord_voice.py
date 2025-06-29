import time
import discord
import yt_dlp
import asyncio
import functools
import os
import traceback
import logging
logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s [%(levelname)s] %(message)s') # For detailed error logging
from src.utils.music import music_manager

VERBOSE_LOGGING = True

# ANSI color codes
class LogColors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m" 
    RED = "\033[91m"
    CYAN = "\033[96m" 

def log(tag, message, color=LogColors.RESET, always_print=False):
    if VERBOSE_LOGGING or always_print:
        print(f"{color}[{tag}]{LogColors.RESET} {message}")

async def join_voice_channel(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user
    guild_id = guild.id

    log("DEBUG_JOIN_TRACE", f"User requested join: {user} in {guild.name} ({guild_id})", LogColors.BLUE)

    user_channel = user.voice.channel if user.voice else None
    if not user_channel:
        await interaction.response.send_message("❌ You must be in a voice channel to use this command.", ephemeral=True)
        return None

    try:
        # Send initial response so followup.send works later
        await interaction.response.defer(ephemeral=True, thinking=False)
    except discord.InteractionResponded:
        pass  # Already responded elsewhere

    # Refresh voice client reference
    bot_voice = guild.voice_client
    # log("VOICE_DEBUG", f"[INIT] user_channel={user_channel}, bot_voice={bot_voice}, connected={bot_voice.is_connected() if bot_voice else 'None'}", LogColors.BLUE)

    try:
        if not bot_voice or not bot_voice.is_connected():
            # log("VOICE_JOIN", f"Attempting to join channel: {user_channel.name}", LogColors.CYAN)

            vc = await asyncio.wait_for(user_channel.connect(), timeout=15.0)
            await asyncio.sleep(1.5)  # Let Discord finalize connection

            if not vc or not vc.is_connected():
                raise Exception("Voice client failed to connect properly.")

            music_manager.voice_clients[guild_id] = vc
            log("VOICE_JOIN_SUCCESS", f"✅ Connected to {vc.channel.name} successfully.", LogColors.GREEN)
            # log("VOICE_DEBUG", f"[POST-CONNECT] vc connected={vc.is_connected()}, channel={vc.channel}", LogColors.BLUE)
            return vc

        elif bot_voice.channel != user_channel:
            # log("VOICE_MOVE", f"Moving from {bot_voice.channel.name} to {user_channel.name}", LogColors.CYAN)

            await asyncio.wait_for(bot_voice.move_to(user_channel), timeout=15.0)
            await asyncio.sleep(1.0)

            music_manager.voice_clients[guild_id] = bot_voice
            log("VOICE_MOVE_SUCCESS", f"✅ Moved to {user_channel.name}", LogColors.GREEN)
            return bot_voice

        else:
            # Already in correct VC
            log("VOICE_JOIN_SKIP", f"Already connected to {user_channel.name}.", LogColors.YELLOW)
            return bot_voice

    except asyncio.TimeoutError:
        log("ERROR_JOIN_VC", f"⏳ Timeout connecting/moving to VC: {user_channel.name}", LogColors.RED)
        try:
            await interaction.followup.send(f"❌ Timed out trying to connect to `{user_channel.name}`.", ephemeral=True)
        except:
            pass
        return None

    except discord.ClientException as e:
        log("ERROR_JOIN_VC", f"ClientException during voice join: {e}", LogColors.RED)
        try:
            await interaction.followup.send(f"❌ Error joining voice: {e}", ephemeral=True)
        except:
            pass
        return None

    except Exception as e:
        log("ERROR_JOIN_VC", f"Unhandled Exception: {e}", LogColors.RED)
        try:
            await interaction.followup.send("❌ An unexpected error occurred while joining VC.", ephemeral=True)
        except:
            pass
        return None



class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

async def play_song(voice_client, search_query, return_source=False, bass_boost=False, download_first=True):
    start_time_op = time.time()
    log_prefix = f"[PLAY_SONG Query: '{search_query[:50]}...'] "

    if download_first:
        os.makedirs("downloads", exist_ok=True)

    cookie_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    if not os.path.exists(cookie_file_path):
        try:
            with open(cookie_file_path, 'w') as cf:
                cf.write("# Netscape HTTP Cookie File\n# Dummy file.\n")
        except IOError as e:
            log(log_prefix + "COOKIE_CREATE_FAIL", f"Failed to create dummy cookie file: {e}", LogColors.YELLOW)
            cookie_file_path = None

    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'cookiefile': cookie_file_path if cookie_file_path and os.path.exists(cookie_file_path) else None,
        'restrictfilenames': True,
        'ignoreerrors': False,
        'logger': MyLogger(),
    }
    if download_first:
        ydl_opts['outtmpl'] = os.path.join('downloads', '%(title)s.%(ext)s')

    loop = asyncio.get_event_loop()
    info = None
    selected_entry = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            extract_task = loop.run_in_executor(None, functools.partial(ydl.extract_info, search_query, download=download_first))
            info = await asyncio.wait_for(extract_task, timeout=60.0)
        except asyncio.TimeoutError:
            log(log_prefix + "YTDL_TIMEOUT", "yt-dlp info extraction timed out.", LogColors.RED)
            raise Exception(f"🚫 Timed out fetching info for '{search_query}'.")
        except Exception as e:
            log(log_prefix + "YTDL_EXTRACT_ERROR", f"yt-dlp extraction failed: {type(e).__name__}: {e}", LogColors.RED)
            logging.exception("Exception occurred")  # Logged to error.log
            if 'DRM' in str(e).upper():
                raise Exception("🚫 DRM-protected track.")
            raise Exception(f"❌ yt-dlp error: {str(e)[:200]}")

        if not info:
            log(log_prefix + "YTDL_NO_INFO", "yt-dlp returned no info.", LogColors.RED)
            raise Exception(f"🔍 No info from yt_dlp for '{search_query}'.")

        selected_entry = info['entries'][0] if 'entries' in info and info['entries'] else info
        if not selected_entry:
            log(log_prefix + "YTDL_NO_VALID_ENTRY", "No valid entry in yt_dlp info.", LogColors.RED)
            raise Exception(f"🔍 No valid entry in yt_dlp info for '{search_query}'.")

    title = selected_entry.get("title", "Unknown Title")
    duration = selected_entry.get("duration")
    thumbnail_url = selected_entry.get("thumbnail")
    webpage_url = selected_entry.get("webpage_url")
    uploader = selected_entry.get("uploader", "Unknown Uploader")
    stream_url_final = None

    if download_first:
        actual_filepath = (
            selected_entry.get('_download_filename') or
            selected_entry.get('requested_downloads', [{}])[0].get('filepath') or
            selected_entry.get('filepath')
        )
        if actual_filepath and os.path.exists(actual_filepath):
            try:
                file_size = os.path.getsize(actual_filepath)
                if file_size > 1024:
                    stream_url_final = actual_filepath
                else:
                    log(log_prefix + "DOWNLOAD_EMPTY_FILE", f"Downloaded file '{actual_filepath}' is too small (Size: {file_size} bytes). Fallback to streaming.", LogColors.YELLOW)
                    download_first = False
            except OSError as e_size:
                log(log_prefix + "DOWNLOAD_SIZE_ERROR", f"Error getting size for '{actual_filepath}': {e_size}. Fallback to streaming.", LogColors.YELLOW)
                download_first = False
        else:
            log(log_prefix + "DOWNLOAD_FAIL_NO_FILE", f"File not found at '{actual_filepath}'. Fallback to streaming.", LogColors.YELLOW)
            download_first = False

    if not download_first:
        direct_url = selected_entry.get('url')
        audio_url_from_formats = None
        if 'formats' in selected_entry:
            format_preference = [
                lambda f: 'opus' in f.get('acodec', '').lower() and f.get('ext') == 'webm',
                lambda f: 'opus' in f.get('acodec', '').lower(),
                lambda f: f.get('ext') == 'webm' and f.get('acodec') != 'none',
                lambda f: f.get('acodec') != 'none' and f.get('vcodec') == 'none',
                lambda f: f.get('protocol') in ['http', 'https']
            ]
            for pref_check in format_preference:
                for f_format in selected_entry['formats']:
                    if f_format.get('url') and pref_check(f_format):
                        audio_url_from_formats = f_format['url']
                        break
                if audio_url_from_formats:
                    break

        stream_url_final = audio_url_from_formats or direct_url
        if not stream_url_final:
            log(log_prefix + "STREAM_URL_FAIL", f"No streamable URL found for '{title}'.", LogColors.RED)
            raise Exception(f"🚫 No streamable URL found for '{title}'.")

    ffmpeg_options_dict = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' if not download_first else '',
        'options': '-vn',
    }

    if bass_boost:
        high_pass_filter = "highpass=f=35"
        low_end_boost_filter = "bass=g=4:f=70:w=0.4"
        definition_boost_filter = "equalizer=f=125:t=q:w=1:g=2"
        complex_filter_string = f"{high_pass_filter},{low_end_boost_filter},{definition_boost_filter}"
        ffmpeg_options_dict['options'] += f" -af \"{complex_filter_string}\""
        log(log_prefix + "FFMPEG_EFFECT", f"Applied 3-band EQ bass boost: {complex_filter_string}", LogColors.CYAN)

    log("INFO", f"Now playing: '{title}' | Duration: {duration}s | Download first: {download_first}", LogColors.YELLOW)
    # log("PLAY_DEBUG", f"Selected Stream URL: {stream_url_final}", LogColors.YELLOW)
    # log("PLAY_DEBUG", f"Formats available: {len(selected_entry.get('formats', []))}", LogColors.BLUE)

    try:
        source = discord.FFmpegPCMAudio(stream_url_final, **ffmpeg_options_dict)
    except Exception as e:
        log(log_prefix + "FFMPEG_ERROR", f"Error creating FFmpegPCMAudio. Path/URL: '{stream_url_final}'. Error: {e}", LogColors.RED)
        logging.exception("Exception occurred")  # Logged to error.log
        raise Exception(f"🚫 Failed to create FFmpeg audio source for '{title}'. Is FFmpeg installed and in PATH?")

    song_data_to_return = {
        "source": source,
        "title": title,
        "duration": duration if duration is not None else 0,
        "thumbnail": thumbnail_url,
        "webpage_url": webpage_url,
        "uploader": uploader,
        "query": search_query
    }

    if return_source:
        return song_data_to_return
    else:
        if voice_client and voice_client.is_connected():
            voice_client.play(source)
        return None

async def search_youtube(search_query: str, num_results: int = 5):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'default_search': f'ytsearch{num_results}',
        'noplaylist': True,
        'forcejson': True,
        'restrictfilenames': True,
        'ignoreerrors': True,
        'logger': MyLogger(),
        'no_warnings': True
    }
    loop = asyncio.get_event_loop()
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_extract_task = loop.run_in_executor(None, functools.partial(ydl.extract_info, search_query, download=False))
            info = await asyncio.wait_for(search_extract_task, timeout=20.0)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry and entry.get("title") and (entry.get("webpage_url") or entry.get("url")):
                        results.append({
                            "title": entry.get("title", "Unknown Title"),
                            "duration": entry.get("duration"),
                            "duration_str": f"{int(entry['duration'] // 60):02d}:{int(entry['duration'] % 60):02d}" if entry.get("duration") is not None else "N/A",
                            "url": entry.get("webpage_url", "#"),
                            "thumbnail": entry.get("thumbnail"),
                            "uploader": entry.get("uploader", "Unknown Uploader"),
                            "query_for_play": entry.get("webpage_url") or entry.get("original_url") or entry.get("title")
                        })
                        if len(results) >= num_results:
                            break
            elif info and info.get("title") and (info.get("webpage_url") or info.get("url")):
                results.append({
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration"),
                    "duration_str": f"{int(info['duration'] // 60):02d}:{int(info['duration'] % 60):02d}" if info.get("duration") is not None else "N/A",
                    "url": info.get("webpage_url", "#"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader", "Unknown Uploader"),
                    "query_for_play": info.get("webpage_url") or info.get("original_url") or info.get("title")
                })
    except asyncio.TimeoutError:
        log("SEARCH_YOUTUBE_ERROR", f"Timeout searching YouTube for '{search_query}'", LogColors.RED)
    except Exception as e:
        log("SEARCH_YOUTUBE_ERROR", f"Error during YouTube search for '{search_query}': {e}", LogColors.RED)
        logging.exception("Exception occurred")  # Logged to error.log

    return results
