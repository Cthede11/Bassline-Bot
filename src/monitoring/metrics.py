"""Metrics collection for BasslineBot Pro."""

import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config.settings import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
COMMAND_COUNTER = Counter('basslinebot_commands_total', 'Total commands executed', ['command', 'guild', 'success'])
COMMAND_DURATION = Histogram('basslinebot_command_duration_seconds', 'Command execution time', ['command'])
ACTIVE_CONNECTIONS = Gauge('basslinebot_active_connections', 'Number of active voice connections')
QUEUE_SIZE = Gauge('basslinebot_queue_size', 'Total songs in all queues')
SONGS_PLAYED = Counter('basslinebot_songs_played_total', 'Total songs played')
ERRORS_TOTAL = Counter('basslinebot_errors_total', 'Total errors', ['error_type'])

class MetricsCollector:
    """Metrics collection and reporting."""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_enabled = settings.metrics_enabled
        
        if self.metrics_enabled:
            # Start Prometheus metrics server
            try:
                start_http_server(settings.prometheus_port)
                logger.info(f"Metrics server started on port {settings.prometheus_port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
    
    def record_command(self, command: str, guild_id: int, success: bool, duration: float):
        """Record command execution."""
        if not self.metrics_enabled:
            return
        
        try:
            COMMAND_COUNTER.labels(command=command, guild=str(guild_id), success=str(success)).inc()
            COMMAND_DURATION.labels(command=command).observe(duration)
        except Exception as e:
            logger.error(f"Error recording command metric: {e}")
    
    def update_voice_connections(self, count: int):
        """Update active voice connections count."""
        if not self.metrics_enabled:
            return
        
        try:
            ACTIVE_CONNECTIONS.set(count)
        except Exception as e:
            logger.error(f"Error updating voice connections metric: {e}")
    
    def update_queue_size(self, total_size: int):
        """Update total queue size."""
        if not self.metrics_enabled:
            return
        
        try:
            QUEUE_SIZE.set(total_size)
        except Exception as e:
            logger.error(f"Error updating queue size metric: {e}")
    
    def record_song_played(self):
        """Record a song being played."""
        if not self.metrics_enabled:
            return
        
        try:
            SONGS_PLAYED.inc()
        except Exception as e:
            logger.error(f"Error recording song played metric: {e}")
    
    def record_error(self, error_type: str):
        """Record an error."""
        if not self.metrics_enabled:
            return
        
        try:
            ERRORS_TOTAL.labels(error_type=error_type).inc()
        except Exception as e:
            logger.error(f"Error recording error metric: {e}")
    
    def get_uptime(self) -> float:
        """Get bot uptime in seconds."""
        return time.time() - self.start_time

# Global metrics collector
metrics_collector = MetricsCollector()

async def collect_metrics(bot):
    """Collect and update metrics."""
    try:
        from src.core.music_manager import music_manager
        
        # Update voice connections
        active_connections = len(music_manager.voice_clients)
        metrics_collector.update_voice_connections(active_connections)
        
        # Update queue sizes
        total_queue_size = sum(len(queue) for queue in music_manager.queues.values())
        metrics_collector.update_queue_size(total_queue_size)
        
        logger.debug(f"Metrics updated: {active_connections} connections, {total_queue_size} queued")
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        metrics_collector.record_error("metrics_collection")