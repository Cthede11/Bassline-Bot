import time
import discord
import yt_dlp
import asyncio
import functools
import os
import traceback # For detailed error logging

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

async def join_voice_channel(interaction: discord.Interaction):
    user_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not user_channel:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ You must be in a voice channel to use this command.", ephemeral=True)
        else:
            await interaction.followup.send("❌ You must be in a voice channel to use this command.", ephemeral=True)
        return None

    bot_voice = interaction.guild.voice_client
    # new_voice_client = None # Not strictly needed here

    try:
        if not bot_voice:
            log("VOICE", f"Bot attempting to join channel: {user_channel.name}", LogColors.GREEN)
            new_voice_client = await asyncio.wait_for(user_channel.connect(), timeout=10.0)
            log("VOICE", f"Bot successfully joined channel: {new_voice_client.channel.name}", LogColors.GREEN)
            return new_voice_client

        if bot_voice.channel != user_channel:
            log("VOICE", f"Bot attempting to move from {bot_voice.channel.name} to {user_channel.name}", LogColors.YELLOW)
            await asyncio.wait_for(bot_voice.move_to(user_channel), timeout=10.0)
            log("VOICE", f"Bot successfully moved to channel: {user_channel.name}", LogColors.YELLOW)
        
        return interaction.guild.voice_client

    except asyncio.TimeoutError:
        log("ERROR", f"Timeout while trying to connect/move to voice channel: {user_channel.name}", LogColors.RED)
        if interaction.response.is_done(): # Check if already responded (e.g., deferred)
             await interaction.followup.send(f"❌ Timed out trying to connect to {user_channel.name}. Please check my permissions and try again.", ephemeral=True)
        else:
             await interaction.response.send_message(f"❌ Timed out trying to connect to {user_channel.name}.", ephemeral=True)
        return None
    except discord.errors.ClientException as e: # Handles cases like already connected, etc.
        log("ERROR", f"Discord ClientException while connecting/moving: {e}", LogColors.RED)
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ Error connecting to voice: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error connecting to voice: {e}", ephemeral=True)
        return None
    except Exception as e: # Catch-all for other unexpected errors
        log("ERROR", f"An unexpected error occurred in join_voice_channel: {e}", LogColors.RED)
        traceback.print_exc()
        if interaction.response.is_done():
            await interaction.followup.send("❌ An unexpected error occurred while trying to join the voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ An unexpected error occurred while trying to join the voice channel.", ephemeral=True)
        return None

