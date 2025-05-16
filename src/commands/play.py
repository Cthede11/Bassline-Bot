import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, ButtonStyle, SelectOption, Object
from discord.ui import Button, View, Select
import asyncio
import time
import traceback 

from src.utils.discord_voice import join_voice_channel, play_song, search_youtube, LogColors, log
from src.utils.music import music_manager, LoopState

class PlayCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_search_views = {} 
        self.idle_check_task.start()

    def cog_unload(self):
        self.idle_check_task.cancel()
        for guild_id, view in self.active_search_views.items():
            if view: 
                view.stop() 
        self.active_search_views.clear()


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
        now_playing_info = music_manager.get_now_playing(guild_id)
        target_channel = None
        if isinstance(interaction_or_context, Interaction): target_channel = interaction_or_context.channel
        elif isinstance(interaction_or_context, discord.TextChannel): target_channel = interaction_or_context
        elif hasattr(interaction_or_context, 'channel') and isinstance(interaction_or_context.channel, discord.abc.Messageable): target_channel = interaction_or_context.channel
        
        if not target_channel: 
            guild = self.bot.get_guild(guild_id)
            if guild:
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages: 
                    target_channel = guild.system_channel
                else:
                    for tc in guild.text_channels:
                        if tc.permissions_for(guild.me).send_messages: 
                            target_channel = tc
                            break
        if not target_channel: 
            log("EMBED_SEND_ERROR", f"PlayCmd NowPlaying: Could not determine target channel for guild {guild_id}.", LogColors.RED)
            return
            
        if not now_playing_info:
            if isinstance(interaction_or_context, Interaction) and not from_play_next:
                message_content = "Nothing is currently playing."
                if is_followup: await interaction_or_context.followup.send(message_content, ephemeral=True)
                else: await interaction_or_context.response.send_message(message_content, ephemeral=True)
            return

        embed = Embed(title="🎶 Now Playing 🎶", color=discord.Color.random())
        embed.add_field(name="Title", value=f"[{now_playing_info['title']}]({now_playing_info.get('url', '#')})", inline=False)
        current_time = time.time()
        elapsed_time = current_time - now_playing_info.get("start_time", current_time)
        total_duration = now_playing_info.get("duration", 0)
        bar_length = 20
        progress = min(1.0, elapsed_time / total_duration) if total_duration and total_duration > 0 else 0
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '─' * (bar_length - filled_length)
        progress_str = f"`{self.format_duration(elapsed_time)} / {self.format_duration(total_duration)}`\n`{bar}`"
        embed.add_field(name="Progress", value=progress_str, inline=False)
        embed.add_field(name="Requested by", value=now_playing_info["requester"], inline=True)
        embed.add_field(name="Uploader", value=now_playing_info.get("uploader", "N/A"), inline=True)
        loop_state = music_manager.get_loop_state(guild_id)
        embed.add_field(name="Loop", value=f"```{loop_state.name.capitalize()}```", inline=True)
        if now_playing_info.get("thumbnail"): embed.set_thumbnail(url=now_playing_info["thumbnail"])
        embed.set_footer(text=f"BasslineBot | {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        try:
            if isinstance(interaction_or_context, Interaction):
                if from_play_next: await target_channel.send(embed=embed)
                elif is_followup: await interaction_or_context.followup.send(embed=embed)
                else: await interaction_or_context.response.send_message(embed=embed)
            else: await target_channel.send(embed=embed)
        except discord.errors.NotFound: 
            log("EMBED_SEND_ERROR", "PlayCmd NowPlaying: Interaction/Channel not found, attempting raw channel send.", LogColors.YELLOW)
            if target_channel: 
                try:
                    await target_channel.send(embed=embed)
                except Exception as e_raw_send:
                    log("EMBED_SEND_ERROR", f"PlayCmd NowPlaying: Raw channel send also failed - {e_raw_send}", LogColors.RED)
        except Exception as e: 
            log("EMBED_SEND_ERROR", f"PlayCmd NowPlaying: Error sending - {e}", LogColors.RED)
            traceback.print_exc()


    async def _play_next(self, interaction_context: Interaction, error=None, retry_count=0): 
        MAX_RETRIES_PER_SONG = 2 # Max times to retry a single failing song before skipping it
        log_prefix = f"[PLAY_CMD_PLAY_NEXT Guild: {interaction_context.guild.id}] "
        log(log_prefix + "INVOKED", f"Error from after_playback_hook: {error}, Retry count for current song: {retry_count}", LogColors.CYAN)

        # If the error is from the 'after' callback, it means the previous playback failed or ended.
        if error:
            log(log_prefix + "PREV_PLAYBACK_ERROR", f"Error passed from 'after' callback: {error}", LogColors.RED)
            # This error is from discord.py's player itself, not necessarily from our song fetching.

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

        # Determine the next song
        if current_loop_state == LoopState.SINGLE and song_that_just_finished and retry_count == 0:
            track_to_play_query = song_that_just_finished.get("query")
            requested_by_obj = song_that_just_finished.get("requested_by_obj")
            log(log_prefix + "LOOP_SINGLE", f"Replaying '{track_to_play_query}'", LogColors.BLUE)
        else:
            next_in_queue = music_manager.get_next(guild_id) # Pops from queue
            if next_in_queue and next_in_queue[0]:
                track_to_play_query, requested_by_obj = next_in_queue
                log(log_prefix + "NEXT_FROM_QUEUE", f"Got '{track_to_play_query}'", LogColors.BLUE)
                if current_loop_state == LoopState.QUEUE and song_that_just_finished:
                    # Re-add the song that just finished (or was skipped after retries)
                    if not error or retry_count >= MAX_RETRIES_PER_SONG : 
                        await music_manager.add_to_queue(guild_id, song_that_just_finished.get("query"), song_that_just_finished.get("requested_by_obj"))
                        log(log_prefix + "LOOP_QUEUE", f"Re-added '{song_that_just_finished.get('query')}' to end of queue.", LogColors.BLUE)
            elif current_loop_state == LoopState.QUEUE and song_that_just_finished: 
                 next_in_queue_after_readd = music_manager.get_next(guild_id)
                 if next_in_queue_after_readd and next_in_queue_after_readd[0]:
                     track_to_play_query, requested_by_obj = next_in_queue_after_readd
                     log(log_prefix + "LOOP_QUEUE_REPICK", f"Got '{track_to_play_query}' from queue after re-add.", LogColors.BLUE)
        
        if not track_to_play_query or not requested_by_obj:
            music_manager.now_playing.pop(guild_id, None) # Clear now_playing
            log(log_prefix + "QUEUE_EMPTY", "Queue is empty and no new song to loop. Playback stopped.", LogColors.BLUE)
            if interaction_context and interaction_context.channel:
                try: await interaction_context.channel.send("✅ Queue ended.")
                except discord.errors.NotFound: log(log_prefix + "QUEUE_ENDED_MSG_FAIL", "Channel not found for queue ended message.", LogColors.YELLOW)
            return

        log(log_prefix + "ATTEMPTING_PLAY", f"Attempting to play '{track_to_play_query}' (Requested by: {requested_by_obj.name}, Retry: {retry_count})", LogColors.CYAN)
        try:
            bass_boost = music_manager.get_bass_boost(requested_by_obj.id)
            # play_song can raise exceptions if fetching/processing fails
            song_details = await play_song(vc, track_to_play_query, return_source=True, bass_boost=bass_boost, download_first=True)
            
            if not song_details or "source" not in song_details:
                log(log_prefix + "PLAY_SONG_FAIL_NO_SOURCE", f"play_song did not return a valid source for '{track_to_play_query}'. Details: {song_details}", LogColors.RED)
                raise Exception("Song processing failed: No audio source found.") # This will be caught by the outer except

            actual_audio_source = song_details["source"]
            log(log_prefix + "SOURCE_OK", f"Audio source obtained for '{track_to_play_query}'", LogColors.GREEN)
            
            music_manager.set_now_playing(guild_id, {
                "title": song_details["title"], "duration": song_details["duration"],
                "thumbnail": song_details.get("thumbnail"), "query": track_to_play_query,
                "start_time": time.time(), "url": song_details.get("webpage_url"),
                "uploader": song_details.get("uploader")}, requested_by_obj)

            # Define the 'after' callback hook with proper logging
            def after_playback_hook(error_from_player):
                # This function is called by discord.py in a separate thread
                hook_log_prefix = f"[PlayCmd Guild: {guild_id}] AFTER_PLAYBACK_HOOK "
                if error_from_player:
                    log(hook_log_prefix + "ERROR", f"Playback error reported by player for '{track_to_play_query}': {error_from_player}", LogColors.RED)
                else:
                    log(hook_log_prefix + "SUCCESS", f"Playback finished for '{track_to_play_query}' (or was stopped).", LogColors.GREEN)
                
                # Schedule _play_next to run on the main event loop, resetting retry_count for the *next distinct* song
                asyncio.run_coroutine_threadsafe(
                    self._play_next(interaction_context, error=error_from_player, retry_count=0),
                    self.bot.loop
                )

            vc.play(actual_audio_source, after=after_playback_hook)
            log(log_prefix + "PLAYBACK_STARTED", f"vc.play() called for '{track_to_play_query}'. Sending NowPlaying embed.", LogColors.GREEN)
            await self.send_now_playing_embed(interaction_context.channel if interaction_context else None, guild_id, from_play_next=True)

        except Exception as e_play: # This catches errors from play_song or if song_details is invalid
            log(log_prefix + "PLAY_EXCEPTION", f"Failed to prepare or start playback for '{track_to_play_query}': {e_play}", LogColors.RED)
            traceback.print_exc() # Print the full traceback of the error from play_song
            
            if retry_count < MAX_RETRIES_PER_SONG:
                log(log_prefix + "RETRYING_SONG", f"Retrying '{track_to_play_query}' (Attempt {retry_count + 1}/{MAX_RETRIES_PER_SONG}).", LogColors.YELLOW)
                await asyncio.sleep(2) 
                asyncio.create_task(self._play_next(interaction_context, error=e_play, retry_count=retry_count + 1)) # Pass the error for context if needed
            else:
                log(log_prefix + "MAX_RETRIES_REACHED", f"Max retries reached for '{track_to_play_query}'. Error: {e_play}. Skipping.", LogColors.RED)
                if interaction_context and interaction_context.channel:
                    try: 
                        await interaction_context.channel.send(
                            f"❌ Failed to play '{track_to_play_query[:70]}...' after multiple attempts due to: `{str(e_play)[:100]}`. Skipping."
                        )
                    except Exception as e_msg_skip: 
                        log(log_prefix + "SKIP_MSG_FAIL", f"Failed to send skip message: {e_msg_skip}", LogColors.YELLOW)
                # Move to the *next different* song in the queue by calling _play_next with retry_count=0 and no error
                asyncio.create_task(self._play_next(interaction_context, error=None, retry_count=0))


    @app_commands.command(name="play", description="Play a song by name or URL.")
    async def play(self, interaction: Interaction, query: str):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        await interaction.response.defer()
        log_prefix = f"[PLAY_CMD Guild: {guild_id}] "

        vc = music_manager.voice_clients.get(guild_id)
        if not vc or not vc.is_connected():
            log(log_prefix + "JOINING_VC", "VC not connected, attempting to join.", LogColors.CYAN)
            vc = await join_voice_channel(interaction)
            if not vc: 
                log(log_prefix + "JOIN_VC_FAIL", "Failed to join VC for /play command.", LogColors.RED)
                return 
            music_manager.voice_clients[guild_id] = vc
        
        if music_manager.is_playing(guild_id) or music_manager.get_queue(guild_id):
            log(log_prefix + "ADDING_TO_QUEUE", f"Adding '{query}' to queue.", LogColors.CYAN)
            await music_manager.add_to_queue(guild_id, query, interaction.user)
            try:
                temp_results = await search_youtube(query, 1) 
                queued_title = temp_results[0]['title'] if temp_results else query
                await interaction.followup.send(f"✅ **{queued_title}** added to queue.")
            except Exception:
                 await interaction.followup.send(f"✅ '{query}' added to queue.")
            return

        log(log_prefix + "PLAYING_DIRECTLY", f"Attempting to play '{query}' directly.", LogColors.CYAN)
        try:
            bass_boost = music_manager.get_bass_boost(interaction.user.id)
            song_details = await play_song(vc, query, return_source=True, bass_boost=bass_boost, download_first=True)
            
            if not song_details or "source" not in song_details:
                log(log_prefix + "PLAY_SONG_FAIL", f"play_song returned invalid details for '{query}'.", LogColors.RED)
                raise Exception("Invalid details from play_song (source missing).")

            actual_audio_source = song_details["source"]
            log(log_prefix + "SOURCE_OK", f"Audio source obtained for '{query}'", LogColors.GREEN)
            
            music_manager.set_now_playing(guild_id, {
                    "title": song_details["title"], "duration": song_details["duration"],
                    "thumbnail": song_details.get("thumbnail"), "query": query,
                    "start_time": time.time(), "url": song_details.get("webpage_url"),
                    "uploader": song_details.get("uploader")},
                interaction.user)

            # Define the 'after' callback hook with proper logging for the initial play
            def after_initial_playback_hook(error_from_player):
                hook_log_prefix = f"[PlayCmd Guild: {guild_id}] AFTER_INITIAL_PLAY_HOOK "
                if error_from_player:
                    log(hook_log_prefix + "ERROR", f"Playback error for initial song '{query}': {error_from_player}", LogColors.RED)
                else:
                    log(hook_log_prefix + "SUCCESS", f"Initial playback finished for '{query}'.", LogColors.GREEN)
                
                asyncio.run_coroutine_threadsafe( 
                    self._play_next(interaction, error=error_from_player, retry_count=0), 
                    self.bot.loop
                )

            vc.play(actual_audio_source, after=after_initial_playback_hook)
            log(log_prefix + "PLAYBACK_STARTED", f"Playback started for '{query}'. Sending NowPlaying embed.", LogColors.GREEN)
            await self.send_now_playing_embed(interaction, guild_id, is_followup=True)

        except Exception as e:
            log(log_prefix + "PLAY_CMD_EXCEPTION", f"Error playing '{query}': {e}", LogColors.RED)
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error playing '{query[:100]}...': {str(e)[:1500]}")


    @app_commands.command(name="loop", description="Set the loop mode for playback.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value=LoopState.OFF.value),
        app_commands.Choice(name="Single Song", value=LoopState.SINGLE.value),
        app_commands.Choice(name="Entire Queue", value=LoopState.QUEUE.value),
    ])
    async def loop(self, interaction: Interaction, mode: app_commands.Choice[int]):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        new_state_enum = LoopState(mode.value)
        music_manager.set_loop_state(guild_id, new_state_enum)
        await interaction.response.send_message(f"🔁 Loop mode set to: **{mode.name}**")

    @app_commands.command(name="nowplaying", description="Shows details about the currently playing song.")
    async def nowplaying(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        await self.send_now_playing_embed(interaction, guild_id, is_followup=False)

    @app_commands.command(name="search", description="Search for a song on YouTube and select from results.")
    async def search(self, interaction: Interaction, query: str):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        await interaction.response.defer()

        results = await search_youtube(query, num_results=5) 
        if not results:
            await interaction.followup.send("🔎 No results found.")
            return

        music_manager.search_results[guild_id] = results
        embed = Embed(title=f"🔎 Search Results for \"{query}\"", color=discord.Color.orange())
        select_options = []
        description_lines = []

        for i, track in enumerate(results):
            description_lines.append(f"**{i+1}.** {track['title']} (`{track['duration_str']}`) - *{track.get('uploader', 'N/A')}*")
            select_options.append(SelectOption(label=f"{i+1}. {track['title'][:90]}...", value=str(i), description=f"Duration: {track['duration_str']}"))
        
        if not select_options:
             await interaction.followup.send("🔎 No selectable results found (all results might be invalid).")
             return

        embed.description = "\n".join(description_lines) if description_lines else "No results."
        embed.set_footer(text="Select a song using the dropdown below.")
        
        class SearchSelectView(View):
            def __init__(self, *, timeout=180.0, original_interaction: Interaction, cog_instance: 'PlayCommand'):
                super().__init__(timeout=timeout)
                self.original_interaction = original_interaction
                self.cog_instance = cog_instance

                select_menu = Select(placeholder="Choose a song to select...", options=select_options, custom_id=f"persistent_search_select_{original_interaction.id}")
                select_menu.callback = self.select_menu_callback
                self.add_item(select_menu)
                self.cog_instance.active_search_views[original_interaction.guild.id] = self


            async def select_menu_callback(self, select_interaction: Interaction):
                if select_interaction.user.id != self.original_interaction.user.id:
                    await select_interaction.response.send_message("You cannot make a selection for this search.", ephemeral=True)
                    return
                
                await select_interaction.response.defer(ephemeral=True) 

                selected_index_str = select_interaction.data['values'][0]
                selected_index = int(selected_index_str)
                guild_id = select_interaction.guild.id
                
                current_search_results = music_manager.search_results.get(guild_id)
                if not current_search_results or selected_index >= len(current_search_results):
                    await select_interaction.followup.send("Search results are no longer available or selection is invalid.", ephemeral=True)
                    await self.stop_and_disable_view(self.original_interaction)
                    return

                selected_track_info = current_search_results[selected_index]
                selected_track_query = selected_track_info["query_for_play"]
                selected_track_title = selected_track_info["title"]
                
                log("SEARCH_SELECT", f"User {select_interaction.user} selected '{selected_track_title}' from search.", LogColors.BLUE)
                music_manager.update_last_activity(guild_id)

                vc = music_manager.voice_clients.get(guild_id)
                if not vc or not vc.is_connected():
                    vc = await join_voice_channel(select_interaction) 
                    if not vc: 
                        await self.stop_and_disable_view(self.original_interaction)
                        return 
                    music_manager.voice_clients[guild_id] = vc

                if music_manager.is_playing(guild_id) or music_manager.get_queue(guild_id):
                    await music_manager.add_to_queue(guild_id, selected_track_query, select_interaction.user)
                    await select_interaction.followup.send(f"✅ **{selected_track_title}** added to queue.", ephemeral=False)
                else: 
                    try:
                        bass_boost = music_manager.get_bass_boost(select_interaction.user.id)
                        song_details = await play_song(vc, selected_track_query, return_source=True, bass_boost=bass_boost, download_first=True)
                        if not song_details or "source" not in song_details: 
                            raise Exception("Invalid details from play_song.")
                        source = song_details["source"]
                        music_manager.set_now_playing(guild_id, {
                            "title": song_details["title"], "duration": song_details["duration"], 
                            "thumbnail": song_details.get("thumbnail"), "query": selected_track_query, 
                            "start_time": time.time(), "url": song_details.get("webpage_url"), 
                            "uploader": song_details.get("uploader")}, select_interaction.user)
                        
                        # Define the 'after' callback hook specifically for search selection
                        def after_search_select_playback_hook(error_from_player):
                            hook_log_prefix = f"[PlayCmd Guild: {guild_id}] AFTER_SEARCH_SELECT_PLAY_HOOK "
                            if error_from_player:
                                log(hook_log_prefix + "ERROR", f"Playback error for search selected song '{selected_track_title}': {error_from_player}", LogColors.RED)
                            else:
                                log(hook_log_prefix + "SUCCESS", f"Search selected song playback finished for '{selected_track_title}'.", LogColors.GREEN)
                            
                            asyncio.run_coroutine_threadsafe(
                                self.cog_instance._play_next(select_interaction, error=error_from_player, retry_count=0), 
                                self.cog_instance.bot.loop
                            )

                        vc.play(source, after=after_search_select_playback_hook)
                        await self.cog_instance.send_now_playing_embed(select_interaction.channel, guild_id, from_play_next=True)
                    except Exception as e:
                        log("SEARCH_SELECT_PLAY_ERROR", f"Error playing '{selected_track_title}': {e}", LogColors.RED)
                        traceback.print_exc()
                        await select_interaction.followup.send(f"❌ Error playing **{selected_track_title}**: {str(e)[:1000]}", ephemeral=True)
                
                await self.stop_and_disable_view(self.original_interaction) 
                music_manager.search_results.pop(guild_id, None)

            async def on_timeout(self):
                log("SEARCH_VIEW", f"SearchSelectView for interaction {self.original_interaction.id} timed out.", LogColors.YELLOW)
                await self.stop_and_disable_view(self.original_interaction, timed_out=True)
                if self.original_interaction.guild_id in self.cog_instance.active_search_views: # Check before pop
                    self.cog_instance.active_search_views.pop(self.original_interaction.guild_id, None)


            async def stop_and_disable_view(self, original_interaction: Interaction, timed_out=False):
                self.stop() 
                for item in self.children:
                    if hasattr(item, 'disabled'):
                        item.disabled = True
                try:
                    message = await original_interaction.original_response()
                    content_update = "\n*(Search selection timed out.)*" if timed_out else "\n*(Selection made or search expired.)*"
                    await message.edit(content=message.content + content_update, view=self if not timed_out else None) 
                except discord.errors.NotFound: 
                    log("SEARCH_VIEW_EDIT_ERROR", "Original search message not found to disable/edit view.", LogColors.YELLOW)
                except Exception as e_edit: 
                    log("SEARCH_VIEW_EDIT_ERROR", f"Error disabling/editing search view: {e_edit}", LogColors.YELLOW)
        
        search_view_instance = SearchSelectView(original_interaction=interaction, cog_instance=self)
        await interaction.followup.send(embed=embed, view=search_view_instance)

    @app_commands.command(name="skip", description="Skips the currently playing song.")
    async def skip(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        vc = music_manager.voice_clients.get(guild_id)
        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message("Nothing is playing to skip.", ephemeral=True)
            return
        
        await interaction.response.send_message("⏭️ Skipping song...")
        vc.stop() 

    @app_commands.command(name="queue", description="Shows the current song queue.")
    async def queue(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        current_queue = music_manager.get_queue(guild_id)
        embed = Embed(title="🎶 Song Queue 🎶", color=discord.Color.purple())
        now_playing_info = music_manager.get_now_playing(guild_id)
        if now_playing_info: 
            duration_np = self.format_duration(now_playing_info.get('duration'))
            embed.add_field(name="Now Playing", value=f"**{now_playing_info['title']}** (`{duration_np}`)\n*Requested by: {now_playing_info['requester']}*", inline=False)
        else: embed.add_field(name="Now Playing", value="Nothing is playing.", inline=False)
        if not current_queue: embed.description = "The queue is currently empty."
        else:
            queue_text_lines = []
            for i, (track_query, user) in enumerate(current_queue[:15]): 
                queue_text_lines.append(f"{i+1}. `{track_query[:70].strip()}` (Requested by: {user.mention})")
            embed.add_field(name=f"Up Next - {len(current_queue)} song(s)", value="\n".join(queue_text_lines) if queue_text_lines else "Empty", inline=False)
            if len(current_queue) > 15: embed.set_footer(text=f"... and {len(current_queue) - 15} more.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pauses the current song.")
    async def pause(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        vc = music_manager.voice_clients.get(guild_id)
        if vc and vc.is_playing() and not vc.is_paused(): 
            music_manager.pause(guild_id)
            await interaction.response.send_message("⏸️ Paused.")
        elif vc and vc.is_paused():
             await interaction.response.send_message("Already paused.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing to pause.", ephemeral=True)

    @app_commands.command(name="resume", description="Resumes the current song.")
    async def resume(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        vc = music_manager.voice_clients.get(guild_id)
        if vc and vc.is_paused():
            music_manager.resume(guild_id)
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("No paused song to resume.", ephemeral=True)

    @app_commands.command(name="shuffle", description="Shuffles the current queue.")
    async def shuffle(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        if not music_manager.get_queue(guild_id):
            await interaction.response.send_message("Nothing in queue to shuffle.", ephemeral=True)
            return
        music_manager.shuffle_queue(guild_id)
        await interaction.response.send_message("🔀 Queue shuffled.")

    @app_commands.command(name="clear", description="Clears the current queue.")
    async def clear(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id)
        music_manager.clear_queue(guild_id)
        await interaction.response.send_message("🗑️ Queue cleared.")

    @app_commands.command(name="stop", description="Stops music, clears queue, and disconnects.")
    async def stop(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.update_last_activity(guild_id) 
        vc = music_manager.voice_clients.get(guild_id)
        if vc and vc.is_connected():
            if vc.is_playing() or vc.is_paused():
                vc.stop() 
            await vc.disconnect()
            log("STOP_CMD", f"Stopped by user and disconnected from '{interaction.guild.name}'.", LogColors.YELLOW)
        music_manager.clear_guild_state(guild_id) 
        await interaction.response.send_message("⏹️ Music stopped, queue cleared, and disconnected.")

    @app_commands.command(name="bassboost", description="Toggle bass boost for yourself.")
    async def bassboost(self, interaction: Interaction):
        guild_id = interaction.guild.id 
        music_manager.update_last_activity(guild_id)
        try:
            state = music_manager.toggle_bass_boost(interaction.user.id)
            emoji = "🔊" if state else "🔈"
            await interaction.response.send_message(
                f"{emoji} Bass Boost {'enabled' if state else 'disabled'} for {interaction.user.mention}"
            )
        except Exception as e:
            log("BASSBOOST_ERROR", f"Bass boost toggle failed: {e}", LogColors.RED)
            await interaction.response.send_message("❌ Failed to toggle bass boost.", ephemeral=True)

    @app_commands.command(name="clean", description="Deletes the bot's messages in the current channel.")
    @app_commands.describe(count="Number of messages to check for deletion (default 10, max 100).")
    @app_commands.checks.has_permissions(manage_messages=True) 
    async def clean(self, interaction: Interaction, count: app_commands.Range[int, 1, 100] = 10):
        await interaction.response.defer(ephemeral=True) 
        deleted_count = 0
        try:
            deleted_messages = await interaction.channel.purge(limit=count, check=lambda m: m.author == self.bot.user, bulk=True)
            deleted_count = len(deleted_messages)
            await interaction.followup.send(f"🧹 Deleted {deleted_count} bot message(s).", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages in this channel.", ephemeral=True)
        except Exception as e:
            log("CLEAN_CMD_ERROR", f"An error occurred while cleaning messages: {e}", LogColors.RED)
            traceback.print_exc()
            await interaction.followup.send(f"An error occurred while cleaning messages: {str(e)[:1000]}", ephemeral=True)

    @clean.error
    async def clean_command_error_handler(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You need the `Manage Messages` permission to use this command.", ephemeral=True)
        else:
            log("CLEAN_CMD_UNHANDLED_ERROR", f"Unexpected error in clean command: {error}", LogColors.RED)
            traceback.print_exc() 
            await interaction.response.send_message(f"An error occurred: {str(error)[:1000]}", ephemeral=True)

    @tasks.loop(minutes=1.0) 
    async def idle_check_task(self):
        current_time = time.time()
        idle_threshold_seconds = 300 
        for guild_id in list(music_manager.voice_clients.keys()): 
            vc = music_manager.voice_clients.get(guild_id)
            guild = self.bot.get_guild(guild_id)
            if not guild: 
                log("IDLE_CHECK", f"Guild {guild_id} not found during idle check. Clearing state.", LogColors.YELLOW)
                music_manager.clear_guild_state(guild_id)
                continue
            if vc and vc.is_connected():
                if vc.is_playing() or vc.is_paused():
                    music_manager.update_last_activity(guild_id)
                    continue 
                actual_members_in_channel = [m for m in vc.channel.members if not m.bot]
                reason_to_leave = None
                if not actual_members_in_channel:
                    reason_to_leave = "I was alone in the voice channel."
                else: 
                    last_activity_time = music_manager.get_last_activity(guild_id)
                    if last_activity_time and (current_time - last_activity_time > idle_threshold_seconds):
                        reason_to_leave = f"after {idle_threshold_seconds // 60} minutes of inactivity."
                if reason_to_leave:
                    log("IDLE_CHECK", f"Leaving guild {guild_id} ({guild.name}). Reason: {reason_to_leave}", LogColors.YELLOW)
                    text_channel_to_notify = None
                    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                        text_channel_to_notify = guild.system_channel
                    else: 
                        for tc_obj in guild.text_channels: 
                            if tc_obj.permissions_for(guild.me).send_messages:
                                text_channel_to_notify = tc_obj
                                break
                    if text_channel_to_notify:
                        try: await text_channel_to_notify.send(f"👋 Disconnecting from {vc.channel.mention}. Reason: {reason_to_leave}")
                        except Exception as e_msg: log("IDLE_MSG_ERROR", f"Failed to send idle leave message to {text_channel_to_notify.name}: {e_msg}", LogColors.YELLOW)
                    await vc.disconnect() 
                    music_manager.clear_guild_state(guild_id) 
            elif guild_id in music_manager.voice_clients: 
                log("IDLE_CHECK_CLEANUP", f"Cleaning up stale VC entry for guild {guild_id}.", LogColors.YELLOW)
                music_manager.clear_guild_state(guild_id)

    @idle_check_task.before_loop
    async def before_idle_check_task(self):
        await self.bot.wait_until_ready()
        log("TASK_START", "Idle check task is now running.", LogColors.GREEN)

async def setup(bot: commands.Bot):
    await bot.add_cog(PlayCommand(bot))
