import asyncio
import discord
import logging
from typing import Optional

from src.core.music_manager import Track
from src.utils.youtube import youtube_manager, YouTubeError
from src.utils.non_disruptive_voice import voice_manager  # NEW IMPORT
from config.settings import settings

logger = logging.getLogger(__name__)

async def join_voice_channel(interaction: discord.Interaction, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
    """Join a voice channel using non-disruptive methods."""
    try:
        # Check if bot is already connected
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel == channel:
                return interaction.guild.voice_client
            else:
                await interaction.guild.voice_client.move_to(channel)
                return interaction.guild.voice_client
        
        # Try non-disruptive connection - UPDATED METHOD
        vc = await voice_manager.connect_with_peak_hour_strategy(channel)
        
        if vc:
            logger.info(f"Connected to voice channel: {channel.name} in guild {interaction.guild.id}")
            return vc
        else:
            # Connection was queued
            await interaction.followup.send(
                "🟡 Voice connection queued due to Discord peak hour issues. "
                "You'll be notified when connected! Use `/status` to check progress.",
                ephemeral=True
            )
            return None
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to join that voice channel.", ephemeral=True)
        return None
    except Exception as e:
        logger.error(f"Error joining voice channel: {e}")
        await interaction.followup.send("❌ Failed to join voice channel.", ephemeral=True)
        return None

async def create_audio_source(track: Track, bass_boost: bool = False, volume: float = 0.5) -> discord.AudioSource:
    """Create audio source for a track."""
    try:
        # Get stream info
        video_info = await youtube_manager.get_info(track.query, download=settings.download_enabled)
        
        # FFmpeg options
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -filter:a "volume={volume}"'
        }
        
        # Add bass boost if enabled
        if bass_boost:
            bass_filter = 'bass=g=4:f=70:w=0.4,equalizer=f=125:t=q:w=1:g=2'
            ffmpeg_options['options'] += f' -af "{bass_filter}"'
        
        # Use downloaded file if available, otherwise stream URL
        source_url = video_info.get('downloaded_file') or video_info['stream_url']
        
        if not source_url:
            raise YouTubeError("No audio source available")
        
        # Create audio source
        audio_source = discord.FFmpegPCMAudio(source_url, **ffmpeg_options)
        
        logger.debug(f"Created audio source for: {track.title}")
        return audio_source
        
    except Exception as e:
        logger.error(f"Error creating audio source: {e}")
        raise YouTubeError(f"Failed to create audio source: {str(e)}")