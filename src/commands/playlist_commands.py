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
                # Ensure user exists
                db_manager.get_or_create_user(interaction.user.id, interaction.user.display_name)
                # Ensure guild exists
                db_manager.get_or_create_guild(guild.id, guild.name)
                
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
                    song_count = len(playlist.songs) if hasattr(playlist, 'songs') else 0
                    
                    playlist_text.append(
                        f"{status} **{playlist.name}**\n"
                        f"   Owner: {owner_name} | Songs: {song_count}\n"
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
    
    @app_commands.command(name="deleteplaylist", description="Delete a playlist")
    @app_commands.describe(name="Name of the playlist to delete")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def delete_playlist(self, interaction: discord.Interaction, name: str):
        """Delete a playlist and its channel."""
        try:
            guild = interaction.guild
            
            # Find playlist in database
            with db_manager:
                playlist = db_manager.get_playlist_by_name(guild.id, name)
            
            if not playlist:
                await interaction.response.send_message(f"⚠️ Playlist '{name}' not found.", ephemeral=True)
                return
            
            # Check if user has permission (owner or admin)
            if playlist.owner_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You can only delete your own playlists.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Delete channel if it exists
            if playlist.channel_id:
                channel = guild.get_channel(playlist.channel_id)
                if channel:
                    try:
                        await channel.delete(reason=f"Playlist deleted by {interaction.user}")
                    except discord.Forbidden:
                        pass
            
            # Delete from database
            with db_manager:
                db_manager.session.delete(playlist)
                db_manager.session.commit()
            
            embed = discord.Embed(
                title="🗑️ Playlist Deleted",
                description=f"Successfully deleted playlist **{playlist.name}**",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Deleted playlist '{playlist.name}' in guild {guild.id}")
            
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            await interaction.followup.send("❌ Failed to delete playlist.", ephemeral=True)
    
    # Error handlers
    @setup_playlists.error
    async def setup_playlists_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
    
    @create_playlist.error
    async def create_playlist_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
    
    @delete_playlist.error
    async def delete_playlist_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PlaylistCommands(bot))