import asyncio
import logging
import re
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from src.core.music_manager import music_manager, Track
from src.core.database_manager import db_manager
from src.utils.checks import is_dj_or_admin_slash
from src.utils.discord_voice import join_voice_channel, create_audio_source
from src.utils.youtube import youtube_manager, YouTubeError
from src.utils.validators import validate_playlist_name
from src.utils.helpers import format_duration, chunks
from config.settings import settings

logger = logging.getLogger(__name__)

class PlaylistCommands(commands.Cog):
    """Playlist management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.playlist_category_name = "🎵 Custom Playlists"
    
    async def cog_load(self):
        """Called when cog is loaded."""
        logger.info("Playlist commands loaded")
    
    @app_commands.command(name="setupplaylists", description="Create playlist category (Admin only)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_playlists(self, interaction: discord.Interaction):
        """Set up playlist category."""
        try:
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name=self.playlist_category_name)
            
            if category:
                embed = discord.Embed(
                    title="✅ Playlist Category Exists",
                    description=f"Category '{self.playlist_category_name}' already exists",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Channel Count",
                    value=f"{len(category.text_channels)} playlist channels",
                    inline=True
                )
            else:
                category = await guild.create_category(self.playlist_category_name)
                embed = discord.Embed(
                    title="✅ Playlist Category Created",
                    description=f"Created category '{category.name}'",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Next Steps",
                    value="Use `/createplaylist` to create playlist channels",
                    inline=False
                )
                logger.info(f"Created playlist category in guild {guild.id}")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create categories.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting up playlists: {e}")
            await interaction.response.send_message("❌ Failed to set up playlist category.", ephemeral=True)
    
    @app_commands.command(name="createplaylist", description="Create a new playlist channel")
    @app_commands.describe(name="Name for the new playlist")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_playlist(self, interaction: discord.Interaction, name: str):
        """Create a new playlist channel."""
        try:
            # Validate playlist name
            is_valid, error_msg = validate_playlist_name(name)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return
            
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name=self.playlist_category_name)
            
            if not category:
                await interaction.response.send_message(
                    "⚠️ Playlist category not found. Run `/setupplaylists` first.",
                    ephemeral=True
                )
                return
            
            # Create channel-safe name
            channel_name = re.sub(r"[^a-z0-9_.-]", "", name.lower().replace(" ", "-"))
            if not channel_name:
                await interaction.response.send_message("⚠️ Invalid playlist name for channel creation.", ephemeral=True)
                return
            
            # Check if channel already exists
            existing_channel = discord.utils.get(category.text_channels, name=channel_name)
            if existing_channel:
                await interaction.response.send_message(
                    f"⚠️ A playlist channel named `{channel_name}` already exists.",
                    ephemeral=True
                )
                return
            
            # Create channel and database entry
            await interaction.response.defer()
            
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                topic=f"Custom Playlist: {name}"
            )
            
            # Create database entry
            with db_manager:
                playlist = db_manager.create_playlist(
                    name=name,
                    guild_id=guild.id,
                    owner_id=interaction.user.id,
                    channel_id=channel.id
                )
            
            # Send intro message to playlist channel
            intro_embed = discord.Embed(
                title=f"🎶 Playlist: {name}",
                description="Welcome to your new playlist!",
                color=discord.Color.blue()
            )
            intro_embed.add_field(
                name="How to add songs",
                value="Type song titles or YouTube URLs below, one per message",
                inline=False
            )
            intro_embed.add_field(
                name="How to play",
                value=f"Use `/playlist {name}` or `/playlist #{channel.name}`",
                inline=False
            )
            intro_embed.set_footer(text=f"Created by {interaction.user.display_name}")
            
            await channel.send(embed=intro_embed)
            
            # Response to user
            response_embed = discord.Embed(
                title="✅ Playlist Created",
                description=f"Created playlist **{name}**",
                color=discord.Color.green()
            )
            response_embed.add_field(
                name="Channel",
                value=channel.mention,
                inline=True
            )
            response_embed.add_field(
                name="How to Use",
                value=f"Add songs in {channel.mention}, then use `/playlist {name}` to play",
                inline=False
            )
            
            await interaction.followup.send(embed=response_embed)
            logger.info(f"Created playlist '{name}' in guild {guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to create channels.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            await interaction.followup.send("❌ Failed to create playlist.", ephemeral=True)
    
    @app_commands.command(name="playlist", description="Play songs from a playlist")
    @app_commands.describe(name="Name of the playlist or #channel-mention")
    async def play_playlist(self, interaction: discord.Interaction, name: str):
        """Play a playlist."""
        try:
            await interaction.response.defer()
            
            guild = interaction.guild
            user = interaction.user
            
            # Ensure user is in voice channel
            if not user.voice or not user.voice.channel:
                await interaction.followup.send("❌ You must be in a voice channel to play a playlist.", ephemeral=True)
                return
            
            # Find playlist channel
            playlist_channel = None
            
            # Check if it's a channel mention
            match = re.match(r"<#(\d+)>", name.strip())
            if match:
                channel_id = int(match.group(1))
                playlist_channel = guild.get_channel(channel_id)
                if not isinstance(playlist_channel, discord.TextChannel):
                    await interaction.followup.send("⚠️ Mentioned channel is not a text channel.", ephemeral=True)
                    return
            else:
                # Search by name in database
                with db_manager:
                    playlist = db_manager.get_playlist_by_name(guild.id, name)
                
                if playlist and playlist.channel_id:
                    playlist_channel = guild.get_channel(playlist.channel_id)
                
                # Fallback: search in playlist category
                if not playlist_channel:
                    category = discord.utils.get(guild.categories, name=self.playlist_category_name)
                    if category:
                        normalized_name = re.sub(r"[^a-z0-9_.-]", "", name.lower().replace(" ", "-"))
                        for channel in category.text_channels:
                            if channel.name == normalized_name or (channel.topic and name in channel.topic):
                                playlist_channel = channel
                                break
            
            if not playlist_channel:
                await interaction.followup.send(f"⚠️ Playlist '{name}' not found.", ephemeral=True)
                return
            
            # Read songs from channel
            songs = []
            try:
                async for message in playlist_channel.history(limit=settings.max_playlist_size, oldest_first=True):
                    if (not message.author.bot and 
                        message.content and 
                        not message.content.startswith(('/', '!', '#', '<@', '<#'))):
                        songs.append(message.content.strip())
                
            except discord.Forbidden:
                await interaction.followup.send(f"❌ No permission to read {playlist_channel.mention}.", ephemeral=True)
                return
            
            if not songs:
                await interaction.followup.send(f"⚠️ No songs found in playlist {playlist_channel.mention}.", ephemeral=True)
                return
            
            # Join voice channel
            vc = await join_voice_channel(interaction, user.voice.channel)
            if not vc:
                return
            
            music_manager.voice_clients[guild.id] = vc
            
            # Process and queue songs
            successful_adds = 0
            failed_adds = 0
            
            for song_query in songs:
                try:
                    # Get video info
                    video_info = await youtube_manager.get_info(song_query, download=False)
                    
                    # Create track
                    track = Track(
                        query=song_query,
                        title=video_info['title'],
                        url=video_info['url'],
                        duration=video_info['duration'],
                        thumbnail=video_info['thumbnail'],
                        uploader=video_info['uploader'],
                        requested_by=user
                    )
                    
                    # Add to queue
                    success = await music_manager.add_to_queue(guild.id, track)
                    if success:
                        successful_adds += 1
                    else:
                        failed_adds += 1
                        break  # Queue is full
                
                except YouTubeError:
                    failed_adds += 1
                except Exception as e:
                    logger.error(f"Error processing song '{song_query}': {e}")
                    failed_adds += 1
            
            # Update playlist play count
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild.id, playlist_channel.name)
                if playlist:
                    # Increment play count logic would go here
                    pass
            
            # Send response
            embed = discord.Embed(
                title="✅ Playlist Loaded",
                description=f"Loaded playlist from {playlist_channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Songs Added",
                value=f"{successful_adds} songs",
                inline=True
            )
            
            if failed_adds > 0:
                embed.add_field(
                    name="Failed",
                    value=f"{failed_adds} songs",
                    inline=True
                )
                embed.color = discord.Color.orange()
            
            await interaction.followup.send(embed=embed)
            
            # Start playing if nothing is currently playing
            if not music_manager.is_playing(guild.id):
                await self._start_playlist_playback(guild.id, vc)
            
        except Exception as e:
            logger.error(f"Error in play_playlist: {e}")
            await interaction.followup.send("❌ An error occurred while loading the playlist.", ephemeral=True)
    
    async def _start_playlist_playback(self, guild_id: int, voice_client: discord.VoiceClient):
        """Start playing the first track in queue."""
        try:
            track = music_manager.get_next_track(guild_id)
            if not track:
                return
            
            # Get user preferences
            bass_boost = music_manager.get_bass_boost(track.requested_by.id)
            volume = music_manager.get_user_volume(track.requested_by.id)
            
            # Create audio source
            audio_source = await create_audio_source(track, bass_boost=bass_boost, volume=volume)
            
            # Set now playing and start playback
            music_manager.set_now_playing(guild_id, track, voice_client)
            
            def after_callback(error):
                if error:
                    logger.error(f"Playback error in guild {guild_id}: {error}")
                # Schedule next track
                asyncio.create_task(self._play_next_from_playlist(guild_id))
            
            voice_client.play(audio_source, after=after_callback)
            
            # Send now playing message
            guild = self.bot.get_guild(guild_id)
            if guild and guild.system_channel:
                embed = discord.Embed(
                    title="🎶 Now Playing from Playlist",
                    description=f"**{track.title}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Duration", value=format_duration(track.duration), inline=True)
                embed.add_field(name="Requested by", value=track.requested_by.mention, inline=True)
                
                if track.thumbnail:
                    embed.set_thumbnail(url=track.thumbnail)
                
                await guild.system_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error starting playlist playback: {e}")
    
    async def _play_next_from_playlist(self, guild_id: int):
        """Play next track from playlist queue."""
        try:
            track = music_manager.get_next_track(guild_id)
            if not track:
                return
            
            vc = music_manager.voice_clients.get(guild_id)
            if not vc or not vc.is_connected():
                return
            
            # Get user preferences
            bass_boost = music_manager.get_bass_boost(track.requested_by.id)
            volume = music_manager.get_user_volume(track.requested_by.id)
            
            # Create audio source
            audio_source = await create_audio_source(track, bass_boost=bass_boost, volume=volume)
            
            # Set now playing and start playback
            music_manager.set_now_playing(guild_id, track, vc)
            
            def after_callback(error):
                if error:
                    logger.error(f"Playback error in guild {guild_id}: {error}")
                # Schedule next track
                asyncio.create_task(self._play_next_from_playlist(guild_id))
            
            vc.play(audio_source, after=after_callback)
            
        except Exception as e:
            logger.error(f"Error in _play_next_from_playlist: {e}")

    @app_commands.command(name="myplaylists", description="View your playlists")
    async def my_playlists(self, interaction: discord.Interaction):
        """Show user's personal playlists."""
        try:
            guild_id = interaction.guild.id
            user_id = interaction.user.id
            
            with db_manager:
                playlists = db_manager.get_playlists(guild_id, owner_id=user_id)
            
            if not playlists:
                embed = discord.Embed(
                    title="📝 No Playlists Found",
                    description="You haven't created any playlists yet.\nUse `/createplaylist` to create your first one!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎵 Your Playlists",
                description=f"You have {len(playlists)} playlist(s)",
                color=discord.Color.blue()
            )
            
            for playlist in playlists[:10]:  # Limit to 10 for display
                with db_manager:
                    songs = db_manager.get_playlist_songs(playlist.id)
                
                total_duration = sum(song.duration or 0 for song in songs)
                duration_str = format_duration(total_duration) if total_duration > 0 else "Unknown"
                
                channel = interaction.guild.get_channel(playlist.channel_id) if playlist.channel_id else None
                channel_status = "✅ Active" if channel else "❌ Channel Deleted"
                
                embed.add_field(
                    name=f"📚 {playlist.name}",
                    value=f"**Songs:** {len(songs)}\n**Duration:** {duration_str}\n**Status:** {channel_status}",
                    inline=True
                )
            
            embed.set_footer(text="Use /playplaylist <name> to play a playlist")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing user playlists: {e}")
            await interaction.response.send_message("❌ Failed to load your playlists.", ephemeral=True)

    @app_commands.command(name="addtoplaylist", description="Add current song or search to a playlist")
    @app_commands.describe(
        playlist_name="Name of the playlist to add to",
        query="Song to search for (leave empty to add current song)"
    )
    async def add_to_playlist(self, interaction: discord.Interaction, playlist_name: str, query: Optional[str] = None):
        """Add a song to a playlist."""
        try:
            await interaction.response.defer()
            
            guild_id = interaction.guild.id
            user_id = interaction.user.id
            
            # Find the playlist
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild_id, playlist_name)
            
            if not playlist:
                await interaction.followup.send(f"❌ Playlist '{playlist_name}' not found.", ephemeral=True)
                return
            
            # Check if user owns the playlist or has admin permissions
            if playlist.owner_id != user_id and not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ You can only add songs to your own playlists.", ephemeral=True)
                return
            
            # Determine what song to add
            song_info = None
            
            if query:
                # Search for the song
                try:
                    search_results = await youtube_manager.search(query, limit=1)
                    if search_results:
                        song_info = search_results[0]
                    else:
                        await interaction.followup.send(f"❌ No results found for '{query}'.", ephemeral=True)
                        return
                except YouTubeError as e:
                    await interaction.followup.send(f"❌ Search failed: {str(e)}", ephemeral=True)
                    return
            else:
                # Use currently playing song
                now_playing = music_manager.get_now_playing(guild_id)
                if not now_playing:
                    await interaction.followup.send("❌ No song is currently playing. Please specify a song to search for.", ephemeral=True)
                    return
                
                track = now_playing.track
                song_info = {
                    'title': track.title,
                    'url': track.url,
                    'duration': track.duration
                }
            
            # Add song to playlist
            with db_manager:
                song = db_manager.add_song_to_playlist(
                    playlist_id=playlist.id,
                    title=song_info['title'],
                    url=song_info['url'],
                    added_by=user_id,
                    duration=song_info.get('duration')
                )
            
            embed = discord.Embed(
                title="✅ Song Added to Playlist",
                description=f"Added **{song_info['title']}** to playlist **{playlist.name}**",
                color=discord.Color.green()
            )
            
            if song_info.get('duration'):
                embed.add_field(name="Duration", value=format_duration(song_info['duration']), inline=True)
            
            # Get updated song count
            with db_manager:
                total_songs = len(db_manager.get_playlist_songs(playlist.id))
            
            embed.add_field(name="Playlist Size", value=f"{total_songs} songs", inline=True)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Added song to playlist {playlist.name} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding song to playlist: {e}")
            await interaction.followup.send("❌ Failed to add song to playlist.", ephemeral=True)

    @app_commands.command(name="playplaylist", description="Play a playlist")
    @app_commands.describe(playlist_name="Name of the playlist to play")
    async def play_playlist(self, interaction: discord.Interaction, playlist_name: str):
        """Play all songs from a playlist."""
        try:
            await interaction.response.defer()
            
            guild_id = interaction.guild.id
            
            # Check if user is in voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ You must be in a voice channel to play a playlist.", ephemeral=True)
                return
            
            # Find the playlist
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild_id, playlist_name)
            
            if not playlist:
                await interaction.followup.send(f"❌ Playlist '{playlist_name}' not found.", ephemeral=True)
                return
            
            # Get playlist songs
            with db_manager:
                songs = db_manager.get_playlist_songs(playlist.id)
            
            if not songs:
                await interaction.followup.send(f"❌ Playlist '{playlist.name}' is empty.", ephemeral=True)
                return
            
            # Join voice channel
            from src.utils.discord_voice import join_voice_channel
            vc = await join_voice_channel(interaction, interaction.user.voice.channel)
            if not vc:
                return
            
            # Add all songs to queue
            added_count = 0
            for song in songs:
                try:
                    # Create track object
                    track = Track(
                        query=song.url,
                        title=song.title,
                        url=song.url,
                        duration=song.duration or 0,
                        thumbnail="",  # Could enhance this later
                        uploader="",
                        requested_by=interaction.user
                    )
                    
                    # Add to queue
                    if await music_manager.add_to_queue(guild_id, track):
                        added_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to add song {song.title} to queue: {e}")
                    continue
            
            if added_count == 0:
                await interaction.followup.send("❌ Failed to add any songs from the playlist.", ephemeral=True)
                return
            
            # Start playing if not already playing
            if not music_manager.is_playing(guild_id):
                await self._start_playback(guild_id)
            
            # Create response embed
            embed = discord.Embed(
                title="🎵 Playlist Added to Queue",
                description=f"Added **{added_count}** songs from playlist **{playlist.name}**",
                color=discord.Color.green()
            )
            
            total_duration = sum(song.duration or 0 for song in songs)
            if total_duration > 0:
                embed.add_field(name="Total Duration", value=format_duration(total_duration), inline=True)
            
            queue_length = len(music_manager.get_queue(guild_id))
            embed.add_field(name="Queue Size", value=f"{queue_length} songs", inline=True)
            
            # Add playlist info
            owner = interaction.guild.get_member(playlist.owner_id)
            if owner:
                embed.add_field(name="Created by", value=owner.display_name, inline=True)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Played playlist {playlist.name} with {added_count} songs")
            
        except Exception as e:
            logger.error(f"Error playing playlist: {e}")
            await interaction.followup.send("❌ Failed to play playlist.", ephemeral=True)

    @app_commands.command(name="deleteplaylist", description="Delete one of your playlists")
    @app_commands.describe(playlist_name="Name of the playlist to delete")
    async def delete_playlist(self, interaction: discord.Interaction, playlist_name: str):
        """Delete a user's playlist."""
        try:
            guild_id = interaction.guild.id
            user_id = interaction.user.id
            
            # Find the playlist
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild_id, playlist_name)
            
            if not playlist:
                await interaction.response.send_message(f"❌ Playlist '{playlist_name}' not found.", ephemeral=True)
                return
            
            # Check ownership or admin permissions
            if playlist.owner_id != user_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You can only delete your own playlists.", ephemeral=True)
                return
            
            # Get song count for confirmation
            with db_manager:
                songs = db_manager.get_playlist_songs(playlist.id)
                song_count = len(songs)
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Playlist Deletion",
                description=f"Are you sure you want to delete playlist **{playlist.name}**?",
                color=discord.Color.orange()
            )
            embed.add_field(name="Songs", value=f"{song_count} songs will be deleted", inline=True)
            embed.add_field(name="This action", value="Cannot be undone", inline=True)
            
            # Create confirmation view
            class ConfirmView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.confirmed = False
                
                @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
                async def confirm_delete(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != user_id:
                        await button_interaction.response.send_message("❌ Only the command user can confirm.", ephemeral=True)
                        return
                    
                    try:
                        # Delete from database (should cascade to songs)
                        with db_manager:
                            db_manager.session.delete(playlist)
                            db_manager.session.commit()
                        
                        # Delete Discord channel if exists
                        if playlist.channel_id:
                            channel = interaction.guild.get_channel(playlist.channel_id)
                            if channel:
                                await channel.delete()
                        
                        success_embed = discord.Embed(
                            title="✅ Playlist Deleted",
                            description=f"Playlist **{playlist.name}** has been deleted successfully.",
                            color=discord.Color.green()
                        )
                        
                        await button_interaction.response.edit_message(embed=success_embed, view=None)
                        logger.info(f"Deleted playlist {playlist.name} by user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error deleting playlist: {e}")
                        await button_interaction.response.edit_message(
                            content="❌ Failed to delete playlist.",
                            embed=None,
                            view=None
                        )
                
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
                async def cancel_delete(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != user_id:
                        await button_interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
                        return
                    
                    cancel_embed = discord.Embed(
                        title="❌ Deletion Cancelled",
                        description="Playlist deletion was cancelled.",
                        color=discord.Color.blue()
                    )
                    await button_interaction.response.edit_message(embed=cancel_embed, view=None)
            
            view = ConfirmView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in delete playlist command: {e}")
            await interaction.response.send_message("❌ Failed to delete playlist.", ephemeral=True)

    @app_commands.command(name="playlistinfo", description="Show detailed information about a playlist")
    @app_commands.describe(playlist_name="Name of the playlist to view")
    async def playlist_info(self, interaction: discord.Interaction, playlist_name: str):
        """Show detailed playlist information."""
        try:
            guild_id = interaction.guild.id
            
            # Find the playlist
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild_id, playlist_name)
            
            if not playlist:
                await interaction.response.send_message(f"❌ Playlist '{playlist_name}' not found.", ephemeral=True)
                return
            
            # Get playlist songs
            with db_manager:
                songs = db_manager.get_playlist_songs(playlist.id)
            
            # Create main embed
            embed = discord.Embed(
                title=f"🎵 {playlist.name}",
                color=discord.Color.blue()
            )
            
            # Add playlist info
            owner = interaction.guild.get_member(playlist.owner_id)
            embed.add_field(name="Owner", value=owner.display_name if owner else "Unknown", inline=True)
            embed.add_field(name="Songs", value=str(len(songs)), inline=True)
            
            # Calculate total duration
            total_duration = sum(song.duration or 0 for song in songs)
            if total_duration > 0:
                embed.add_field(name="Duration", value=format_duration(total_duration), inline=True)
            
            # Channel status
            if playlist.channel_id:
                channel = interaction.guild.get_channel(playlist.channel_id)
                status = f"✅ {channel.mention}" if channel else "❌ Channel Deleted"
                embed.add_field(name="Channel", value=status, inline=True)
            
            # Show first 10 songs
            if songs:
                song_list = []
                for i, song in enumerate(songs[:10], 1):
                    duration_str = format_duration(song.duration) if song.duration else "Unknown"
                    song_list.append(f"`{i:2}.` **{song.title}** ({duration_str})")
                
                embed.add_field(
                    name="Songs" + (f" (showing first 10 of {len(songs)})" if len(songs) > 10 else ""),
                    value="\n".join(song_list),
                    inline=False
                )
            else:
                embed.add_field(name="Songs", value="*This playlist is empty*", inline=False)
            
            # Add creation date if available
            if hasattr(playlist, 'created_at') and playlist.created_at:
                embed.set_footer(text=f"Created: {playlist.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing playlist info: {e}")
            await interaction.response.send_message("❌ Failed to load playlist information.", ephemeral=True)

    async def _start_playback(self, guild_id: int):
        """Helper method to start playback."""
        try:
            track = music_manager.get_next_track(guild_id)
            if not track:
                return
            
            vc = music_manager.voice_clients.get(guild_id)
            if not vc or not vc.is_connected():
                return
            
            # Import here to avoid circular imports
            from src.utils.discord_voice import create_audio_source
            
            # Create audio source
            audio_source = await create_audio_source(track)
            
            # Set now playing and start playback
            music_manager.set_now_playing(guild_id, track, vc)
            
            def after_callback(error):
                if error:
                    logger.error(f"Playback error in guild {guild_id}: {error}")
                # Could add auto-next logic here if needed
            
            vc.play(audio_source, after=after_callback)
            
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
    
    @app_commands.command(name="listplaylists", description="List all playlists in this server")
    async def list_playlists(self, interaction: discord.Interaction):
        """List all playlists in the server."""
        try:
            guild = interaction.guild
            
            # Get playlists from database
            with db_manager:
                playlists = db_manager.get_playlists(guild.id)
            
            if not playlists:
                embed = discord.Embed(
                    title="📝 No Playlists Found",
                    description="No playlists have been created yet.\nUse `/createplaylist` to create one!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create paginated list
            embed = discord.Embed(
                title="🎵 Server Playlists",
                description=f"Found {len(playlists)} playlist(s)",
                color=discord.Color.blue()
            )
            
            # Group playlists for display
            for chunk in chunks(playlists, 10):
                playlist_text = []
                for playlist in chunk:
                    channel = guild.get_channel(playlist.channel_id) if playlist.channel_id else None
                    owner = guild.get_member(playlist.owner_id)
                    
                    status = "✅" if channel else "❌"
                    owner_name = owner.display_name if owner else "Unknown"
                    
                    playlist_text.append(
                        f"{status} **{playlist.name}**\n"
                        f"   Owner: {owner_name} | Songs: {len(playlist.songs)}\n"
                        f"   Channel: {channel.mention if channel else 'Deleted'}"
                    )
                
                if playlist_text:
                    embed.add_field(
                        name="Playlists",
                        value="\n\n".join(playlist_text),
                        inline=False
                    )
            
            embed.set_footer(text="Use /playlist <name> to play a playlist")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            await interaction.response.send_message("❌ Failed to list playlists.", ephemeral=True)
    
    # Error handlers
    @setup_playlists.error
    async def setup_playlists_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
    
    @create_playlist.error
    async def create_playlist_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PlaylistCommands(bot))

    