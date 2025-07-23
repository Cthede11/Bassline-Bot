### src/commands/admin_commands.py
import logging
import time
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from src.core.music_manager import music_manager
from src.core.database_manager import db_manager
from src.utils.checks import is_dj_or_admin_slash
from src.utils.helpers import format_duration, time_ago
from config.settings import settings

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Administrative commands for bot management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Called when cog is loaded."""
        logger.info("Admin commands loaded")
    
    @app_commands.command(name="setdjrole", description="Set the DJ role for this server")
    @app_commands.describe(role="The role to designate as the DJ role")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_dj_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the DJ role for the guild."""
        try:
            guild_id = interaction.guild.id
            music_manager.set_dj_role(guild_id, role.id)
            
            embed = discord.Embed(
                title="🎧 DJ Role Updated",
                description=f"DJ role has been set to {role.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Permissions",
                value="Users with this role can control music playback",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"DJ role set to {role.name} in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error setting DJ role: {e}")
            await interaction.response.send_message("❌ Failed to set DJ role.", ephemeral=True)
    
    @app_commands.command(name="cleardjrole", description="Clear the DJ role for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_dj_role(self, interaction: discord.Interaction):
        """Clear the DJ role for the guild."""
        try:
            guild_id = interaction.guild.id
            music_manager.set_dj_role(guild_id, None)
            
            embed = discord.Embed(
                title="🎧 DJ Role Cleared",
                description="DJ role has been cleared. Only administrators can now control music.",
                color=discord.Color.orange()
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"DJ role cleared in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error clearing DJ role: {e}")
            await interaction.response.send_message("❌ Failed to clear DJ role.", ephemeral=True)
    
    @app_commands.command(name="checkdjrole", description="Check the current DJ role")
    async def check_dj_role(self, interaction: discord.Interaction):
        """Check the current DJ role."""
        try:
            guild_id = interaction.guild.id
            dj_role_id = music_manager.get_dj_role_id(guild_id)
            
            embed = discord.Embed(title="🎧 DJ Role Status", color=discord.Color.blue())
            
            if dj_role_id:
                role = interaction.guild.get_role(dj_role_id)
                if role:
                    embed.description = f"Current DJ role: {role.mention}"
                    embed.add_field(
                        name="Members with DJ Role",
                        value=f"{len(role.members)} members",
                        inline=True
                    )
                else:
                    embed.description = f"DJ role ID `{dj_role_id}` is set but role not found"
                    embed.color = discord.Color.red()
            else:
                embed.description = "No DJ role is currently set"
                embed.add_field(
                    name="Current Behavior",
                    value="Only administrators can control music",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error checking DJ role: {e}")
            await interaction.response.send_message("❌ Failed to check DJ role.", ephemeral=True)
    
    @app_commands.command(name="stats", description="Show bot statistics")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stats(self, interaction: discord.Interaction):
        """Show comprehensive bot statistics."""
        try:
            await interaction.response.defer()
            
            guild_id = interaction.guild.id
            
            # Get guild stats
            guild_stats = music_manager.get_guild_stats(guild_id)
            
            # Get database stats
            with db_manager:
                usage_stats = db_manager.get_usage_stats(guild_id=guild_id, days=7)
                guild_settings = db_manager.get_guild_settings(guild_id)
            
            # Create embed
            embed = discord.Embed(
                title="📊 Bot Statistics",
                description=f"Statistics for **{interaction.guild.name}**",
                color=discord.Color.blue()
            )
            
            # Current session info
            embed.add_field(
                name="🎵 Current Session",
                value=f"Queue Length: `{guild_stats['queue_length']}`\n"
                      f"Playing: `{'Yes' if guild_stats['is_playing'] else 'No'}`\n"
                      f"Loop Mode: `{guild_stats['loop_state']}`",
                inline=True
            )
            
            # Usage statistics (last 7 days)
            embed.add_field(
                name="📈 Usage (7 days)",
                value=f"Commands: `{usage_stats.get('total_commands', 0)}`\n"
                      f"Success Rate: `{usage_stats.get('successful_commands', 0) / max(usage_stats.get('total_commands', 1), 1) * 100:.1f}%`\n"
                      f"Unique Users: `{usage_stats.get('unique_users', 0)}`",
                inline=True
            )
            
            # Settings info
            if guild_settings:
                embed.add_field(
                    name="⚙️ Settings",
                    value=f"Max Queue: `{guild_settings.max_queue_size}`\n"
                          f"Timeout: `{guild_settings.auto_disconnect_timeout}s`\n"
                          f"Bass Boost: `{'Enabled' if guild_settings.bass_boost_enabled else 'Disabled'}`",
                    inline=True
                )
            
            # Activity info
            last_activity = guild_stats.get('last_activity', 0)
            if last_activity:
                embed.add_field(
                    name="🕒 Activity",
                    value=f"Last Activity: `{time_ago(last_activity)}`",
                    inline=True
                )
            
            # Bot-wide stats
            global_metrics = music_manager.get_metrics()
            embed.add_field(
                name="🌐 Global Stats",
                value=f"Total Songs Played: `{global_metrics.get('songs_played', 0)}`\n"
                      f"Active Connections: `{len(music_manager.voice_clients)}`\n"
                      f"Total Queued: `{sum(len(q) for q in music_manager.queues.values())}`",
                inline=True
            )
            
            # Command breakdown
            if usage_stats.get('command_breakdown'):
                top_commands = sorted(
                    usage_stats['command_breakdown'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                command_text = "\n".join([f"`{cmd}`: {count}" for cmd, count in top_commands])
                embed.add_field(
                    name="🔝 Top Commands",
                    value=command_text,
                    inline=True
                )
            
            embed.set_footer(text=f"Uptime: {format_duration(int(time.time() - self.bot.startup_time if hasattr(self.bot, 'startup_time') else 0))}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await interaction.followup.send("❌ Failed to retrieve statistics.", ephemeral=True)
    
    @app_commands.command(name="settings", description="View or update bot settings")
    @app_commands.describe(
        max_queue_size="Maximum number of songs in queue",
        auto_disconnect="Auto-disconnect timeout in seconds",
        bass_boost="Enable or disable bass boost feature"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def settings(self, interaction: discord.Interaction, 
                      max_queue_size: Optional[int] = None,
                      auto_disconnect: Optional[int] = None,
                      bass_boost: Optional[bool] = None):
        """View or update guild settings."""
        try:
            guild_id = interaction.guild.id
            
            # If no parameters provided, show current settings
            if all(param is None for param in [max_queue_size, auto_disconnect, bass_boost]):
                with db_manager:
                    guild_settings = db_manager.get_guild_settings(guild_id)
                
                embed = discord.Embed(
                    title="⚙️ Current Settings",
                    description=f"Settings for **{interaction.guild.name}**",
                    color=discord.Color.blue()
                )
                
                if guild_settings:
                    embed.add_field(
                        name="Queue Settings",
                        value=f"Max Queue Size: `{guild_settings.max_queue_size}`",
                        inline=True
                    )
                    embed.add_field(
                        name="Connection Settings",
                        value=f"Auto Disconnect: `{guild_settings.auto_disconnect_timeout}s`",
                        inline=True
                    )
                    embed.add_field(
                        name="Audio Settings",
                        value=f"Bass Boost: `{'Enabled' if guild_settings.bass_boost_enabled else 'Disabled'}`",
                        inline=True
                    )
                    embed.add_field(
                        name="Command Prefix",
                        value=f"Prefix: `{guild_settings.prefix}`",
                        inline=True
                    )
                else:
                    embed.description = "Using default settings"
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Update settings
            updates = {}
            if max_queue_size is not None:
                if 1 <= max_queue_size <= 500:
                    updates['max_queue_size'] = max_queue_size
                else:
                    await interaction.response.send_message("❌ Max queue size must be between 1 and 500.", ephemeral=True)
                    return
            
            if auto_disconnect is not None:
                if 60 <= auto_disconnect <= 3600:
                    updates['auto_disconnect_timeout'] = auto_disconnect
                else:
                    await interaction.response.send_message("❌ Auto disconnect must be between 60 and 3600 seconds.", ephemeral=True)
                    return
            
            if bass_boost is not None:
                updates['bass_boost_enabled'] = bass_boost
            
            # Apply updates
            with db_manager:
                success = db_manager.update_guild_settings(guild_id, **updates)
            
            if success:
                embed = discord.Embed(
                    title="✅ Settings Updated",
                    description="Guild settings have been updated successfully",
                    color=discord.Color.green()
                )
                
                for key, value in updates.items():
                    embed.add_field(
                        name=key.replace('_', ' ').title(),
                        value=f"`{value}`",
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                logger.info(f"Guild settings updated for {guild_id}: {updates}")
            else:
                await interaction.response.send_message("❌ Failed to update settings.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in settings command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing settings.", ephemeral=True)
    
    @app_commands.command(name="cleanup", description="Clean up bot messages")
    @app_commands.describe(count="Number of messages to check (default: 10, max: 100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def cleanup(self, interaction: discord.Interaction, count: int = 10):
        """Clean up bot messages in the channel."""
        try:
            if count < 1 or count > 100:
                await interaction.response.send_message("❌ Count must be between 1 and 100.", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Delete bot messages
            deleted = 0
            async for message in interaction.channel.history(limit=count):
                if message.author == self.bot.user:
                    try:
                        await message.delete()
                        deleted += 1
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        break
            
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Deleted {deleted} bot message(s)",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Cleaned up {deleted} messages in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ You do not have permission to manage messages.", ephemeral=True)