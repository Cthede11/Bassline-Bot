import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from config.database import get_db, SessionLocal

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the bot."""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = SessionLocal()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is None:
                try:
                    self.session.commit()
                except Exception as e:
                    logger.error(f"Error committing transaction: {e}")
                    self.session.rollback()
                    raise
            else:
                self.session.rollback()
            self.session.close()
    
    def _get_session(self):
        """Get current session or create new one."""
        if self.session is None:
            self.session = SessionLocal()
        return self.session
    
    # Guild operations
    def get_or_create_guild(self, guild_id: int, guild_name: str):
        """Get or create a guild record."""
        from src.database.models import Guild
        
        session = self._get_session()
        guild = session.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            guild = Guild(id=guild_id, name=guild_name)
            session.add(guild)
            try:
                session.commit()
                logger.info(f"Created new guild record: {guild_name} ({guild_id})")
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating guild: {e}")
                raise
        else:
            # Update name if changed
            if guild.name != guild_name:
                guild.name = guild_name
                session.commit()
        
        return guild
    
    def update_guild_settings(self, guild_id: int, **kwargs) -> bool:
        """Update guild settings."""
        from src.database.models import Guild
        
        try:
            session = self._get_session()
            guild = session.query(Guild).filter(Guild.id == guild_id).first()
            if guild:
                for key, value in kwargs.items():
                    if hasattr(guild, key):
                        setattr(guild, key, value)
                guild.updated_at = datetime.utcnow()
                session.commit()
                return True
            else:
                # Create guild with settings if it doesn't exist
                guild = Guild(id=guild_id, name="Unknown Guild", **kwargs)
                session.add(guild)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating guild settings: {e}")
            if session:
                session.rollback()
            return False
    
    def get_guild_settings(self, guild_id: int):
        """Get guild settings."""
        from src.database.models import Guild
        
        session = self._get_session()
        return session.query(Guild).filter(Guild.id == guild_id).first()
    
    # User operations
    def get_or_create_user(self, user_id: int, username: str):
        """Get or create a user record."""
        from src.database.models import User
        
        session = self._get_session()
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, username=username)
            session.add(user)
            try:
                session.commit()
                logger.info(f"Created new user record: {username} ({user_id})")
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating user: {e}")
                raise
        else:
            # Update username and last seen if changed
            if user.username != username:
                user.username = username
            user.last_seen = datetime.utcnow()
            session.commit()
        
        return user
    
    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """Update user settings."""
        from src.database.models import User
        
        try:
            session = self._get_session()
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            if session:
                session.rollback()
            return False
    
    # Playlist operations
    def create_playlist(self, name: str, guild_id: int, owner_id: int, channel_id: int = None):
        """Create a new playlist."""
        from src.database.models import Playlist
        
        try:
            session = self._get_session()
            playlist = Playlist(
                name=name,
                guild_id=guild_id,
                owner_id=owner_id,
                channel_id=channel_id
            )
            session.add(playlist)
            session.commit()
            logger.info(f"Created playlist: {name} in guild {guild_id}")
            return playlist
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            if session:
                session.rollback()
            raise
    
    def get_playlists(self, guild_id: int, owner_id: int = None) -> List:
        """Get playlists for a guild, optionally filtered by owner."""
        from src.database.models import Playlist
        
        session = self._get_session()
        query = session.query(Playlist).filter(Playlist.guild_id == guild_id)
        if owner_id:
            query = query.filter(Playlist.owner_id == owner_id)
        return query.all()
    
    def get_playlist_by_name(self, guild_id: int, name: str):
        """Get a playlist by name."""
        from src.database.models import Playlist
        
        session = self._get_session()
        return session.query(Playlist).filter(
            Playlist.guild_id == guild_id,
            Playlist.name.ilike(f"%{name}%")
        ).first()
    
    def add_song_to_playlist(self, playlist_id: int, title: str, url: str, added_by: int, duration: int = None):
        """Add a song to a playlist."""
        from src.database.models import Song
        
        try:
            session = self._get_session()
            # Get the next position
            max_position = session.query(func.max(Song.position)).filter(
                Song.playlist_id == playlist_id
            ).scalar() or 0
            
            song = Song(
                playlist_id=playlist_id,
                title=title,
                url=url,
                duration=duration,
                added_by=added_by,
                position=max_position + 1
            )
            session.add(song)
            session.commit()
            return song
        except Exception as e:
            logger.error(f"Error adding song to playlist: {e}")
            if session:
                session.rollback()
            raise
    
    def get_playlist_songs(self, playlist_id: int) -> List:
        """Get all songs in a playlist."""
        from src.database.models import Song
        
        session = self._get_session()
        return session.query(Song).filter(
            Song.playlist_id == playlist_id
        ).order_by(Song.position).all()
    
    # Usage tracking
    def log_command_usage(self, guild_id: int, user_id: int, command_name: str, 
                         execution_time: float = None, success: bool = True, 
                         error_message: str = None):
        """Log command usage for analytics."""
        from src.database.models import Usage
        
        try:
            session = self._get_session()
            usage = Usage(
                guild_id=guild_id,
                user_id=user_id,
                command_name=command_name,
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )
            session.add(usage)
            session.commit()
        except Exception as e:
            logger.error(f"Error logging command usage: {e}")
            if session:
                session.rollback()
    
    def get_usage_stats(self, guild_id: int = None, days: int = 7) -> dict:
        """Get usage statistics."""
        from src.database.models import Usage
        
        session = self._get_session()
        start_date = datetime.utcnow() - timedelta(days=days)
        query = session.query(Usage).filter(Usage.timestamp >= start_date)
        
        if guild_id:
            query = query.filter(Usage.guild_id == guild_id)
        
        usage_records = query.all()
        
        stats = {
            'total_commands': len(usage_records),
            'successful_commands': len([u for u in usage_records if u.success]),
            'failed_commands': len([u for u in usage_records if not u.success]),
            'unique_users': len(set(u.user_id for u in usage_records)),
            'unique_guilds': len(set(u.guild_id for u in usage_records)),
            'command_breakdown': {},
            'avg_execution_time': 0
        }
        
        # Command breakdown
        for usage in usage_records:
            cmd = usage.command_name
            if cmd not in stats['command_breakdown']:
                stats['command_breakdown'][cmd] = 0
            stats['command_breakdown'][cmd] += 1
        
        # Average execution time
        execution_times = [u.execution_time for u in usage_records if u.execution_time]
        if execution_times:
            stats['avg_execution_time'] = sum(execution_times) / len(execution_times)
        
        return stats

# Global database manager instance
db_manager = DatabaseManager()