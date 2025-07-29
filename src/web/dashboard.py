# Replace your src/web/dashboard.py with this comprehensive version:

"""Comprehensive Web Dashboard for BasslineBot Pro."""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import discord
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.database.models import Guild, User, Playlist, Song, Usage
from config.settings import settings
from config.database import get_db, engine
from src.core.database_manager import db_manager
from src.core.music_manager import music_manager
from src.monitoring.health import get_health_monitor

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BasslineBot Pro Dashboard",
    description="Comprehensive administrative dashboard for BasslineBot Pro",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_enabled else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# WebSocket connections for live updates
websocket_connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(5)
            data = await get_comprehensive_stats()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Comprehensive main dashboard page."""
    try:
        stats = await get_comprehensive_stats()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "stats": stats,
            "bot_name": settings.bot_name,
            "version": "2.0.0",
            "current_time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint."""
    try:
        health_monitor = get_health_monitor()
        if health_monitor:
            health_data = health_monitor.get_detailed_health()
        else:
            health_data = await basic_health_check()
        
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Get comprehensive bot statistics."""
    return await get_comprehensive_stats()

@app.get("/api/system")
async def get_system_info():
    """Get detailed system information."""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network information
        network_stats = psutil.net_io_counters()
        
        # Process information
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Python/Bot specific info
        import sys
        python_version = sys.version
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network_stats.bytes_sent,
                    "bytes_recv": network_stats.bytes_recv,
                    "packets_sent": network_stats.packets_sent,
                    "packets_recv": network_stats.packets_recv
                }
            },
            "process": {
                "memory": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms,
                    "percent": process.memory_percent()
                },
                "cpu_percent": process.cpu_percent(),
                "create_time": process.create_time(),
                "num_threads": process.num_threads()
            },
            "python": {
                "version": python_version,
                "implementation": sys.implementation.name
            }
        }
    except Exception as e:
        logger.error(f"System info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/discord")
async def get_discord_info():
    """Get Discord connection and guild information with correct metrics."""
    try:
        bot = get_bot_instance()
        if not bot:
            return {"error": "Bot instance not available"}
        
        guilds_info = []
        total_members = 0
        
        for guild in bot.guilds:
            try:
                # Get comprehensive guild-specific stats
                guild_stats = music_manager.get_guild_stats(guild.id)
                
                # Get database info
                with db_manager:
                    db_guild = db_manager.get_guild_settings(guild.id)
                
                # Get recent activity for this guild
                with db_manager:
                    recent_usage = db_manager.session.query(Usage).filter(
                        Usage.guild_id == guild.id,
                        Usage.timestamp >= datetime.utcnow() - timedelta(hours=24)
                    ).count()
                
                guild_info = {
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "owner": {
                        "id": str(guild.owner.id) if guild.owner else None,
                        "name": guild.owner.display_name if guild.owner else "Unknown"
                    },
                    "created_at": guild.created_at.isoformat(),
                    "features": guild.features,
                    "voice_connection": guild_stats['voice_connection'],
                    "music": {
                        "queue_length": guild_stats['queue_length'],
                        "queue_duration": guild_stats['queue_duration'],
                        "queue_duration_formatted": guild_stats['queue_duration_formatted'],
                        "is_playing": guild_stats['is_playing'],
                        "is_paused": guild_stats['is_paused'],
                        "loop_state": guild_stats['loop_state'],
                        "has_queue": guild_stats['has_queue'],
                        "current_track": guild_stats['current_track'],
                        "estimated_finish_time": guild_stats['estimated_finish_time']
                    },
                    "settings": {
                        "max_queue_size": db_guild.max_queue_size if db_guild else settings.max_queue_size,
                        "auto_disconnect_timeout": db_guild.auto_disconnect_timeout if db_guild else settings.idle_timeout,
                        "bass_boost_enabled": db_guild.bass_boost_enabled if db_guild else settings.bass_boost_enabled,
                        "dj_role_id": str(db_guild.dj_role_id) if db_guild and db_guild.dj_role_id else None,
                        "prefix": db_guild.prefix if db_guild else settings.bot_prefix
                    },
                    "activity": {
                        "last_activity": guild_stats['last_activity'],
                        "last_activity_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(guild_stats['last_activity'])),
                        "commands_24h": recent_usage,
                        "minutes_since_activity": (time.time() - guild_stats['last_activity']) / 60
                    }
                }
                
                guilds_info.append(guild_info)
                total_members += guild.member_count or 0
                
            except Exception as e:
                logger.error(f"Error getting info for guild {guild.id}: {e}")
                guilds_info.append({
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count or 0,
                    "error": str(e)
                })
                total_members += guild.member_count or 0
        
        # Get comprehensive music manager metrics
        music_metrics = music_manager.get_comprehensive_metrics()
        
        return {
            "bot": {
                "id": str(bot.user.id),
                "username": bot.user.name,
                "discriminator": bot.user.discriminator,
                "avatar_url": str(bot.user.avatar.url) if bot.user.avatar else None,
                "is_ready": bot.is_ready(),
                "is_closed": bot.is_closed(),
                "latency": bot.latency * 1000,  # Convert to ms
                "uptime": time.time() - getattr(bot, 'startup_time', time.time()),
                "shard_count": getattr(bot, 'shard_count', None)
            },
            "guilds": guilds_info,
            "totals": {
                "guild_count": len(bot.guilds),
                "total_members": total_members,
                "active_voice_connections": music_metrics['active_voice_connections'],
                "connected_voice_clients": music_metrics['connected_voice_clients'],
                "total_queued_tracks": music_metrics['total_queued_tracks'],
                "currently_playing_sessions": music_metrics['currently_playing_sessions'],
                "non_empty_queues": music_metrics['non_empty_queues']
            },
            "music_metrics": music_metrics
        }
    except Exception as e:
        logger.error(f"Discord info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database")
async def get_database_info():
    """Get database statistics and connection info."""
    try:
        with db_manager:
            # Basic table counts
            guild_count = db_manager.session.query(Guild).count()
            user_count = db_manager.session.query(User).count()
            playlist_count = db_manager.session.query(Playlist).count()
            song_count = db_manager.session.query(Song).count()
            usage_count = db_manager.session.query(Usage).count()
            
            # Recent activity
            recent_usage = db_manager.session.query(Usage).filter(
                Usage.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            # Database connection info
            from sqlalchemy import text
            try:
                if settings.database_url.startswith("sqlite"):
                    # SQLite version query
                    db_version = db_manager.session.execute(text("SELECT sqlite_version()")).scalar()
                    db_version = f"SQLite {db_version}"
                elif settings.database_url.startswith("postgresql"):
                    # PostgreSQL version query
                    db_version = db_manager.session.execute(text("SELECT version()")).scalar()
                else:
                    # Generic fallback
                    db_version = "Unknown database type"
            except Exception as e:
                logger.warning(f"Could not determine database version: {e}")
                db_version = "Version unavailable"
            
        # Connection pool info (if applicable)
        pool_info = {}
        if hasattr(engine.pool, 'size'):
            pool_info = {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "invalid": engine.pool.invalidated()
            }
        
        return {
            "tables": {
                "guilds": guild_count,
                "users": user_count,
                "playlists": playlist_count,
                "songs": song_count,
                "usage_logs": usage_count
            },
            "activity": {
                "recent_usage_24h": recent_usage
            },
            "connection": {
                "database_url": settings.database_url.split('@')[0] + '@***',  # Hide credentials
                "version": db_version,
                "pool_info": pool_info
            }
        }
    except Exception as e:
        logger.error(f"Database info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/errors")
async def get_error_info():
    """Get error logs and statistics."""
    try:
        bot = get_bot_instance()
        error_info = {
            "total_errors": 0,
            "recent_errors": [],
            "error_types": {},
            "error_rate": 0
        }
        
        if bot and hasattr(bot, 'error_handler'):
            error_handler = bot.error_handler
            error_info.update({
                "total_errors": getattr(error_handler, 'error_count', 0),
                "recent_errors": getattr(error_handler, 'recent_errors', [])[-50:],  # Last 50 errors
                "error_rate": len(getattr(error_handler, 'recent_errors', [])) / max(1, 
                    (time.time() - getattr(bot, 'startup_time', time.time())) / 3600)  # Errors per hour
            })
            
            # Count error types
            for error in getattr(error_handler, 'recent_errors', []):
                error_type = error.get('error_type', 'Unknown')
                error_info['error_types'][error_type] = error_info['error_types'].get(error_type, 0) + 1
        
        return error_info
    except Exception as e:
        logger.error(f"Error info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance")
async def get_performance_metrics():
    """Get performance metrics and statistics."""
    try:
        # Music manager metrics
        music_metrics = music_manager.get_metrics()
        
        # Command usage statistics
        with db_manager:
            # Recent command usage (last 24 hours)
            recent_commands = db_manager.session.query(Usage).filter(
                Usage.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            # Command success rate
            total_commands = len(recent_commands)
            successful_commands = len([c for c in recent_commands if c.success])
            success_rate = (successful_commands / max(1, total_commands)) * 100
            
            # Average execution time
            execution_times = [c.execution_time for c in recent_commands if c.execution_time]
            avg_execution_time = sum(execution_times) / max(1, len(execution_times))
            
            # Popular commands
            command_counts = {}
            for command in recent_commands:
                command_counts[command.command_name] = command_counts.get(command.command_name, 0) + 1
            
            popular_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "music": music_metrics,
            "commands": {
                "total_24h": total_commands,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "popular_commands": popular_commands
            },
            "cache": {
                "search_cache_size": len(getattr(music_manager, 'search_results', {}))
            }
        }
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/troubleshooting")
async def get_troubleshooting_info():
    """Get troubleshooting information and diagnostics."""
    try:
        bot = get_bot_instance()
        issues = []
        recommendations = []
        
        # Check common issues
        if bot:
            # High latency check
            if bot.latency > 0.5:  # 500ms
                issues.append({
                    "type": "warning",
                    "title": "High Discord Latency",
                    "description": f"Current latency: {bot.latency*1000:.0f}ms",
                    "recommendation": "Check network connection and Discord API status"
                })
            
            # Check for stale voice connections
            stale_connections = []
            current_time = time.time()
            for guild_id, last_activity in music_manager.last_activity.items():
                if current_time - last_activity > 3600:  # 1 hour
                    stale_connections.append(guild_id)
            
            if stale_connections:
                issues.append({
                    "type": "warning",
                    "title": "Stale Voice Connections",
                    "description": f"{len(stale_connections)} connections inactive for >1 hour",
                    "recommendation": "Consider implementing automatic cleanup"
                })
        
        # System resource checks
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            issues.append({
                "type": "critical",
                "title": "High Memory Usage",
                "description": f"System memory usage: {memory.percent:.1f}%",
                "recommendation": "Consider restarting the bot or increasing system memory"
            })
        
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            issues.append({
                "type": "warning",
                "title": "High CPU Usage",
                "description": f"CPU usage: {cpu_percent:.1f}%",
                "recommendation": "Check for resource-intensive operations"
            })
        
        # Database connection check
        try:
            with db_manager:
                from sqlalchemy import text
                db_manager.session.execute(text("SELECT 1"))
        except Exception as e:
            issues.append({
                "type": "critical",
                "title": "Database Connection Issue",
                "description": str(e),
                "recommendation": "Check database server status and connection settings"
            })
        
        # General recommendations
        if not issues:
            recommendations.append("System is running smoothly! Consider enabling more detailed monitoring.")
        else:
            recommendations.append("Address critical issues first, then warnings.")
            recommendations.append("Monitor system resources regularly.")
            recommendations.append("Check Discord API status if experiencing connection issues.")
        
        return {
            "issues": issues,
            "recommendations": recommendations,
            "system_health": "healthy" if not any(i["type"] == "critical" for i in issues) else "degraded",
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Troubleshooting info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/music/detailed")
async def get_detailed_music_info():
    """Get detailed music system information."""
    try:
        detailed_info = {}
        
        for guild_id in music_manager.voice_clients.keys():
            guild_stats = music_manager.get_guild_stats(guild_id)
            queue = music_manager.get_queue(guild_id)
            
            # Get guild name
            bot = get_bot_instance()
            guild_name = "Unknown"
            if bot:
                guild = bot.get_guild(guild_id)
                if guild:
                    guild_name = guild.name
            
            detailed_info[str(guild_id)] = {
                "guild_name": guild_name,
                "stats": guild_stats,
                "queue_tracks": [
                    {
                        "title": track.title,
                        "duration": track.duration,
                        "duration_formatted": music_manager._format_duration(track.duration) if track.duration else "Unknown",
                        "requested_by": track.requested_by.display_name,
                        "added_at": track.added_at,
                        "url": track.url,
                        "thumbnail": track.thumbnail
                    }
                    for track in queue[:10]  # Limit to first 10 tracks
                ],
                "queue_summary": {
                    "total_tracks": len(queue),
                    "showing_tracks": min(len(queue), 10),
                    "total_duration": sum(track.duration for track in queue if track.duration),
                    "estimated_finish": time.time() + sum(track.duration for track in queue if track.duration) if queue else None
                }
            }
        
        return {
            "detailed_guilds": detailed_info,
            "summary": music_manager.get_comprehensive_metrics(),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Detailed music info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_comprehensive_stats():
    """Get all dashboard statistics with corrected metrics."""
    try:
        # Get comprehensive music metrics first
        music_metrics = music_manager.get_comprehensive_metrics()
        
        # Run all stat gathering concurrently
        system_task = get_system_info()
        discord_task = get_discord_info()
        database_task = get_database_info()
        performance_task = get_performance_metrics()
        error_task = get_error_info()
        troubleshooting_task = get_troubleshooting_info()
        
        system_info, discord_info, db_info, perf_info, error_info, troubleshoot_info = await asyncio.gather(
            system_task, discord_task, database_task, performance_task, error_task, troubleshooting_task,
            return_exceptions=True
        )
        
        # Handle any exceptions
        def safe_result(result, default={}):
            return result if not isinstance(result, Exception) else {"error": str(result), **default}
        
        # Calculate additional derived metrics
        bot = get_bot_instance()
        uptime = time.time() - getattr(bot, 'startup_time', time.time()) if bot else 0
        
        # Guild activity analysis
        active_guilds = music_metrics['active_guilds_1h']
        total_guilds = discord_info.get('totals', {}).get('guild_count', 0) if not isinstance(discord_info, Exception) else 0
        activity_rate = (active_guilds / max(1, total_guilds)) * 100
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": uptime,
            "system": safe_result(system_info),
            "discord": safe_result(discord_info),
            "database": safe_result(db_info),
            "performance": safe_result(perf_info),
            "errors": safe_result(error_info),
            "troubleshooting": safe_result(troubleshoot_info),
            "music_comprehensive": music_metrics,
            "derived_metrics": {
                "guild_activity_rate": activity_rate,
                "avg_members_per_guild": (discord_info.get('totals', {}).get('total_members', 0) / max(1, total_guilds)) if not isinstance(discord_info, Exception) else 0,
                "voice_connection_rate": (music_metrics['connected_voice_clients'] / max(1, total_guilds)) * 100,
                "music_engagement_rate": (music_metrics['currently_playing_sessions'] / max(1, total_guilds)) * 100,
                "avg_queue_efficiency": music_metrics['avg_queue_size'],
                "system_health_score": calculate_health_score(system_info, discord_info, music_metrics)
            }
        }
    except Exception as e:
        logger.error(f"Comprehensive stats error: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

def calculate_health_score(system_info, discord_info, music_metrics):
    """Calculate an overall system health score (0-100)."""
    try:
        score = 100
        
        # System resource penalties
        if not isinstance(system_info, Exception) and 'system' in system_info:
            cpu_percent = system_info['system'].get('cpu_percent', 0)
            memory_percent = system_info['system'].get('memory', {}).get('percent', 0)
            
            if cpu_percent > 80:
                score -= 20
            elif cpu_percent > 60:
                score -= 10
                
            if memory_percent > 85:
                score -= 20
            elif memory_percent > 70:
                score -= 10
        
        # Discord connection penalties
        if not isinstance(discord_info, Exception) and 'bot' in discord_info:
            if not discord_info['bot'].get('is_ready', False):
                score -= 30
            if discord_info['bot'].get('latency', 0) > 500:  # 500ms
                score -= 15
            elif discord_info['bot'].get('latency', 0) > 200:  # 200ms
                score -= 5
        
        # Music system penalties
        connection_rate = music_metrics.get('connection_success_rate', 100)
        if connection_rate < 90:
            score -= 15
        elif connection_rate < 95:
            score -= 5
        
        # Error rate penalties
        total_operations = music_metrics.get('songs_played_total', 0) + music_metrics.get('queue_adds_total', 0)
        if total_operations > 0:
            error_rate = (music_metrics.get('errors_total', 0) / total_operations) * 100
            if error_rate > 10:
                score -= 20
            elif error_rate > 5:
                score -= 10
        
        return max(0, min(100, score))
        
    except Exception:
        return 50  # Default neutral score on calculation error

async def basic_health_check():
    """Basic health check when health monitor is not available."""
    try:
        # Test database
        with db_manager:
            from sqlalchemy import text
            db_manager.session.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "message": "Basic health check passed",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

def get_bot_instance():
    """Get the bot instance from the global scope."""
    try:
        # This would need to be set when starting the dashboard
        import sys
        for name, obj in sys.modules.items():
            if hasattr(obj, 'bot') and hasattr(obj.bot, 'user'):
                return obj.bot
        return None
    except Exception:
        return None

async def start_dashboard(bot):
    """Start the dashboard server with bot instance."""
    import uvicorn
    
    # Store bot instance globally for access
    global _bot_instance
    _bot_instance = bot
    
    # Start health monitoring
    health_monitor = get_health_monitor(bot)
    if health_monitor and settings.health_check_enabled:
        asyncio.create_task(health_monitor.start_monitoring())
    
    # Configure and start the server
    config = uvicorn.Config(
        app=app,
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()

# Make bot instance accessible
_bot_instance = None

def get_bot_instance():
    """Get the stored bot instance."""
    return _bot_instance