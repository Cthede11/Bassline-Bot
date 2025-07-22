"""REST API endpoints for BasslineBot Pro."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

from config.database import get_db
from src.core.database_manager import db_manager
from src.core.music_manager import music_manager, LoopState
from src.monitoring.health import get_health_monitor
from src.utils.youtube import youtube_manager

logger = logging.getLogger(__name__)

# Create API router
api_router = APIRouter(prefix="/api/v1", tags=["api"])

# Pydantic models for request/response
class PlayRequest(BaseModel):
    query: str = Field(..., description="Song name or YouTube URL")
    user_id: str = Field(..., description="Discord user ID")
    position: str = Field("end", description="Queue position: 'start', 'end', or number")

class PlaybackControlRequest(BaseModel):
    action: str = Field(..., description="Action: play, pause, skip, stop, shuffle")
    user_id: str = Field(..., description="Discord user ID")
    mode: Optional[str] = Field(None, description="Loop mode for loop action")

class GuildSettingsUpdate(BaseModel):
    max_queue_size: Optional[int] = Field(None, ge=1, le=500)
    auto_disconnect_timeout: Optional[int] = Field(None, ge=60, le=3600)
    bass_boost_enabled: Optional[bool] = None
    prefix: Optional[str] = Field(None, max_length=10)

class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner_id: str = Field(..., description="Discord user ID")
    is_public: bool = Field(False)

class SongAdd(BaseModel):
    title: str = Field(..., max_length=255)
    url: str = Field(..., description="YouTube URL")
    duration: Optional[int] = Field(None, ge=0)
    added_by: str = Field(..., description="Discord user ID")

# Health endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_monitor = get_health_monitor()
        if health_monitor:
            health_data = health_monitor.get_overall_health()
            status_code = 200 if health_data['status'] == 'healthy' else 503
            return health_data
        else:
            return {
                "status": "healthy",
                "message": "Basic health check passed",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")

@api_router.get("/health/detailed")
async def detailed_health():
    """Detailed health information."""
    try:
        health_monitor = get_health_monitor()
        if health_monitor:
            return health_monitor.get_detailed_health()
        else:
            raise HTTPException(status_code=503, detail="Health monitor not available")
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health information")

# Statistics endpoints
@api_router.get("/stats")
async def get_stats():
    """Get general bot statistics."""
    try:
        # Get basic metrics
        metrics = music_manager.get_metrics()
        
        # Get database stats
        with db_manager:
            usage_stats = db_manager.get_usage_stats(days=7)
        
        return {
            "total_guilds": len(music_manager.last_activity),
            "active_connections": len(music_manager.voice_clients),
            "total_queued": sum(len(queue) for queue in music_manager.queues.values()),
            "songs_played": metrics.get('songs_played', 0),
            "total_commands": usage_stats.get('total_commands', 0),
            "success_rate": (usage_stats.get('successful_commands', 0) / max(usage_stats.get('total_commands', 1), 1)) * 100,
            "avg_execution_time": usage_stats.get('avg_execution_time', 0),
            "unique_users": usage_stats.get('unique_users', 0)
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

# Guild endpoints
@api_router.get("/guilds")
async def get_guilds(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False)
):
    """Get list of guilds."""
    try:
        with db_manager:
            guilds = db_manager.session.query(db_manager.Guild).all()
        
        # Filter and paginate
        filtered_guilds = []
        for guild in guilds:
            if search and search.lower() not in guild.name.lower():
                continue
            
            if active_only and guild.id not in music_manager.voice_clients:
                continue
            
            guild_stats = music_manager.get_guild_stats(guild.id)
            now_playing = music_manager.get_now_playing(guild.id)
            
            guild_data = {
                "id": str(guild.id),
                "name": guild.name,
                "is_active": guild.id in music_manager.voice_clients,
                "queue_length": guild_stats['queue_length'],
                "now_playing": {
                    "title": now_playing.track.title if now_playing else None,
                    "duration": now_playing.track.duration if now_playing else None,
                    "position": int(time.time() - now_playing.start_time) if now_playing else None
                } if now_playing else None,
                "settings": {
                    "max_queue_size": guild.max_queue_size,
                    "dj_role_id": str(guild.dj_role_id) if guild.dj_role_id else None,
                    "auto_disconnect": guild.auto_disconnect_timeout,
                    "prefix": guild.prefix
                },
                "last_activity": guild_stats.get('last_activity', 0)
            }
            filtered_guilds.append(guild_data)
        
        # Paginate
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_guilds = filtered_guilds[start_idx:end_idx]
        
        return {
            "guilds": paginated_guilds,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(filtered_guilds),
                "total_pages": (len(filtered_guilds) + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting guilds: {e}")
        raise HTTPException(status_code=500, detail="Failed to get guilds")

@api_router.get("/guilds/{guild_id}")
async def get_guild(guild_id: str):
    """Get detailed guild information."""
    try:
        guild_id_int = int(guild_id)
        
        with db_manager:
            guild = db_manager.get_guild_settings(guild_id_int)
        
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        
        guild_stats = music_manager.get_guild_stats(guild_id_int)
        now_playing = music_manager.get_now_playing(guild_id_int)
        queue = music_manager.get_queue(guild_id_int)
        
        return {
            "id": guild_id,
            "name": guild.name,
            "settings": {
                "max_queue_size": guild.max_queue_size,
                "dj_role_id": str(guild.dj_role_id) if guild.dj_role_id else None,
                "auto_disconnect_timeout": guild.auto_disconnect_timeout,
                "bass_boost_enabled": guild.bass_boost_enabled,
                "prefix": guild.prefix
            },
            "current_session": {
                "is_connected": guild_id_int in music_manager.voice_clients,
                "queue_length": len(queue),
                "now_playing": {
                    "title": now_playing.track.title,
                    "url": now_playing.track.url,
                    "duration": now_playing.track.duration,
                    "position": int(time.time() - now_playing.start_time),
                    "requested_by": str(now_playing.track.requested_by.id)
                } if now_playing else None,
                "loop_mode": music_manager.get_loop_state(guild_id_int).name.lower()
            }
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid guild ID")
    except Exception as e:
        logger.error(f"Error getting guild {guild_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get guild information")

@api_router.put("/guilds/{guild_id}/settings")
async def update_guild_settings(guild_id: str, settings: GuildSettingsUpdate):
    """Update guild settings."""
    try:
        guild_id_int = int(guild_id)
        
        # Prepare updates
        updates = {}
        if settings.max_queue_size is not None:
            updates['max_queue_size'] = settings.max_queue_size
        if settings.auto_disconnect_timeout is not None:
            updates['auto_disconnect_timeout'] = settings.auto_disconnect_timeout
        if settings.bass_boost_enabled is not None:
            updates['bass_boost_enabled'] = settings.bass_boost_enabled
        if settings.prefix is not None:
            updates['prefix'] = settings.prefix
        
        # Update in database
        with db_manager:
            success = db_manager.update_guild_settings(guild_id_int, **updates)
        
        if success:
            return {
                "success": True,
                "message": "Settings updated successfully",
                "settings": updates
            }
        else:
            raise HTTPException(status_code=404, detail="Guild not found")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid guild ID")
    except Exception as e:
        logger.error(f"Error updating guild settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

import time  # Add this import at the top if not present

# Music control endpoints
@api_router.get("/guilds/{guild_id}/queue")
async def get_queue(guild_id: str):
    """Get current queue for guild."""
    try:
        guild_id_int = int(guild_id)

        now_playing = music_manager.get_now_playing(guild_id_int)
        queue = music_manager.get_queue(guild_id_int)

        queue_data = []
        for i, track in enumerate(queue):
            queue_data.append({
                "position": i + 1,
                "title": track.title,
                "url": track.url,
                "duration": track.duration,
                "thumbnail": track.thumbnail,
                "requested_by": {
                    "id": str(track.requested_by.id),
                    "username": track.requested_by.display_name
                },
                "added_at": datetime.fromtimestamp(track.added_at).isoformat()
            })

        return {
            "guild_id": guild_id,
            "now_playing": {
                "title": now_playing.track.title,
                "url": now_playing.track.url,
                "duration": now_playing.track.duration,
                "position": int(time.time() - now_playing.start_time),
                "thumbnail": now_playing.track.thumbnail,
                "requested_by": {
                    "id": str(now_playing.track.requested_by.id),
                    "username": now_playing.track.requested_by.display_name
                },
                "started_at": datetime.fromtimestamp(now_playing.start_time).isoformat()
            } if now_playing else None,
            "queue": queue_data,
            "total_duration": sum(track.duration for track in queue if track.duration)
        }
    except Exception as e:
        logger.error(f"Error getting queue for guild {guild_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue")