import discord
from discord.ext import commands
from discord import app_commands
from typing import Union

from src.core.music_manager import music_manager
from src.core.database_manager import db_manager

class PermissionError(commands.CheckFailure):
    """Custom permission error."""
    pass

def is_dj_or_admin():
    """Check if user is DJ or admin."""
    async def predicate(ctx_or_interaction: Union[commands.Context, discord.Interaction]) -> bool:
        # Handle both context and interaction
        if isinstance(ctx_or_interaction, commands.Context):
            user = ctx_or_interaction.author
            guild = ctx_or_interaction.guild
        else:  # discord.Interaction
            user = ctx_or_interaction.user
            guild = ctx_or_interaction.guild
        
        if not guild:
            return False
        
        # Check if user is administrator
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True
        
        # Check DJ role
        dj_role_id = music_manager.get_dj_role_id(guild.id)
        if dj_role_id and isinstance(user, discord.Member):
            dj_role = guild.get_role(dj_role_id)
            if dj_role and dj_role in user.roles:
                return True
        
        # If no DJ role is set, allow everyone
        if not dj_role_id:
            return True
        
        return False
    
    return commands.check(predicate)

def is_dj_or_admin_slash():
    """Check if user is DJ or admin for slash commands."""
    async def predicate(interaction: discord.Interaction) -> bool:
        user = interaction.user
        guild = interaction.guild
        
        if not guild:
            return False
        
        # Check if user is administrator
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True
        
        # Check DJ role
        dj_role_id = music_manager.get_dj_role_id(guild.id)
        if dj_role_id and isinstance(user, discord.Member):
            dj_role = guild.get_role(dj_role_id)
            if dj_role and dj_role in user.roles:
                return True
            else:
                raise PermissionError(f"You need the DJ role or administrator permissions to use this command.")
        
        # If no DJ role is set, allow everyone
        return True
    
    return app_commands.check(predicate)

def is_in_voice():
    """Check if user is in a voice channel."""
    async def predicate(ctx_or_interaction: Union[commands.Context, discord.Interaction]) -> bool:
        # Handle both context and interaction
        if isinstance(ctx_or_interaction, commands.Context):
            user = ctx_or_interaction.author
        else:  # discord.Interaction
            user = ctx_or_interaction.user
        
        if isinstance(user, discord.Member) and user.voice and user.voice.channel:
            return True
        
        raise PermissionError("You must be in a voice channel to use this command.")
    
    return commands.check(predicate)

def bot_has_permissions(**perms):
    """Check if bot has required permissions."""
    async def predicate(ctx_or_interaction: Union[commands.Context, discord.Interaction]) -> bool:
        # Handle both context and interaction
        if isinstance(ctx_or_interaction, commands.Context):
            guild = ctx_or_interaction.guild
            me = guild.me if guild else None
        else:  # discord.Interaction
            guild = ctx_or_interaction.guild
            me = guild.me if guild else None
        
        if not guild or not me:
            return False
        
        missing = [perm for perm, value in perms.items() 
                  if getattr(me.guild_permissions, perm, None) != value]
        
        if missing:
            raise PermissionError(f"Bot is missing permissions: {', '.join(missing)}")
        
        return True
    
    return commands.check(predicate)

def is_premium_user():
    """Check if user has premium features."""
    async def predicate(ctx_or_interaction: Union[commands.Context, discord.Interaction]) -> bool:
        # Handle both context and interaction
        if isinstance(ctx_or_interaction, commands.Context):
            user_id = ctx_or_interaction.author.id
        else:  # discord.Interaction
            user_id = ctx_or_interaction.user.id
        
        user = db_manager.session.query(db_manager.User).filter(db_manager.User.id == user_id).first()
        if user and user.tier in ['premium', 'pro']:
            return True
        
        raise PermissionError("This feature requires a premium subscription.")
    
    return commands.check(predicate)