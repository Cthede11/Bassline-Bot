import asyncio
import logging
import sys
import traceback
from pathlib import Path
import time
import locale

import discord
from discord.ext import commands, tasks

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
from src.web.dashboard import start_dashboard

# Fix Unicode issues on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


class ShardedBasslineBot(commands.AutoShardedBot):
    """Enhanced Discord music bot with automatic sharding support."""
    
    def __init__(self, shard_id=None, shard_count=None):
        # Bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.guild_messages = True
        
        # Initialize startup time and error tracking BEFORE super().__init__
        self.startup_time = time.time()
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
        
        # Track which shards are ready
        for shard_id in self.shard_ids or [0]:
            self.shard_ready_events[shard_id] = asyncio.Event()
        
        logger.info(f"Initializing {settings.bot_name} with sharding")
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
        logger.info(f"Setting up bot with {len(self.shard_ids or [0])} shard(s)...")
        try:
            # Initialize database (only once, not per shard)
            init_db()
            logger.info("Database initialized")
            
            # Load extensions
            await self.load_cogs()
            
            # Sync slash commands globally (will be handled by Discord across shards)
            await self.tree.sync()
            logger.info("Slash commands synced")
            
            # Start background tasks
            self.cleanup_task.start()
            if settings.metrics_enabled:
                self.metrics_task.start()
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up bot: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    async def load_cogs(self):
        """Load all command cogs."""
        cogs = [
            ('MusicCommands', MusicCommands),
            ('PlaylistCommands', PlaylistCommands),
            ('AdminCommands', AdminCommands),
            ('UtilityCommands', UtilityCommands),
        ]
        
        for name, cog_class in cogs:
            try:
                await self.add_cog(cog_class(self))
                logger.info(f"Loaded cog: {name}")
            except Exception as e:
                logger.error(f"Failed to load cog {name}: {e}")
                traceback.print_exc()
    
    async def on_ready(self):
        """Called when a shard becomes ready."""
        # Note: This is called for EACH shard when it becomes ready
        shard_id = getattr(self, 'shard_id', 0) or 0
        
        logger.info(f"[SHARD {shard_id}] Ready! Shard latency: {self.get_shard(shard_id).latency * 1000:.2f}ms")
        
        # Mark this shard as ready
        if shard_id in self.shard_ready_events:
            self.shard_ready_events[shard_id].set()
        
        # Check if all shards are ready
        all_ready = all(
            event.is_set() 
            for event in self.shard_ready_events.values()
        )
        
        if all_ready and not hasattr(self, '_all_shards_ready'):
            self._all_shards_ready = True
            await self._on_all_shards_ready()
    
    async def _on_all_shards_ready(self):
        """Called when ALL shards are ready."""
        total_guilds = len(self.guilds)
        total_users = sum(g.member_count for g in self.guilds)
        
        logger.info(f"[SUCCESS] All shards ready! {self.user.name} is fully online!")
        logger.info(f"[STATS] Total guilds: {total_guilds}")
        logger.info(f"[STATS] Total users: {total_users}")
        logger.info(f"[STATS] Shard count: {self.shard_count}")
        
        # Log per-shard statistics
        for shard_id, shard in self.shards.items():
            shard_guilds = [g for g in self.guilds if g.shard_id == shard_id]
            logger.info(f"[SHARD {shard_id}] Guilds: {len(shard_guilds)}, Latency: {shard.latency * 1000:.2f}ms")
        
        # Start web dashboard only when all shards are ready
        if settings.dashboard_enabled:
            await self.start_dashboard()
        
        # Initialize health monitoring for all shards
        health_monitor = get_health_monitor(self)
        if health_monitor and settings.health_check_enabled:
            logger.info("Starting health monitoring for all shards...")
            asyncio.create_task(health_monitor.start_monitoring())
    
    async def on_shard_ready(self, shard_id):
        """Called when a specific shard becomes ready."""
        shard = self.get_shard(shard_id)
        shard_guilds = [g for g in self.guilds if g.shard_id == shard_id]
        
        logger.info(f"[SHARD {shard_id}] Connected to {len(shard_guilds)} guilds")
        logger.info(f"[SHARD {shard_id}] Latency: {shard.latency * 1000:.2f}ms")
    
    async def on_shard_connect(self, shard_id):
        """Called when a shard connects to Discord."""
        logger.info(f"[SHARD {shard_id}] Connected to Discord")
    
    async def on_shard_disconnect(self, shard_id):
        """Called when a shard disconnects from Discord."""
        logger.warning(f"[SHARD {shard_id}] Disconnected from Discord")
    
    async def on_shard_resumed(self, shard_id):
        """Called when a shard resumes connection."""
        logger.info(f"[SHARD {shard_id}] Resumed connection")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a guild."""
        shard_id = guild.shard_id
        logger.info(f"[SHARD {shard_id}] Joined guild: {guild.name} ({guild.id})")
        
        # Create guild record in database
        with db_manager:
            db_manager.get_or_create_guild(guild.id, guild.name)
        
        # Send welcome message
        if guild.system_channel:
            embed = discord.Embed(
                title=f"{settings.bot_name} has joined!",
                description="Thank you for adding me to your server!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Getting Started",
                value="Use `/play <song>` to start playing music!\nUse `/help` for all commands.",
                inline=False
            )
            embed.add_field(
                name="Powered by Sharding",
                value=f"Running on shard {shard_id} for optimal performance!",
                inline=False
            )
            
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                pass
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot leaves a guild."""
        shard_id = guild.shard_id
        logger.info(f"[SHARD {shard_id}] Left guild: {guild.name} ({guild.id})")
        
        # Clean up guild state
        music_manager.clear_guild_state(guild.id)
    
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates."""
        if member.id != self.user.id:
            return
        
        guild_id = member.guild.id
        shard_id = member.guild.shard_id
        
        # Bot was disconnected
        if before.channel and not after.channel:
            logger.info(f"[SHARD {shard_id}] Bot disconnected from voice in guild {guild_id}")
            music_manager.clear_guild_state(guild_id)
        
        # Bot moved channels
        elif before.channel != after.channel and after.channel:
            logger.info(f"[SHARD {shard_id}] Bot moved to {after.channel.name} in guild {guild_id}")
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle command errors."""
        shard_id = ctx.guild.shard_id if ctx.guild else "DM"
        logger.error(f"[SHARD {shard_id}] Command error in {ctx.command}: {error}")
        
        self.error_count += 1
        self.recent_errors.append({
            'error': str(error),
            'command': str(ctx.command),
            'guild_id': ctx.guild.id if ctx.guild else None,
            'shard_id': shard_id,
            'timestamp': time.time()
        })
        
        # Keep only recent errors (last 10)
        self.recent_errors = self.recent_errors[-10:]
        
        await self.error_handler.handle_error(ctx, error)
    
    def get_shard_info(self):
        """Get comprehensive shard information."""
        if not self.shards:
            return None
        
        shard_info = {
            'shard_count': self.shard_count,
            'shards': {}
        }
        
        for shard_id, shard in self.shards.items():
            shard_guilds = [g for g in self.guilds if g.shard_id == shard_id]
            shard_users = sum(g.member_count for g in shard_guilds)
            
            shard_info['shards'][shard_id] = {
                'id': shard_id,
                'latency': round(shard.latency * 1000, 2),
                'is_ready': not shard.is_closed(),
                'guild_count': len(shard_guilds),
                'user_count': shard_users,
                'is_ws_ratelimited': shard.is_ws_ratelimited(),
            }
        
        return shard_info
    
    async def start_dashboard(self):
        """Start the web dashboard with shard support."""
        try:
            # Only start dashboard on the first shard to avoid conflicts
            if self.shard_id is None or self.shard_id == 0:
                await start_dashboard(self)
                logger.info(f"Dashboard started on port {settings.dashboard_port}")
            else:
                logger.info(f"[SHARD {self.shard_id}] Dashboard not started (handled by shard 0)")
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
    
    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """Periodic cleanup task."""
        try:
            # Clean up inactive voice connections
            for guild in self.guilds:
                if guild.voice_client and not guild.voice_client.is_playing():
                    # Check if queue is empty and no one is in channel
                    voice_channel = guild.voice_client.channel
                    if voice_channel and len(voice_channel.members) <= 1:  # Only bot
                        await guild.voice_client.disconnect()
                        music_manager.clear_guild_state(guild.id)
                        logger.info(f"[SHARD {guild.shard_id}] Cleaned up inactive connection in {guild.name}")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
    
    @tasks.loop(minutes=1)
    async def metrics_task(self):
        """Collect metrics for monitoring."""
        try:
            # Collect shard-specific metrics
            for shard_id, shard in self.shards.items():
                shard_guilds = [g for g in self.guilds if g.shard_id == shard_id]
                
                metrics = {
                    'shard_id': shard_id,
                    'latency': shard.latency,
                    'guild_count': len(shard_guilds),
                    'user_count': sum(g.member_count for g in shard_guilds),
                    'active_connections': len([g for g in shard_guilds if g.voice_client]),
                    'timestamp': time.time()
                }
                
                # Store metrics (implement your metrics storage here)
                # self.store_shard_metrics(metrics)
                
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")


# Main bot instance
async def create_bot():
    """Create and return the bot instance."""
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
    
    return bot


async def main():
    """Main bot entry point."""
    try:
        bot = await create_bot()
        
        # Start the bot
        async with bot:
            await bot.start(settings.discord_token)
            
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    # Set up asyncio for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)