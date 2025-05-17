import discord
from discord.ext import commands, tasks 
from discord import app_commands, Interaction, Embed
import asyncio
import re
import time 
import traceback

from src.utils.discord_voice import join_voice_channel, play_song, LogColors, log 
from src.utils.music import music_manager, LoopState 
# Import the check from play.py or a shared utility file
# For now, assuming it might be defined in play.py and we'd ideally move it to a shared utils.checks
# If is_dj_or_admin is in play.py, this direct import won't work cleanly without circular dependencies.
# A better solution is to move is_dj_or_admin to a new file like src/utils/checks.py
# For this example, I'll assume it's accessible or we're not applying it directly to /playlist command itself.
# from src.commands.play import is_dj_or_admin # This would be ideal if check is sharable

# If you want to restrict /playlist command itself, you'd need the check:
# from .play import is_dj_or_admin # If in same directory and play.py has it.

class PlaylistCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.playlist_category_name = "🎵 Custom Playlists"

    def format_duration(self, seconds, include_hours_if_zero=False):
        # ... (implementation as before)
        if seconds is None: return "N/A"
        try: seconds = int(seconds)
        except (ValueError, TypeError): return "N/A"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0 or (include_hours_if_zero and hours == 0):
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    async def send_now_playing_embed(self, interaction_or_context, guild_id, is_followup=False, from_play_next=False):
        # ... (implementation as before)
        now_playing_info = music_manager.get_now_playing(guild_id)
        target_channel = None
        if isinstance(interaction_or_context, Interaction): target_channel = interaction_or_context.channel
        elif isinstance(interaction_or_context, discord.TextChannel): target_channel = interaction_or_context
        elif hasattr(interaction_or_context, 'channel') and isinstance(interaction_or_context.channel, discord.abc.Messageable): target_channel = interaction_or_context.channel
        if not target_channel: 
            guild = self.bot.get_guild(guild_id)
            if guild:
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages: target_channel = guild.system_channel
                else:
                    for tc in guild.text_channels:
                        if tc.permissions_for(guild.me).send_messages: target_channel = tc; break
        if not target_channel: log("EMBED_SEND_ERROR", f"PlaylistCmd NowPlaying: Could not determine target channel for guild {guild_id}.", LogColors.RED); return
        if not now_playing_info: return
        embed = Embed(title="🎶 Now Playing 🎶", color=discord.Color.random())
        embed.add_field(name="Title", value=f"[{now_playing_info['title']}]({now_playing_info.get('url', '#')})", inline=False)
        current_time = time.time(); elapsed_time = current_time - now_playing_info.get("start_time", current_time); total_duration = now_playing_info.get("duration", 0)
        bar_length = 20; progress = min(1.0, elapsed_time / total_duration) if total_duration and total_duration > 0 else 0; filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '─' * (bar_length - filled_length); progress_str = f"`{self.format_duration(elapsed_time)} / {self.format_duration(total_duration)}`\n`{bar}`"
        embed.add_field(name="Progress", value=progress_str, inline=False)
        embed.add_field(name="Requested by", value=now_playing_info["requester"], inline=True); embed.add_field(name="Uploader", value=now_playing_info.get("uploader", "N/A"), inline=True)
        loop_state = music_manager.get_loop_state(guild_id); embed.add_field(name="Loop", value=f"```{loop_state.name.capitalize()}```", inline=True)
        if now_playing_info.get("thumbnail"): embed.set_thumbnail(url=now_playing_info["thumbnail"])
        embed.set_footer(text=f"BasslineBot | {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        try:
            if isinstance(interaction_or_context, Interaction):
                if from_play_next: await target_channel.send(embed=embed)
                elif is_followup: await interaction_or_context.followup.send(embed=embed)
                else: await interaction_or_context.response.send_message(embed=embed)
            else: await target_channel.send(embed=embed)
        except discord.errors.NotFound: 
            if target_channel: 
                try: await target_channel.send(embed=embed)
                except Exception as e_raw_send: log("EMBED_SEND_ERROR", f"PlaylistCmd NowPlaying: Raw channel send also failed - {e_raw_send}", LogColors.RED)
        except Exception as e: log("EMBED_SEND_ERROR", f"PlaylistCmd NowPlaying: Error sending - {e}", LogColors.RED)

    @app_commands.command(name="setupplaylists", description="Create a category for storing custom playlists (Admin only).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_playlists(self, interaction: Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            try:
                category = await guild.create_category(self.playlist_category_name)
                await interaction.response.send_message(f"✅ Playlist category '{category.name}' created!")
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to create categories.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Error creating category: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Playlist category '{category.name}' already exists.")

    @setup_playlists.error
    async def setup_playlists_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


    @app_commands.command(name="createplaylist", description="Create a new playlist channel (Admin only).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_playlist(self, interaction: Interaction, playlist_name: str):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            await interaction.response.send_message("⚠️ Playlist category not found. Run `/setupplaylists` first.", ephemeral=True)
            return
        channel_name = re.sub(r"[^a-z0-9_.-]", "", playlist_name.lower().replace(" ", "-"))
        if not channel_name:
            await interaction.response.send_message("⚠️ Invalid playlist name for channel creation.", ephemeral=True)
            return
        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"⚠️ A playlist channel named `{channel_name}` already exists.", ephemeral=True)
            return
        try:
            new_channel = await guild.create_text_channel(channel_name, category=category, topic=f"Custom Playlist: {playlist_name}")
            intro_message = (
                f"🎶 **Playlist: {playlist_name}** (`#{new_channel.name}`)\n\n"
                f"Type song titles or YouTube URLs below, one per message. These will be added to the queue when you play this playlist.\n\n"
                f"To play this playlist, use the command:\n`/playlist {playlist_name}` (or mention `#{new_channel.name}`)"
            )
            await new_channel.send(intro_message)
            await interaction.response.send_message(f"✅ Playlist channel `{playlist_name}` (`#{new_channel.name}`) created under '{category.name}'!")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create channels in that category.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating playlist channel: {e}", ephemeral=True)

    @create_playlist.error
    async def create_playlist_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

    @app_commands.command(name="playlist", description="Play songs from a custom playlist channel.")
    @app_commands.describe(playlist_identifier="Name of the playlist or #channel-mention")
    # If you want to restrict /playlist itself:
    # @is_dj_or_admin() 
    async def play_playlist(self, interaction: Interaction, playlist_identifier: str):
        log_prefix_cmd = f"[PLAYLIST_CMD Guild: {interaction.guild.id}] "
        log(log_prefix_cmd + "START", f"Received /playlist for '{playlist_identifier}' by {interaction.user}", LogColors.CYAN)
        await interaction.response.defer()
        music_manager.update_last_activity(interaction.guild.id)

        guild = interaction.guild
        playlist_channel = None 

        try: 
            match = re.match(r"<#(\d+)>", playlist_identifier.strip())
            if match:
                channel_id = int(match.group(1))
                playlist_channel = guild.get_channel(channel_id)
                if not isinstance(playlist_channel, discord.TextChannel):
                    log(log_prefix_cmd + "ERROR", f"Mentioned ID {channel_id} is not a text channel.", LogColors.YELLOW)
                    await interaction.followup.send("⚠️ Mentioned channel is not a valid text channel.", ephemeral=True)
                    return
            else: 
                category = discord.utils.get(guild.categories, name=self.playlist_category_name)
                if not category:
                    log(log_prefix_cmd + "ERROR", f"Playlist category '{self.playlist_category_name}' not found.", LogColors.YELLOW)
                    await interaction.followup.send(f"⚠️ Playlist category '{self.playlist_category_name}' not found. Run `/setupplaylists` if you are an admin.", ephemeral=True)
                    return
                
                normalized_target_name = re.sub(r"[^a-z0-9_.-]", "", playlist_identifier.lower().replace(" ", "-"))
                for ch in category.text_channels:
                    channel_name_for_norm = ch.name 
                    channel_topic_for_check = ch.topic
                    normalized_channel_name = re.sub(r"[^a-z0-9_.-]", "", channel_name_for_norm.lower())
                    topic_name_match = False
                    if channel_topic_for_check is not None and isinstance(channel_topic_for_check, str):
                        topic_to_match = f"Custom Playlist: {str(playlist_identifier)}"
                        if topic_to_match == channel_topic_for_check.strip(): topic_name_match = True
                    if normalized_channel_name == normalized_target_name or topic_name_match:
                        playlist_channel = ch; break 
            
            if not playlist_channel:
                log(log_prefix_cmd + "CHANNEL_NOT_FOUND", f"Playlist channel NOT found for '{playlist_identifier}'.", LogColors.YELLOW)
                await interaction.followup.send(f"⚠️ Playlist '{playlist_identifier}' not found.", ephemeral=True)
                return
            
            log(log_prefix_cmd + "CHANNEL_FOUND", f"Playlist channel: {playlist_channel.name} ({playlist_channel.id})", LogColors.GREEN)

            songs_to_queue = []
            message_count = 0
            history_fetch_timeout = 30.0 
            try:
                history_iterator = playlist_channel.history(limit=200, oldest_first=True)
                async def collect_history_messages():
                    nonlocal message_count 
                    async for message in history_iterator: 
                        message_count += 1
                        if not message.author.bot and message.content and not message.content.startswith(('/', '!', '#', '<@', '<#')):
                            song_query = message.content.strip()
                            if song_query: songs_to_queue.append(song_query)
                await asyncio.wait_for(collect_history_messages(), timeout=history_fetch_timeout)
                log(log_prefix_cmd + "HISTORY_END", f"Found {len(songs_to_queue)} songs in {playlist_channel.name}.", LogColors.BLUE)
            except asyncio.TimeoutError:
                log(log_prefix_cmd + "HISTORY_TIMEOUT", f"Timeout fetching history from {playlist_channel.name}.", LogColors.RED)
                if not songs_to_queue: await interaction.followup.send(f"⚠️ Timed out reading playlist {playlist_channel.mention}.", ephemeral=True); return
            except discord.Forbidden:
                log(log_prefix_cmd + "HISTORY_FORBIDDEN", f"Forbidden to read history in {playlist_channel.name}.", LogColors.RED)
                await interaction.followup.send(f"❌ No permission to read messages in {playlist_channel.mention}.", ephemeral=True); return
            except Exception as e:
                log(log_prefix_cmd + "HISTORY_ERROR", f"Error reading playlist messages: {e}", LogColors.RED); traceback.print_exc()
                await interaction.followup.send(f"❌ Error reading playlist messages: {e}", ephemeral=True); return
            
            if not songs_to_queue:
                log(log_prefix_cmd + "NO_SONGS_IN_PLAYLIST", f"No songs found in {playlist_channel.name}.", LogColors.YELLOW)
                await interaction.followup.send(f"⚠️ No songs found in playlist {playlist_channel.mention}.", ephemeral=True); return

            vc = music_manager.voice_clients.get(guild.id)
            if not vc or not vc.is_connected():
                vc = await join_voice_channel(interaction)
                if not vc: return 
                music_manager.voice_clients[guild.id] = vc

            is_currently_playing = music_manager.is_playing(guild.id)
            current_queue_was_empty = not music_manager.get_queue(guild.id)
            for track_query in songs_to_queue:
                await music_manager.add_to_queue(guild.id, track_query, interaction.user)

            await interaction.followup.send(f"✅ Queued {len(songs_to_queue)} song(s) from **{playlist_channel.name}**.")

            if not is_currently_playing and current_queue_was_empty:
                log(log_prefix_cmd + "STARTING_PLAYBACK", "Calling _play_next to start playlist.", LogColors.CYAN)
                asyncio.create_task(self._play_next(interaction))
            else:
                log(log_prefix_cmd + "ALREADY_PLAYING_OR_QUEUED", "Bot already playing or queue not empty, playlist songs added.", LogColors.BLUE)

        except Exception as e_outer:
            log(log_prefix_cmd + "UNEXPECTED_ERROR_OUTER", f"Unexpected error in play_playlist: {e_outer}", LogColors.RED)
            traceback.print_exc()
            if interaction.response.is_done():
                 try: await interaction.followup.send("An unexpected error occurred. Please try again.", ephemeral=True)
                 except discord.errors.NotFound: pass


    async def _play_next(self, interaction_context: Interaction, error=None, retry_count=0):
        MAX_RETRIES_PER_SONG = 1 
        log_prefix = f"[PLAYLIST_PLAY_NEXT Guild: {interaction_context.guild.id}] "
        log(log_prefix + "INVOKED", f"Error from after_playback_hook: '{error}', Retry count for current song: {retry_count}", LogColors.CYAN)

        guild_id = interaction_context.guild.id
        vc = interaction_context.guild.voice_client
        if not vc: vc = music_manager.voice_clients.get(guild_id)

        if not vc or not vc.is_connected():
            log(log_prefix + "VC_ISSUE", "VC not found or not connected at start of _play_next. Stopping.", LogColors.YELLOW)
            music_manager.clear_guild_state(guild_id)
            if interaction_context.channel and not interaction_context.response.is_done():
                try: await interaction_context.channel.send("I've been disconnected from voice. Playback stopped.")
                except: pass
            return

        current_loop_state = music_manager.get_loop_state(guild_id)
        song_that_just_finished = music_manager.get_now_playing(guild_id)
        track_to_play_query = None; requested_by_obj = None

        if current_loop_state == LoopState.SINGLE and song_that_just_finished and retry_count == 0:
            track_to_play_query = song_that_just_finished.get("query")
            requested_by_obj = song_that_just_finished.get("requested_by_obj")
        else:
            next_in_queue = music_manager.get_next(guild_id)
            if next_in_queue and next_in_queue[0]:
                track_to_play_query, requested_by_obj = next_in_queue
                if current_loop_state == LoopState.QUEUE and song_that_just_finished:
                    if not error or retry_count >= MAX_RETRIES_PER_SONG: 
                        await music_manager.add_to_queue(guild_id, song_that_just_finished.get("query"), song_that_just_finished.get("requested_by_obj"))
            elif current_loop_state == LoopState.QUEUE and song_that_just_finished:
                 next_in_queue_after_readd = music_manager.get_next(guild_id)
                 if next_in_queue_after_readd and next_in_queue_after_readd[0]:
                     track_to_play_query, requested_by_obj = next_in_queue_after_readd
        
        if not track_to_play_query or not requested_by_obj:
            music_manager.now_playing.pop(guild_id, None)
            log(log_prefix + "QUEUE_EMPTY", "Queue empty, no loop. Playback stopped.", LogColors.BLUE)
            if interaction_context.channel: 
                try: await interaction_context.channel.send("✅ Queue ended.")
                except: pass
            return

        log(log_prefix + "ATTEMPTING_PLAY", f"Trying to play '{track_to_play_query}' (Retry: {retry_count})", LogColors.CYAN)
        playback_exception = None
        try:
            vc = interaction_context.guild.voice_client 
            if not vc or not vc.is_connected():
                log(log_prefix + "VC_DISCONNECTED_PRE_PLAYSONG", "VC disconnected before play_song. Stopping.", LogColors.RED)
                music_manager.clear_guild_state(guild_id)
                if interaction_context.channel: await interaction_context.channel.send("⚠️ I was disconnected before I could play the next song.")
                return

            bass_boost = music_manager.get_bass_boost(requested_by_obj.id)
            song_details = await play_song(vc, track_to_play_query, return_source=True, bass_boost=bass_boost, download_first=True)
            
            if not song_details or "source" not in song_details:
                log(log_prefix + "PLAY_SONG_FAIL", f"play_song invalid details for '{track_to_play_query}'.", LogColors.RED)
                raise Exception("Song processing failed: No audio source.")

            actual_audio_source = song_details["source"]
            music_manager.set_now_playing(guild_id, {
                "title": song_details["title"], "duration": song_details["duration"],
                "thumbnail": song_details.get("thumbnail"), "query": track_to_play_query,
                "start_time": time.time(), "url": song_details.get("webpage_url"),
                "uploader": song_details.get("uploader")}, requested_by_obj)

            await asyncio.sleep(0.1) 
            vc = interaction_context.guild.voice_client 
            if not vc or not vc.is_connected():
                log(log_prefix + "VC_DISCONNECTED_PRE_VC_PLAY", "VC disconnected right before vc.play(). Aborting this track.", LogColors.RED)
                asyncio.create_task(self._play_next(interaction_context, error="VC Disconnected Pre-Play", retry_count=MAX_RETRIES_PER_SONG + 1)) 
                return

            def after_playback_hook(error_from_player):
                hook_log_prefix = f"[PlaylistCmd Guild: {guild_id}] AFTER_PLAYBACK_HOOK "
                effective_error = error_from_player
                current_song_info = music_manager.get_now_playing(guild_id) 

                if error_from_player is None and current_song_info:
                    playback_start_time = current_song_info.get("start_time", 0)
                    expected_duration = current_song_info.get("duration", 0)
                    if playback_start_time > 0: 
                        actual_play_time = time.time() - playback_start_time
                        if expected_duration > 3 and actual_play_time < 1.5: 
                            silent_fail_msg = f"Playback finished too quickly (expected {expected_duration:.0f}s, played {actual_play_time:.2f}s). Likely an issue with the audio source or FFmpeg."
                            log(hook_log_prefix + "SILENT_FAILURE_DETECTED", silent_fail_msg, LogColors.YELLOW)
                            effective_error = Exception(silent_fail_msg) 
                
                log(hook_log_prefix + "TRIGGERED", f"For song '{current_song_info.get('query') if current_song_info else 'N/A'}'. Player Error: '{error_from_player}', Effective Error for Retry: '{effective_error}'", LogColors.CYAN)
                
                asyncio.run_coroutine_threadsafe(
                    self._play_next(interaction_context, error=effective_error, retry_count=0),
                    self.bot.loop
                )

            vc.play(actual_audio_source, after=after_playback_hook)
            log(log_prefix + "PLAYBACK_STARTED", f"vc.play() called for '{track_to_play_query}'.", LogColors.GREEN)
            await self.send_now_playing_embed(interaction_context.channel if interaction_context else None, guild_id, from_play_next=True)
            return 

        except Exception as e_play: 
            playback_exception = e_play
            log(log_prefix + "PLAY_EXCEPTION", f"Failed to prepare or start playback for '{track_to_play_query}': {type(e_play).__name__}: {e_play}", LogColors.RED)
            traceback.print_exc() 
            
        if retry_count < MAX_RETRIES_PER_SONG:
            log(log_prefix + "RETRYING_SONG", f"Retrying '{track_to_play_query}' due to error: {playback_exception} (Attempt {retry_count + 1}/{MAX_RETRIES_PER_SONG}).", LogColors.YELLOW)
            await asyncio.sleep(1) 
            asyncio.create_task(self._play_next(interaction_context, error=playback_exception, retry_count=retry_count + 1))
        else:
            log(log_prefix + "MAX_RETRIES_REACHED", f"Max retries for '{track_to_play_query}'. Error: {playback_exception}. Skipping.", LogColors.RED)
            if interaction_context.channel:
                try: await interaction_context.channel.send(f"❌ Failed to play '{track_to_play_query[:70]}...' (Error: {str(playback_exception)[:50]}). Skipping.")
                except: pass
            asyncio.create_task(self._play_next(interaction_context, error=None, retry_count=0))


async def setup(bot: commands.Bot):
    await bot.add_cog(PlaylistCommand(bot))
