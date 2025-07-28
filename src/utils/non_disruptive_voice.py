
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
        self.fallback_strategies = ['retry_timing', 'connection_pooling', 'smart_detection']
    
    async def connect_with_peak_hour_strategy(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """Connect using strategies that don't disrupt the channel."""
        
        # Strategy 1: Smart Timing with Exponential Backoff
        if await self._try_smart_timing_connection(channel):
            return channel.guild.voice_client
        
        # Strategy 2: Connection Persistence
        if await self._try_persistent_connection(channel):
            return channel.guild.voice_client
        
        # Strategy 3: Queue-Based Approach
        return await self._queue_connection_attempt(channel)
    
    async def _try_smart_timing_connection(self, channel: discord.VoiceChannel, max_attempts: int = 15) -> bool:
        """Try connecting with intelligent timing to avoid peak congestion."""
        for attempt in range(max_attempts):
            try:
                # Calculate delay with jitter to avoid thundering herd
                base_delay = min(30, 2 ** (attempt // 3))  # Cap at 30 seconds
                jitter = random.uniform(0.5, 1.5)
                delay = base_delay * jitter
                
                if attempt > 0:
                    logger.info(f"Voice connection attempt {attempt + 1}/{max_attempts} in {delay:.1f}s")
                    await asyncio.sleep(delay)
                
                # Try connection with optimized timeout
                vc = await channel.connect(timeout=8.0)
                logger.info(f"Successfully connected on attempt {attempt + 1}")
                return True
                
            except discord.ConnectionClosed as e:
                if e.code == 4006:  # Invalid session
                    logger.debug(f"Connection attempt {attempt + 1} failed with 4006")
                    continue
                else:
                    logger.error(f"Non-4006 error: {e}")
                    break
            except asyncio.TimeoutError:
                logger.debug(f"Connection attempt {attempt + 1} timed out")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in connection attempt {attempt + 1}: {e}")
                break
        
        return False
    
    async def _try_persistent_connection(self, channel: discord.VoiceChannel) -> bool:
        """Try to maintain persistent connection through brief outages."""
        try:
            vc = await channel.connect(timeout=12.0)
            return True
        except Exception as e:
            logger.debug(f"Persistent connection failed: {e}")
            return False
    
    async def _queue_connection_attempt(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """Queue connection attempt for when Discord stabilizes."""
        guild_id = channel.guild.id
        
        if guild_id not in self.connection_attempts:
            self.connection_attempts[guild_id] = {
                'channel': channel,
                'attempts': 0,
                'last_attempt': datetime.utcnow(),
                'status': 'queued'
            }
        
        asyncio.create_task(self._process_connection_queue(guild_id))
        return None
    
    async def _process_connection_queue(self, guild_id: int):
        """Process queued connection attempts in background."""
        attempt_info = self.connection_attempts.get(guild_id)
        if not attempt_info or attempt_info['status'] == 'processing':
            return
        
        attempt_info['status'] = 'processing'
        channel = attempt_info['channel']
        
        while attempt_info['attempts'] < 20:
            try:
                await asyncio.sleep(random.uniform(30, 60))
                
                vc = await channel.connect(timeout=10.0)
                logger.info(f"Queued connection successful for guild {guild_id}")
                
                if channel.guild.system_channel:
                    await channel.guild.system_channel.send(
                        "🎵 Bot is now connected to voice! Peak hour connection issues resolved."
                    )
                
                del self.connection_attempts[guild_id]
                return
                
            except discord.ConnectionClosed as e:
                if e.code == 4006:
                    attempt_info['attempts'] += 1
                    continue
                else:
                    break
            except Exception as e:
                logger.error(f"Error in queued connection for guild {guild_id}: {e}")
                break
        
        logger.warning(f"All queued connection attempts failed for guild {guild_id}")
        attempt_info['status'] = 'failed'
    
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
