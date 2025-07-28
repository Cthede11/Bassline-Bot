import asyncio
import logging
import sys
import traceback
from pathlib import Path
import time

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

class BasslineBot(commands.Bot):
    """Enhanced Discord music bot with professional features."""
    
    def __init__(self):
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
        
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            description=f"{settings.bot_name} - Professional Discord Music Bot",
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play | Premium Music Bot"
            )
        )
        
        # Initialize error handler AFTER super().__init__
        self.error_handler = ErrorHandler(self)
        self.ready_guilds = set()
        
        logger.info(f"Initializing {settings.bot_name}")
    
    async def _get_prefix(self, bot, message):
        """Get command prefix for guild."""
        if not message.guild:
            return settings.bot_prefix
        
        guild_settings = db_manager.get_guild_settings(message.guild.id)
        if guild_settings and guild_settings.prefix:
            return guild_settings.prefix
        
        return settings.bot_prefix
    
    async def setup_hook(self):
        """Set up the bot."""
        logger.info("Setting up bot...")
        try:
            # Initialize database
            init_db()
            logger.info("Database initialized")
            
            # Load extensions
            await self.load_cogs()
            
            # Sync slash commands
            await self.tree.sync()
            logger.info("Slash commands synced")
            
            # Start background tasks
            self.cleanup_task.start()
            if settings.metrics_enabled:
                self.metrics_task.start()
            
            # Initialize health monitoring
            health_monitor = get_health_monitor(self)
            if health_monitor and settings.health_check_enabled:
                logger.info("Starting health monitoring...")
                asyncio.create_task(health_monitor.start_monitoring())
            
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
        """Called when bot is ready."""
        if not hasattr(self, '_ready_called'):
            self._ready_called = True
            
            logger.info(f"[SUCCESS] {self.user.name} is online!")
            logger.info(f"[STATS] Connected to {len(self.guilds)} guilds")
            logger.info(f"[USERS] Serving {sum(g.member_count for g in self.guilds)} users")
            
            # Start web dashboard if enabled
            if settings.dashboard_enabled:
                await self.start_dashboard()
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a guild."""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Create guild record in database
        with db_manager:
            db_manager.get_or_create_guild(guild.id, guild.name)
        
        # Send welcome message
        if guild.system_channel:
            embed = discord.Embed(
                title=f"🎵 {settings.bot_name} has joined!",
                description="Thank you for adding me to your server!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Getting Started",
                value="Use `/play <song>` to start playing music!\nUse `/help` for all commands.",
                inline=False
            )
            embed.add_field(
                name="Need Help?",
                value="Check out our documentation or join our support server.",
                inline=False
            )
            
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                pass
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} ({guild.id})")
        
        # Clean up guild state
        music_manager.clear_guild_state(guild.id)
    
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates."""
        if member.id != self.user.id:
            return
        
        guild_id = member.guild.id
        
        # Bot was disconnected
        if before.channel and not after.channel:
            logger.info(f"Bot disconnected from voice in guild {guild_id}")
            music_manager.clear_guild_state(guild_id)
        
        # Bot moved channels
        elif before.channel != after.channel and after.channel:
            logger.info(f"Bot moved to {after.channel.name} in guild {guild_id}")
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle command errors."""
        self.error_count += 1
        error_info = {
            'timestamp': time.time(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'command': ctx.command.name if ctx.command else 'Unknown',
            'guild_id': ctx.guild.id if ctx.guild else None,
            'user_id': ctx.author.id,
            'traceback': traceback.format_exc()
        }
        
        self.recent_errors.append(error_info)
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)
        
        # Log to database if possible
        if error_info['guild_id']:
            try:
                db_manager.log_command_usage(
                    guild_id=error_info['guild_id'],
                    user_id=error_info['user_id'],
                    command_name=error_info['command'],
                    success=False,
                    error_message=error_info['error_message']
                )
            except Exception as db_error:
                logger.error(f"Failed to log error to database: {db_error}")
        
        # Use error handler
        await self.error_handler.handle_command_error(ctx, error)
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Handle slash command errors."""
        self.error_count += 1
        error_info = {
            'timestamp': time.time(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'command': interaction.command.name if interaction.command else 'Unknown',
            'guild_id': interaction.guild.id if interaction.guild else None,
            'user_id': interaction.user.id,
            'traceback': traceback.format_exc()
        }
        
        self.recent_errors.append(error_info)
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)
        
        # Log to database
        if error_info['guild_id']:
            try:
                db_manager.log_command_usage(
                    guild_id=error_info['guild_id'],
                    user_id=error_info['user_id'],
                    command_name=error_info['command'],
                    success=False,
                    error_message=error_info['error_message']
                )
            except Exception as db_error:
                logger.error(f"Failed to log error to database: {db_error}")
        
        # Use error handler
        await self.error_handler.handle_interaction_error(interaction, error)
    
    async def start_dashboard(self):
        """Start the web dashboard."""
        if not settings.dashboard_enabled:
            return
        
        try:
            logger.info(f"Starting dashboard on {settings.dashboard_host}:{settings.dashboard_port}")
            
            # Start dashboard using the comprehensive implementation
            asyncio.create_task(start_dashboard(self))
            
            logger.info(f"Dashboard available at http://{settings.dashboard_host}:{settings.dashboard_port}")
            
        except ImportError:
            logger.warning("Dashboard dependencies not installed")
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            traceback.print_exc()
    
    @tasks.loop(minutes=30)
    async def cleanup_task(self):
        """Periodic cleanup task."""
        try:
            # Clean up inactive voice connections
            current_time = time.time()
            inactive_guilds = []
            
            for guild_id, last_activity in music_manager.last_activity.items():
                if current_time - last_activity > settings.idle_timeout:
                    vc = music_manager.voice_clients.get(guild_id)
                    if vc and not vc.is_playing():
                        inactive_guilds.append(guild_id)
            
            for guild_id in inactive_guilds:
                vc = music_manager.voice_clients.get(guild_id)
                if vc:
                    try:
                        await vc.disconnect()
                        logger.info(f"Disconnected from inactive guild {guild_id}")
                    except:
                        pass
                music_manager.clear_guild_state(guild_id)
            
            # Clean up old downloads
            try:
                from src.utils.youtube import youtube_manager
                youtube_manager.cleanup_old_downloads()
            except ImportError:
                pass  # youtube_manager might not exist yet
            
            logger.debug("Cleanup task completed")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
    
    @tasks.loop(minutes=5)
    async def metrics_task(self):
        """Collect metrics."""
        try:
            if settings.metrics_enabled:
                try:
                    from src.monitoring.metrics import collect_metrics
                    await collect_metrics(self)
                except ImportError:
                    logger.debug("Metrics module not available")
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    @cleanup_task.before_loop
    @metrics_task.before_loop
    async def before_tasks(self):
        """Wait for bot to be ready before starting tasks."""
        await self.wait_until_ready()

async def main():
    """Main entry point."""
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("downloads").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    
    # Create bot instance
    bot = BasslineBot()
    
    try:
        logger.info("Starting Bassline-Bot with comprehensive monitoring...")
        
        # Start the bot
        await bot.start(settings.discord_token)
        
    except discord.LoginFailure:
        logger.error("Invalid Discord token provided")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if not bot.is_closed():
            await bot.close()
        
        # Stop health monitoring
        health_monitor = get_health_monitor()
        if health_monitor:
            logger.info("Stopping health monitoring...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown completed")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)