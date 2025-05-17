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
    try:
        if not bot_voice:
            # log("VOICE_JOIN", f"Attempting to join channel: {user_channel.name}", LogColors.CYAN)
            new_voice_client = await asyncio.wait_for(user_channel.connect(), timeout=10.0)
            # log("VOICE_JOIN_SUCCESS", f"Successfully joined channel: {new_voice_client.channel.name}", LogColors.GREEN)
            return new_voice_client
        if bot_voice.channel != user_channel:
            # log("VOICE_MOVE", f"Attempting to move from {bot_voice.channel.name} to {user_channel.name}", LogColors.CYAN)
            await asyncio.wait_for(bot_voice.move_to(user_channel), timeout=10.0)
            # log("VOICE_MOVE_SUCCESS", f"Successfully moved to channel: {user_channel.name}", LogColors.GREEN)
        return interaction.guild.voice_client
    except asyncio.TimeoutError:
        log("ERROR_JOIN_VC", f"Timeout connecting/moving to VC: {user_channel.name}", LogColors.RED)
        if interaction.response.is_done(): await interaction.followup.send(f"❌ Timed out connecting to {user_channel.name}.", ephemeral=True)
        else: await interaction.response.send_message(f"❌ Timed out connecting to {user_channel.name}.", ephemeral=True)
        return None
    except discord.errors.ClientException as e:
        log("ERROR_JOIN_VC", f"ClientException connecting/moving: {e}", LogColors.RED)
        if interaction.response.is_done(): await interaction.followup.send(f"❌ Error connecting to voice: {e}", ephemeral=True)
        else: await interaction.response.send_message(f"❌ Error connecting to voice: {e}", ephemeral=True)
        return None
    except Exception as e:
        log("ERROR_JOIN_VC", f"Unexpected error in join_voice_channel: {e}", LogColors.RED); traceback.print_exc()
        if interaction.response.is_done(): await interaction.followup.send("❌ Unexpected error joining voice.", ephemeral=True)
        else: await interaction.response.send_message("❌ Unexpected error joining voice.", ephemeral=True)
        return None

