import asyncio
import functools
import logging
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import yt_dlp
from datetime import datetime

from config.settings import settings
from src.utils.helpers import retry
from src.utils.validators import sanitize_filename
from src.core.database_manager import db_manager

logger = logging.getLogger(__name__)

class YouTubeError(Exception):
    """Custom YouTube-related error."""
    pass

class YouTubeManager:
    """Enhanced YouTube manager with caching and error handling."""
    
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self.cache_ttl = 3600  # 1 hour
        self.rate_limit_delay = 1.0
        self.last_request_time = 0
        
        # Create downloads directory
        os.makedirs("downloads", exist_ok=True)
        
        # YT-DLP options
        self.base_opts = {
            'format': 'bestaudio[ext=webm]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'restrictfilenames': True,
            'extractflat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'noprogress': True,
            'progress': False,       # 🔹 Force disable progress
            'encoding': 'utf-8',     # 🔹 Ensure output strings are UTF-8 encoded
        }
    
    def _get_cache_key(self, query: str, options: dict = None) -> str:
        """Generate cache key for query."""
        return f"{query}_{hash(str(options or {}))}"
    
    def _is_cache_valid(self, entry: dict) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - entry['timestamp'] < self.cache_ttl
    
    async def _rate_limit(self):
        """Apply rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry(max_attempts=3, delay=2.0)
    async def search(self, query: str, max_results: int = 5) -> List[dict]:
        """Search for videos on YouTube."""
        cache_key = self._get_cache_key(f"search_{query}_{max_results}")
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.debug(f"Cache hit for search: {query}")
            return self.cache[cache_key]['data']
        
        await self._rate_limit()
        
        search_opts = self.base_opts.copy()
        search_opts.update({
            'default_search': f'ytsearch{max_results}',
            'noplaylist': True,
            'extract_flat': False,
        })
        
        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                extract_task = loop.run_in_executor(
                    None, 
                    functools.partial(ydl.extract_info, query, download=False)
                )
                info = await asyncio.wait_for(extract_task, timeout=30.0)
            
            if not info or 'entries' not in info:
                raise YouTubeError("No search results found")
            
            results = []
            for entry in info['entries']:
                if not entry:
                    continue
                
                result = {
                    'id': entry.get('id'),
                    'title': entry.get('title', 'Unknown Title'),
                    'url': entry.get('webpage_url', ''),
                    'duration': entry.get('duration'),
                    'duration_str': self._format_duration(entry.get('duration')),
                    'thumbnail': entry.get('thumbnail'),
                    'uploader': entry.get('uploader', 'Unknown'),
                    'view_count': entry.get('view_count', 0),
                    'upload_date': entry.get('upload_date'),
                }
                results.append(result)
                
                if len(results) >= max_results:
                    break
            
            # Cache results
            self.cache[cache_key] = {
                'data': results,
                'timestamp': time.time()
            }
            
            logger.debug(f"Search completed: {query} - {len(results)} results")
            return results
            
        except asyncio.TimeoutError:
            raise YouTubeError("Search timed out")
        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")
            raise YouTubeError(f"Search failed: {str(e)}")
    
    @retry(max_attempts=3, delay=2.0)
    async def get_info(self, url_or_query: str, download: bool = True) -> Dict:
        """Enhanced info extraction with database integration."""
        
        # First check if we already have this song downloaded in database
        if download and url_or_query.startswith(('http', 'https')):
            existing_path = db_manager.get_downloaded_song_path(url_or_query)
            if existing_path:
                logger.info(f"Using existing download: {existing_path}")
                # Get cached info and update with local path
                cache_key = self._get_cache_key(f"info_{url_or_query}_false")
                if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
                    result = self.cache[cache_key]['data'].copy()
                    result['downloaded_file'] = existing_path
                    result['local_path'] = existing_path
                    return result
        
        # Continue with existing get_info logic...
        cache_key = self._get_cache_key(f"info_{url_or_query}_{download}")
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.debug(f"Cache hit for info: {url_or_query}")
            return self.cache[cache_key]['data']
        
        await self._rate_limit()
        
        info_opts = self.base_opts.copy()
        
        if download and settings.download_enabled:
            info_opts.update({
                'outtmpl': os.path.join('downloads', '%(title)s-%(id)s.%(ext)s'),
            })
        else:
            download = False
        
        # Determine if it's a URL or search query
        if not (url_or_query.startswith('http') or url_or_query.startswith('www')):
            info_opts['default_search'] = 'ytsearch1'
        
        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                extract_task = loop.run_in_executor(
                    None,
                    functools.partial(ydl.extract_info, url_or_query, download=download)
                )
                info = await asyncio.wait_for(extract_task, timeout=60.0)

            
            if not info:
                raise YouTubeError("No video information found")
            
            # Handle search results
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
            else:
                entry = info
            
            if not entry:
                raise YouTubeError("No valid video found")
            
            # Extract relevant information
            result = {
                'id': entry.get('id'),
                'title': entry.get('title', 'Unknown Title'),
                'url': entry.get('webpage_url', ''),
                'stream_url': entry.get('url'),
                'duration': entry.get('duration', 0),
                'thumbnail': entry.get('thumbnail'),
                'uploader': entry.get('uploader', 'Unknown'),
                'description': entry.get('description', ''),
                'view_count': entry.get('view_count', 0),
                'like_count': entry.get('like_count', 0),
                'upload_date': entry.get('upload_date'),
                'formats': entry.get('formats', []),
                'downloaded_file': None,
                'local_path': None,
                'file_size': None
            }
            
            # Handle downloaded file and update database
            if download:
                downloaded_file = entry.get('_filename') or entry.get('filepath')
                if downloaded_file and os.path.exists(downloaded_file):
                    result['downloaded_file'] = downloaded_file
                    result['local_path'] = downloaded_file
                    result['file_size'] = os.path.getsize(downloaded_file)
                    
                    # Update database if this is for a playlist song
                    try:
                        existing_song = db_manager.get_song_by_url(result['url'])
                        if existing_song:
                            db_manager.update_song_download_info(
                                existing_song.id, 
                                downloaded_file, 
                                result['file_size']
                            )
                            logger.info(f"Updated database with download info for song: {existing_song.id}")
                    except Exception as db_error:
                        logger.error(f"Error updating database with download info: {db_error}")
                else:
                    result['stream_url'] = downloaded_file
            
            # Get best audio format for streaming if not downloaded
            if not result.get('downloaded_file') and result['formats']:
                audio_formats = [f for f in result['formats'] 
                               if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                if audio_formats:
                    # Prefer opus/webm format
                    best_format = next(
                        (f for f in audio_formats if 'opus' in f.get('acodec', '').lower()),
                        audio_formats[0]
                    )
                    result['stream_url'] = best_format['url']
            
            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.debug(f"Info extraction completed: {result['title']}")
            return result
            
        except asyncio.TimeoutError:
            raise YouTubeError("Information extraction timed out")
        except Exception as e:
            logger.error(f"Info extraction error for '{url_or_query}': {e}")
            raise YouTubeError(f"Failed to get video info: {str(e)}")
    
    def cleanup_old_downloads(self, max_age_hours: int = 24):
        """Enhanced cleanup with database integration."""
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_files = 0
        
        for filename in os.listdir(downloads_dir):
            filepath = os.path.join(downloads_dir, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    try:
                        os.remove(filepath)
                        cleaned_files += 1
                        logger.debug(f"Removed old download: {filename}")
                    except OSError as e:
                        logger.error(f"Failed to remove {filename}: {e}")
        
        # Clean up database entries for missing files
        db_cleaned = db_manager.cleanup_missing_downloads()
        
        if cleaned_files > 0 or db_cleaned > 0:
            logger.info(f"Cleanup completed: {cleaned_files} files removed, {db_cleaned} database entries cleaned")
    
    def get_storage_info(self) -> dict:
        """Get storage information combining filesystem and database data."""
        # Get database stats
        db_stats = db_manager.get_download_stats()
        
        # Get filesystem stats
        downloads_dir = Path("downloads")
        filesystem_size = 0
        filesystem_files = 0
        
        if downloads_dir.exists():
            for file_path in downloads_dir.iterdir():
                if file_path.is_file():
                    filesystem_files += 1
                    filesystem_size += file_path.stat().st_size
        
        return {
            **db_stats,
            'filesystem_files': filesystem_files,
            'filesystem_size_bytes': filesystem_size,
            'filesystem_size_mb': round(filesystem_size / (1024 * 1024), 2),
            'downloads_directory': str(downloads_dir.absolute())
        }
    
    def _format_duration(self, duration: Optional[int]) -> str:
        """Format duration in seconds to MM:SS format."""
        if duration is None:
            return "N/A"
        
        try:
            duration = int(duration)
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        except (ValueError, TypeError):
            return "N/A"
    
    def clear_cache(self):
        """Clear the cache."""
        self.cache.clear()
        logger.info("YouTube cache cleared")

    async def get_info_with_database(self, url_or_query: str, requested_by: int = None) -> dict:
        """
        Enhanced info extraction with database integration.
        This is the new method that checks database first, then downloads if needed.
        """
        try:
            # Step 1: If it's a URL, check database first
            if url_or_query.startswith(('http', 'https')):
                existing_song = db_manager.get_song_by_url(url_or_query)
                if existing_song:
                    # Found in database! Update play count and return cached info
                    existing_song.play_count += 1
                    existing_song.last_played = datetime.utcnow()
                    if requested_by:
                        existing_song.last_requested_by = requested_by
                    db_manager.session.commit()
                    
                    # Convert database song to dict format
                    result = {
                        'id': existing_song.url.split('=')[-1] if '=' in existing_song.url else 'unknown',
                        'title': existing_song.title,
                        'url': existing_song.url,
                        'webpage_url': existing_song.url,
                        'duration': existing_song.duration,
                        'thumbnail': existing_song.thumbnail,
                        'uploader': existing_song.uploader,
                        'play_count': existing_song.play_count,
                        'is_downloaded': existing_song.is_downloaded,
                        'local_path': existing_song.local_path,
                        'file_size': existing_song.file_size,
                        'downloaded_file': existing_song.local_path if existing_song.is_downloaded else None,
                        'stream_url': existing_song.local_path if existing_song.is_downloaded else None,
                        # Legacy fields for compatibility
                        'description': '',
                        'view_count': 0,
                        'formats': []
                    }
                    
                    logger.info(f"Using cached song: {existing_song.title} (played {existing_song.play_count} times)")
                    return result
            
            # Step 2: Not in database, get info from YouTube using existing method
            logger.info(f"Song not in cache, extracting from YouTube: {url_or_query}")
            result = await self.get_info(url_or_query, download=settings.download_enabled)
            
            # Step 3: Store in database for future use
            try:
                song = db_manager.find_or_create_song(
                    url=result['url'],
                    title=result['title'],
                    duration=result.get('duration'),
                    thumbnail=result.get('thumbnail'),
                    uploader=result.get('uploader'),
                    requested_by=requested_by
                )
                
                # If file was downloaded, update database
                if result.get('downloaded_file') and os.path.exists(result['downloaded_file']):
                    file_size = os.path.getsize(result['downloaded_file'])
                    db_manager.update_song_download_status(song.id, result['downloaded_file'], file_size)
                    result['is_downloaded'] = True
                    result['local_path'] = result['downloaded_file']
                    result['file_size'] = file_size
                    logger.info(f"Stored and downloaded: {song.title}")
                else:
                    result['is_downloaded'] = False
                    result['local_path'] = None
                    logger.info(f"Stored in database: {song.title}")
                
                result['play_count'] = song.play_count
                result['database_id'] = song.id
                
            except Exception as db_error:
                logger.error(f"Database storage error: {db_error}")
                # Continue without database - don't break playback
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced info extraction error: {e}")
            # Fallback to original method
            return await self.get_info(url_or_query, download=settings.download_enabled)
    

# Global YouTube manager instance
youtube_manager = YouTubeManager()