async def play_song(voice_client, search_query, return_source=False, bass_boost=False, download_first=True):
    start_time_op = time.time()

    if download_first:
        os.makedirs("downloads", exist_ok=True)

    cookie_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

    if not os.path.exists(cookie_file_path):
        log("WARN", f"Cookie file not found at {cookie_file_path}. Some age-restricted songs might fail. Attempting to create an empty one.", LogColors.YELLOW)
        try:
            with open(cookie_file_path, 'w') as cf:
                cf.write("# Netscape HTTP Cookie File\n# This is a dummy file created by the bot.\n# For actual cookie usage, replace this with a valid cookies.txt from your browser.\n") 
            log("INFO", f"Empty cookie file created at {cookie_file_path}.", LogColors.CYAN)
        except IOError as e:
            log("ERROR", f"Failed to create empty cookie file at {cookie_file_path}: {e}. Proceeding without cookies.", LogColors.RED)
            cookie_file_path = None


    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch1', 
        'noplaylist': True,
        'cookiefile': cookie_file_path if cookie_file_path and os.path.exists(cookie_file_path) else None,
        'restrictfilenames': True,
        'forcejson': True,
        'ignoreerrors': False, # For play_song, we want errors for the specific item.
        # Add source_address for potential IP rotation or binding if needed, e.g. 'source_address': '0.0.0.0'
    }

    if download_first:
        ydl_opts['outtmpl'] = os.path.join('downloads', '%(title)s.%(ext)s')


    loop = asyncio.get_event_loop()
    info = None
    selected_entry = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            log("YTDL", f"Extracting song info for: '{search_query}'", LogColors.CYAN)
            # Add a timeout for the executor task for yt-dlp
            extract_task = loop.run_in_executor(
                None,
                functools.partial(ydl.extract_info, search_query, download=download_first)
            )
            info = await asyncio.wait_for(extract_task, timeout=45.0) # 45 seconds timeout for ytdl processing
            log("YTDL", f"Successfully extracted info for: '{search_query}'", LogColors.GREEN)

        except asyncio.TimeoutError:
            log("YTDL_ERROR", f"Timeout extracting info for '{search_query}' after 45 seconds.", LogColors.RED)
            raise Exception(f"🚫 Timed out trying to fetch info for '{search_query}'. Please try a different song or check the link.")
        except Exception as e: # Catches other errors from extract_info or ydl itself
            if 'DRM' in str(e).upper():
                raise Exception("🚫 The selected track is DRM-protected and cannot be played.")
            # Check for common yt-dlp specific operational errors
            if isinstance(e, yt_dlp.utils.DownloadError) or isinstance(e, yt_dlp.utils.ExtractorError):
                 log("YTDL_ERROR", f"yt-dlp Download/Extractor error for '{search_query}': {e}", LogColors.RED)
                 raise Exception(f"❌ yt-dlp could not process '{search_query}': {str(e)}")
            else: # General unexpected error during ytdl phase
                log("YTDL_ERROR", f"Unexpected yt_dlp related error for '{search_query}': {e}", LogColors.RED)
                traceback.print_exc()
                raise Exception(f"❌ Unexpected yt_dlp error processing '{search_query}': {str(e)}")


        if not info: # Should be caught by exceptions above, but as a safeguard
            raise Exception(f"🔍 No information returned by yt_dlp for '{search_query}'.")

        if 'entries' in info and info['entries']: # ytsearch might return a playlist-like structure
            selected_entry = info['entries'][0] 
            log("YTDL", f"Search returned multiple entries for a single query, taking first: {selected_entry.get('title')}", LogColors.YELLOW)
        else:
            selected_entry = info

        if not selected_entry: 
            raise Exception(f"🔍 No valid entry found for '{search_query}'.")
        
        if selected_entry.get("duration", 0) is None or selected_entry.get("duration", 0) < 1:
            log("YTDL_WARN", f"Video for '{search_query}' has no duration or is too short. Title: {selected_entry.get('title')}", LogColors.YELLOW)


    title = selected_entry.get("title", "Unknown Title")
    duration = selected_entry.get("duration") 
    thumbnail_url = selected_entry.get("thumbnail")
    webpage_url = selected_entry.get("webpage_url")
    uploader = selected_entry.get("uploader", "Unknown Uploader")
    stream_url_final = None

    if download_first:
        actual_filepath = None
        if selected_entry.get('_download_filename'):
             actual_filepath = selected_entry['_download_filename']
        elif selected_entry.get('requested_downloads') and \
             len(selected_entry['requested_downloads']) > 0 and \
             selected_entry['requested_downloads'][0].get('filepath'):
            actual_filepath = selected_entry['requested_downloads'][0]['filepath']
        elif selected_entry.get('filepath'): 
            actual_filepath = selected_entry.get('filepath')
        
        if actual_filepath and os.path.exists(actual_filepath):
            stream_url_final = actual_filepath
            log("YTDL_DOWNLOAD", f"Using downloaded file: {stream_url_final}", LogColors.GREEN)
        else:
            log("YTDL_ERROR", f"Downloaded file path not found or file does not exist (expected at '{actual_filepath}'). Falling back to streaming.", LogColors.RED)
            download_first = False 
    
    if not download_first: 
        direct_url = selected_entry.get('url') 
        audio_url_from_formats = None
        if 'formats' in selected_entry:
            format_preference = [
                lambda f: 'opus' in f.get('acodec','').lower() and f.get('ext') == 'webm',
                lambda f: 'opus' in f.get('acodec','').lower(),
                lambda f: f.get('ext') == 'webm' and f.get('acodec') != 'none',
                lambda f: f.get('acodec') != 'none' and f.get('vcodec') == 'none', 
                lambda f: f.get('protocol') in ['http', 'https'] 
            ]
            for pref_check in format_preference:
                for f_format in selected_entry['formats']: # Renamed to avoid conflict with outer 'f' if any
                    if f_format.get('url') and pref_check(f_format):
                        audio_url_from_formats = f_format['url']
                        log("YTDL_STREAM", f"Selected format for streaming: ext={f_format.get('ext')}, acodec={f_format.get('acodec')}", LogColors.CYAN)
                        break
                if audio_url_from_formats:
                    break
        
        stream_url_final = audio_url_from_formats or direct_url 
        if not stream_url_final:
            log("YTDL_ERROR", f"No streamable URL could be reliably found for '{title}'. Webpage: {selected_entry.get('webpage_url', 'N/A')}", LogColors.RED)
            raise Exception(f"🚫 No streamable URL found for '{title}'.")
        log("YTDL_STREAM", f"Using stream URL for '{title}'", LogColors.CYAN)


    log("PLAY_INFO", f"Title: {title}", LogColors.BLUE)
    log("PLAY_INFO", f"Duration: {duration}s" if duration is not None else "Duration: Unknown", LogColors.BLUE)
    # log("PLAY_INFO", f"{'File path' if download_first else 'Stream URL'}: {stream_url_final}", LogColors.BLUE) # URL can be very long

    ffmpeg_options_dict = { # Renamed to avoid conflict
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' if not download_first else '',
        'options': '-vn', 
    }

    if bass_boost:
        bass_filter = 'lowshelf=f=100:g=5' 
        limiter_filter = 'alimiter=level_in=1:level_out=1:limit=0.85:attack=5:release=50:makeup=0'
        ffmpeg_options_dict['options'] += f" -af \"{bass_filter},{limiter_filter}\""
        log("FFMPEG_EFFECT", "Applied smooth bass boost with limiter.", LogColors.CYAN)

    log("FFMPEG", f"Using FFMPEG options: {ffmpeg_options_dict['options']}", LogColors.YELLOW)

    try:
        source = discord.FFmpegPCMAudio(stream_url_final, **ffmpeg_options_dict)
    except Exception as e:
        log("FFMPEG_ERROR", f"Error creating FFmpegPCMAudio with URL (type: {type(stream_url_final)}): {e}", LogColors.RED)
        traceback.print_exc()
        raise Exception(f"🚫 Failed to create FFmpeg source: {e}")


    elapsed_op = time.time() - start_time_op
    log("TIME", f"play_song op for '{title}' took {elapsed_op:.2f}s.", LogColors.GREEN)

    song_data_to_return = {
        "source": source, "title": title,
        "duration": duration if duration is not None else 0, 
        "thumbnail": thumbnail_url, "webpage_url": webpage_url,
        "uploader": uploader, "query": search_query 
    }

    if return_source:
        return song_data_to_return
    else: # Should not be used typically
        if voice_client and voice_client.is_connected(): 
            voice_client.play(source)
        return None


