# src/bot.py - Complete Discord Bot with Comprehensive Monitoring Integration

import asyncio
import logging
import sys
import traceback
from pathlib import Path
import time

import discord
from discord.ext import commands, tasks

# ===== EMERGENCY VOICE CONNECTION PATCH =====
# This patch prevents infinite 4006 (Invalid Session) retry loops
logging.getLogger(__name__).info("Applying emergency voice connection patch...")

# Store original methods before patching
original_connect = discord.VoiceChannel.connect
original_move_to = discord.VoiceClient.move_to

async def patched_connect(self, *, timeout=60.0, reconnect=True, cls=discord.VoiceClient):
    """Patched voice channel connect with 4006 error limiting."""
    
    max_4006_retries = 3  # Limit 4006 retries to 3 attempts
    attempt_count = 0
    
    while attempt_count < max_4006_retries:
        try:
            return await original_connect(self, timeout=min(timeout, 10.0), reconnect=False, cls=cls)
            
        except discord.ConnectionClosed as e:
            if e.code == 4006:  # Invalid session
                attempt_count += 1
                if attempt_count >= max_4006_retries:
                    logging.error(f"Voice connection failed after {max_4006_retries} 4006 errors for guild {self.guild.id}")
                    raise e
                
                # Wait before retrying with exponential backoff
                wait_time = min(30, 2 ** attempt_count)
                logging.warning(f"4006 error #{attempt_count}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                # Non-4006 errors should be raised immediately
                raise e
                
        except Exception as e:
            # Any other error should be raised immediately
            raise e
    
    # This should never be reached, but just in case
    raise discord.ConnectionClosed(None, shard_id=None, code=4006)

async def patched_move_to(self, channel):
    """Patched move_to with better error handling."""
    try:
        return await original_move_to(self, channel)
    except discord.ConnectionClosed as e:
        if e.code == 4006:
            logging.error(f"Move failed with 4006 error for guild {channel.guild.id}, disconnecting...")
            if self.is_connected():
                await self.disconnect()
            raise e
        else:
            raise e

# Apply the patches
discord.VoiceChannel.connect = patched_connect
discord.VoiceClient.move_to = patched_move_to

logging.getLogger(__name__).info("Emergency voice connection patches applied successfully")
# ===== END EMERGENCY PATCH =====

# Import configuration and setup
from config.settings import settings
from config.logging import logger
from config.database import init_db

# Import core components
from src.core.music_manager import music_manager
from src.core.error_handler import ErrorHandler
from src.core.database_manager import db_manager

# Import command modules
from src.commands.music_commands import MusicCommands
from src.commands.playlist_commands import PlaylistCommands
from src.commands.admin_commands import AdminCommands
from src.commands.utility_commands import UtilityCommands

# Import monitoring
from src.monitoring.health import get_health_monitor
from src.web.dashboard import start_dashboard, set_bot_instance
from src.monitoring.metrics_tracker import BotMetricsTracker

class ShardedBasslineBot(commands.Bot):
    """Enhanced Discord music bot with professional features and comprehensive monitoring."""
    
    def __init__(self, shard_id=None, shard_count=None):
        # Bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.guild_messages = True
        
        # Initialize startup time and error tracking BEFORE super().__init__
        self.startup_time = time.time()
        self._start_time = time.time()  # For dashboard tracking
        self.error_count = 0
        self.recent_errors = []
        
        # Sharding configuration
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            description=f"{settings.bot_name} - Professional Discord Music Bot",
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play | Premium Music Bot"
            ),
            shard_id=shard_id,
            shard_count=shard_count,
            # Automatically determine shard count if not specified
            auto_reconnect=True,
            chunk_guilds_at_startup=False,  # Performance optimization
            member_cache_flags=discord.MemberCacheFlags.none(),  # Reduce memory usage
        )
        
        # Initialize error handler AFTER super().__init__
        self.error_handler = ErrorHandler(self)
        self.ready_guilds = set()
        self.shard_ready_events = {}
        
        # Initialize metrics tracker
        self.metrics_tracker = BotMetricsTracker(self)
        
        # Track which shards are ready
        shard_ids = getattr(self, 'shard_ids', None) or [0]
        for shard_id in shard_ids:
            self.shard_ready_events[shard_id] = asyncio.Event()
        
        logger.info(f"Initializing {settings.bot_name} with comprehensive monitoring")
        if self.shard_count:
            logger.info(f"Shard configuration: {self.shard_id}/{self.shard_count}")
    
    async def _get_prefix(self, bot, message):
        """Get command prefix for guild."""
        if not message.guild:
            return settings.bot_prefix
        
        guild_settings = db_manager.get_guild_settings(message.guild.id)
        if guild_settings and guild_settings.prefix:
            return guild_settings.prefix
        
        return settings.bot_prefix
    
    async def setup_hook(self):
        """Set up the bot - called once when bot starts."""
        logger.info("Setting up bot with comprehensive monitoring...")
        
        # Initialize database
        try:
            init_db()  # Remove await since init_db() is not async
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        
        # Load command modules (cogs)
        try:
            await self.add_cog(MusicCommands(self))
            logger.info("Loaded cog: MusicCommands")
            
            await self.add_cog(PlaylistCommands(self))
            logger.info("Loaded cog: PlaylistCommands")
            
            await self.add_cog(AdminCommands(self))
            logger.info("Loaded cog: AdminCommands")
            
            await self.add_cog(UtilityCommands(self))
            logger.info("Loaded cog: UtilityCommands")
            
        except Exception as e:
            logger.error(f"Failed to load cogs: {e}")
            raise
        
        # Add comprehensive metrics event listeners
        try:
            # Core metrics events
            self.add_listener(self.metrics_tracker.on_ready, 'on_ready')
            self.add_listener(self.metrics_tracker.on_command, 'on_command')
            self.add_listener(self.metrics_tracker.on_command_completion, 'on_command_completion')
            self.add_listener(self.metrics_tracker.on_command_error, 'on_command_error')
            
            # Voice and music tracking
            self.add_listener(self.metrics_tracker.on_voice_state_update, 'on_voice_state_update')
            
            # Guild tracking
            self.add_listener(self.metrics_tracker.on_guild_join, 'on_guild_join')
            self.add_listener(self.metrics_tracker.on_guild_remove, 'on_guild_remove')
            
            # Connection tracking
            self.add_listener(self.metrics_tracker.on_message, 'on_message')
            self.add_listener(self.metrics_tracker.on_disconnect, 'on_disconnect')
            self.add_listener(self.metrics_tracker.on_resumed, 'on_resumed')
            
            logger.info("[SUCCESS] Comprehensive dashboard metrics tracking enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup metrics tracking: {e}")
        
        # Sync slash commands
        try:
            await self.tree.sync()
            logger.info("Slash commands synced")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
        
        # Start periodic stats logging
        try:
            asyncio.create_task(self.metrics_tracker.periodic_stats_log())
            logger.info("Started periodic statistics logging")
        except Exception as e:
            logger.error(f"Failed to start periodic stats: {e}")
        
        logger.info("Bot setup completed successfully")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        shard_id = getattr(self, 'shard_id', None)
        if shard_id is None:
            shard_id = 0  # Default for non-sharded bots
        
        if shard_id not in self.ready_guilds:
            self.ready_guilds.add(shard_id)
            
            # Log shard ready information
            if self.shard_count:
                guild_count = len([g for g in self.guilds if g.shard_id == shard_id])
                latency = round(self.get_shard(shard_id).latency * 1000, 1)
            else:
                guild_count = len(self.guilds)
                latency = round(self.latency * 1000, 1)
            
            logger.info(f"[SHARD {shard_id}] Connected to Discord")
        
        # Check if all shards are ready
        expected_shards = self.shard_count or 1
        if len(self.ready_guilds) >= expected_shards:
            logger.info(f"[SHARD {shard_id}] Connected to {len(self.guilds)} guilds")
            logger.info(f"[SHARD {shard_id}] Latency: {round(self.latency * 1000, 1)}ms")
            logger.info(f"[SHARD {shard_id}] Ready! Shard latency: {round(self.latency * 1000, 1)}ms")
            
            # Log comprehensive stats when all shards are ready
            if len(self.ready_guilds) == expected_shards:
                await self._log_startup_complete()
    
    async def _log_startup_complete(self):
        """Log comprehensive startup completion statistics."""
        try:
            total_guilds = len(self.guilds)
            total_users = sum(getattr(g, 'member_count', 0) for g in self.guilds)
            shard_count = self.shard_count or 1
            
            logger.info("[SUCCESS] All shards ready! BasslineBot is fully online!")
            logger.info(f"[STATS] Total guilds: {total_guilds:,}")
            logger.info(f"[STATS] Total users: {total_users:,}")
            logger.info(f"[STATS] Shard count: {shard_count}")
            
            # Log per-shard statistics only if actually sharded
            if self.shard_count and self.shard_count > 1:
                for shard_id in range(shard_count):
                    try:
                        shard_guilds = [g for g in self.guilds if getattr(g, 'shard_id', 0) == shard_id]
                        shard_latency = round(self.get_shard(shard_id).latency * 1000, 1)
                        logger.info(f"[SHARD {shard_id}] Guilds: {len(shard_guilds)}, Latency: {shard_latency}ms")
                    except Exception as e:
                        logger.warning(f"[SHARD {shard_id}] Could not get shard metrics: {e}")
            
            # Start dashboard if this is the primary shard or non-sharded
            primary_shard = getattr(self, 'shard_id', None)
            if primary_shard is None or primary_shard == 0:
                try:
                    await start_dashboard(self)
                    logger.info(f"Dashboard started on port {getattr(settings, 'dashboard_port', 8080)}")
                except Exception as e:
                    logger.error(f"Failed to start dashboard: {e}")
            
            # Start health monitoring
            try:
                health_monitor = get_health_monitor(self)
                if health_monitor and getattr(settings, 'health_check_enabled', True):
                    logger.info("Starting health monitoring for all shards...")
                    asyncio.create_task(health_monitor.start_monitoring())
                
            except Exception as e:
                logger.error(f"Failed to start health monitoring: {e}")
                
        except Exception as e:
            logger.error(f"Error in startup completion logging: {e}")
    
    async def on_shard_ready(self, shard_id):
        """Called when a specific shard becomes ready."""
        try:
            if shard_id in self.shard_ready_events:
                self.shard_ready_events[shard_id].set()
            
            # Only collect shard-specific metrics if we're actually sharded
            if self.shard_count and self.shard_count > 1:
                # Collect shard-specific metrics
                shard_guilds = [g for g in self.guilds if getattr(g, 'shard_id', 0) == shard_id]
                
                metrics = {
                    'shard_id': shard_id,
                    'latency': self.get_shard(shard_id).latency if hasattr(self, 'get_shard') else self.latency,
                    'guild_count': len(shard_guilds),
                    'user_count': sum(getattr(g, 'member_count', 0) for g in shard_guilds),
                    'active_connections': len([g for g in shard_guilds if getattr(g, 'voice_client', None)]),
                    'timestamp': time.time()
                }
                
                logger.debug(f"Shard {shard_id} metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Shard ready metrics collection error: {e}")
    
    async def close(self):
        """Enhanced cleanup when bot shuts down."""
        try:
            logger.info("Starting bot shutdown sequence...")
            
            # Log session statistics
            if hasattr(self, 'metrics_tracker'):
                stats = self.metrics_tracker.get_session_stats()
                logger.info("📊 Final Session Statistics:")
                for key, value in stats.items():
                    logger.info(f"   {key}: {value}")
            
            # Disconnect from all voice channels
            voice_clients = [vc for vc in self.voice_clients if vc.is_connected()]
            if voice_clients:
                logger.info(f"Disconnecting from {len(voice_clients)} voice channels...")
                for vc in voice_clients:
                    try:
                        await vc.disconnect(force=True)
                    except:
                        pass
            
            # Close database connections
            if db_manager:
                try:
                    await db_manager.close()
                    logger.info("Database connections closed")
                except:
                    pass
            
            logger.info("Bot shutdown sequence completed")
            
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
        
        finally:
            await super().close()

