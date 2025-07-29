import asyncio
import logging
import time
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import os

from src.core.music_manager import music_manager, Track, LoopState
from src.core.database_manager import db_manager
from src.utils.checks import is_dj_or_admin_slash, is_in_voice
from src.utils.discord_voice import join_voice_channel, create_audio_source
from src.utils.youtube import youtube_manager, YouTubeError
from src.utils.validators import validate_search_query, validate_volume
from src.utils.helpers import format_duration, Timer, ProgressBar
from config.settings import settings

logger = logging.getLogger(__name__)

class MusicCommands(commands.Cog):
    """Music playback commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_players = {}
    
    async def cog_load(self):
        """Called when cog is loaded."""
        logger.info("Music commands loaded")
    
    @app_commands.command(name="play", description="Play a song from YouTube")
    @app_commands.describe(query="Song name or YouTube URL")
    async def play(self, interaction: discord.Interaction, query: str):
        """Enhanced play command with database integration."""
        timer = Timer().start()
        
        try:
            # Validate input
            is_valid, error_msg = validate_search_query(query)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            guild_id = interaction.guild.id
            user = interaction.user
            
            # Ensure user is in voice channel
            if not user.voice or not user.voice.channel:
                await interaction.followup.send("❌ You must be in a voice channel to play music.", ephemeral=True)
                return
            
            # Join voice channel if needed
            vc = await join_voice_channel(interaction, user.voice.channel)
            if not vc:
                return
            
            music_manager.voice_clients[guild_id] = vc
            
            # Get video information with database integration
            try:
                video_info = await youtube_manager.get_info(query, download=settings.download_enabled)
            except YouTubeError as e:
                await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
                return
            
            # Create track object with enhanced info
            track = Track(
                query=query,
                title=video_info['title'],
                url=video_info['url'],
                duration=video_info['duration'],
                thumbnail=video_info['thumbnail'],
                uploader=video_info['uploader'],
                requested_by=user
            )
            
            # Add local path info if available
            if video_info.get('local_path'):
                track.local_path = video_info['local_path']
                track.file_size = video_info.get('file_size')
            
            # Check if currently playing
            if music_manager.is_playing(guild_id):
                # Add to queue
                success = await music_manager.add_to_queue(guild_id, track)
                if success:
                    # Create enhanced embed with download status
                    embed = discord.Embed(
                        title="✅ Added to Queue",
                        description=f"**{track.title}**\nDuration: {format_duration(track.duration)}",
                        color=discord.Color.green()
                    )
                    
                    # Show download status
                    if video_info.get('local_path'):
                        embed.add_field(
                            name="📁 File Status", 
                            value="Downloaded (faster playback)", 
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🌐 File Status", 
                            value="Streaming", 
                            inline=True
                        )
                    
                    embed.set_footer(text=f"Position in queue: {len(music_manager.get_queue(guild_id))}")
                    
                    if track.thumbnail:
                        embed.set_thumbnail(url=track.thumbnail)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Queue is full. Please wait for some songs to finish.", ephemeral=True)
            else:
                # Add to queue first, then start playing
                success = await music_manager.add_to_queue(guild_id, track)
                if success:
                    # Get the track we just added and start playing
                    first_track = music_manager.pop_next_track(guild_id)
                    if first_track:
                        await self._play_track(interaction, vc, first_track, video_info)
                else:
                    await interaction.followup.send("❌ Queue is full.", ephemeral=True)
            
            # Log usage
            timer.stop()
            with db_manager:
                db_manager.log_command_usage(
                    guild_id=guild_id,
                    user_id=user.id,
                    command_name="play",
                    execution_time=timer.elapsed(),
                    success=True
                )
        
        except Exception as e:
            logger.error(f"Error in play command: {e}", exc_info=True)
            timer.stop()
            
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ An error occurred while processing your request.", ephemeral=True)
            except:
                pass
            
            # Log failed usage
            with db_manager:
                db_manager.log_command_usage(
                    guild_id=interaction.guild.id,
                    user_id=interaction.user.id,
                    command_name="play",
                    execution_time=timer.elapsed(),
                    success=False,
                    error_message=str(e)
                )
    
    async def _play_track(self, interaction: discord.Interaction, voice_client: discord.VoiceClient, track: Track, video_info: dict):
        """Enhanced track playing with database integration."""
        try:
            # Get user preferences
            bass_boost = music_manager.get_bass_boost(track.requested_by.id)
            volume = music_manager.get_user_volume(track.requested_by.id)
            
            # Create audio source with enhanced info
            audio_source = await self._create_audio_source(track, video_info, bass_boost, volume)
            
            # Set now playing
            music_manager.set_now_playing(interaction.guild.id, track, voice_client)
            
            # Play audio with enhanced callback
            voice_client.play(audio_source, after=lambda e: self._handle_playback_finished(interaction.guild.id, track, e))
            
            # Send enhanced now playing embed
            await self._send_now_playing_embed(interaction, track, video_info)
            
            # Record play in database if song exists
            try:
                existing_song = db_manager.get_song_by_url(track.url)
                if existing_song:
                    db_manager.record_song_play(existing_song.id)
            except Exception as db_error:
                logger.error(f"Error recording song play: {db_error}")
            
            logger.info(f"Started playing: {track.title} in guild {interaction.guild.id}")
        
        except Exception as e:
            logger.error(f"Error playing track: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error playing track: {str(e)}", ephemeral=True)
    
    def _handle_playback_finished(self, guild_id: int, track: Track, error):
        """Enhanced playback finished handler with database integration."""
        if error:
            logger.error(f"Playback error in guild {guild_id}: {error}")
        
        # Record successful play completion in database
        try:
            existing_song = db_manager.get_song_by_url(track.url)
            if existing_song and not error:
                db_manager.record_song_play(existing_song.id)
        except Exception as db_error:
            logger.error(f"Error recording completed play: {db_error}")
        
        # Schedule next track using thread-safe method
        asyncio.run_coroutine_threadsafe(
            self._play_next(guild_id), 
            self.bot.loop
        )

    async def _create_audio_source(self, track: Track, video_info: dict, bass_boost: bool = False, volume: float = 0.5) -> discord.AudioSource:
        """Create audio source with priority for downloaded files."""
        try:
            # FFmpeg options
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': f'-vn -filter:a "volume={volume}"'
            }
            
            # Add bass boost if enabled
            if bass_boost:
                bass_filter = 'bass=g=4:f=70:w=0.4,equalizer=f=125:t=q:w=1:g=2'
                ffmpeg_options['options'] += f' -af "{bass_filter}"'
            
            # Priority order: downloaded file > stream URL
            source_url = None
            
            # 1. Check for downloaded file in video_info
            if video_info.get('downloaded_file') and os.path.exists(video_info['downloaded_file']):
                source_url = video_info['downloaded_file']
                logger.debug(f"Using downloaded file: {source_url}")
            
            # 2. Check database for existing download
            elif track.url:
                existing_path = db_manager.get_downloaded_song_path(track.url)
                if existing_path:
                    source_url = existing_path
                    logger.debug(f"Using database cached file: {source_url}")
            
            # 3. Fall back to streaming
            if not source_url:
                source_url = video_info.get('stream_url')
                logger.debug(f"Using stream URL: {source_url[:50]}...")
            
            if not source_url:
                raise YouTubeError("No audio source available")
            
            # Create audio source
            audio_source = discord.FFmpegPCMAudio(source_url, **ffmpeg_options)
            
            logger.debug(f"Created audio source for: {track.title}")
            return audio_source
            
        except Exception as e:
            logger.error(f"Error creating enhanced audio source: {e}")
            raise YouTubeError(f"Failed to create audio source: {str(e)}")
    
    async def _play_next(self, guild_id: int):
        """Play the next track in queue."""
        try:
            loop_state = music_manager.get_loop_state(guild_id)
            now_playing = music_manager.get_now_playing(guild_id)
            
            next_track = None
            
            # Handle loop modes
            if loop_state == LoopState.SINGLE and now_playing:
                # For single loop, replay the same track without removing from queue
                next_track = now_playing.track
            elif loop_state == LoopState.QUEUE and now_playing:
                # For queue loop, move current track to end of queue
                await music_manager.add_to_queue(guild_id, now_playing.track)
                next_track = music_manager.pop_next_track(guild_id)  # FIXED: Use pop_next_track
            else:
                # Normal mode: get next track and remove from queue
                next_track = music_manager.pop_next_track(guild_id)  # FIXED: Use pop_next_track
            
            if next_track:
                vc = music_manager.voice_clients.get(guild_id)
                if vc and vc.is_connected():
                    # Get a text channel to send the now playing message
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        channel = None
                        if guild.system_channel:
                            channel = guild.system_channel
                        else:
                            channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
                        
                        if channel:
                            bass_boost = music_manager.get_bass_boost(next_track.requested_by.id)
                            volume = music_manager.get_user_volume(next_track.requested_by.id)
                            
                            audio_source = await create_audio_source(next_track, bass_boost=bass_boost, volume=volume)
                            music_manager.set_now_playing(guild_id, next_track, vc)
                            
                            vc.play(audio_source, after=lambda e: self._handle_playback_finished(guild_id, e))
                            
                            # Send now playing message
                            embed = self._create_now_playing_embed(next_track)
                            await channel.send(embed=embed)
            else:
                # Queue is empty - clear now playing
                music_manager.now_playing.pop(guild_id, None)
                logger.info(f"Queue finished in guild {guild_id}")
                
                # Send queue finished message
                guild = self.bot.get_guild(guild_id)
                if guild and guild.system_channel:
                    embed = discord.Embed(
                        title="🎵 Queue Finished",
                        description="All songs have been played!",
                        color=discord.Color.blue()
                    )
                    await guild.system_channel.send(embed=embed)
    
        except Exception as e:
            logger.error(f"Error in _play_next: {e}", exc_info=True)
    
    async def _send_now_playing_embed(self, interaction: discord.Interaction, track: Track, video_info: dict):
        """Send enhanced now playing embed with download status."""
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Duration", value=format_duration(track.duration), inline=True)
        embed.add_field(name="Requested by", value=track.requested_by.mention, inline=True)
        embed.add_field(name="Uploader", value=track.uploader, inline=True)
        
        # Show file status
        if video_info.get('downloaded_file') or video_info.get('local_path'):
            file_size_mb = round((video_info.get('file_size', 0)) / (1024 * 1024), 2)
            embed.add_field(
                name="📁 File Status", 
                value=f"Downloaded ({file_size_mb} MB)", 
                inline=True
            )
        else:
            embed.add_field(
                name="🌐 File Status", 
                value="Streaming", 
                inline=True
            )
        
        # Show play count if available
        try:
            existing_song = db_manager.get_song_by_url(track.url)
            if existing_song and existing_song.play_count > 0:
                embed.add_field(
                    name="🔄 Play Count", 
                    value=f"{existing_song.play_count} times", 
                    inline=True
                )
        except Exception:
            pass
        
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        embed.set_footer(text=f"Added {format_duration(int(time.time() - track.added_at))} ago")
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)
    
    def _create_now_playing_embed(self, track: Track) -> discord.Embed:
        """Create now playing embed."""
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Duration", value=format_duration(track.duration), inline=True)
        embed.add_field(name="Requested by", value=track.requested_by.mention, inline=True)
        embed.add_field(name="Uploader", value=track.uploader, inline=True)
        
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        embed.set_footer(text=f"Added {format_duration(int(time.time() - track.added_at))} ago")
        
        return embed
    
    @app_commands.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current queue."""
        guild_id = interaction.guild.id
        queue = music_manager.get_queue(guild_id)
        now_playing = music_manager.get_now_playing(guild_id)
        
        embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.purple())
        
        # Now playing section
        if now_playing:
            embed.add_field(
                name="🎶 Now Playing",
                value=f"**{now_playing.track.title}**\nRequested by {now_playing.track.requested_by.mention}",
                inline=False
            )
        else:
            embed.add_field(name="🎶 Now Playing", value="Nothing is playing", inline=False)
        
        # Queue section
        if queue:
            queue_text = []
            total_duration = 0
            
            for i, track in enumerate(queue[:10], 1):  # Show first 10 tracks
                duration_str = format_duration(track.duration)
                queue_text.append(f"`{i}.` **{track.title[:50]}{'...' if len(track.title) > 50 else ''}** ({duration_str})")
                if track.duration:
                    total_duration += track.duration
            
            embed.add_field(
                name=f"📝 Up Next ({len(queue)} songs)",
                value="\n".join(queue_text) if queue_text else "Queue is empty",
                inline=False
            )
            
            if len(queue) > 10:
                embed.add_field(
                    name="➕ More",
                    value=f"... and {len(queue) - 10} more songs",
                    inline=False
                )
            
            embed.add_field(
                name="⏱️ Total Duration",
                value=format_duration(total_duration),
                inline=True
            )
        else:
            embed.add_field(name="📝 Queue", value="Queue is empty", inline=False)
        
        # Loop state
        loop_state = music_manager.get_loop_state(guild_id)
        embed.add_field(name="🔁 Loop", value=loop_state.name.title(), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="skip", description="Skip the current song")
    @is_dj_or_admin_slash()
    async def skip(self, interaction: discord.Interaction):
        """Skip the current song."""
        guild_id = interaction.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
            return
        
        now_playing = music_manager.get_now_playing(guild_id)
        if now_playing:
            vc.stop()  # This will trigger the after callback
            await interaction.response.send_message(f"⏭️ Skipped **{now_playing.track.title}**")
        else:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
    
    @app_commands.command(name="pause", description="Pause the current song")
    @is_dj_or_admin_slash()
    async def pause(self, interaction: discord.Interaction):
        """Pause the current song."""
        guild_id = interaction.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
            return
        
        vc.pause()
        await interaction.response.send_message("⏸️ Paused playback.")
    
    @app_commands.command(name="resume", description="Resume the current song")
    @is_dj_or_admin_slash()
    async def resume(self, interaction: discord.Interaction):
        """Resume the current song."""
        guild_id = interaction.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        
        if not vc or not vc.is_paused():
            await interaction.response.send_message("❌ Nothing is currently paused.", ephemeral=True)
            return
        
        vc.resume()
        await interaction.response.send_message("▶️ Resumed playback.")
    
    @app_commands.command(name="stop", description="Stop music and clear the queue")
    @is_dj_or_admin_slash()
    async def stop(self, interaction: discord.Interaction):
        """Stop music and clear queue."""
        guild_id = interaction.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        
        if vc:
            vc.stop()
        
        music_manager.clear_queue(guild_id)
        music_manager.now_playing.pop(guild_id, None)
        
        await interaction.response.send_message("🛑 Stopped music and cleared the queue.")
    
    @app_commands.command(name="loop", description="Set loop mode")
    @app_commands.describe(mode="Loop mode to set")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value=0),
        app_commands.Choice(name="Single Song", value=1),
        app_commands.Choice(name="Queue", value=2),
    ])
    @is_dj_or_admin_slash()
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[int]):
        """Set loop mode."""
        guild_id = interaction.guild.id
        loop_state = LoopState(mode.value)
        
        music_manager.set_loop_state(guild_id, loop_state)
        
        await interaction.response.send_message(f"🔁 Loop mode set to: **{mode.name}**")
    
    @app_commands.command(name="shuffle", description="Shuffle the current queue")
    @is_dj_or_admin_slash()
    async def shuffle(self, interaction: discord.Interaction):
        """Shuffle the queue."""
        guild_id = interaction.guild.id
        queue = music_manager.get_queue(guild_id)
        
        if not queue:
            await interaction.response.send_message("❌ Queue is empty.", ephemeral=True)
            return
        
        music_manager.shuffle_queue(guild_id)
        await interaction.response.send_message(f"🔀 Shuffled {len(queue)} songs in the queue.")
    
    @app_commands.command(name="clear", description="Clear the music queue")
    @is_dj_or_admin_slash()
    async def clear(self, interaction: discord.Interaction):
        """Clear the queue."""
        guild_id = interaction.guild.id
        queue_length = len(music_manager.get_queue(guild_id))
        
        music_manager.clear_queue(guild_id)
        
        if queue_length > 0:
            await interaction.response.send_message(f"🗑️ Cleared {queue_length} songs from the queue.")
        else:
            await interaction.response.send_message("❌ Queue is already empty.", ephemeral=True)
    
    @app_commands.command(name="nowplaying", description="Show current song info")
    async def nowplaying(self, interaction: discord.Interaction):
        """Show current song information."""
        guild_id = interaction.guild.id
        now_playing = music_manager.get_now_playing(guild_id)
        
        if not now_playing:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
            return
        
        track = now_playing.track
        elapsed = time.time() - now_playing.start_time
        
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.blue()
        )
        
        # Progress bar
        if track.duration:
            progress = min(elapsed / track.duration, 1.0)
            progress_bar = ProgressBar.create(int(elapsed), track.duration, length=25)
            embed.add_field(
                name="Progress",
                value=f"{format_duration(int(elapsed))} / {format_duration(track.duration)}\n{progress_bar}",
                inline=False
            )
        
        embed.add_field(name="Requested by", value=track.requested_by.mention, inline=True)
        embed.add_field(name="Uploader", value=track.uploader, inline=True)
        
        loop_state = music_manager.get_loop_state(guild_id)
        embed.add_field(name="Loop", value=loop_state.name.title(), inline=True)
        
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        embed.set_footer(text=f"Started {format_duration(int(elapsed))} ago")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="bassboost", description="Toggle bass boost for yourself")
    async def bassboost(self, interaction: discord.Interaction):
        """Toggle bass boost."""
        user_id = interaction.user.id
        new_state = music_manager.toggle_bass_boost(user_id)
        
        emoji = "🔊" if new_state else "🔈"
        state_text = "enabled" if new_state else "disabled"
        
        await interaction.response.send_message(f"{emoji} Bass boost {state_text} for {interaction.user.mention}")
    
    @app_commands.command(name="volume", description="Set your personal volume")
    @app_commands.describe(level="Volume level (0.0 to 1.0)")
    async def volume(self, interaction: discord.Interaction, level: float):
        """Set personal volume."""
        is_valid, error_msg = validate_volume(level)
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        user_id = interaction.user.id
        music_manager.set_user_volume(user_id, level)
        
        percentage = int(level * 100)
        await interaction.response.send_message(f"🔊 Volume set to {percentage}% for {interaction.user.mention}")

    @app_commands.command(name="storage", description="Show download storage statistics")
    @app_commands.describe()
    async def storage_stats(self, interaction: discord.Interaction):
        """Show storage and download statistics."""
        try:
            await interaction.response.defer()
            
            # Get storage information
            storage_info = youtube_manager.get_storage_info()
            
            embed = discord.Embed(
                title="📊 Storage Statistics",
                color=discord.Color.blue()
            )
            
            # Database stats
            embed.add_field(
                name="🗄️ Database", 
                value=f"Downloaded: {storage_info.get('total_downloaded', 0)} songs\n"
                    f"Size: {storage_info.get('total_size_mb', 0):.1f} MB",
                inline=True
            )
            
            # Filesystem stats
            embed.add_field(
                name="💾 Filesystem", 
                value=f"Files: {storage_info.get('filesystem_files', 0)}\n"
                    f"Size: {storage_info.get('filesystem_size_mb', 0):.1f} MB",
                inline=True
            )
            
            # Status
            missing_files = storage_info.get('missing_files', 0)
            if missing_files > 0:
                embed.add_field(
                    name="⚠️ Status", 
                    value=f"{missing_files} files missing\n(Run cleanup to fix)",
                    inline=True
                )
            else:
                embed.add_field(
                    name="✅ Status", 
                    value="All files synced",
                    inline=True
                )
            
            embed.add_field(
                name="📁 Directory", 
                value=f"`{storage_info.get('downloads_directory', 'downloads/')}`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in storage stats command: {e}")
            await interaction.followup.send("❌ Error retrieving storage statistics.", ephemeral=True)

    @app_commands.command(name="cleandownloads", description="Clean up old downloads and sync database")
    @is_dj_or_admin_slash()
    async def cleanup_downloads(self, interaction: discord.Interaction):
        """Clean up old downloads and sync database."""
        try:
            await interaction.response.defer()
            
            # Perform cleanup
            youtube_manager.cleanup_old_downloads(max_age_hours=24)
            
            # Get updated stats
            storage_info = youtube_manager.get_storage_info()
            
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Results", 
                value=f"Files: {storage_info.get('filesystem_files', 0)}\n"
                    f"Size: {storage_info.get('filesystem_size_mb', 0):.1f} MB\n"
                    f"Missing: {storage_info.get('missing_files', 0)}",
                inline=True
            )
            
            embed.set_footer(text="Old downloads removed and database synced")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in cleanup command: {e}")
            await interaction.followup.send("❌ Error during cleanup.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))