import logging
import traceback
import discord
from typing import Optional
from datetime import datetime
from discord.ext import commands

from config.settings import settings
from src.core.database_manager import db_manager

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling and reporting."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.error_count = 0
        self.recent_errors = []
    
    async def handle_command_error(self, ctx: commands.Context, error: Exception) -> bool:
        """Handle command errors."""
        self.error_count += 1
        error_info = {
            'timestamp': datetime.utcnow(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'command': ctx.command.name if ctx.command else 'Unknown',
            'guild_id': ctx.guild.id if ctx.guild else None,
            'user_id': ctx.author.id,
            'traceback': traceback.format_exc()
        }
        
        self.recent_errors.append(error_info)
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)
        
        # Log to database
        if error_info['guild_id']:
            db_manager.log_command_usage(
                guild_id=error_info['guild_id'],
                user_id=error_info['user_id'],
                command_name=error_info['command'],
                success=False,
                error_message=error_info['error_message']
            )
        
        # Handle specific error types
        if isinstance(error, commands.CommandNotFound):
            return False  # Ignore command not found
        
        elif isinstance(error, commands.MissingPermissions):
            await self._send_error_message(
                ctx, 
                "❌ You don't have the required permissions to use this command.",
                ephemeral=True
            )
            return True
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await self._send_error_message(
                ctx,
                f"❌ Missing required argument: `{error.param.name}`",
                ephemeral=True
            )
            return True
        
        elif isinstance(error, commands.BadArgument):
            await self._send_error_message(
                ctx,
                f"❌ Invalid argument provided: {str(error)}",
                ephemeral=True
            )
            return True
        
        elif isinstance(error, commands.CommandOnCooldown):
            await self._send_error_message(
                ctx,
                f"❌ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
            return True
        
        elif isinstance(error, discord.Forbidden):
            await self._send_error_message(
                ctx,
                "❌ I don't have permission to perform this action.",
                ephemeral=True
            )
            return True
        
        elif isinstance(error, discord.HTTPException):
            await self._send_error_message(
                ctx,
                "❌ A Discord API error occurred. Please try again later.",
                ephemeral=True
            )
            return True
        
        else:
            # Log unexpected errors
            logger.error(f"Unhandled command error: {error}", exc_info=True)
            await self._send_error_message(
                ctx,
                "❌ An unexpected error occurred. The developers have been notified.",
                ephemeral=True
            )
            return True
    
    async def handle_interaction_error(self, interaction: discord.Interaction, error: Exception) -> bool:
        """Handle slash command errors."""
        self.error_count += 1
        error_info = {
            'timestamp': datetime.utcnow(),
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
            db_manager.log_command_usage(
                guild_id=error_info['guild_id'],
                user_id=error_info['user_id'],
                command_name=error_info['command'],
                success=False,
                error_message=error_info['error_message']
            )
        
        # Handle specific error types
        if isinstance(error, discord.app_commands.MissingPermissions):
            await self._send_interaction_error(
                interaction,
                "❌ You don't have the required permissions to use this command."
            )
            return True
        
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await self._send_interaction_error(
                interaction,
                f"❌ Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            )
            return True
        
        elif isinstance(error, discord.Forbidden):
            await self._send_interaction_error(
                interaction,
                "❌ I don't have permission to perform this action."
            )
            return True
        
        else:
            logger.error(f"Unhandled interaction error: {error}", exc_info=True)
            await self._send_interaction_error(
                interaction,
                "❌ An unexpected error occurred. The developers have been notified."
            )
            return True
    
    async def _send_error_message(self, ctx: commands.Context, message: str, ephemeral: bool = False):
        """Send error message to context."""
        try:
            if ephemeral and hasattr(ctx, 'send'):
                await ctx.send(message, ephemeral=True)
            else:
                await ctx.send(message)
        except discord.HTTPException:
            logger.error(f"Failed to send error message: {message}")
    
    async def _send_interaction_error(self, interaction: discord.Interaction, message: str):
        """Send error message to interaction."""
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            logger.error(f"Failed to send interaction error message: {message}")
    
    def get_error_stats(self) -> dict:
        """Get error statistics."""
        return {
            'total_errors': self.error_count,
            'recent_errors': len(self.recent_errors),
            'error_types': {}
        }
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors."""
        return self.recent_errors[-limit:]