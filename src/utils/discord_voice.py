import asyncio
import discord
import logging
from typing import Optional

from src.core.music_manager import Track
from src.utils.youtube import youtube_manager, YouTubeError
from config.settings import settings

logger = logging.getLogger(__name__)

# Custom VoiceClient to handle UDP discovery issues
class FixedVoiceClient(discord.VoiceClient):
    """Custom VoiceClient with UDP discovery fixes for error 4006."""
    
    async def connect_websocket(self):
        """Override connect_websocket to handle IP discovery issues."""
        try:
            return await super().connect_websocket()
        except discord.errors.ConnectionClosed as e:
            if e.code == 4006:
                logger.warning("Got 4006 error, attempting UDP discovery fix...")
                # The issue is often with IP discovery timing
                # Wait a bit and try once more with different timing
                await asyncio.sleep(1.0)
                try:
                    return await super().connect_websocket()
                except discord.errors.ConnectionClosed as e2:
                    if e2.code == 4006:
                        logger.error("UDP discovery still failing - this is likely a network/firewall issue")
                        raise discord.errors.ConnectionClosed(
                            e2.ws, 
                            shard_id=None, 
                            code=4006
                        )
                    else:
                        raise
            else:
                raise

async def join_voice_channel(interaction: discord.Interaction, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
    """Join voice channel with UDP discovery fix."""
    try:
        # Check existing connection
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel == channel:
                logger.info(f"Already connected to {channel.name}")
                return interaction.guild.voice_client
            else:
                logger.info(f"Moving to {channel.name}")
                await interaction.guild.voice_client.move_to(channel)
                return interaction.guild.voice_client
        
        logger.info(f"Connecting to {channel.name} with UDP fix...")
        
        # Use our custom VoiceClient with UDP discovery fix
        vc = await channel.connect(
            cls=FixedVoiceClient,
            timeout=30.0,
            reconnect=True
        )
        
        if vc and vc.is_connected():
            logger.info(f"✅ Successfully connected to {channel.name}")
            return vc
        else:
            logger.error("Connection appeared to succeed but bot is not connected")
            return None
            
    except discord.errors.ConnectionClosed as e:
        if e.code == 4006:
            logger.error("❌ Discord Voice Error 4006 - IP Discovery Failed")
            logger.error("This is a known Discord/network issue. Solutions:")
            logger.error("1. Check Windows Firewall UDP settings")
            logger.error("2. Try different voice channel")
            logger.error("3. Restart Discord client")
            logger.error("4. Check if Discord is having voice issues")
            
            try:
                await interaction.followup.send(
                    "❌ **Voice Connection Failed (Error 4006)**\n\n"
                    "This is a Discord voice server issue. Try:\n"
                    "• **Different voice channel** in this server\n"
                    "• **Restart Discord** completely\n"
                    "• **Check Windows Firewall** (allow Python/Discord)\n"
                    "• **Wait a few minutes** and try again\n\n"
                    "This error affects many Discord bots and is not specific to this bot.",
                    ephemeral=True
                )
            except:
                pass
        else:
            logger.error(f"Voice connection failed with code {e.code}: {e}")
            try:
                await interaction.followup.send(f"❌ Voice connection failed: Discord error {e.code}", ephemeral=True)
            except:
                pass
    
    except discord.Forbidden:
        logger.error(f"No permission to join {channel.name}")
        try:
            await interaction.followup.send("❌ No permission to join that voice channel", ephemeral=True)
        except:
            pass
    
    except asyncio.TimeoutError:
        logger.error("Voice connection timed out")
        try:
            await interaction.followup.send("❌ Voice connection timed out - try again", ephemeral=True)
        except:
            pass
    
    except Exception as e:
        logger.error(f"Unexpected voice connection error: {e}")
        try:
            await interaction.followup.send("❌ Unexpected error connecting to voice", ephemeral=True)
        except:
            pass
    
    return None

async def create_audio_source(track: Track, bass_boost: bool = False, volume: float = 0.5) -> discord.AudioSource:
    """Create audio source for playback."""
    try:
        # Get video info
        video_info = await youtube_manager.get_info(track.query, download=settings.download_enabled)
        
        if not video_info:
            raise YouTubeError("Failed to get video information")
        
        # Get audio source URL
        source_url = (
            video_info.get('downloaded_file') or 
            video_info.get('stream_url') or 
            video_info.get('url')
        )
        
        if not source_url:
            raise YouTubeError("No audio source URL found")
        
        # FFmpeg options optimized for reliability
        before_options = (
            '-reconnect 1 '
            '-reconnect_streamed 1 '
            '-reconnect_delay_max 5 '
            '-reconnect_at_eof 1'
        )
        
        options = '-vn'  # No video
        
        # Add audio filters if needed
        filters = []
        if volume != 1.0:
            filters.append(f'volume={volume:.2f}')
        
        if bass_boost:
            filters.append(f'bass=g={settings.bass_boost_gain}:f={settings.bass_boost_frequency}:w={settings.bass_boost_width}')
        
        if filters:
            options += f' -af "{",".join(filters)}"'
        
        # Create audio source
        audio_source = discord.FFmpegPCMAudio(
            source_url,
            before_options=before_options,
            options=options
        )
        
        logger.info(f"✅ Created audio source for: {track.title}")
        return audio_source
        
    except Exception as e:
        logger.error(f"Error creating audio source: {e}")
        raise YouTubeError(f"Failed to create audio: {str(e)}")

def check_voice_requirements():
    """Check if voice requirements are met."""
    try:
        import socket
        
        # Test UDP socket creation (needed for Discord voice)
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.close()
        logger.info("✅ UDP socket test passed")
        
        # Check if PyNaCl is available (required for voice)
        try:
            import nacl
            logger.info("✅ PyNaCl (voice encryption) available")
        except ImportError:
            logger.error("❌ PyNaCl not found - voice will not work")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Voice requirements check failed: {e}")
        return False