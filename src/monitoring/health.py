# Replace your src/monitoring/health.py with this enhanced version:

"""Enhanced Health monitoring and diagnostics for BasslineBot Pro."""

import asyncio
import logging
import time
import psutil
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from config.settings import settings
from config.database import engine
from src.core.music_manager import music_manager

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    metrics: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None

class EnhancedHealthMonitor:
    """Comprehensive health monitoring system for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.checks: Dict[str, HealthCheck] = {}
        self.last_check = time.time()
        self.check_interval = 30  # seconds
        self.alerts = []
        self.performance_history = []
        self.error_tracking = {
            'total_errors': 0,
            'error_types': {},
            'recent_errors': [],
            'error_rate_history': []
        }
        
        # Thresholds for different checks
        self.thresholds = {
            'cpu_warning': 70,
            'cpu_critical': 85,
            'memory_warning': 75,
            'memory_critical': 90,
            'disk_warning': 80,
            'disk_critical': 95,
            'latency_warning': 500,  # ms
            'latency_critical': 1000,  # ms
            'error_rate_warning': 10,  # errors per hour
            'error_rate_critical': 50,  # errors per hour
        }
        
    async def start_monitoring(self):
        """Start the comprehensive health monitoring task."""
        logger.info("Starting enhanced health monitoring")
        
        while True:
            try:
                await self.run_comprehensive_health_checks()
                await self.analyze_trends()
                await self.generate_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def run_comprehensive_health_checks(self):
        """Run all comprehensive health checks."""
        self.last_check = time.time()
        
        # Define all health checks
        check_tasks = [
            self.check_bot_connection(),
            self.check_database_health(),
            self.check_system_resources(),
            self.check_voice_connections(),
            self.check_music_manager_health(),
            self.check_error_rates(),
            self.check_performance_metrics(),
            self.check_discord_api_health(),
            self.check_memory_leaks(),
            self.check_file_system_health(),
            self.check_network_connectivity(),
        ]
        
        # Run all checks concurrently
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            check_name = check_tasks[i].__name__
            if isinstance(result, Exception):
                logger.error(f"Health check {check_name} failed: {result}")
                self.checks[check_name] = HealthCheck(
                    name=check_name,
                    status=HealthStatus.ERROR,
                    message=f"Check failed: {str(result)}",
                    timestamp=time.time(),
                    metrics={},
                    details={'exception': str(result), 'traceback': traceback.format_exc()},
                    recommendations=['Check system logs', 'Restart the affected service']
                )
            else:
                self.checks[check_name] = result
    
    async def check_bot_connection(self) -> HealthCheck:
        """Comprehensive Discord bot connection check."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            if not self.bot:
                return HealthCheck(
                    name="bot_connection",
                    status=HealthStatus.ERROR,
                    message="Bot instance not available",
                    timestamp=time.time(),
                    metrics={},
                    recommendations=['Check bot initialization']
                )
            
            # Basic connection status
            is_ready = self.bot.is_ready()
            is_closed = self.bot.is_closed()
            latency = self.bot.latency * 1000  # Convert to ms
            
            metrics.update({
                'is_ready': is_ready,
                'is_closed': is_closed,
                'latency_ms': latency,
                'guild_count': len(self.bot.guilds) if is_ready else 0,
                'user_count': sum(g.member_count or 0 for g in self.bot.guilds) if is_ready else 0
            })
            
            details.update({
                'bot_id': str(self.bot.user.id) if self.bot.user else None,
                'bot_username': self.bot.user.name if self.bot.user else None,
                'uptime': time.time() - getattr(self.bot, 'startup_time', time.time())
            })
            
            # Determine status based on conditions
            if not is_ready or is_closed:
                status = HealthStatus.UNHEALTHY
                message = "Bot is not ready or connection is closed"
                recommendations.extend([
                    'Check Discord token validity',
                    'Verify network connectivity',
                    'Check Discord API status'
                ])
            elif latency > self.thresholds['latency_critical']:
                status = HealthStatus.UNHEALTHY
                message = f"Critical latency: {latency:.0f}ms"
                recommendations.extend([
                    'Check network connection',
                    'Verify Discord API status',
                    'Consider server location change'
                ])
            elif latency > self.thresholds['latency_warning']:
                status = HealthStatus.DEGRADED
                message = f"High latency: {latency:.0f}ms"
                recommendations.append('Monitor network conditions')
            else:
                status = HealthStatus.HEALTHY
                message = f"Bot connection healthy, latency: {latency:.0f}ms"
            
            return HealthCheck(
                name="bot_connection",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="bot_connection",
                status=HealthStatus.ERROR,
                message=f"Bot connection check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check bot instance', 'Verify Discord connection']
            )
    
    async def check_database_health(self) -> HealthCheck:
        """Comprehensive database health check."""
        try:
            start_time = time.time()
            metrics = {}
            details = {}
            recommendations = []
            
            # Test basic connection
            from sqlalchemy import text

            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                if not result:
                    raise Exception("Database query returned no result")
            
            query_time = (time.time() - start_time) * 1000
            metrics['query_time_ms'] = query_time
            
            # Connection pool information
            if hasattr(engine.pool, 'size'):
                pool_info = {
                    'pool_size': engine.pool.size(),
                    'checked_in': engine.pool.checkedin(),
                    'checked_out': engine.pool.checkedout(),
                    'overflow': engine.pool.overflow(),
                    'invalid': engine.pool.invalidated()
                }
                metrics.update(pool_info)
                details['pool_info'] = pool_info
                
                # Check for connection pool issues
                if pool_info['checked_out'] > pool_info['pool_size'] * 0.8:
                    recommendations.append('High connection pool usage detected')
            
            # Database size and performance
            try:
                from src.core.database_manager import db_manager
                with db_manager:
                    # Get table counts for monitoring
                    from src.database.models import Guild, User, Playlist, Song, Usage
                    
                    table_counts = {
                        'guilds': db_manager.session.query(Guild).count(),
                        'users': db_manager.session.query(User).count(),
                        'playlists': db_manager.session.query(Playlist).count(),
                        'songs': db_manager.session.query(Song).count(),
                        'usage_logs': db_manager.session.query(Usage).count()
                    }
                    
                    metrics.update(table_counts)
                    details['table_counts'] = table_counts
                    
                    # Check for unusual growth
                    total_records = sum(table_counts.values())
                    if total_records > 1000000:  # 1 million records
                        recommendations.append('Large database detected, consider archiving old data')
                        
            except Exception as db_error:
                details['table_check_error'] = str(db_error)
                recommendations.append('Could not retrieve table statistics')
            
            # Determine status
            if query_time > 5000:  # 5 seconds
                status = HealthStatus.UNHEALTHY
                message = f"Database critically slow: {query_time:.0f}ms"
                recommendations.extend([
                    'Check database server performance',
                    'Optimize database queries',
                    'Consider database maintenance'
                ])
            elif query_time > 1000:  # 1 second
                status = HealthStatus.DEGRADED
                message = f"Database slow response: {query_time:.0f}ms"
                recommendations.append('Monitor database performance')
            else:
                status = HealthStatus.HEALTHY
                message = f"Database healthy, response time: {query_time:.0f}ms"
            
            return HealthCheck(
                name="database_health",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="database_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=[
                    'Check database server status',
                    'Verify connection string',
                    'Check network connectivity to database'
                ]
            )
    
    async def check_system_resources(self) -> HealthCheck:
        """Comprehensive system resource monitoring."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            
            metrics.update({
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_average': load_avg[0] if load_avg else None
            })
            
            # Memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.update({
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_percent': memory.percent,
                'memory_used': memory.used,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent
            })
            
            # Disk information
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.update({
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                'disk_write_bytes': disk_io.write_bytes if disk_io else 0
            })
            
            # Network information
            network = psutil.net_io_counters()
            metrics.update({
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'network_packets_sent': network.packets_sent,
                'network_packets_recv': network.packets_recv
            })
            
            # Process-specific information
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics.update({
                'process_memory_rss': process_memory.rss,
                'process_memory_vms': process_memory.vms,
                'process_memory_percent': process.memory_percent(),
                'process_cpu_percent': process.cpu_percent(),
                'process_num_threads': process.num_threads(),
                'process_num_fds': process.num_fds() if hasattr(process, 'num_fds') else None
            })
            
            details.update({
                'boot_time': psutil.boot_time(),
                'process_create_time': process.create_time(),
                'python_memory_info': {
                    'rss_mb': process_memory.rss / 1024 / 1024,
                    'vms_mb': process_memory.vms / 1024 / 1024
                }
            })
            
            # Determine overall system status
            critical_issues = []
            warning_issues = []
            
            if cpu_percent > self.thresholds['cpu_critical']:
                critical_issues.append(f"Critical CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > self.thresholds['cpu_warning']:
                warning_issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory.percent > self.thresholds['memory_critical']:
                critical_issues.append(f"Critical memory usage: {memory.percent:.1f}%")
            elif memory.percent > self.thresholds['memory_warning']:
                warning_issues.append(f"High memory usage: {memory.percent:.1f}%")
            
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > self.thresholds['disk_critical']:
                critical_issues.append(f"Critical disk usage: {disk_percent:.1f}%")
            elif disk_percent > self.thresholds['disk_warning']:
                warning_issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            # Generate recommendations
            if cpu_percent > self.thresholds['cpu_warning']:
                recommendations.extend([
                    'Monitor CPU-intensive processes',
                    'Consider scaling resources',
                    'Check for infinite loops or heavy operations'
                ])
            
            if memory.percent > self.thresholds['memory_warning']:
                recommendations.extend([
                    'Monitor memory usage trends',
                    'Check for memory leaks',
                    'Consider increasing system memory'
                ])
            
            if disk_percent > self.thresholds['disk_warning']:
                recommendations.extend([
                    'Clean up temporary files',
                    'Archive old logs',
                    'Monitor disk usage growth'
                ])
            
            # Determine status
            if critical_issues:
                status = HealthStatus.UNHEALTHY
                message = "; ".join(critical_issues)
            elif warning_issues:
                status = HealthStatus.DEGRADED  
                message = "; ".join(warning_issues)
            else:
                status = HealthStatus.HEALTHY
                message = f"System resources healthy - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Disk: {disk_percent:.1f}%"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.ERROR,
                message=f"System resource check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check system monitoring tools']
            )
    
    async def check_voice_connections(self) -> HealthCheck:
        """Comprehensive voice connection health check."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            total_connections = len(music_manager.voice_clients)
            healthy_connections = 0
            issues = []
            connection_details = []
            
            current_time = time.time()
            
            for guild_id, vc in music_manager.voice_clients.items():
                try:
                    connection_info = {
                        'guild_id': guild_id,
                        'connected': vc.is_connected() if vc else False,
                        'playing': vc.is_playing() if vc else False,
                        'paused': vc.is_paused() if vc else False,
                        'channel': vc.channel.name if vc and vc.channel else None,
                        'latency': getattr(vc, 'latency', None)
                    }
                    
                    if vc and vc.is_connected():
                        healthy_connections += 1
                        
                        # Check for stale connections
                        last_activity = music_manager.last_activity.get(guild_id, current_time)
                        inactive_time = current_time - last_activity
                        
                        if inactive_time > 3600:  # 1 hour
                            connection_info['stale'] = True
                            connection_info['inactive_minutes'] = inactive_time / 60
                            issues.append(f'Guild {guild_id}: inactive for {inactive_time/60:.0f} minutes')
                        
                        # Check for connection quality issues
                        if hasattr(vc, 'latency') and vc.latency and vc.latency > 0.5:
                            connection_info['high_latency'] = True
                            issues.append(f'Guild {guild_id}: high voice latency ({vc.latency*1000:.0f}ms)')
                    else:
                        connection_info['issue'] = 'disconnected'
                        issues.append(f'Guild {guild_id}: disconnected')
                    
                    connection_details.append(connection_info)
                    
                except Exception as e:
                    issues.append(f'Guild {guild_id}: error checking connection - {str(e)}')
                    connection_details.append({
                        'guild_id': guild_id,
                        'error': str(e)
                    })
            
            metrics.update({
                'total_connections': total_connections,
                'healthy_connections': healthy_connections,
                'connection_success_rate': (healthy_connections / max(1, total_connections)) * 100,
                'issues_count': len(issues)
            })
            
            details['connections'] = connection_details[:10]  # Limit details
            details['issues'] = issues[:20]  # Limit issues
            
            # Determine status
            if total_connections == 0:
                status = HealthStatus.HEALTHY
                message = 'No active voice connections'
            elif healthy_connections == total_connections and len(issues) == 0:
                status = HealthStatus.HEALTHY
                message = f'All {total_connections} voice connections healthy'
            elif healthy_connections / max(1, total_connections) >= 0.8:
                status = HealthStatus.DEGRADED
                message = f'{healthy_connections}/{total_connections} voice connections healthy'
                recommendations.extend([
                    'Monitor voice connection stability',
                    'Check Discord API status for voice'
                ])
            else:
                status = HealthStatus.UNHEALTHY
                message = f'Multiple voice connection issues: {healthy_connections}/{total_connections} healthy'
                recommendations.extend([
                    'Restart voice connections',
                    'Check Discord voice API status',
                    'Verify bot voice permissions'
                ])
            
            # Add recommendations for stale connections
            stale_count = len([i for i in issues if 'inactive' in i])
            if stale_count > 0:
                recommendations.append(f'Clean up {stale_count} stale voice connections')
            
            return HealthCheck(
                name="voice_connections",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="voice_connections",
                status=HealthStatus.ERROR,
                message=f"Voice connection check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check music manager status']
            )
    
    async def check_music_manager_health(self) -> HealthCheck:
        """Comprehensive music manager health check."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Basic music manager stats
            total_queued = sum(len(queue) for queue in music_manager.queues.values())
            active_sessions = len([guild_id for guild_id in music_manager.now_playing])
            total_guilds_tracked = len(music_manager.last_activity)
            
            # Get music manager metrics
            manager_metrics = music_manager.get_metrics()
            
            metrics.update({
                'total_queued': total_queued,
                'active_sessions': active_sessions,
                'total_guilds_tracked': total_guilds_tracked,
                'songs_played': manager_metrics.get('songs_played', 0),
                'total_playtime': manager_metrics.get('total_playtime', 0),
                'queue_adds': manager_metrics.get('queue_adds', 0),
                'errors': manager_metrics.get('errors', 0)
            })
            
            # Check for potential issues
            issues = []
            current_time = time.time()
            
            # Check for oversized queues
            oversized_queues = []
            for guild_id, queue in music_manager.queues.items():
                if len(queue) > 100:  # Arbitrary large queue size
                    oversized_queues.append((guild_id, len(queue)))
            
            if oversized_queues:
                issues.append(f'{len(oversized_queues)} guilds with oversized queues')
                details['oversized_queues'] = oversized_queues[:5]
                recommendations.append('Monitor queue sizes and implement limits')
            
            # Check for stale now_playing entries
            stale_playing = []
            for guild_id, now_playing in music_manager.now_playing.items():
                if hasattr(now_playing, 'start_time'):
                    playing_duration = current_time - now_playing.start_time
                    if playing_duration > 7200:  # 2 hours
                        stale_playing.append((guild_id, playing_duration))
            
            if stale_playing:
                issues.append(f'{len(stale_playing)} potentially stale playing sessions')
                details['stale_playing'] = stale_playing[:5]
                recommendations.append('Check for stuck playback sessions')
            
            # Check search cache size
            search_cache_size = len(getattr(music_manager, 'search_results', {}))
            if search_cache_size > 10000:
                issues.append(f'Large search cache: {search_cache_size} entries')
                recommendations.append('Clear search cache periodically')
            
            metrics['search_cache_size'] = search_cache_size
            
            # Performance analysis
            if manager_metrics.get('errors', 0) > 0:
                error_rate = manager_metrics['errors'] / max(1, manager_metrics.get('songs_played', 1))
                if error_rate > 0.1:  # 10% error rate
                    issues.append(f'High error rate: {error_rate*100:.1f}%')
                    recommendations.extend([
                        'Investigate common error causes',
                        'Check YouTube API status',
                        'Verify FFmpeg installation'
                    ])
                metrics['error_rate'] = error_rate
            
            # Determine status
            if len(issues) == 0:
                status = HealthStatus.HEALTHY
                message = 'Music manager operating normally'
            elif len(issues) <= 2:
                status = HealthStatus.DEGRADED
                message = f'Music manager has minor issues: {"; ".join(issues[:2])}'
            else:
                status = HealthStatus.UNHEALTHY
                message = f'Music manager has multiple issues: {len(issues)} problems detected'
                recommendations.append('Consider restarting music manager')
            
            return HealthCheck(
                name="music_manager_health",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="music_manager_health",
                status=HealthStatus.ERROR,
                message=f"Music manager check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check music manager initialization']
            )
    
    async def check_error_rates(self) -> HealthCheck:
        """Comprehensive error rate monitoring."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Get error information from bot's error handler
            total_errors = 0
            recent_errors = []
            error_types = {}
            
            if hasattr(self.bot, 'error_handler'):
                error_handler = self.bot.error_handler
                total_errors = getattr(error_handler, 'error_count', 0)
                recent_errors = getattr(error_handler, 'recent_errors', [])
                
                # Analyze error types
                for error in recent_errors:
                    error_type = error.get('error_type', 'Unknown')
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Calculate error rate (errors per hour)
            uptime_hours = (time.time() - getattr(self.bot, 'startup_time', time.time())) / 3600
            error_rate = len(recent_errors) / max(1, uptime_hours)
            
            # Recent error rate (last hour)
            current_time = time.time()
            recent_hour_errors = [
                e for e in recent_errors 
                if current_time - e.get('timestamp', 0) < 3600
            ]
            recent_error_rate = len(recent_hour_errors)
            
            metrics.update({
                'total_errors': total_errors,
                'recent_errors_count': len(recent_errors),
                'error_rate_per_hour': error_rate,
                'recent_hour_error_rate': recent_error_rate,
                'unique_error_types': len(error_types)
            })
            
            details.update({
                'error_types': error_types,
                'recent_errors': recent_errors[-10:],  # Last 10 errors
                'top_errors': sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
            })
            
            # Track error rate history
            self.error_tracking['error_rate_history'].append({
                'timestamp': current_time,
                'error_rate': recent_error_rate
            })
            
            # Keep only last 24 hours of history
            cutoff_time = current_time - 86400
            self.error_tracking['error_rate_history'] = [
                entry for entry in self.error_tracking['error_rate_history']
                if entry['timestamp'] > cutoff_time
            ]
            
            # Determine status and recommendations
            if recent_error_rate > self.thresholds['error_rate_critical']:
                status = HealthStatus.UNHEALTHY
                message = f'Critical error rate: {recent_error_rate} errors/hour'
                recommendations.extend([
                    'Investigate immediate error causes',
                    'Check system logs',
                    'Consider emergency restart if errors persist'
                ])
            elif recent_error_rate > self.thresholds['error_rate_warning']:
                status = HealthStatus.DEGRADED
                message = f'High error rate: {recent_error_rate} errors/hour'
                recommendations.extend([
                    'Monitor error trends',
                    'Review recent changes',
                    'Check for system resource issues'
                ])
            elif len(recent_errors) > 0:
                status = HealthStatus.HEALTHY
                message = f'Normal error rate: {recent_error_rate} errors/hour, {len(recent_errors)} total recent'
                if len(error_types) > 5:
                    recommendations.append('Variety of error types detected, review error handling')
            else:
                status = HealthStatus.HEALTHY
                message = 'No recent errors detected'
            
            # Add specific recommendations based on error types
            if 'ConnectionClosed' in error_types:
                recommendations.append('Discord connection issues detected - check network')
            if 'HTTPException' in error_types:
                recommendations.append('Discord API errors detected - check rate limits')
            if 'YouTubeError' in error_types:
                recommendations.append('YouTube API issues detected - check service status')
            
            return HealthCheck(
                name="error_rates",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="error_rates",
                status=HealthStatus.ERROR,
                message=f"Error rate check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check error tracking system']
            )
    
    async def check_performance_metrics(self) -> HealthCheck:
        """Monitor overall performance metrics."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Command performance from database
            try:
                from src.core.database_manager import db_manager
                with db_manager:
                    from src.database.models import Usage
                    
                    # Recent command usage (last 24 hours)
                    recent_usage = db_manager.session.query(Usage).filter(
                        Usage.timestamp >= datetime.utcnow() - timedelta(hours=24)
                    ).all()
                    
                    total_commands = len(recent_usage)
                    successful_commands = len([c for c in recent_usage if c.success])
                    
                    # Execution time analysis
                    execution_times = [c.execution_time for c in recent_usage if c.execution_time]
                    avg_execution_time = sum(execution_times) / max(1, len(execution_times))
                    max_execution_time = max(execution_times) if execution_times else 0
                    
                    # Success rate
                    success_rate = (successful_commands / max(1, total_commands)) * 100
                    
                    metrics.update({
                        'commands_24h': total_commands,
                        'success_rate': success_rate,
                        'avg_execution_time_ms': avg_execution_time,
                        'max_execution_time_ms': max_execution_time,
                        'failed_commands': total_commands - successful_commands
                    })
                    
                    # Command frequency analysis
                    command_counts = {}
                    for cmd in recent_usage:
                        command_counts[cmd.command_name] = command_counts.get(cmd.command_name, 0) + 1
                    
                    details['popular_commands'] = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    # Performance trends
                    if avg_execution_time > 1000:  # 1 second
                        recommendations.append('High average command execution time detected')
                    
                    if success_rate < 95:
                        recommendations.append(f'Command success rate below 95%: {success_rate:.1f}%')
                    
            except Exception as db_error:
                details['database_error'] = str(db_error)
                recommendations.append('Could not retrieve command performance data')
            
            # Memory usage trends
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            metrics['current_memory_mb'] = current_memory
            
            # Store performance history
            self.performance_history.append({
                'timestamp': time.time(),
                'memory_mb': current_memory,
                'cpu_percent': psutil.cpu_percent(),
                'commands_per_hour': total_commands if 'total_commands' in locals() else 0
            })
            
            # Keep only last 24 hours
            cutoff_time = time.time() - 86400
            self.performance_history = [
                entry for entry in self.performance_history
                if entry['timestamp'] > cutoff_time
            ]
            
            # Analyze trends
            if len(self.performance_history) > 10:
                recent_memory = [entry['memory_mb'] for entry in self.performance_history[-10:]]
                memory_trend = (recent_memory[-1] - recent_memory[0]) / recent_memory[0] * 100
                
                if memory_trend > 20:  # 20% increase
                    recommendations.append(f'Memory usage increasing trend: +{memory_trend:.1f}%')
                    details['memory_trend'] = memory_trend
            
            # Determine overall performance status
            issues = []
            
            if 'success_rate' in metrics and metrics['success_rate'] < 90:
                issues.append(f"Low success rate: {metrics['success_rate']:.1f}%")
            
            if 'avg_execution_time_ms' in metrics and metrics['avg_execution_time_ms'] > 2000:
                issues.append(f"Slow commands: {metrics['avg_execution_time_ms']:.0f}ms avg")
            
            if current_memory > 1000:  # 1GB
                issues.append(f"High memory usage: {current_memory:.0f}MB")
            
            if len(issues) == 0:
                status = HealthStatus.HEALTHY
                message = 'Performance metrics within normal ranges'
            elif len(issues) == 1:
                status = HealthStatus.DEGRADED
                message = f'Performance concern: {issues[0]}'
            else:
                status = HealthStatus.UNHEALTHY
                message = f'Multiple performance issues: {len(issues)} detected'
            
            return HealthCheck(
                name="performance_metrics",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="performance_metrics",
                status=HealthStatus.ERROR,
                message=f"Performance check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check performance monitoring system']
            )
    
    async def check_discord_api_health(self) -> HealthCheck:
        """Check Discord API health and rate limiting."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Check bot's rate limiting status
            if hasattr(self.bot, 'http'):
                http_client = self.bot.http
                
                # Get rate limit information
                if hasattr(http_client, '_global_over'):
                    metrics['global_rate_limited'] = http_client._global_over.is_set()
                
                # Check for recent rate limit hits
                if hasattr(http_client, '_rate_limit_logs'):
                    recent_limits = getattr(http_client, '_rate_limit_logs', [])
                    metrics['recent_rate_limits'] = len(recent_limits)
                    details['rate_limit_details'] = recent_limits[-5:]  # Last 5
            
            # API response time test
            start_time = time.time()
            try:
                # Simple API call to test responsiveness
                if self.bot.is_ready() and self.bot.guilds:
                    guild = self.bot.guilds[0]
                    await guild.fetch_channels()
                    api_response_time = (time.time() - start_time) * 1000
                    metrics['api_response_time_ms'] = api_response_time
                    
                    if api_response_time > 5000:  # 5 seconds
                        recommendations.append('Slow Discord API response time')
                else:
                    details['api_test'] = 'Skipped - bot not ready or no guilds'
            except Exception as api_error:
                details['api_test_error'] = str(api_error)
                recommendations.append('Discord API test failed')
            
            # Check shard health if applicable
            if hasattr(self.bot, 'shard_count') and self.bot.shard_count:
                shard_info = {}
                for shard_id in range(self.bot.shard_count):
                    shard = self.bot.get_shard(shard_id)
                    if shard:
                        shard_info[shard_id] = {
                            'latency': shard.latency,
                            'is_closed': shard.is_closed()
                        }
                
                metrics['shard_count'] = self.bot.shard_count
                details['shard_info'] = shard_info
            
            # Determine status
            status = HealthStatus.HEALTHY
            message = 'Discord API connection healthy'
            
            if metrics.get('global_rate_limited', False):
                status = HealthStatus.DEGRADED
                message = 'Global rate limiting active'
                recommendations.append('Reduce API call frequency')
            
            if metrics.get('recent_rate_limits', 0) > 10:
                status = HealthStatus.DEGRADED
                message = 'Frequent rate limiting detected'
                recommendations.extend([
                    'Review API usage patterns',
                    'Implement better rate limiting',
                    'Consider request batching'
                ])
            
            if metrics.get('api_response_time_ms', 0) > 10000:  # 10 seconds
                status = HealthStatus.UNHEALTHY
                message = 'Discord API extremely slow'
                recommendations.extend([
                    'Check Discord API status',
                    'Verify network connectivity',
                    'Consider using different server region'
                ])
            
            return HealthCheck(
                name="discord_api_health",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="discord_api_health",
                status=HealthStatus.ERROR,
                message=f"Discord API check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check Discord API connectivity']
            )
    
    async def check_memory_leaks(self) -> HealthCheck:
        """Detect potential memory leaks."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            process = psutil.Process()
            current_memory = process.memory_info().rss
            memory_percent = process.memory_percent()
            
            metrics.update({
                'current_memory_bytes': current_memory,
                'current_memory_mb': current_memory / 1024 / 1024,
                'memory_percent': memory_percent
            })
            
            # Memory growth analysis
            if len(self.performance_history) > 5:
                memory_history = [entry['memory_mb'] for entry in self.performance_history[-20:]]
                
                if len(memory_history) >= 2:
                    # Calculate memory growth rate
                    initial_memory = memory_history[0]
                    current_memory_mb = memory_history[-1]
                    growth_rate = (current_memory_mb - initial_memory) / initial_memory * 100
                    
                    metrics['memory_growth_rate'] = growth_rate
                    details['memory_history'] = memory_history[-10:]  # Last 10 entries
                    
                    # Check for concerning growth
                    if growth_rate > 50:  # 50% growth
                        recommendations.extend([
                            'Significant memory growth detected',
                            'Check for memory leaks',
                            'Monitor object retention',
                            'Consider garbage collection tuning'
                        ])
                    elif growth_rate > 20:  # 20% growth
                        recommendations.append('Monitor memory usage trends')
            
            # Check for specific memory-intensive components
            # Music manager memory usage
            queue_sizes = [len(queue) for queue in music_manager.queues.values()]
            total_queue_items = sum(queue_sizes)
            
            if total_queue_items > 10000:
                recommendations.append(f'Large queue memory usage: {total_queue_items} items')
            
            # Check search cache size
            search_cache_size = len(getattr(music_manager, 'search_results', {}))
            if search_cache_size > 5000:
                recommendations.append(f'Large search cache: {search_cache_size} entries')
            
            metrics.update({
                'total_queue_items': total_queue_items,
                'search_cache_size': search_cache_size
            })
            
            # Memory threshold checks
            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f'Critical memory usage: {memory_percent:.1f}%'
                recommendations.extend([
                    'Immediate memory cleanup required',
                    'Consider restarting the bot',
                    'Check for memory leaks'
                ])
            elif memory_percent > 75:
                status = HealthStatus.DEGRADED
                message = f'High memory usage: {memory_percent:.1f}%'
                recommendations.append('Monitor memory usage closely')
            else:
                status = HealthStatus.HEALTHY
                message = f'Memory usage normal: {memory_percent:.1f}%'
            
            return HealthCheck(
                name="memory_leaks",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="memory_leaks",
                status=HealthStatus.ERROR,
                message=f"Memory leak check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check memory monitoring system']
            )
    
    async def check_file_system_health(self) -> HealthCheck:
        """Check file system health and disk space."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Check main disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            metrics.update({
                'disk_total_bytes': disk_usage.total,
                'disk_used_bytes': disk_usage.used,
                'disk_free_bytes': disk_usage.free,
                'disk_percent': disk_percent
            })
            
            # Check specific directories
            important_dirs = ['logs', 'data', 'downloads']
            dir_info = {}
            
            for dir_name in important_dirs:
                try:
                    import os
                    if os.path.exists(dir_name):
                        dir_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(dir_name)
                            for filename in filenames
                        )
                        dir_info[dir_name] = {
                            'size_bytes': dir_size,
                            'size_mb': dir_size / 1024 / 1024
                        }
                except Exception as dir_error:
                    dir_info[dir_name] = {'error': str(dir_error)}
            
            details['directory_sizes'] = dir_info
            
            # Check log file sizes
            try:
                log_file = getattr(settings, 'log_file', 'logs/basslinebot.log')
                if os.path.exists(log_file):
                    log_size = os.path.getsize(log_file)
                    metrics['log_file_size_mb'] = log_size / 1024 / 1024
                    
                    if log_size > 100 * 1024 * 1024:  # 100MB
                        recommendations.append('Log file is large, consider rotation')
            except Exception:
                pass
            
            # Check download cache if applicable
            downloads_size = dir_info.get('downloads', {}).get('size_mb', 0)
            if downloads_size > 1000:  # 1GB
                recommendations.append(f'Downloads directory is large: {downloads_size:.0f}MB')
            
            # I/O statistics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics.update({
                    'disk_read_count': disk_io.read_count,
                    'disk_write_count': disk_io.write_count,
                    'disk_read_bytes': disk_io.read_bytes,
                    'disk_write_bytes': disk_io.write_bytes
                })
            
            # Determine status
            if disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f'Critical disk space: {disk_percent:.1f}% used'
                recommendations.extend([
                    'Free disk space immediately',
                    'Clean up temporary files',
                    'Archive old logs'
                ])
            elif disk_percent > 85:
                status = HealthStatus.DEGRADED
                message = f'Low disk space: {disk_percent:.1f}% used'
                recommendations.append('Monitor disk usage and plan cleanup')
            else:
                status = HealthStatus.HEALTHY
                message = f'Disk space healthy: {disk_percent:.1f}% used'
            
            return HealthCheck(
                name="file_system_health",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="file_system_health",
                status=HealthStatus.ERROR,
                message=f"File system check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check file system access']
            )
    
    async def check_network_connectivity(self) -> HealthCheck:
        """Check network connectivity and performance."""
        try:
            metrics = {}
            details = {}
            recommendations = []
            
            # Network I/O statistics
            network_io = psutil.net_io_counters()
            metrics.update({
                'bytes_sent': network_io.bytes_sent,
                'bytes_received': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_received': network_io.packets_recv,
                'errors_in': network_io.errin,
                'errors_out': network_io.errout,
                'drops_in': network_io.dropin,
                'drops_out': network_io.dropout
            })
            
            # Check for network errors
            total_errors = network_io.errin + network_io.errout
            total_drops = network_io.dropin + network_io.dropout
            
            if total_errors > 0:
                recommendations.append(f'Network errors detected: {total_errors}')
            
            if total_drops > 0:
                recommendations.append(f'Network packet drops detected: {total_drops}')
            
            # Test connectivity to important services
            connectivity_tests = {}
            
            try:
                # Test Discord API connectivity
                import aiohttp
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    start_time = time.time()
                    async with session.get('https://discord.com/api/v10/gateway') as response:
                        discord_response_time = (time.time() - start_time) * 1000
                        connectivity_tests['discord_api'] = {
                            'status': response.status,
                            'response_time_ms': discord_response_time
                        }
            except Exception as e:
                connectivity_tests['discord_api'] = {'error': str(e)}
                recommendations.append('Discord API connectivity issue')
            
            # Test YouTube connectivity (if using yt-dlp)
            try:
                start_time = time.time()
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get('https://www.youtube.com') as response:
                        youtube_response_time = (time.time() - start_time) * 1000
                        connectivity_tests['youtube'] = {
                            'status': response.status,
                            'response_time_ms': youtube_response_time
                        }
            except Exception as e:
                connectivity_tests['youtube'] = {'error': str(e)}
                recommendations.append('YouTube connectivity issue')
            
            details['connectivity_tests'] = connectivity_tests
            
            # Determine status based on connectivity tests
            failed_tests = [name for name, result in connectivity_tests.items() if 'error' in result]
            
            if len(failed_tests) >= 2:
                status = HealthStatus.UNHEALTHY
                message = f'Multiple connectivity issues: {", ".join(failed_tests)}'
                recommendations.extend([
                    'Check internet connection',
                    'Verify DNS resolution',
                    'Check firewall settings'
                ])
            elif len(failed_tests) == 1:
                status = HealthStatus.DEGRADED
                message = f'Connectivity issue with {failed_tests[0]}'
                recommendations.append('Monitor network connectivity')
            else:
                status = HealthStatus.HEALTHY
                message = 'Network connectivity healthy'
            
            return HealthCheck(
                name="network_connectivity",
                status=status,
                message=message,
                timestamp=time.time(),
                metrics=metrics,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return HealthCheck(
                name="network_connectivity",
                status=HealthStatus.ERROR,
                message=f"Network connectivity check failed: {str(e)}",
                timestamp=time.time(),
                metrics={},
                recommendations=['Check network monitoring system']
            )
    
    async def analyze_trends(self):
        """Analyze performance trends and predict issues."""
        try:
            if len(self.performance_history) < 10:
                return  # Not enough data for trend analysis
            
            # Analyze memory usage trends
            memory_values = [entry['memory_mb'] for entry in self.performance_history[-20:]]
            if len(memory_values) >= 5:
                # Simple linear regression to detect trends
                x_values = list(range(len(memory_values)))
                n = len(memory_values)
                
                sum_x = sum(x_values)
                sum_y = sum(memory_values)
                sum_xy = sum(x * y for x, y in zip(x_values, memory_values))
                sum_x_squared = sum(x * x for x in x_values)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
                
                # If slope is positive and significant, we have a growing trend
                if slope > 5:  # 5MB per measurement period
                    logger.warning(f"Memory usage trending upward: +{slope:.2f}MB per period")
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
    
    async def generate_alerts(self):
        """Generate alerts based on health check results."""
        try:
            critical_checks = [
                check for check in self.checks.values()
                if check.status == HealthStatus.UNHEALTHY
            ]
            
            if critical_checks:
                alert_message = f"CRITICAL: {len(critical_checks)} systems unhealthy"
                logger.critical(alert_message)
                
                # Could integrate with external alerting systems here
                # (Slack, Discord webhook, email, etc.)
                
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        if not self.checks:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No health checks have been run yet',
                'timestamp': time.time(),
                'check_count': 0
            }
        
        # Count status types  
        status_counts = {}
        for check in self.checks.values():
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Determine overall status
        if status_counts.get('unhealthy', 0) > 0 or status_counts.get('error', 0) > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts.get('degraded', 0) > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'status': overall_status.value,
            'message': f'Overall system health: {overall_status.value}',
            'timestamp': time.time(),
            'check_count': len(self.checks),
            'status_breakdown': status_counts,
            'last_check': self.last_check
        }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information for dashboard."""
        overall = self.get_overall_health()
        
        # Convert checks to serializable format
        checks_data = {}
        for name, check in self.checks.items():
            checks_data[name] = {
                'name': check.name,
                'status': check.status.value,
                'message': check.message,
                'timestamp': check.timestamp,
                'metrics': check.metrics,
                'details': check.details,
                'recommendations': check.recommendations
            }
        
        return {
            'overall': overall,
            'checks': checks_data,
            'system_info': {
                'uptime': time.time() - (getattr(self.bot, 'startup_time', time.time())),
                'guild_count': len(self.bot.guilds) if self.bot and self.bot.is_ready() else 0,
                'user_count': sum(g.member_count or 0 for g in self.bot.guilds) if self.bot and self.bot.is_ready() else 0,
                'voice_connections': len(music_manager.voice_clients),
                'active_queues': len([q for q in music_manager.queues.values() if q])
            },
            'performance_history': self.performance_history[-50:],  # Last 50 entries
            'error_tracking': self.error_tracking
        }

# Global health monitor instance
health_monitor = None

def get_health_monitor(bot=None):
    """Get or create health monitor instance."""
    global health_monitor
    if health_monitor is None and bot:
        health_monitor = EnhancedHealthMonitor(bot)
    return health_monitor