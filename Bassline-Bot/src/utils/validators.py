import re
import validators
from typing import Optional, Tuple
from urllib.parse import urlparse

def validate_youtube_url(url: str) -> bool:
    """Validate if URL is a valid YouTube URL."""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def validate_playlist_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate playlist name."""
    if not name:
        return False, "Playlist name cannot be empty"
    
    if len(name) > 100:
        return False, "Playlist name must be 100 characters or less"
    
    if len(name) < 3:
        return False, "Playlist name must be at least 3 characters"
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    if any(char in name for char in invalid_chars):
        return False, f"Playlist name cannot contain: {', '.join(invalid_chars)}"
    
    return True, None

def validate_search_query(query: str) -> Tuple[bool, Optional[str]]:
    """Validate search query."""
    if not query or not query.strip():
        return False, "Search query cannot be empty"
    
    if len(query) > 500:
        return False, "Search query must be 500 characters or less"
    
    # Remove common problematic patterns
    cleaned_query = re.sub(r'[<>@#]', '', query.strip())
    if not cleaned_query:
        return False, "Search query contains only invalid characters"
    
    return True, None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:252] + "..."
    
    return filename.strip()

def validate_volume(volume: float) -> Tuple[bool, Optional[str]]:
    """Validate volume level."""
    if not isinstance(volume, (int, float)):
        return False, "Volume must be a number"
    
    if not 0.0 <= volume <= 1.0:
        return False, "Volume must be between 0.0 and 1.0"
    
    return True, None

def validate_duration(duration: int) -> Tuple[bool, Optional[str]]:
    """Validate song duration."""
    if not isinstance(duration, int):
        return False, "Duration must be an integer"
    
    if duration < 0:
        return False, "Duration cannot be negative"
    
    max_duration = 3600 * 3  # 3 hours
    if duration > max_duration:
        return False, f"Duration cannot exceed {max_duration // 3600} hours"
    
    return True, None