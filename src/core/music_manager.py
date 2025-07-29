import asyncio
import discord
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from config.settings import settings
from src.core.database_manager import db_manager

logger = logging.getLogger(__name__)

class LoopState(Enum):
    OFF = 0
    SINGLE = 1
    QUEUE = 2

@dataclass
class Track:
    """Represents a track in the queue."""
    query: str
    title: str
    url: str
    duration: int
    thumbnail: str
    uploader: str
    requested_by: discord.User
    added_at: float = field(default_factory=time.time)

@dataclass
class NowPlaying:
    """Represents currently playing track."""
    track: Track
    start_time: float
    voice_client: discord.VoiceClient

class MusicManager:
    """Enhanced music manager with database integration and advanced features."""
    
    def __init__(self):
        # Core music state
        self.queues: Dict[int, List[Track]] = defaultdict(list)
        self.voice_clients: Dict[int, discord.VoiceClient] = {}
        self.now_playing: Dict[int, NowPlaying] = {}
        self.loop_states: Dict[int, LoopState] = defaultdict(lambda: LoopState.OFF)
        
        # User preferences
        self.user_bass_boost: Dict[int, bool] = defaultdict(bool)
        self.user_volumes: Dict[int, float] = defaultdict(lambda: settings.default_volume)
        
        # Activity tracking
        self.last_activity: Dict[int, float] = defaultdict(time.time)
        self.search_results: Dict[int, List[dict]] = {}
        
        # Performance metrics
        self.metrics = {
            'songs_played': 0,
            'total_playtime': 0,
            'queue_adds': 0,
            'errors': 0
        }
        
        logger.info("MusicManager initialized with enhanced features")
    
    # Guild State Management
    def update_last_activity(self, guild_id: int):
        """Update last activity timestamp for a guild."""
        self.last_activity[guild_id] = time.time()
    
    def get_last_activity(self, guild_id: int) -> float:
        """Get last activity timestamp for a guild."""
        return self.last_activity.get(guild_id, 0)
    
    def clear_guild_state(self, guild_id: int):
        """Clear all state for a guild."""
        self.queues.pop(guild_id, None)
        self.voice_clients.pop(guild_id, None)
        self.now_playing.pop(guild_id, None)
        self.loop_states.pop(guild_id, None)
        self.search_results.pop(guild_id, None)
        self.last_activity.pop(guild_id, None)
        logger.info(f"Cleared guild state for {guild_id}")
    
    # Queue Management
    async def add_to_queue(self, guild_id: int, track: Track) -> bool:
        """Add a track to the queue."""
        try:
            guild_settings = db_manager.get_guild_settings(guild_id)
            max_queue = guild_settings.max_queue_size if guild_settings else settings.max_queue_size
            
            if len(self.queues[guild_id]) >= max_queue:
                return False
            
            self.queues[guild_id].append(track)
            self.update_last_activity(guild_id)
            self.metrics['queue_adds'] += 1
            
            logger.debug(f"Added track to queue: {track.title} in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding track to queue: {e}")
            self.metrics['errors'] += 1
            return False
    
    def get_queue(self, guild_id: int) -> List[Track]:
        """Get the queue for a guild."""
        return self.queues.get(guild_id, [])
    
    def get_next_track(self, guild_id: int) -> Optional[Track]:
        """Get the next track from the queue without removing it."""
        queue = self.queues.get(guild_id, [])
        return queue[0] if queue else None
    
    def pop_next_track(self, guild_id: int) -> Optional[Track]:
        """Remove and return the next track from the queue."""
        queue = self.queues.get(guild_id, [])
        if queue:
            track = queue.pop(0)
            logger.debug(f"Popped track from queue: {track.title} in guild {guild_id}")
            self.update_last_activity(guild_id)
            return track
        return None
    
    def shuffle_queue(self, guild_id: int):
        """Shuffle the queue for a guild."""
        if guild_id in self.queues:
            random.shuffle(self.queues[guild_id])
            self.update_last_activity(guild_id)
            logger.debug(f"Shuffled queue for guild {guild_id}")
    
    def clear_queue(self, guild_id: int):
        """Clear the queue for a guild."""
        self.queues[guild_id] = []
        self.update_last_activity(guild_id)
        logger.debug(f"Cleared queue for guild {guild_id}")
    
    def remove_track(self, guild_id: int, index: int) -> bool:
        """Remove a track from the queue by index."""
        try:
            queue = self.queues.get(guild_id, [])
            if 0 <= index < len(queue):
                removed = queue.pop(index)
                self.update_last_activity(guild_id)
                logger.debug(f"Removed track from queue: {removed.title}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing track from queue: {e}")
            return False
    
    def move_track(self, guild_id: int, from_index: int, to_index: int) -> bool:
        """Move a track in the queue."""
        try:
            queue = self.queues.get(guild_id, [])
            if 0 <= from_index < len(queue) and 0 <= to_index < len(queue):
                track = queue.pop(from_index)
                queue.insert(to_index, track)
                self.update_last_activity(guild_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Error moving track in queue: {e}")
            return False
    
    # Playback Control
    def set_now_playing(self, guild_id: int, track: Track, voice_client: discord.VoiceClient):
        """Set the currently playing track."""
        self.now_playing[guild_id] = NowPlaying(
            track=track,
            start_time=time.time(),
            voice_client=voice_client
        )
        self.update_last_activity(guild_id)
        self.metrics['songs_played'] += 1
        logger.debug(f"Now playing: {track.title} in guild {guild_id}")
    
    def get_now_playing(self, guild_id: int) -> Optional[NowPlaying]:
        """Get the currently playing track."""
        return self.now_playing.get(guild_id)
    
    def is_playing(self, guild_id: int) -> bool:
        """Check if music is currently playing."""
        vc = self.voice_clients.get(guild_id)
        return vc and vc.is_playing()
    
    def is_paused(self, guild_id: int) -> bool:
        """Check if music is currently paused."""
        vc = self.voice_clients.get(guild_id)
        return vc and vc.is_paused()
    
    # Loop Control
    def get_loop_state(self, guild_id: int) -> LoopState:
        """Get the loop state for a guild."""
        return self.loop_states.get(guild_id, LoopState.OFF)
    
    def set_loop_state(self, guild_id: int, state: LoopState):
        """Set the loop state for a guild."""
        self.loop_states[guild_id] = state
        self.update_last_activity(guild_id)
        logger.debug(f"Set loop state to {state.name} for guild {guild_id}")
    
    # User Preferences
    def toggle_bass_boost(self, user_id: int) -> bool:
        """Toggle bass boost for a user."""
        self.user_bass_boost[user_id] = not self.user_bass_boost[user_id]
        
        # Update in database
        db_manager.update_user_settings(user_id, bass_boost_enabled=self.user_bass_boost[user_id])
        
        logger.debug(f"Bass boost {'enabled' if self.user_bass_boost[user_id] else 'disabled'} for user {user_id}")
        return self.user_bass_boost[user_id]
    
    def get_bass_boost(self, user_id: int) -> bool:
        """Get bass boost setting for a user."""
        return self.user_bass_boost.get(user_id, False)
    
    def set_user_volume(self, user_id: int, volume: float):
        """Set volume preference for a user."""
        volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        self.user_volumes[user_id] = volume
        logger.debug(f"Set volume to {volume} for user {user_id}")
    
    def get_user_volume(self, user_id: int) -> float:
        """Get volume preference for a user."""
        return self.user_volumes.get(user_id, settings.default_volume)
    
    # DJ Role Management
    def get_dj_role_id(self, guild_id: int) -> Optional[int]:
        """Get the DJ role ID for a guild."""
        guild_settings = db_manager.get_guild_settings(guild_id)
        return guild_settings.dj_role_id if guild_settings else None
    
    def set_dj_role(self, guild_id: int, role_id: Optional[int]):
        """Set the DJ role for a guild."""
        db_manager.update_guild_settings(guild_id, dj_role_id=role_id)
        logger.info(f"Set DJ role to {role_id} for guild {guild_id}")
    
    # Statistics and Metrics
    def get_queue_duration(self, guild_id: int) -> int:
        """Get total duration of tracks in queue."""
        queue = self.queues.get(guild_id, [])
        return sum(track.duration for track in queue if track.duration)
    
    def get_metrics(self) -> dict:
        """Get performance metrics."""
        return self.metrics.copy()
    
    def get_guild_stats(self, guild_id: int) -> dict:
        """Get comprehensive statistics for a specific guild."""
        now_playing = self.get_now_playing(guild_id)
        queue = self.get_queue(guild_id)
        voice_client = self.voice_clients.get(guild_id)
        
        # Calculate queue duration
        queue_duration = sum(track.duration for track in queue if track.duration)
        
        # Get currently playing track info
        current_track_info = None
        if now_playing:
            elapsed_time = time.time() - now_playing.start_time
            current_track_info = {
                'title': now_playing.track.title,
                'duration': now_playing.track.duration,
                'elapsed': elapsed_time,
                'remaining': (now_playing.track.duration - elapsed_time) if now_playing.track.duration else None,
                'progress_percent': (elapsed_time / now_playing.track.duration * 100) if now_playing.track.duration else 0,
                'requested_by': now_playing.track.requested_by.display_name,
                'thumbnail': now_playing.track.thumbnail,
                'url': now_playing.track.url
            }
        
        # Voice connection status
        voice_status = {
            'connected': voice_client is not None and voice_client.is_connected() if voice_client else False,
            'channel': voice_client.channel.name if voice_client and voice_client.channel else None,
            'channel_id': voice_client.channel.id if voice_client and voice_client.channel else None,
            'latency': getattr(voice_client, 'latency', None) * 1000 if voice_client and hasattr(voice_client, 'latency') else None,
            'is_playing': voice_client.is_playing() if voice_client else False,
            'is_paused': voice_client.is_paused() if voice_client else False
        }
        
        return {
            'queue_length': len(queue),
            'queue_duration': queue_duration,
            'queue_duration_formatted': self._format_duration(queue_duration),
            'is_playing': self.is_playing(guild_id),
            'is_paused': self.is_paused(guild_id),
            'loop_state': self.get_loop_state(guild_id).name,
            'last_activity': self.get_last_activity(guild_id),
            'current_track': current_track_info,
            'voice_connection': voice_status,
            'has_queue': len(queue) > 0,
            'estimated_finish_time': time.time() + queue_duration if queue_duration > 0 else None
        }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable format."""
        if not seconds or seconds <= 0:
            return "0:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
        
    def get_comprehensive_metrics(self) -> dict:
        """Get comprehensive metrics for dashboard."""
        current_time = time.time()
        
        # Basic metrics
        total_guilds = len(self.last_activity)
        active_voice_connections = len(self.voice_clients)
        connected_voice_clients = len([vc for vc in self.voice_clients.values() if vc and vc.is_connected()])
        
        # Queue metrics
        total_queued = sum(len(queue) for queue in self.queues.values())
        non_empty_queues = len([queue for queue in self.queues.values() if queue])
        total_queue_duration = sum(
            sum(track.duration for track in queue if track.duration) 
            for queue in self.queues.values()
        )
        
        # Playing metrics
        currently_playing = len(self.now_playing)
        active_sessions = len([
            guild_id for guild_id, vc in self.voice_clients.items() 
            if vc and vc.is_playing()
        ])
        
        # Activity metrics
        active_guilds_1h = len([
            guild_id for guild_id, last_activity in self.last_activity.items()
            if current_time - last_activity < 3600  # 1 hour
        ])
        
        active_guilds_24h = len([
            guild_id for guild_id, last_activity in self.last_activity.items()
            if current_time - last_activity < 86400  # 24 hours
        ])
        
        # User metrics
        unique_users_in_queues = set()
        for queue in self.queues.values():
            for track in queue:
                unique_users_in_queues.add(track.requested_by.id)
        
        # Performance metrics
        avg_queue_size = total_queued / max(1, total_guilds)
        
        return {
            # Basic counts
            'total_guilds_tracked': total_guilds,
            'active_voice_connections': active_voice_connections,
            'connected_voice_clients': connected_voice_clients,
            'connection_success_rate': (connected_voice_clients / max(1, active_voice_connections)) * 100,
            
            # Queue metrics
            'total_queued_tracks': total_queued,
            'non_empty_queues': non_empty_queues,
            'avg_queue_size': round(avg_queue_size, 1),
            'total_queue_duration': total_queue_duration,
            'total_queue_duration_formatted': self._format_duration(total_queue_duration),
            
            # Playback metrics
            'currently_playing_sessions': currently_playing,
            'active_playing_sessions': active_sessions,
            'songs_played_total': self.metrics.get('songs_played', 0),
            'total_playtime': self.metrics.get('total_playtime', 0),
            'queue_adds_total': self.metrics.get('queue_adds', 0),
            'errors_total': self.metrics.get('errors', 0),
            
            # Activity metrics
            'active_guilds_1h': active_guilds_1h,
            'active_guilds_24h': active_guilds_24h,
            'unique_users_in_queues': len(unique_users_in_queues),
            
            # User preferences
            'users_with_bass_boost': len([uid for uid, enabled in self.user_bass_boost.items() if enabled]),
            'users_with_custom_volume': len([uid for uid, vol in self.user_volumes.items() if vol != 0.5]),
            
            # Loop states distribution
            'loop_states_distribution': {
                'off': len([state for state in self.loop_states.values() if state == LoopState.OFF]),
                'single': len([state for state in self.loop_states.values() if state == LoopState.SINGLE]),
                'queue': len([state for state in self.loop_states.values() if state == LoopState.QUEUE])
            }
        }

# Global music manager instance
music_manager = MusicManager()