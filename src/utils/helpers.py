import asyncio
import functools
import time
from typing import Any, Callable, Optional
from datetime import datetime, timedelta

def format_duration(seconds: Optional[int], include_hours: bool = False) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS format."""
    if seconds is None:
        return "N/A"
    
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "N/A"
    
    if seconds < 0:
        return "N/A"
    
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    
    if hours > 0 or include_hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"

def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to readable string."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def time_ago(timestamp: float) -> str:
    """Get human-readable time difference."""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return f"{int(diff)} seconds ago"
    elif diff < 3600:
        return f"{int(diff // 60)} minutes ago"
    elif diff < 86400:
        return f"{int(diff // 3600)} hours ago"
    else:
        return f"{int(diff // 86400)} days ago"

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def chunks(lst: list, chunk_size: int):
    """Yield successive chunks from list."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def rate_limit(calls: int, period: int):
    """Rate limiting decorator."""
    def decorator(func: Callable):
        calls_made = []
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls outside the period
            calls_made[:] = [call_time for call_time in calls_made if now - call_time < period]
            
            if len(calls_made) >= calls:
                sleep_time = period - (now - calls_made[0])
                await asyncio.sleep(sleep_time)
                calls_made.pop(0)
            
            calls_made.append(now)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Remove or replace invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove extra whitespace and control characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:252] + "..."
    
    return filename.strip()

class ProgressBar:
    """Generate ASCII progress bar."""
    
    @staticmethod
    def create(current: int, total: int, length: int = 20, fill: str = "█", empty: str = "─") -> str:
        """Create progress bar string."""
        if total <= 0:
            return empty * length
        
        progress = min(1.0, current / total)
        filled_length = int(length * progress)
        
        bar = fill * filled_length + empty * (length - filled_length)
        return f"`{bar}`"

class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        return self
    
    def stop(self):
        """Stop the timer."""
        self.end_time = time.time()
        return self
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time or time.time()
        return end - self.start_time
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, *args):
        self.stop()