# Legacy class for backwards compatibility
class BasslineBot(ShardedBasslineBot):
    """Legacy class name for backwards compatibility."""
    def __init__(self):
        super().__init__()

# Main bot instance creation
async def create_bot():
    """Create and return the bot instance with comprehensive monitoring."""
    # Check if manual sharding is configured
    shard_id = getattr(settings, 'shard_id', None)
    shard_count = getattr(settings, 'shard_count', None)
    
    if shard_id is not None and shard_count is not None:
        # Manual sharding configuration
        logger.info(f"Using manual sharding: {shard_id}/{shard_count}")
        bot = ShardedBasslineBot(shard_id=shard_id, shard_count=shard_count)
    else:
        # Automatic sharding (recommended)
        logger.info("Using automatic sharding")
        bot = ShardedBasslineBot()
    
    # Dashboard integration - set bot instance and track start time
    bot._start_time = time.time()  # Track when bot starts
    set_bot_instance(bot)  # Give dashboard access to bot
    logger.info("Bot instance configured for comprehensive dashboard monitoring")
    
    return bot

async def main():
    """Main bot entry point with enhanced error handling."""
    # Ensure required directories exist
    directories = ['logs', 'data', 'downloads', 'static', 'templates']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    try:
        logger.info(f"Starting Bassline-Bot with comprehensive monitoring system...")
        
        # Create bot instance
        bot = await create_bot()
        
        # Start the bot
        async with bot:
            await bot.start(settings.discord_token)
            
    except discord.LoginFailure:
        logger.error("[ERROR] Invalid Discord token provided - check your .env file")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        logger.error("[ERROR] Privileged intents required - enable them in Discord Developer Portal")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("[STOP] Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"[FATAL] Fatal error during bot execution: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("[SHUTDOWN] Bot shutdown complete")

# Entry point
if __name__ == "__main__":
    # Set up asyncio for Windows compatibility
    if sys.platform == 'win32':
        # Use ProactorEventLoop on Windows for better performance
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        # Run the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[STOP] Bot stopped by user")
    except Exception as e:
        logger.error(f"[FATAL] Failed to start bot: {e}")
        sys.exit(1)