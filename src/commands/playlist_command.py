import discord
from discord.ext import commands, tasks 
from discord import app_commands, Interaction, Embed
import asyncio
import re
import time 
import traceback

from src.utils.discord_voice import join_voice_channel, play_song, LogColors, log 
from src.utils.music import music_manager, LoopState 

class PlaylistCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.playlist_category_name = "🎵 Custom Playlists"

    def format_duration(self, seconds, include_hours_if_zero=False):
        if seconds is None: return "N/A"
        try: seconds = int(seconds)
        except (ValueError, TypeError): return "N/A"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0 or (include_hours_if_zero and hours == 0):
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    async def send_now_playing_embed(self, interaction_or_context, guild_id, is_followup=False, from_play_next=False):
        # ... (implementation as previously corrected)
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
        except discord.errors.NotFound: log("EMBED_SEND_ERROR", "PlaylistCmd NowPlaying: Interaction/Channel not found.", LogColors.YELLOW); await target_channel.send(embed=embed) 
        except Exception as e: log("EMBED_SEND_ERROR", f"PlaylistCmd NowPlaying: Error sending - {e}", LogColors.RED)

    @app_commands.command(name="setupplaylists", description="Create a category for storing custom playlists (admin).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_playlists(self, interaction: Interaction):
        # ... (implementation as before)
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


    @app_commands.command(name="createplaylist", description="Create a new playlist channel (admin).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_playlist(self, interaction: Interaction, playlist_name: str):
        # ... (implementation as before)
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
    async def play_playlist(self, interaction: Interaction, playlist_identifier: str):
        log("PLAYLIST_CMD_START", f"Received /playlist for '{playlist_identifier}' by {interaction.user} in guild {interaction.guild.id}", LogColors.CYAN)
        await interaction.response.defer()
        log("PLAYLIST_CMD_DEFERRED", f"Interaction deferred for '{playlist_identifier}'", LogColors.CYAN)
        music_manager.update_last_activity(interaction.guild.id)

        guild = interaction.guild
        playlist_channel = None 

        try: 
            log("PLAYLIST_CMD_LOGIC_ENTER", "Entering main playlist identification logic", LogColors.BLUE)
            match = re.match(r"<#(\d+)>", playlist_identifier.strip())
            if match:
                channel_id = int(match.group(1))
                log("PLAYLIST_CMD_DEBUG", f"Attempting to get channel by ID: {channel_id}", LogColors.BLUE)
                playlist_channel = guild.get_channel(channel_id)
                if not isinstance(playlist_channel, discord.TextChannel):
                    log("PLAYLIST_CMD_ERROR", f"Mentioned ID {channel_id} is not a text channel.", LogColors.YELLOW)
                    await interaction.followup.send("⚠️ Mentioned channel is not a valid text channel.", ephemeral=True)
                    return
                log("PLAYLIST_CMD_DEBUG", f"Channel found by mention: {playlist_channel.name}", LogColors.GREEN)
            else: 
                log("PLAYLIST_CMD_DEBUG", "No channel mention, searching by name.", LogColors.BLUE)
                category = discord.utils.get(guild.categories, name=self.playlist_category_name)
                if not category:
                    log("PLAYLIST_CMD_ERROR", f"Playlist category '{self.playlist_category_name}' not found.", LogColors.YELLOW)
                    await interaction.followup.send(f"⚠️ Playlist category '{self.playlist_category_name}' not found. Run `/setupplaylists` if you are an admin.", ephemeral=True)
                    return
                
                normalized_target_name = re.sub(r"[^a-z0-9_.-]", "", playlist_identifier.lower().replace(" ", "-"))
                log("PLAYLIST_CMD_DEBUG", f"Normalized target playlist name: '{normalized_target_name}' (Type: {type(normalized_target_name)})", LogColors.BLUE)
                log("PLAYLIST_CMD_DEBUG", f"Starting to iterate through {len(category.text_channels)} text channels in category '{category.name}'.", LogColors.BLUE)
                
                for ch_idx, ch in enumerate(category.text_channels):
                    log("PLAYLIST_CMD_DEBUG", f"Loop iteration {ch_idx + 1}: Accessing channel ID {ch.id}, Name '{ch.name}' (Type: {type(ch.name)})", LogColors.BLUE)
                    try:
                        channel_name_for_norm = ch.name 
                        channel_topic_for_check = ch.topic
                        log("PLAYLIST_CMD_DEBUG", f"  Channel '{channel_name_for_norm}', Topic '{channel_topic_for_check}' (Type: {type(channel_topic_for_check)})", LogColors.BLUE)
                    except Exception as e_attr:
                        log("PLAYLIST_CMD_ERROR", f"  Error accessing attributes for channel at index {ch_idx} (ID {ch.id}): {e_attr}", LogColors.RED)
                        continue 

                    normalized_channel_name = re.sub(r"[^a-z0-9_.-]", "", channel_name_for_norm.lower())
                    log("PLAYLIST_CMD_DEBUG", f"  Normalized channel name: '{normalized_channel_name}' (Type: {type(normalized_channel_name)})", LogColors.BLUE)
                    
                    topic_name_match = False
                    log("PLAYLIST_CMD_DEBUG", f"  Before topic check. playlist_identifier: '{playlist_identifier}' (Type: {type(playlist_identifier)})", LogColors.BLUE)
                    if channel_topic_for_check is not None and isinstance(channel_topic_for_check, str):
                        log("PLAYLIST_CMD_DEBUG", f"  Topic is a string: '{channel_topic_for_check}'. Checking for exact match with 'Custom Playlist: {playlist_identifier}'", LogColors.BLUE)
                        topic_to_match = f"Custom Playlist: {str(playlist_identifier)}"
                        if topic_to_match == channel_topic_for_check.strip():
                            topic_name_match = True
                            log("PLAYLIST_CMD_DEBUG", f"  Topic match FOUND for '{playlist_identifier}' in channel '{channel_name_for_norm}'", LogColors.GREEN)
                    else:
                        log("PLAYLIST_CMD_DEBUG", f"  Topic is None or not a string. Skipping topic match.", LogColors.BLUE)
                    
                    log("PLAYLIST_CMD_DEBUG", f"  Before final match condition for '{channel_name_for_norm}'. Normalized Ch Name: '{normalized_channel_name}', Target: '{normalized_target_name}', Topic Match: {topic_name_match}", LogColors.BLUE)
                    if normalized_channel_name == normalized_target_name or topic_name_match:
                        log("PLAYLIST_CMD_DEBUG", f"  MATCH FOUND! Channel: '{channel_name_for_norm}'. Setting playlist_channel.", LogColors.GREEN)
                        playlist_channel = ch
                        log("PLAYLIST_CMD_DEBUG", f"  playlist_channel set to: {playlist_channel.name}. Breaking loop.", LogColors.GREEN)
                        break 
                    else:
                        log("PLAYLIST_CMD_DEBUG", f"  No match for channel '{channel_name_for_norm}'. Continuing loop.", LogColors.BLUE)
                
                log("PLAYLIST_CMD_DEBUG", f"Loop finished. playlist_channel is: {playlist_channel.name if playlist_channel else 'None'}", LogColors.BLUE)
            
            if not playlist_channel:
                log("PLAYLIST_CMD_CHANNEL_NOT_FOUND", f"Playlist channel NOT found for '{playlist_identifier}' after search attempts.", LogColors.YELLOW)
                await interaction.followup.send(f"⚠️ Playlist '{playlist_identifier}' not found. Ensure it's a valid channel name or mention under the '{self.playlist_category_name}' category.", ephemeral=True)
                return
            
            log("PLAYLIST_CMD_CHANNEL_FOUND", f"Playlist channel successfully identified: {playlist_channel.name} ({playlist_channel.id})", LogColors.GREEN)

            log("PLAYLIST_CMD_HISTORY_START", f"Fetching history for {playlist_channel.name}", LogColors.CYAN)
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
                            if song_query: 
                                songs_to_queue.append(song_query)
                        if message_count % 50 == 0: 
                            log("PLAYLIST_CMD_HISTORY_PROGRESS", f"Processed {message_count} messages from {playlist_channel.name}", LogColors.BLUE)
                
                await asyncio.wait_for(collect_history_messages(), timeout=history_fetch_timeout)
                log("PLAYLIST_CMD_HISTORY_END", f"Fetched and processed {message_count} messages, found {len(songs_to_queue)} potential songs from {playlist_channel.name}", LogColors.BLUE)

            except asyncio.TimeoutError:
                log("PLAYLIST_CMD_ERROR", f"Timeout fetching message history from {playlist_channel.name} after {history_fetch_timeout}s. Processed {message_count} messages.", LogColors.RED)
                if not songs_to_queue: 
                    await interaction.followup.send(f"⚠️ Timed out trying to read the playlist {playlist_channel.mention}. The channel might be too long or there's a network issue.", ephemeral=True)
                    return
            except discord.Forbidden:
                log("PLAYLIST_CMD_ERROR", f"Forbidden to read history in {playlist_channel.name}", LogColors.RED)
                await interaction.followup.send(f"❌ I don't have permission to read messages in {playlist_channel.mention}.", ephemeral=True)
                return
            except Exception as e:
                log("PLAYLIST_CMD_ERROR", f"Error reading playlist messages from {playlist_channel.name}: {e}", LogColors.RED)
                traceback.print_exc()
                await interaction.followup.send(f"❌ Error reading playlist messages: {e}", ephemeral=True)
                return
            
            if not songs_to_queue:
                log("PLAYLIST_CMD_NO_SONGS", f"No valid song queries found in playlist {playlist_channel.name}", LogColors.YELLOW)
                await interaction.followup.send(f"⚠️ No songs found in the playlist {playlist_channel.mention}. Add song titles or URLs to the channel.", ephemeral=True)
                return

            log("PLAYLIST_CMD_JOIN_VC_START", "Attempting to join voice channel if not already in one.", LogColors.CYAN)
            vc = music_manager.voice_clients.get(guild.id)
            if not vc or not vc.is_connected():
                vc = await join_voice_channel(interaction)
                if not vc:
                    log("PLAYLIST_CMD_JOIN_VC_FAIL", "Failed to join voice channel (join_voice_channel handled msg).", LogColors.RED)
                    return 
                music_manager.voice_clients[guild.id] = vc
            log("PLAYLIST_CMD_JOIN_VC_STATUS", f"Voice client status: Connected to {vc.channel.name if vc else 'None'}", LogColors.BLUE)

            is_currently_playing = music_manager.is_playing(guild.id)
            current_queue_was_empty = not music_manager.get_queue(guild.id)
            log("PLAYLIST_CMD_QUEUEING", f"Queueing {len(songs_to_queue)} songs. Currently playing: {is_currently_playing}, Queue was empty before: {current_queue_was_empty}", LogColors.CYAN)

            for track_query in songs_to_queue:
                await music_manager.add_to_queue(guild.id, track_query, interaction.user)

            await interaction.followup.send(f"✅ Queued {len(songs_to_queue)} song(s) from playlist **{playlist_channel.name}**.")
            log("PLAYLIST_CMD_QUEUED_MSG_SENT", "Queue confirmation message sent.", LogColors.BLUE)

            if not is_currently_playing and current_queue_was_empty:
                log("PLAYLIST_CMD_CALLING_PLAY_NEXT", "Calling _play_next to start playback from new playlist.", LogColors.CYAN)
                asyncio.create_task(self._play_next(interaction))
            else:
                log("PLAYLIST_CMD_NOT_CALLING_PLAY_NEXT", "Not calling _play_next; bot is already playing or queue had items.", LogColors.BLUE)

        except Exception as e_outer:
            log("PLAYLIST_CMD_UNEXPECTED_ERROR", f"An unexpected error occurred in play_playlist: {e_outer}", LogColors.RED)
            traceback.print_exc()
            if not interaction.response.is_done():
                 pass 
            else: 
                 try:
                    await interaction.followup.send("An unexpected error occurred while processing the playlist. Please try again.", ephemeral=True)
                 except discord.errors.NotFound: 
                    log("PLAYLIST_CMD_ERROR", "Failed to send followup error for playlist command, interaction expired.", LogColors.YELLOW)


    async def _play_next(self, interaction_context: Interaction, error=None, retry_count=0):
        MAX_RETRIES_PER_SONG = 2 
        log_prefix = f"[PLAYLIST_PLAY_NEXT Guild: {interaction_context.guild.id}] "
        log(log_prefix + "INVOKED", f"Error from previous: {error}, Retry: {retry_count}", LogColors.CYAN)

        if error:
            log(log_prefix + "PREV_ERROR", f"Previous playback error: {error}", LogColors.RED)

        guild_id = interaction_context.guild.id
        vc = music_manager.voice_clients.get(guild_id)

        if not vc or not vc.is_connected():
            log(log_prefix + "VC_ISSUE", "VC not found or not connected. Stopping.", LogColors.YELLOW)
            music_manager.clear_guild_state(guild_id)
            return

        current_loop_state = music_manager.get_loop_state(guild_id)
        song_that_just_finished = music_manager.get_now_playing(guild_id)
        track_to_play_query = None
        requested_by_obj = None

        if current_loop_state == LoopState.SINGLE and song_that_just_finished and retry_count == 0:
            track_to_play_query = song_that_just_finished.get("query")
            requested_by_obj = song_that_just_finished.get("requested_by_obj")
            log(log_prefix + "LOOP_SINGLE", f"Replaying '{track_to_play_query}'", LogColors.BLUE)
        else:
            next_in_queue = music_manager.get_next(guild_id) 
            if next_in_queue and next_in_queue[0]:
                track_to_play_query, requested_by_obj = next_in_queue
                log(log_prefix + "NEXT_FROM_QUEUE", f"Got '{track_to_play_query}'", LogColors.BLUE)
                if current_loop_state == LoopState.QUEUE and song_that_just_finished:
                    if not error or retry_count > 0 : 
                        await music_manager.add_to_queue(guild_id, song_that_just_finished.get("query"), song_that_just_finished.get("requested_by_obj"))
                        log(log_prefix + "LOOP_QUEUE", f"Re-added '{song_that_just_finished.get('query')}' to end.", LogColors.BLUE)
            elif current_loop_state == LoopState.QUEUE and song_that_just_finished: 
                 next_in_queue_after_readd = music_manager.get_next(guild_id)
                 if next_in_queue_after_readd and next_in_queue_after_readd[0]:
                     track_to_play_query, requested_by_obj = next_in_queue_after_readd
                     log(log_prefix + "LOOP_QUEUE_REPICK", f"Got '{track_to_play_query}' after re-add", LogColors.BLUE)
        
        if not track_to_play_query or not requested_by_obj:
            music_manager.now_playing.pop(guild_id, None)
            log(log_prefix + "QUEUE_EMPTY", "Queue is empty and no loop active for a new song.", LogColors.BLUE)
            if interaction_context and interaction_context.channel:
                try: await interaction_context.channel.send("✅ Queue ended.")
                except discord.errors.NotFound: log(log_prefix + "QUEUE_ENDED_MSG_FAIL", "Channel not found.", LogColors.YELLOW)
            return

        log(log_prefix + "ATTEMPTING_PLAY", f"Attempting to play '{track_to_play_query}' (Retry: {retry_count})", LogColors.CYAN)
        try:
            bass_boost = music_manager.get_bass_boost(requested_by_obj.id)
            song_details = await play_song(vc, track_to_play_query, return_source=True, bass_boost=bass_boost, download_first=True)
            
            if not song_details or "source" not in song_details:
                log(log_prefix + "PLAY_SONG_FAIL", f"play_song returned invalid details for '{track_to_play_query}'. Details: {song_details}", LogColors.RED)
                raise Exception("Invalid song details (source missing).")

            actual_audio_source = song_details["source"]
            log(log_prefix + "SOURCE_OK", f"Audio source obtained for '{track_to_play_query}'", LogColors.GREEN)
            
            music_manager.set_now_playing(guild_id, {
                "title": song_details["title"], "duration": song_details["duration"],
                "thumbnail": song_details.get("thumbnail"), "query": track_to_play_query,
                "start_time": time.time(), "url": song_details.get("webpage_url"),
                "uploader": song_details.get("uploader")}, requested_by_obj)

            vc.play(actual_audio_source, 
                after=lambda e: asyncio.run_coroutine_threadsafe( # CORRECTED: Use run_coroutine_threadsafe
                    self._play_next(interaction_context, error=e, retry_count=0), 
                    self.bot.loop
                ) # No .result() here
            )
            log(log_prefix + "PLAYBACK_STARTED", f"'{track_to_play_query}'. Sending NowPlaying embed.", LogColors.GREEN)
            await self.send_now_playing_embed(interaction_context.channel if interaction_context else None, guild_id, from_play_next=True)

        except Exception as e_play: 
            log(log_prefix + "PLAY_EXCEPTION", f"Error playing '{track_to_play_query}': {e_play}", LogColors.RED)
            traceback.print_exc()
            
            if retry_count < MAX_RETRIES_PER_SONG:
                log(log_prefix + "RETRYING_SONG", f"Retrying '{track_to_play_query}' (Attempt {retry_count + 1}/{MAX_RETRIES_PER_SONG}).", LogColors.YELLOW)
                await asyncio.sleep(2) 
                asyncio.create_task(self._play_next(interaction_context, error=e_play, retry_count=retry_count + 1))
            else:
                log(log_prefix + "MAX_RETRIES_REACHED", f"Max retries reached for '{track_to_play_query}'. Skipping.", LogColors.RED)
                if interaction_context and interaction_context.channel:
                    try: await interaction_context.channel.send(f"❌ Failed to play '{track_to_play_query[:70]}...' after multiple attempts. Skipping.")
                    except: pass
                asyncio.create_task(self._play_next(interaction_context, error=e_play, retry_count=0)) # Move to next song


async def setup(bot: commands.Bot):
    await bot.add_cog(PlaylistCommand(bot))

