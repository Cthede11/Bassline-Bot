# src/monitoring/metrics_tracker.py
# Comprehensive real-time metrics tracking integration for Discord bot

import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from discord.ext import commands
import discord

logger = logging.getLogger(__name__)

class BotMetricsTracker:
    """Comprehensive metrics tracking for dashboard monitoring."""
    
    def __init__(self, bot):
        self.bot = bot
        self.command_start_times = {}
        self.session_start_time = time.time()
        self.command_count = 0
        self.error_count = 0
        self.music_sessions = {}
        
        # Performance tracking
        self.response_times = []
        self.peak_memory = 0
        self.peak_cpu = 0
        
        logger.info("Metrics tracker initialized for comprehensive monitoring")
        
    async def on_ready(self):
        """Track when bot becomes ready."""
        try:
            logger.info(f"Bot ready - tracking {len(self.bot.guilds)} guilds with {sum(g.member_count for g in self.bot.guilds)} total users")
            
            # Update metrics with current bot state
            from src.web.dashboard import metrics
            if hasattr(metrics, 'total_songs_played'):
                # Initialize if this is first startup
                pass
                
        except Exception as e:
            logger.error(f"Failed to track ready event: {e}")
    
    async def on_command(self, ctx):
        """Track when a command starts."""
        try:
            self.command_count += 1
            self.command_start_times[ctx.message.id] = time.time()
            
            logger.debug(f"Command started: {ctx.command.name} by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}")
            
        except Exception as e:
            logger.error(f"Failed to track command start: {e}")
        
    async def on_command_completion(self, ctx):
        """Track successful command completion with detailed metrics."""
        try:
            start_time = self.command_start_times.pop(ctx.message.id, time.time())
            response_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Add to response times for averaging
            self.response_times.append(response_time)
            if len(self.response_times) > 100:  # Keep last 100
                self.response_times.pop(0)
            
            # Import here to avoid circular imports
            from src.web.dashboard import record_command_metric, metrics
            
            # Determine if it's a music command
            music_keywords = [
                'play', 'pause', 'resume', 'skip', 'stop', 'queue', 'nowplaying',
                'volume', 'shuffle', 'loop', 'lyrics', 'search', 'bassboost',
                'clear', 'join', 'leave', 'disconnect'
            ]
            
            is_music = any(keyword in ctx.command.name.lower() for keyword in music_keywords)
            
            # Track music-specific metrics
            if is_music:
                if ctx.command.name.lower() == 'play':
                    metrics.total_songs_played += 1
                    metrics.songs_played_today += 1
                    
                    # Track music session
                    if ctx.guild and ctx.guild.voice_client:
                        self.music_sessions[ctx.guild.id] = {
                            'start_time': time.time(),
                            'user_count': len(ctx.guild.voice_client.channel.members) if ctx.guild.voice_client.channel else 1
                        }
            
            # Record the metrics
            record_command_metric(ctx.command.name, response_time, is_music)
            
            # Log successful command with timing
            logger.info(f"[SUCCESS] Command completed: {ctx.command.name} ({response_time:.1f}ms) - User: {ctx.author} - Guild: {ctx.guild.name if ctx.guild else 'DM'}")
            
        except Exception as e:
            logger.error(f"Failed to record command completion metric: {e}")
    
    async def on_command_error(self, ctx, error):
        """Track command errors with detailed categorization."""
        # Clean up timing
        self.command_start_times.pop(ctx.message.id, None)
        self.error_count += 1
        
        try:
            from src.web.dashboard import record_error_metric
            
            error_type = type(error).__name__
            error_message = str(error)
            
            # Enhanced severity classification
            severity = 'error'  # default
            
            # Info level errors (expected/handled)
            if any(err in error_type for err in [
                'CommandOnCooldown', 'MissingPermissions', 'BotMissingPermissions',
                'CommandNotFound', 'MissingRequiredArgument', 'BadArgument'
            ]):
                severity = 'info'
            
            # Warning level errors (concerning but not critical)
            elif any(err in error_type for err in [
                'NotFound', 'Forbidden', 'HTTPException', 'DiscordServerError',
                'CheckFailure', 'UserInputError'
            ]):
                severity = 'warning'
            
            # Critical errors (system issues)
            elif any(err in error_type for err in [
                'ConnectionClosed', 'GatewayNotFound', 'LoginFailure',
                'PrivilegedIntentsRequired', 'ClientException'
            ]):
                severity = 'critical'
            
            # Record the error
            record_error_metric(error_type, error_message, severity)
            
            # Enhanced logging with context
            guild_info = f"Guild: {ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "DM"
            user_info = f"User: {ctx.author} ({ctx.author.id})"
            command_info = f"Command: {ctx.command.name if ctx.command else 'Unknown'}"
            
            logger.error(f"[ERROR] Command Error ({severity.upper()}): {error_type} - {error_message}")
            logger.error(f"   Context: {command_info} | {user_info} | {guild_info}")
            
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")
    
    async def on_voice_state_update(self, member, before, after):
        """Track voice connection changes for comprehensive music activity monitoring."""
        try:
            from src.web.dashboard import metrics
            
            # Track when bot joins/leaves voice channels
            if member == self.bot.user:
                if before.channel is None and after.channel is not None:
                    # Bot joined a voice channel
                    logger.info(f"[VOICE] Bot joined voice channel: {after.channel.name} in {after.channel.guild.name}")
                    
                    # Initialize session tracking
                    if after.channel.guild.id not in self.music_sessions:
                        self.music_sessions[after.channel.guild.id] = {
                            'start_time': time.time(),
                            'user_count': len(after.channel.members) - 1  # Exclude bot
                        }
                    
                elif before.channel is not None and after.channel is None:
                    # Bot left a voice channel
                    logger.info(f"[VOICE] Bot left voice channel: {before.channel.name} in {before.channel.guild.name}")
                    
                    # End session tracking
                    if before.channel.guild.id in self.music_sessions:
                        session = self.music_sessions.pop(before.channel.guild.id)
                        session_duration = time.time() - session['start_time']
                        logger.info(f"[STATS] Music session ended: {session_duration:.1f}s duration, {session['user_count']} peak users")
            
            # Track user voice activity for listener metrics
            elif after.channel and after.channel.guild.voice_client:
                # Update listener count for active sessions
                if after.channel.guild.id in self.music_sessions:
                    current_listeners = len(after.channel.members) - 1  # Exclude bot
                    self.music_sessions[after.channel.guild.id]['user_count'] = max(
                        self.music_sessions[after.channel.guild.id]['user_count'],
                        current_listeners
                    )
            
        except Exception as e:
            logger.error(f"Failed to track voice state update: {e}")
    
    async def on_guild_join(self, guild):
        """Track when bot joins new guilds with detailed information."""
        try:
            # Enhanced guild join logging
            owner_info = f"Owner: {guild.owner} ({guild.owner.id})" if guild.owner else "Owner: Unknown"
            features = ", ".join(guild.features) if guild.features else "No special features"
            
            logger.info(f"[GUILD] Bot joined new guild: {guild.name} ({guild.id})")
            logger.info(f"   [STATS] Members: {guild.member_count:,} | Channels: {len(guild.channels)} | Roles: {len(guild.roles)}")
            logger.info(f"   [OWNER] {owner_info}")
            logger.info(f"   [FEATURES] Features: {features}")
            logger.info(f"   [DATE] Created: {guild.created_at.strftime('%Y-%m-%d')}")
            
            # Check bot permissions
            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                perms = bot_member.guild_permissions
                important_perms = {
                    'administrator': perms.administrator,
                    'manage_guild': perms.manage_guild,
                    'connect': perms.connect,
                    'speak': perms.speak,
                    'use_slash_commands': perms.use_slash_commands,
                    'send_messages': perms.send_messages
                }
                
                missing_perms = [perm for perm, has_perm in important_perms.items() if not has_perm]
                if missing_perms:
                    logger.warning(f"   [WARNING] Missing permissions: {', '.join(missing_perms)}")
                else:
                    logger.info(f"   [SUCCESS] All important permissions granted")
            
        except Exception as e:
            logger.error(f"Failed to track guild join: {e}")
    
    async def on_guild_remove(self, guild):
        """Track when bot leaves/gets removed from guilds."""
        try:
            logger.info(f"[GUILD] Bot left guild: {guild.name} ({guild.id}) - {guild.member_count:,} members")
            
            # Clean up any active sessions
            if guild.id in self.music_sessions:
                session = self.music_sessions.pop(guild.id)
                session_duration = time.time() - session['start_time']
                logger.info(f"   [VOICE] Ended active music session ({session_duration:.1f}s)")
                
        except Exception as e:
            logger.error(f"Failed to track guild remove: {e}")
    
    async def on_message(self, message):
        """Track message activity for engagement metrics."""
        try:
            # Don't track bot messages
            if message.author.bot:
                return
            
            # Track mentions of the bot
            if self.bot.user in message.mentions:
                logger.debug(f"[MENTION] Bot mentioned by {message.author} in {message.guild.name if message.guild else 'DM'}")
            
        except Exception as e:
            logger.error(f"Failed to track message: {e}")
    
    async def on_disconnect(self):
        """Track disconnection events."""
        try:
            uptime = time.time() - self.session_start_time
            logger.warning(f"[DISCONNECT] Bot disconnected after {uptime:.1f}s uptime")
            logger.info(f"[STATS] Session stats: {self.command_count} commands, {self.error_count} errors")
            
        except Exception as e:
            logger.error(f"Failed to track disconnect: {e}")
    
    async def on_resumed(self):
        """Track when bot resumes connection."""
        try:
            logger.info(f"[RECONNECT] Bot resumed connection")
            
        except Exception as e:
            logger.error(f"Failed to track resume: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        try:
            uptime = time.time() - self.session_start_time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            return {
                'uptime': uptime,
                'commands_processed': self.command_count,
                'errors_encountered': self.error_count,
                'success_rate': ((self.command_count - self.error_count) / max(1, self.command_count)) * 100,
                'avg_response_time': avg_response_time,
                'active_music_sessions': len(self.music_sessions),
                'total_listeners': sum(session['user_count'] for session in self.music_sessions.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {}
    
    async def periodic_stats_log(self):
        """Periodically log comprehensive statistics."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                stats = self.get_session_stats()
                if stats:
                    logger.info(f"[PERIODIC] Stats Report:")
                    logger.info(f"   Uptime: {stats['uptime']:.1f}s")
                    logger.info(f"   Commands: {stats['commands_processed']} (Success: {stats['success_rate']:.1f}%)")
                    logger.info(f"   Avg Response: {stats['avg_response_time']:.1f}ms")
                    logger.info(f"   Active Sessions: {stats['active_music_sessions']}")
                    logger.info(f"   Total Listeners: {stats['total_listeners']}")
                
            except Exception as e:
                logger.error(f"Failed to log periodic stats: {e}")
            
            await asyncio.sleep(300)  # 5 minutes