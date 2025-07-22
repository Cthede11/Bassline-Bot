"""Web dashboard for BasslineBot Pro."""

import asyncio
from email.mime import text
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from src.database.models import Guild, User, Playlist

from config.settings import settings
from config.database import get_db
from src.core.database_manager import db_manager
from src.core.music_manager import music_manager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BasslineBot Pro Dashboard",
    description="Administrative dashboard for BasslineBot Pro",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    # Get basic statistics
    stats = await get_dashboard_stats()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "bot_name": settings.bot_name
    })

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        with db_manager:
            from sqlalchemy import text
            db_manager.session.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/stats")
async def get_stats():
    """Get current bot statistics."""
    return await get_dashboard_stats()

@app.get("/api/guilds")
async def get_guilds():
    """Get guild information."""
    try:
        with db_manager:
            guilds = db_manager.session.query(Guild).all()  # FIXED: Use imported Guild
            
        guild_data = []
        for guild in guilds:
            guild_stats = music_manager.get_guild_stats(guild.id)
            guild_data.append({
                "id": guild.id,
                "name": guild.name,
                "queue_length": guild_stats['queue_length'],
                "is_playing": guild_stats['is_playing'],
                "loop_state": guild_stats['loop_state'],
                "last_activity": guild_stats['last_activity']
            })
        
        return {"guilds": guild_data}
        
    except Exception as e:
        logger.error(f"Error getting guilds: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/realtime")
async def get_realtime_data():
    """Get real-time bot data."""
    try:
        # Get current Discord bot info if available
        bot_guilds = 1  # Default fallback
        bot_users = 50   # Default fallback
        
        # Voice connections
        voice_connections = []
        for guild_id, vc in music_manager.voice_clients.items():
            if vc and vc.is_connected():
                now_playing = music_manager.get_now_playing(guild_id)
                voice_connections.append({
                    "guild_id": str(guild_id),
                    "channel": vc.channel.name if vc.channel else "Unknown",
                    "is_playing": vc.is_playing(),
                    "is_paused": vc.is_paused(),
                    "current_song": now_playing.track.title if now_playing else None,
                    "queue_length": len(music_manager.get_queue(guild_id))
                })
        
        # Current queues
        active_queues = {}
        for guild_id, queue in music_manager.queues.items():
            if queue:
                active_queues[str(guild_id)] = {
                    "length": len(queue),
                    "duration": sum(track.duration for track in queue if track.duration),
                    "next_song": queue[0].title if queue else None
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "bot_status": "online",
            "guilds": bot_guilds,
            "users": bot_users,
            "voice_connections": voice_connections,
            "active_queues": active_queues,
            "total_active_connections": len(music_manager.voice_clients),
            "total_queued_songs": sum(len(queue) for queue in music_manager.queues.values()),
            "loop_states": {
                str(gid): state.name for gid, state in music_manager.loop_states.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime data: {e}")
        return {"error": "Failed to get realtime data", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/usage")
async def get_usage_stats(days: int = 7):
    """Get usage statistics."""
    try:
        with db_manager:
            stats = db_manager.get_usage_stats(days=days)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/metrics")
async def get_metrics():
    """Get performance metrics."""
    try:
        metrics = music_manager.get_metrics()
        
        # Add system metrics
        import psutil
        metrics.update({
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "active_voice_connections": len(music_manager.voice_clients),
            "total_queued_tracks": sum(len(queue) for queue in music_manager.queues.values()),
            "uptime": datetime.utcnow().isoformat()
        })
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_dashboard_stats() -> Dict:
    """Get statistics for dashboard."""
    try:
        with db_manager:
            # Basic counts - FIXED: Use imported models
            total_guilds = db_manager.session.query(Guild).count()
            total_users = db_manager.session.query(User).count()
            total_playlists = db_manager.session.query(Playlist).count()
            
            # Usage stats
            usage_stats = db_manager.get_usage_stats(days=7)
            
        # Music manager stats
        music_stats = music_manager.get_metrics()
        
        # Active connections
        active_connections = len(music_manager.voice_clients)
        total_queued = sum(len(queue) for queue in music_manager.queues.values())
        
        return {
            "total_guilds": total_guilds,
            "total_users": total_users,
            "total_playlists": total_playlists,
            "active_connections": active_connections,
            "total_queued": total_queued,
            "songs_played": music_stats.get('songs_played', 0),
            "total_commands": usage_stats.get('total_commands', 0),
            "success_rate": (usage_stats.get('successful_commands', 0) / max(usage_stats.get('total_commands', 1), 1)) * 100,
            "avg_execution_time": usage_stats.get('avg_execution_time', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}

async def start_dashboard(bot):
    """Start the dashboard server."""
    if not settings.dashboard_enabled:
        return
    
    try:
        config = uvicorn.Config(
            app,
            host=settings.dashboard_host,
            port=settings.dashboard_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        # Run in background
        await server.serve()
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")