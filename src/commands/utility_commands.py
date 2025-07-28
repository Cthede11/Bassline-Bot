import logging
import time
import psutil
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from src.core.music_manager import music_manager
from src.core.database_manager import db_manager
from src.utils.youtube import youtube_manager
from src.utils.helpers import format_duration, time_ago
from config.settings import settings

logger = logging.getLogger(__name__)

class UtilityCommands(commands.Cog):
    """Utility and information commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Called when cog is loaded."""
        logger.info("Utility commands loaded")
    
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency."""
        try:
            start_time = time.time()
            await interaction.response.defer()
            end_time = time.time()
            
            # Calculate latencies
            api_latency = (end_time - start_time) * 1000
            websocket_latency = self.bot.latency * 1000
            
            embed = discord.Embed(
                title="🏓 Pong!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="API Latency",
                value=f"`{api_latency:.2f}ms`",
                inline=True
            )
            embed.add_field(
                name="WebSocket Latency",
                value=f"`{websocket_latency:.2f}ms`",
                inline=True
            )
            
            # Add status indicator
            if api_latency < 100:
                status = "🟢 Excellent"
            elif api_latency < 200:
                status = "🟡 Good"
            elif api_latency < 500:
                status = "🟠 Fair"
            else:
                status = "🔴 Poor"
            
            embed.add_field(
                name="Status",
                value=status,
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            await interaction.followup.send("❌ Failed to check latency.", ephemeral=True)

    @app_commands.command(name="status", description="Check voice connection status")
    async def voice_status(self, interaction: discord.Interaction):
        """Show current voice connection status and peak hour information."""
        from src.utils.non_disruptive_voice import voice_manager
        
        guild_id = interaction.guild.id
        status = voice_manager.get_connection_status(guild_id)
        
        embed = discord.Embed(title="🎵 Voice Connection Status", color=discord.Color.blue())
        
        if interaction.guild.voice_client and interaction.guild.voice_client.is_connected():
            embed.add_field(name="Status", value="🟢 Connected", inline=True)
            embed.add_field(name="Channel", value=interaction.guild.voice_client.channel.mention, inline=True)
        elif status['status'] == 'queued':
            embed.add_field(name="Status", value="🟡 Queued (Peak Hours)", inline=True)
            embed.add_field(name="Position", value=f"Attempt {status['attempts']}/20", inline=True)
            embed.add_field(name="Est. Wait", value=status['estimated_wait'], inline=True)
        else:
            embed.add_field(name="Status", value="🔴 Disconnected", inline=True)
        
        # Add peak hour information
        import datetime
        current_hour = datetime.datetime.now().hour
        if 12 <= current_hour <= 20:
            embed.add_field(
                name="ℹ️ Peak Hours Notice", 
                value="Discord voice servers are experiencing high load. Connection may take longer than usual.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="info", description="Show bot information")
    async def info(self, interaction: discord.Interaction):
        """Show bot information."""
        try:
            # Get system info
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate uptime
            if hasattr(self.bot, 'startup_time'):
                uptime = time.time() - self.bot.startup_time
            else:
                uptime = 0
            
            embed = discord.Embed(
                title=f"ℹ️ {settings.bot_name}",
                description="Professional Discord Music Bot",
                color=discord.Color.blue()
            )
            
            # Bot stats
            embed.add_field(
                name="📊 Bot Statistics",
                value=f"Servers: `{len(self.bot.guilds)}`\n"
                      f"Users: `{sum(g.member_count for g in self.bot.guilds):,}`\n"
                      f"Uptime: `{format_duration(int(uptime))}`",
                inline=True
            )
            
            # Music stats
            active_connections = len(music_manager.voice_clients)
            total_queued = sum(len(queue) for queue in music_manager.queues.values())
            
            embed.add_field(
                name="🎵 Music Statistics",
                value=f"Active Connections: `{active_connections}`\n"
                      f"Total Queued: `{total_queued}`\n"
                      f"Songs Played: `{music_manager.get_metrics().get('songs_played', 0)}`",
                inline=True
            )
            
            # System stats
            embed.add_field(
                name="🖥️ System Statistics",
                value=f"CPU: `{cpu_usage:.1f}%`\n"
                      f"RAM: `{memory.percent:.1f}%`\n"
                      f"Disk: `{disk.percent:.1f}%`",
                inline=True
            )
            
            # Features
            features = []
            if settings.download_enabled:
                features.append("📥 Download Mode")
            if settings.bass_boost_enabled:
                features.append("🔊 Bass Boost")
            if settings.dashboard_enabled:
                features.append("🌐 Web Dashboard")
            if settings.metrics_enabled:
                features.append("📈 Metrics")
            
            if features:
                embed.add_field(
                    name="✨ Features",
                    value="\n".join(features),
                    inline=True
                )
            
            # Links and info
            embed.add_field(
                name="🔗 Links",
                value="[Dashboard](http://localhost:8000) | [Support](https://discord.gg/support) | [GitHub](https://github.com/yourusername/bassline-bot-pro)",
                inline=False
            )
            
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            embed.set_footer(text=f"Version 1.0.0 | Made with ❤️")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in info command: {e}")
            await interaction.response.send_message("❌ Failed to retrieve bot information.", ephemeral=True)
    
    @app_commands.command(name="help", description="Show help information")
    async def help(self, interaction: discord.Interaction, command: Optional[str] = None):
        """Show help information."""
        try:
            if command:
                # Show specific command help
                cmd = self.bot.tree.get_command(command)
                if cmd:
                    embed = discord.Embed(
                        title=f"❓ Help: /{command}",
                        description=cmd.description or "No description available",
                        color=discord.Color.blue()
                    )
                    
                    if hasattr(cmd, 'parameters') and cmd.parameters:
                        param_text = []
                        for param in cmd.parameters:
                            required = "Required" if param.required else "Optional"
                            param_text.append(f"`{param.name}` - {param.description or 'No description'} ({required})")
                        
                        embed.add_field(
                            name="Parameters",
                            value="\n".join(param_text),
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Command `/{command}` not found.", ephemeral=True)
                return
            
            # Show general help
            embed = discord.Embed(
                title=f"❓ {settings.bot_name} Help",
                description="Here are all available commands:",
                color=discord.Color.blue()
            )
            
            # Music commands
            music_commands = [
                "`/play <song>` - Play a song or add to queue",
                "`/queue` - Show current queue",
                "`/skip` - Skip current song (DJ/Admin)",
                "`/pause` - Pause playback (DJ/Admin)",
                "`/resume` - Resume playback (DJ/Admin)",
                "`/stop` - Stop and clear queue (DJ/Admin)",
                "`/loop <mode>` - Set loop mode (DJ/Admin)",
                "`/shuffle` - Shuffle queue (DJ/Admin)",
                "`/clear` - Clear queue (DJ/Admin)",
                "`/nowplaying` - Show current song info",
                "`/bassboost` - Toggle bass boost",
                "`/volume <level>` - Set your volume"
            ]
            
            embed.add_field(
                name="🎵 Music Commands",
                value="\n".join(music_commands),
                inline=False
            )
            
            # Playlist commands
            playlist_commands = [
                "`/setupplaylists` - Setup playlist category (Admin)",
                "`/createplaylist <n>` - Create playlist (Admin)",
                "`/listplaylists` - List all server playlists",
                "`/myplaylists` - View your personal playlists",
                "`/addtoplaylist <playlist> [song]` - Add song to playlist",
                "`/playplaylist <n>` - Play all songs from a playlist",
                "`/playlistinfo <n>` - Show detailed playlist information",
                "`/deleteplaylist <n>` - Delete your playlist"
            ]
            
            embed.add_field(
                name="📝 Playlist Commands",
                value="\n".join(playlist_commands),
                inline=False
            )
            
            # Admin commands
            admin_commands = [
                "`/setdjrole <role>` - Set DJ role (Admin)",
                "`/cleardjrole` - Clear DJ role (Admin)",
                "`/checkdjrole` - Check current DJ role",
                "`/stats` - Show bot statistics (Admin)",
                "`/settings` - View/update settings (Admin)",
                "`/cleanup` - Clean bot messages (Admin)"
            ]
            
            embed.add_field(
                name="⚙️ Admin Commands",
                value="\n".join(admin_commands),
                inline=False
            )
            
            # Utility commands
            utility_commands = [
                "`/ping` - Check bot latency",
                "`/info` - Show bot information",
                "`/help [command]` - Show this help or command details"
            ]
            
            embed.add_field(
                name="🔧 Utility Commands",
                value="\n".join(utility_commands),
                inline=False
            )
            
            embed.add_field(
                name="💡 Tips",
                value="• Use `/help <command>` for detailed command help\n"
                      "• DJ role members can control music playback\n"
                      "• Visit the dashboard for advanced features",
                inline=False
            )
            
            embed.set_footer(text="Use /help <command> for detailed information about a specific command")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.response.send_message("❌ Failed to show help information.", ephemeral=True)
    
    @app_commands.command(name="search", description="Search for songs on YouTube")
    @app_commands.describe(query="Search query for YouTube")
    async def search(self, interaction: discord.Interaction, query: str):
        """Search for songs on YouTube."""
        try:
            await interaction.response.defer()
            
            # Search YouTube
            results = await youtube_manager.search(query, max_results=5)
            
            if not results:
                await interaction.followup.send("No results found.")
                return

            # Present results
            embed = discord.Embed(title="🎵 YouTube Search Results", color=discord.Color.blue())
            for idx, video in enumerate(results, start=1):
                embed.add_field(
                    name=f"Result {idx}",
                    value=f"[{video.title}]({video.url})\nDuration: {format_duration(video.duration)}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in search command: {e}")
            await interaction.followup.send("❌ Failed to search for songs.", ephemeral=True)