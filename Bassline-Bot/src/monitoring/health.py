"""Health monitoring and checks for BasslineBot Pro."""

import asyncio
import logging
import time
import psutil
from typing import Dict, Any, List
from datetime import datetime, timedelta

from config.settings import settings
from config.database import engine
from src.core.music_manager import music_manager

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Health monitoring system for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.checks = {}
        self.last_check = time.time()
        self.check_interval = 30  # seconds
        self.alerts = []
        
    async def start_monitoring(self):
        """Start the health monitoring task."""
        while True:
            try:
                await self.run_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def run_health_checks(self):
        """Run all health checks."""
        self.last_check = time.time()
        
        checks = [
            self.check_bot_connection(),
            self.check_database_connection(),
            self.check_system_resources(),
            self.check_voice_connections(),
            self.check_music_manager(),
            self.check_error_rates(),
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for i, result in enumerate(results):
            check_name = checks[i].__name__
            if isinstance(result, Exception):
                self.checks[check_name] = {
                    'status': 'error',
                    'message': str(result),
                    'timestamp': time.time()
                }
                logger.error(f"Health check {check_name} failed: {result}")
            else:
                self.checks[check_name] = result
    
    async def check_bot_connection(self) -> Dict[str, Any]:
        """Check Discord bot connection."""
        try:
            if not self.bot.is_ready():
                return {
                    'status': 'unhealthy',
                    'message': 'Bot is not ready',
                    'timestamp': time.time()
                }
            
            if self.bot.is_closed():
                return {
                    'status': 'unhealthy',
                    'message': 'Bot connection is closed',
                    'timestamp': time.time()
                }
            
            # Check latency
            latency = self.bot.latency * 1000
            if latency > 1000:  # More than 1 second
                return {
                    'status': 'degraded',
                    'message': f'High latency: {latency:.2f}ms',
                    'timestamp': time.time(),
                    'metrics': {'latency_ms': latency}
                }
            
            return {
                'status': 'healthy',
                'message': 'Bot connection is stable',
                'timestamp': time.time(),
                'metrics': {
                    'latency_ms': latency,
                    'guild_count': len(self.bot.guilds)
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Bot connection check failed: {str(e)}',
                'timestamp': time.time()
            }
    
    async def check_database_connection(self) -> Dict[str, Any]:
        """Check database connection."""
        try:
            start_time = time.time()
            
            # Test database connection
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").fetchone()
                if not result:
                    raise Exception("Database query returned no result")
            
            query_time = (time.time() - start_time) * 1000
            
            if query_time > 1000:  # More than 1 second
                return {
                    'status': 'degraded',
                    'message': f'Slow database response: {query_time:.2f}ms',
                    'timestamp': time.time(),
                    'metrics': {'query_time_ms': query_time}
                }
            
            return {
                'status': 'healthy',
                'message': 'Database connection is stable',
                'timestamp': time.time(),
                'metrics': {'query_time_ms': query_time}
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}',
                'timestamp': time.time()
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check thresholds
            issues = []
            status = 'healthy'
            
            if cpu_percent > 90:
                issues.append(f'High CPU usage: {cpu_percent:.1f}%')
                status = 'degraded'
            
            if memory.percent > 90:
                issues.append(f'High memory usage: {memory.percent:.1f}%')
                status = 'degraded'
            
            if disk.percent > 90:
                issues.append(f'High disk usage: {disk.percent:.1f}%')
                status = 'degraded'
            
            message = '; '.join(issues) if issues else 'System resources are normal'
            
            return {
                'status': status,
                'message': message,
                'timestamp': time.time(),
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'System resource check failed: {str(e)}',
                'timestamp': time.time()
            }
    
    async def check_voice_connections(self) -> Dict[str, Any]:
        """Check voice connections health."""
        try:
            total_connections = len(music_manager.voice_clients)
            healthy_connections = 0
            issues = []
            
            for guild_id, vc in music_manager.voice_clients.items():
                try:
                    if vc.is_connected():
                        healthy_connections += 1
                    else:
                        issues.append(f'Guild {guild_id}: disconnected')
                except Exception as e:
                    issues.append(f'Guild {guild_id}: {str(e)}')
            
            if total_connections == 0:
                status = 'healthy'
                message = 'No active voice connections'
            elif healthy_connections == total_connections:
                status = 'healthy'
                message = f'All {total_connections} voice connections are healthy'
            else:
                status = 'degraded'
                message = f'{healthy_connections}/{total_connections} voice connections healthy'
            
            return {
                'status': status,
                'message': message,
                'timestamp': time.time(),
                'metrics': {
                    'total_connections': total_connections,
                    'healthy_connections': healthy_connections,
                    'issues': issues[:10]  # Limit to prevent overflow
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Voice connection check failed: {str(e)}',
                'timestamp': time.time()
            }
    
    async def check_music_manager(self) -> Dict[str, Any]:
        """Check music manager health."""
        try:
            total_queued = sum(len(queue) for queue in music_manager.queues.values())
            active_sessions = len([guild_id for guild_id in music_manager.now_playing])
            
            # Check for stale sessions
            current_time = time.time()
            stale_sessions = []
            
            for guild_id, last_activity in music_manager.last_activity.items():
                if current_time - last_activity > 3600:  # 1 hour
                    stale_sessions.append(guild_id)
            
            status = 'healthy'
            issues = []
            
            if len(stale_sessions) > 0:
                issues.append(f'{len(stale_sessions)} stale sessions detected')
                status = 'degraded'
            
            if total_queued > 10000:  # Arbitrary large number
                issues.append(f'Very large total queue: {total_queued}')
                status = 'degraded'
            
            message = '; '.join(issues) if issues else 'Music manager is operating normally'
            
            return {
                'status': status,
                'message': message,
                'timestamp': time.time(),
                'metrics': {
                    'total_queued': total_queued,
                    'active_sessions': active_sessions,
                    'stale_sessions': len(stale_sessions),
                    'total_guilds_tracked': len(music_manager.last_activity)
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Music manager check failed: {str(e)}',
                'timestamp': time.time()
            }
    
    async def check_error_rates(self) -> Dict[str, Any]:
        """Check recent error rates."""
        try:
            # This would typically check error logs or metrics
            # For now, we'll use a simple check
            
            if hasattr(self.bot, 'error_handler'):
                error_count = self.bot.error_handler.error_count
                recent_errors = len(self.bot.error_handler.recent_errors)
                
                if recent_errors > 100:  # More than 100 recent errors
                    return {
                        'status': 'degraded',
                        'message': f'High error rate: {recent_errors} recent errors',
                        'timestamp': time.time(),
                        'metrics': {
                            'total_errors': error_count,
                            'recent_errors': recent_errors
                        }
                    }
            
            return {
                'status': 'healthy',
                'message': 'Error rates are normal',
                'timestamp': time.time(),
                'metrics': {
                    'total_errors': getattr(self.bot.error_handler, 'error_count', 0) if hasattr(self.bot, 'error_handler') else 0,
                    'recent_errors': len(getattr(self.bot.error_handler, 'recent_errors', [])) if hasattr(self.bot, 'error_handler') else 0
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error rate check failed: {str(e)}',
                'timestamp': time.time()
            }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status."""
        if not self.checks:
            return {
                'status': 'unknown',
                'message': 'No health checks have been run yet',
                'timestamp': time.time()
            }
        
        # Determine overall status
        statuses = [check['status'] for check in self.checks.values()]
        
        if 'unhealthy' in statuses or 'error' in statuses:
            overall_status = 'unhealthy'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        # Count status types
        status_counts = {}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'status': overall_status,
            'message': f'Overall system health: {overall_status}',
            'timestamp': time.time(),
            'check_count': len(self.checks),
            'status_breakdown': status_counts,
            'last_check': self.last_check
        }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information."""
        overall = self.get_overall_health()
        
        return {
            'overall': overall,
            'checks': self.checks,
            'system_info': {
                'uptime': time.time() - (self.bot.startup_time if hasattr(self.bot, 'startup_time') else time.time()),
                'guild_count': len(self.bot.guilds) if self.bot.is_ready() else 0,
                'user_count': sum(g.member_count for g in self.bot.guilds) if self.bot.is_ready() else 0,
                'voice_connections': len(music_manager.voice_clients),
                'active_queues': len([q for q in music_manager.queues.values() if q])
            }
        }

# Global health monitor instance
health_monitor = None

def get_health_monitor(bot=None):
    """Get or create health monitor instance."""
    global health_monitor
    if health_monitor is None and bot:
        health_monitor = HealthMonitor(bot)
    return health_monitor