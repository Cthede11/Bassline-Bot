import asyncio
import functools
import logging
import os
import time
from typing import Dict, List, Optional
import yt_dlp

from config.settings import settings
from src.utils.helpers import retry
from src.utils.validators import sanitize_filename

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
    async def get_info(self, url_or_query: str, download: bool = False) -> dict:
        """Get detailed information about a video."""
        cache_key = self._get_cache_key(f"info_{url_or_query}_{download}")
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.debug(f"Cache hit for info: {url_or_query}")
            return self.cache[cache_key]['data']
        
        await self._rate_limit()
        
        info_opts = self.base_opts.copy()
        
        if download and settings.download_enabled:
            info_opts.update({
                'outtmpl': os.path.join('downloads', '%(title)s.%(ext)s'),
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
                'downloaded_file': None
            }
            
            # Handle downloaded file
            if download:
                downloaded_file = entry.get('_filename') or entry.get('filepath')
                if downloaded_file and os.path.exists(downloaded_file):
                    result['downloaded_file'] = downloaded_file
                    result['stream_url'] = downloaded_file
            
            # Get best audio format for streaming
            if not download and result['formats']:
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
    
    def cleanup_old_downloads(self, max_age_hours: int = 24):
        """Clean up old downloaded files."""
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(downloads_dir):
            filepath = os.path.join(downloads_dir, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    try:
                        os.remove(filepath)
                        logger.debug(f"Removed old download: {filename}")
                    except OSError as e:
                        logger.error(f"Failed to remove {filename}: {e}")

# Global YouTube manager instance
youtube_manager = YouTubeManager()