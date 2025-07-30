# Emergency fix for NonDisruptiveVoiceManager
# Replace your current src/utils/non_disruptive_voice.py with this version

import discord
import asyncio
import logging
import random
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NonDisruptiveVoiceManager:
    """Manage voice connections without disrupting Discord channels."""
    
    def __init__(self):
        self.region_health = {}
        self.connection_attempts = {}
        self.active_connections = {}  # Track active connections to prevent duplicates
        self.fallback_strategies = ['retry_timing', 'connection_pooling', 'smart_detection']
    
    async def connect_with_peak_hour_strategy(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """Connect using strategies that don't disrupt the channel."""
        guild_id = channel.guild.id
        
        # Prevent multiple simultaneous connection attempts
        if guild_id in self.active_connections:
            logger.warning(f"Connection attempt already in progress for guild {guild_id}")
            return None
        
        try:
            self.active_connections[guild_id] = True
            
            # Strategy 1: Smart Timing with Exponential Backoff (FIXED)
            if await self._try_smart_timing_connection(channel):
                return channel.guild.voice_client
            
            # If smart timing fails, don't try other strategies to prevent spam
            logger.warning(f"All connection strategies failed for guild {guild_id}")
            return None
            
        finally:
            # Always cleanup
            self.active_connections.pop(guild_id, None)
    
    async def _try_smart_timing_connection(self, channel: discord.VoiceChannel, max_attempts: int = 5) -> bool:
        """Try connecting with intelligent timing to avoid peak congestion."""
        guild_id = channel.guild.id
        
        for attempt in range(max_attempts):
            try:
                # Check if guild already has a voice client
                if channel.guild.voice_client and channel.guild.voice_client.is_connected():
                    logger.info(f"Guild {guild_id} already has active voice connection")
                    return True
                
                # Calculate delay with jitter to avoid thundering herd
                if attempt > 0:
                    base_delay = min(10, 2 ** attempt)  # Reduced max delay
                    jitter = random.uniform(0.8, 1.2)
                    delay = base_delay * jitter
                    
                    logger.info(f"Voice connection attempt {attempt + 1}/{max_attempts} in {delay:.1f}s")
                    await asyncio.sleep(delay)
                
                # Try connection with shorter timeout
                logger.debug(f"Attempting connection to {channel.name} in guild {guild_id}")
                vc = await asyncio.wait_for(channel.connect(), timeout=5.0)
                logger.info(f"Successfully connected on attempt {attempt + 1}")
                return True
                
            except discord.ConnectionClosed as e:
                if e.code == 4006:  # Invalid session
                    logger.debug(f"Connection attempt {attempt + 1} failed with 4006 (Invalid Session)")
                    # Don't continue immediately - add forced delay to prevent spam
                    if attempt >= max_attempts - 1:
                        logger.error(f"Max connection attempts ({max_attempts}) reached for guild {guild_id}")
                        return False
                    continue
                else:
                    logger.error(f"Non-4006 connection error: {e}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.debug(f"Connection attempt {attempt + 1} timed out")
                if attempt >= max_attempts - 1:
                    return False
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error in connection attempt {attempt + 1}: {e}")
                return False
        
        logger.error(f"All {max_attempts} connection attempts failed for guild {guild_id}")
        return False
    
    async def _try_persistent_connection(self, channel: discord.VoiceChannel) -> bool:
        """Try to maintain persistent connection through brief outages."""
        try:
            vc = await asyncio.wait_for(channel.connect(), timeout=8.0)
            return True
        except Exception as e:
            logger.debug(f"Persistent connection failed: {e}")
            return False
    
    def get_connection_status(self, guild_id: int) -> Dict:
        """Get current connection status for a guild."""
        if guild_id in self.connection_attempts:
            attempt_info = self.connection_attempts[guild_id]
            return {
                'status': attempt_info['status'],
                'attempts': attempt_info['attempts'],
                'last_attempt': attempt_info['last_attempt'].isoformat(),
                'estimated_wait': f"{max(0, 20 - attempt_info['attempts']) * 45} seconds"
            }
        
        return {'status': 'not_queued'}

# Global manager instance
voice_manager = NonDisruptiveVoiceManager()