async def play_song(voice_client, search_query, return_source=False, bass_boost=False, download_first=True):
    start_time_op = time.time()
    log_prefix = f"[PLAY_SONG Query: '{search_query[:50]}...'] "

    if download_first: os.makedirs("downloads", exist_ok=True)
    cookie_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    if not os.path.exists(cookie_file_path):
        try:
            with open(cookie_file_path, 'w') as cf: cf.write("# Netscape HTTP Cookie File\n# Dummy file.\n") 
        except IOError as e:
            log(log_prefix + "COOKIE_CREATE_FAIL", f"Failed to create dummy cookie file: {e}", LogColors.YELLOW)
            cookie_file_path = None

    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best', 'quiet': True, 
        'default_search': 'ytsearch1', 'noplaylist': True,
        'cookiefile': cookie_file_path if cookie_file_path and os.path.exists(cookie_file_path) else None,
        'restrictfilenames': True, 'forcejson': True, 'ignoreerrors': False,
    }
    if download_first: ydl_opts['outtmpl'] = os.path.join('downloads', '%(title)s.%(ext)s')

    loop = asyncio.get_event_loop(); info = None; selected_entry = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            extract_task = loop.run_in_executor(None, functools.partial(ydl.extract_info, search_query, download=download_first))
            info = await asyncio.wait_for(extract_task, timeout=60.0)
        except asyncio.TimeoutError:
            log(log_prefix + "YTDL_TIMEOUT", "yt-dlp info extraction timed out.", LogColors.RED)
            raise Exception(f"🚫 Timed out fetching info for '{search_query}'.")
        except Exception as e: 
            log(log_prefix + "YTDL_EXTRACT_ERROR", f"yt-dlp extraction failed: {type(e).__name__}: {e}", LogColors.RED); traceback.print_exc()
            if 'DRM' in str(e).upper(): raise Exception("🚫 DRM-protected track.")
            raise Exception(f"❌ yt-dlp error: {str(e)[:200]}")

        if not info: 
            log(log_prefix + "YTDL_NO_INFO", "yt-dlp returned no info.", LogColors.RED)
            raise Exception(f"🔍 No info from yt_dlp for '{search_query}'.")
        selected_entry = info['entries'][0] if 'entries' in info and info['entries'] else info
        if not selected_entry: 
            log(log_prefix + "YTDL_NO_VALID_ENTRY", "No valid entry in yt_dlp info.", LogColors.RED)
            raise Exception(f"🔍 No valid entry in yt_dlp info for '{search_query}'.")

    title = selected_entry.get("title", "Unknown Title")
    duration = selected_entry.get("duration"); thumbnail_url = selected_entry.get("thumbnail")
    webpage_url = selected_entry.get("webpage_url"); uploader = selected_entry.get("uploader", "Unknown Uploader")
    stream_url_final = None

    if download_first:
        actual_filepath = None
        if selected_entry.get('_download_filename'): actual_filepath = selected_entry['_download_filename']
        elif selected_entry.get('requested_downloads') and selected_entry['requested_downloads'][0].get('filepath'):
            actual_filepath = selected_entry['requested_downloads'][0]['filepath']
        elif selected_entry.get('filepath'): actual_filepath = selected_entry.get('filepath')
        
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
                lambda f: 'opus' in f.get('acodec','').lower() and f.get('ext') == 'webm',
                lambda f: 'opus' in f.get('acodec','').lower(),
                lambda f: f.get('ext') == 'webm' and f.get('acodec') != 'none',
                lambda f: f.get('acodec') != 'none' and f.get('vcodec') == 'none', 
                lambda f: f.get('protocol') in ['http', 'https'] 
            ]
            for pref_check in format_preference:
                for f_format in selected_entry['formats']: 
                    if f_format.get('url') and pref_check(f_format):
                        audio_url_from_formats = f_format['url']; break
                if audio_url_from_formats: break
        
        stream_url_final = audio_url_from_formats or direct_url 
        if not stream_url_final:
            log(log_prefix + "STREAM_URL_FAIL", f"No streamable URL found for '{title}'.", LogColors.RED)
            raise Exception(f"🚫 No streamable URL found for '{title}'.")

    ffmpeg_options_dict = { 
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' if not download_first else '',
        'options': '-vn', 
    }
    if bass_boost:
        # 3-band EQ approach for smoother, punchier bass with definition
        # 1. High-pass filter to remove sub-bass rumble
        high_pass_filter = "highpass=f=35" # Cut frequencies below 35Hz

        # 2. Boost low-end for weight and power
        # g=gain, f=center frequency, w=bandwidth in octaves (smaller w = narrower Q = more punchy)
        low_end_boost_filter = "bass=g=4:f=70:w=0.4" 

        # 3. Peak EQ for definition and attack in upper bass/low mids
        # f=center frequency, t=q (width type is Q factor), w=Q factor, g=gain
        definition_boost_filter = "equalizer=f=125:t=q:w=1:g=2"
        
        # Chain the filters. Order: Cut first, then boosts.
        complex_filter_string = f"{high_pass_filter},{low_end_boost_filter},{definition_boost_filter}"
        
        ffmpeg_options_dict['options'] += f" -af \"{complex_filter_string}\""
        log(log_prefix + "FFMPEG_EFFECT", f"Applied 3-band EQ bass boost: {complex_filter_string}", LogColors.CYAN)
    
    try:
        source = discord.FFmpegPCMAudio(stream_url_final, **ffmpeg_options_dict) 
    except Exception as e:
        log(log_prefix + "FFMPEG_ERROR", f"Error creating FFmpegPCMAudio. Path/URL: '{stream_url_final}'. Error: {e}", LogColors.RED)
        traceback.print_exc() 
        raise Exception(f"🚫 Failed to create FFmpeg audio source for '{title}'. Is FFmpeg installed and in PATH?")

    song_data_to_return = {
        "source": source, "title": title, "duration": duration if duration is not None else 0, 
        "thumbnail": thumbnail_url, "webpage_url": webpage_url,
        "uploader": uploader, "query": search_query 
    }
    if return_source: return song_data_to_return
    else: 
        if voice_client and voice_client.is_connected(): voice_client.play(source)
        return None

async def search_youtube(search_query: str, num_results: int = 5):
    ydl_opts = {
        'format': 'bestaudio', 'quiet': True, 'default_search': f'ytsearch{num_results}', 
        'noplaylist': True, 'forcejson': True, 'restrictfilenames': True, 'ignoreerrors': True, 
    }
    loop = asyncio.get_event_loop(); results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_extract_task = loop.run_in_executor(None, functools.partial(ydl.extract_info, search_query, download=False))
            info = await asyncio.wait_for(search_extract_task, timeout=20.0) 
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry and entry.get("title") and (entry.get("webpage_url") or entry.get("url")):
                        results.append({"title": entry.get("title", "Unknown Title"),"duration": entry.get("duration"), "duration_str": f"{int(entry['duration'] // 60):02d}:{int(entry['duration'] % 60):02d}" if entry.get("duration") is not None else "N/A","url": entry.get("webpage_url", "#"), "thumbnail": entry.get("thumbnail"),"uploader": entry.get("uploader", "Unknown Uploader"),"query_for_play": entry.get("webpage_url") or entry.get("original_url") or entry.get("title")})
                    if len(results) >= num_results: break
            elif info and info.get("title") and (info.get("webpage_url") or info.get("url")): 
                 results.append({"title": info.get("title", "Unknown Title"), "duration": info.get("duration"),"duration_str": f"{int(info['duration'] // 60):02d}:{int(info['duration'] % 60):02d}" if info.get("duration") is not None else "N/A","url": info.get("webpage_url", "#"), "thumbnail": info.get("thumbnail"),"uploader": info.get("uploader", "Unknown Uploader"),"query_for_play": info.get("webpage_url") or info.get("original_url") or info.get("title")})
    except asyncio.TimeoutError: log("SEARCH_YOUTUBE_ERROR", f"Timeout searching YouTube for '{search_query}'", LogColors.RED)
    except Exception as e: log("SEARCH_YOUTUBE_ERROR", f"Error during YouTube search for '{search_query}': {e}", LogColors.RED); traceback.print_exc()
    return results