async def search_youtube(search_query: str, num_results: int = 5):
    ydl_opts = {
        'format': 'bestaudio', 
        'quiet': True, 'default_search': f'ytsearch{num_results}', 
        'noplaylist': True, 'forcejson': True,
        'restrictfilenames': True, 'ignoreerrors': True, 
    }
    loop = asyncio.get_event_loop()
    results = []
    log("SEARCH", f"Searching YouTube for: '{search_query}' (Targeting {num_results} results)", LogColors.CYAN)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Add timeout for search extraction as well
            search_extract_task = loop.run_in_executor(None, functools.partial(ydl.extract_info, search_query, download=False))
            info = await asyncio.wait_for(search_extract_task, timeout=20.0) # 20s timeout for search
            
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
                            "title": info.get("title", "Unknown Title"), "duration": info.get("duration"),
                            "duration_str": f"{int(info['duration'] // 60):02d}:{int(info['duration'] % 60):02d}" if info.get("duration") is not None else "N/A",
                            "url": info.get("webpage_url", "#"), "thumbnail": info.get("thumbnail"),
                            "uploader": info.get("uploader", "Unknown Uploader"),
                            "query_for_play": info.get("webpage_url") or info.get("original_url") or info.get("title")
                        })
    except asyncio.TimeoutError:
        log("SEARCH_ERROR", f"Timeout searching YouTube for '{search_query}' after 20 seconds.", LogColors.RED)
        # Return empty list or raise, depending on desired behavior
    except Exception as e:
        log("SEARCH_ERROR", f"Error during YouTube search for '{search_query}': {e}", LogColors.RED)
        traceback.print_exc()
    
    log("SEARCH", f"Found {len(results)} results for '{search_query}'.", LogColors.GREEN if results else LogColors.YELLOW)
    return results