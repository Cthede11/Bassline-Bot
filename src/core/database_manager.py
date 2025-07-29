import logging
import os
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from config.database import get_db, SessionLocal
from src.database.models import Guild, User, Playlist, Song, Usage
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the bot."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    # Guild operations
    def get_or_create_guild(self, guild_id: int, guild_name: str) -> Guild:
        """Get or create a guild record."""
        guild = self.session.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            guild = Guild(id=guild_id, name=guild_name)
            self.session.add(guild)
            self.session.commit()
            logger.info(f"Created new guild record: {guild_name} ({guild_id})")
        return guild
    
    def update_guild_settings(self, guild_id: int, **kwargs) -> bool:
        """Update guild settings."""
        try:
            guild = self.session.query(Guild).filter(Guild.id == guild_id).first()
            if guild:
                for key, value in kwargs.items():
                    if hasattr(guild, key):
                        setattr(guild, key, value)
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating guild settings: {e}")
            self.session.rollback()
            return False
    
    def get_guild_settings(self, guild_id: int) -> Optional[Guild]:
        """Get guild settings."""
        return self.session.query(Guild).filter(Guild.id == guild_id).first()
    
    # User operations
    def get_or_create_user(self, user_id: int, username: str) -> User:
        """Get or create a user record."""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, username=username)
            self.session.add(user)
            self.session.commit()
            logger.info(f"Created new user record: {username} ({user_id})")
        return user
    
    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """Update user settings."""
        try:
            user = self.session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            self.session.rollback()
            return False
    
    # Enhanced song operations for database-first architecture
    def find_or_create_song(self, url: str, title: str = None, duration: int = None, 
                           thumbnail: str = None, uploader: str = None, 
                           requested_by: int = None) -> Song:
        """Find existing song or create new one. Core method for database-first approach."""
        try:
            # First, try to find existing song by URL
            song = self.session.query(Song).filter(Song.url == url).first()
            
            if song:
                # Update last played info and play count
                song.play_count += 1
                song.last_played = datetime.utcnow()
                if requested_by:
                    song.last_requested_by = requested_by
                song.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Found existing song: {song.title} (played {song.play_count} times)")
                return song
            else:
                # Create new song record
                song = Song(
                    title=title or "Unknown Title",
                    url=url,
                    duration=duration,
                    thumbnail=thumbnail,
                    uploader=uploader,
                    play_count=1,
                    first_played=datetime.utcnow(),
                    last_played=datetime.utcnow(),
                    last_requested_by=requested_by,
                    is_downloaded=False
                )
                self.session.add(song)
                self.session.commit()
                logger.info(f"Created new song record: {song.title}")
                return song
                
        except Exception as e:
            logger.error(f"Error finding/creating song: {e}")
            self.session.rollback()
            raise
    
    def update_song_download_status(self, song_id: int, local_path: str, file_size: int = None) -> bool:
        """Update song with download information."""
        try:
            song = self.session.query(Song).filter(Song.id == song_id).first()
            if song:
                song.local_path = local_path
                song.file_size = file_size
                song.is_downloaded = True
                song.download_date = datetime.utcnow()
                song.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Updated download status for song {song_id}: {local_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating song download status: {e}")
            self.session.rollback()
            return False
    
    def get_song_by_url(self, url: str) -> Optional[Song]:
        """Get song by URL - primary lookup method."""
        try:
            return self.session.query(Song).filter(Song.url == url).first()
        except Exception as e:
            logger.error(f"Error getting song by URL: {e}")
            return None
    
    def get_downloaded_song_path(self, url: str) -> Optional[str]:
        """Get local file path for downloaded song, verify file exists."""
        try:
            song = self.session.query(Song).filter(
                Song.url == url,
                Song.is_downloaded == True,
                Song.local_path.isnot(None)
            ).first()
            
            if song and song.local_path:
                if os.path.exists(song.local_path):
                    return song.local_path
                else:
                    # File missing, update database
                    song.is_downloaded = False
                    song.local_path = None
                    self.session.commit()
                    logger.warning(f"File missing for song {song.id}, updated database")
            return None
        except Exception as e:
            logger.error(f"Error getting downloaded song path: {e}")
            return None
    
    def record_song_play(self, song_id: int) -> bool:
        """Record that a song was played."""
        try:
            song = self.session.query(Song).filter(Song.id == song_id).first()
            if song:
                song.play_count += 1
                song.last_played = datetime.utcnow()
                song.updated_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error recording song play: {e}")
            self.session.rollback()
            return False
    
    def cleanup_unused_songs(self, days_inactive: int = 30, min_play_count: int = 2) -> Tuple[int, int]:
        """Clean up songs that haven't been played recently and have low play counts."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
            
            # Find songs to delete (not played recently AND low play count)
            songs_to_delete = self.session.query(Song).filter(
                Song.last_played < cutoff_date,
                Song.play_count < min_play_count,
                Song.playlist_id.is_(None)  # Don't delete playlist songs
            ).all()
            
            deleted_files = 0
            deleted_records = 0
            
            for song in songs_to_delete:
                try:
                    # Delete file if it exists
                    if song.local_path and os.path.exists(song.local_path):
                        os.remove(song.local_path)
                        deleted_files += 1
                        logger.info(f"Deleted file: {song.local_path}")
                    
                    # Delete database record
                    self.session.delete(song)
                    deleted_records += 1
                    logger.info(f"Deleted song record: {song.title}")
                    
                except Exception as file_error:
                    logger.error(f"Error deleting song {song.id}: {file_error}")
                    continue
            
            self.session.commit()
            logger.info(f"Cleanup completed: {deleted_files} files, {deleted_records} records deleted")
            return deleted_files, deleted_records
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self.session.rollback()
            return 0, 0
    
    def get_song_analytics(self) -> dict:
        """Get comprehensive song analytics."""
        try:
            total_songs = self.session.query(Song).count()
            downloaded_songs = self.session.query(Song).filter(Song.is_downloaded == True).count()
            playlist_songs = self.session.query(Song).filter(Song.playlist_id.isnot(None)).count()
            global_songs = total_songs - playlist_songs
            
            # Most popular songs
            popular_songs = self.session.query(Song).filter(
                Song.playlist_id.is_(None)
            ).order_by(Song.play_count.desc()).limit(10).all()
            
            # Recent activity
            recent_plays = self.session.query(Song).filter(
                Song.last_played >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            # Storage stats
            total_storage = self.session.query(func.sum(Song.file_size)).scalar() or 0
            
            return {
                'total_songs': total_songs,
                'downloaded_songs': downloaded_songs,
                'playlist_songs': playlist_songs,
                'global_songs': global_songs,
                'recent_plays_7d': recent_plays,
                'total_storage_bytes': total_storage,
                'total_storage_mb': round(total_storage / (1024 * 1024), 2),
                'popular_songs': [
                    {
                        'title': song.title,
                        'play_count': song.play_count,
                        'last_played': song.last_played.isoformat() if song.last_played else None
                    }
                    for song in popular_songs
                ]
            }
        except Exception as e:
            logger.error(f"Error getting song analytics: {e}")
            return {}
    
    def sync_filesystem_with_database(self) -> dict:
        """Sync database records with actual filesystem."""
        try:
            synced = 0
            missing_files = 0
            
            # Check database records against filesystem
            downloaded_songs = self.session.query(Song).filter(
                Song.is_downloaded == True,
                Song.local_path.isnot(None)
            ).all()
            
            for song in downloaded_songs:
                if not os.path.exists(song.local_path):
                    song.is_downloaded = False
                    song.local_path = None
                    missing_files += 1
                else:
                    synced += 1
            
            self.session.commit()
            
            return {
                'synced_files': synced,
                'missing_files': missing_files
            }
            
        except Exception as e:
            logger.error(f"Error syncing filesystem: {e}")
            self.session.rollback()
            return {'error': str(e)}
    
    def cleanup_missing_downloads(self) -> int:
        """Clean up database entries for files that no longer exist."""
        try:
            cleaned_count = 0
            downloaded_songs = self.session.query(Song).filter(
                Song.is_downloaded == True,
                Song.local_path.isnot(None)
            ).all()
            
            for song in downloaded_songs:
                if not os.path.exists(song.local_path):
                    song.is_downloaded = False
                    song.local_path = None
                    cleaned_count += 1
                    logger.info(f"Cleaned up missing file for song: {song.title}")
            
            if cleaned_count > 0:
                self.session.commit()
                logger.info(f"Cleaned up {cleaned_count} missing file entries")
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up missing files: {e}")
            self.session.rollback()
            return 0
    
    def get_download_stats(self) -> dict:
        """Get statistics about downloaded songs."""
        try:
            downloaded_songs = self.session.query(Song).filter(Song.is_downloaded == True).all()
            
            total_files = len(downloaded_songs)
            total_size = sum(song.file_size or 0 for song in downloaded_songs)
            
            # Check which files still exist
            existing_files = 0
            existing_size = 0
            for song in downloaded_songs:
                if song.local_path and os.path.exists(song.local_path):
                    existing_files += 1
                    existing_size += song.file_size or 0
            
            return {
                'total_downloaded': total_files,
                'total_size_bytes': total_size,
                'existing_files': existing_files,
                'existing_size_bytes': existing_size,
                'missing_files': total_files - existing_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'existing_size_mb': round(existing_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Error getting download stats: {e}")
            return {
                'total_downloaded': 0,
                'total_size_bytes': 0,
                'existing_files': 0,
                'existing_size_bytes': 0,
                'missing_files': 0,
                'total_size_mb': 0,
                'existing_size_mb': 0
            }
    
    # Playlist operations
    def create_playlist(self, name: str, guild_id: int, owner_id: int, channel_id: int = None) -> Playlist:
        """Create a new playlist."""
        try:
            playlist = Playlist(
                name=name,
                guild_id=guild_id,
                owner_id=owner_id,
                channel_id=channel_id
            )
            self.session.add(playlist)
            self.session.commit()
            logger.info(f"Created playlist: {name} in guild {guild_id}")
            return playlist
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            self.session.rollback()
            raise
    
    def get_playlists(self, guild_id: int, owner_id: int = None) -> List[Playlist]:
        """Get playlists for a guild, optionally filtered by owner."""
        query = self.session.query(Playlist).filter(Playlist.guild_id == guild_id)
        if owner_id:
            query = query.filter(Playlist.owner_id == owner_id)
        return query.all()
    
    def get_playlist_by_name(self, guild_id: int, name: str) -> Optional[Playlist]:
        """Get a playlist by name."""
        return self.session.query(Playlist).filter(
            Playlist.guild_id == guild_id,
            Playlist.name.ilike(f"%{name}%")
        ).first()
    
    def get_playlist_by_id(self, playlist_id: int) -> Optional[Playlist]:
        """Get a playlist by ID."""
        return self.session.query(Playlist).filter(Playlist.id == playlist_id).first()
    
    def add_song_to_playlist(self, playlist_id: int, title: str, url: str, added_by: int, duration: int = None) -> Song:
        """Add a song to a playlist."""
        try:
            # Get the next position
            max_position = self.session.query(func.max(Song.position)).filter(
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
            self.session.add(song)
            self.session.commit()
            return song
        except Exception as e:
            logger.error(f"Error adding song to playlist: {e}")
            self.session.rollback()
            raise
    
    def get_playlist_songs(self, playlist_id: int) -> List[Song]:
        """Get all songs in a playlist."""
        return self.session.query(Song).filter(
            Song.playlist_id == playlist_id
        ).order_by(Song.position).all()
    
    def delete_playlist(self, playlist_id: int) -> bool:
        """Delete a playlist and all its songs."""
        try:
            playlist = self.session.query(Playlist).filter(Playlist.id == playlist_id).first()
            if playlist:
                # Delete all songs in the playlist first
                self.session.query(Song).filter(Song.playlist_id == playlist_id).delete()
                # Delete the playlist
                self.session.delete(playlist)
                self.session.commit()
                logger.info(f"Deleted playlist {playlist_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            self.session.rollback()
            return False
    
    def remove_song_from_playlist(self, playlist_id: int, song_id: int) -> bool:
        """Remove a specific song from a playlist."""
        try:
            song = self.session.query(Song).filter(
                Song.id == song_id,
                Song.playlist_id == playlist_id
            ).first()
            
            if song:
                self.session.delete(song)
                self.session.commit()
                
                # Reorder remaining songs
                remaining_songs = self.session.query(Song).filter(
                    Song.playlist_id == playlist_id
                ).order_by(Song.position).all()
                
                for i, remaining_song in enumerate(remaining_songs, 1):
                    remaining_song.position = i
                
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing song from playlist: {e}")
            self.session.rollback()
            return False
    
    def search_playlists(self, guild_id: int, search_term: str, limit: int = 10) -> List[Playlist]:
        """Search playlists by name."""
        return self.session.query(Playlist).filter(
            Playlist.guild_id == guild_id,
            Playlist.name.ilike(f"%{search_term}%")
        ).limit(limit).all()
    
    def update_playlist(self, playlist_id: int, **kwargs) -> bool:
        """Update playlist properties."""
        try:
            playlist = self.session.query(Playlist).filter(Playlist.id == playlist_id).first()
            if playlist:
                for key, value in kwargs.items():
                    if hasattr(playlist, key):
                        setattr(playlist, key, value)
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            self.session.rollback()
            return False
    
    def get_user_playlist_count(self, user_id: int, guild_id: int) -> int:
        """Get the number of playlists a user has created."""
        return self.session.query(Playlist).filter(
            Playlist.owner_id == user_id,
            Playlist.guild_id == guild_id
        ).count()
    
    def get_popular_playlists(self, guild_id: int, limit: int = 10) -> List[Playlist]:
        """Get playlists sorted by song count (popularity)."""
        result = self.session.query(
            Playlist,
            func.count(Song.id).label('song_count')
        ).outerjoin(Song).filter(
            Playlist.guild_id == guild_id
        ).group_by(Playlist.id).order_by(
            func.count(Song.id).desc()
        ).limit(limit).all()
        
        return [playlist for playlist, song_count in result]
    
    # Usage tracking
    def log_command_usage(self, guild_id: int, user_id: int, command_name: str, 
                         execution_time: float = None, success: bool = True, 
                         error_message: str = None):
        """Log command usage for analytics."""
        try:
            usage = Usage(
                guild_id=guild_id,
                user_id=user_id,
                command_name=command_name,
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )
            self.session.add(usage)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error logging command usage: {e}")
            self.session.rollback()
    
    def get_usage_stats(self, guild_id: int = None, days: int = 7) -> dict:
        """Get usage statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(Usage).filter(Usage.timestamp >= start_date)
        
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