### src/tests/test_utils.py
"""Tests for utility functions."""

import pytest
import time
from unittest.mock import Mock, patch

from src.utils.helpers import (
    format_duration, format_timestamp, time_ago, truncate_string, 
    safe_int, safe_float, chunks, ProgressBar, Timer
)
from src.utils.validators import (
    validate_youtube_url, validate_playlist_name, validate_search_query,
    sanitize_filename, validate_volume, validate_duration
)
from src.utils.checks import is_dj_or_admin

class TestHelpers:
    """Test helper functions."""
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(90) == "01:30"
        assert format_duration(3661) == "01:01:01"
        assert format_duration(30) == "00:30"
        assert format_duration(None) == "N/A"
        assert format_duration("invalid") == "N/A"
        assert format_duration(-10) == "N/A"
    
    def test_format_duration_with_hours(self):
        """Test duration formatting with hours."""
        assert format_duration(90, include_hours=True) == "00:01:30"
        assert format_duration(30, include_hours=True) == "00:00:30"
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = format_timestamp(timestamp)
        assert "2022-01-01" in result or "2021-12-31" in result  # Account for timezone
    
    def test_time_ago(self):
        """Test time ago formatting."""
        now = time.time()
        
        assert "seconds ago" in time_ago(now - 30)
        assert "minutes ago" in time_ago(now - 120)
        assert "hours ago" in time_ago(now - 3600)
        assert "days ago" in time_ago(now - 86400)
    
    def test_truncate_string(self):
        """Test string truncation."""
        assert truncate_string("hello world", 10) == "hello w..."
        assert truncate_string("hello", 10) == "hello"
        assert truncate_string("hello world", 5, "!!") == "hel!!"
    
    def test_safe_int(self):
        """Test safe integer conversion."""
        assert safe_int("123") == 123
        assert safe_int("invalid") == 0
        assert safe_int("invalid", 42) == 42
        assert safe_int(123.45) == 123
        assert safe_int(None) == 0
    
    def test_safe_float(self):
        """Test safe float conversion."""
        assert safe_float("123.45") == 123.45
        assert safe_float("invalid") == 0.0
        assert safe_float("invalid", 42.0) == 42.0
        assert safe_float(123) == 123.0
        assert safe_float(None) == 0.0
    
    def test_chunks(self):
        """Test list chunking."""
        data = list(range(10))
        chunked = list(chunks(data, 3))
        
        assert len(chunked) == 4
        assert chunked[0] == [0, 1, 2]
        assert chunked[1] == [3, 4, 5]
        assert chunked[2] == [6, 7, 8]
        assert chunked[3] == [9]
    
    def test_progress_bar(self):
        """Test progress bar creation."""
        bar = ProgressBar.create(50, 100, length=10)
        assert "█" in bar
        assert "─" in bar
        assert bar.count("█") == 5  # 50% of 10
        
        # Test edge cases
        assert ProgressBar.create(0, 100) == "`────────────────────`"
        assert ProgressBar.create(100, 100) == "`████████████████████`"
        assert ProgressBar.create(50, 0) == "`────────────────────`"  # Avoid division by zero
    
    def test_timer(self):
        """Test timer functionality."""
        timer = Timer()
        
        # Test context manager
        with timer:
            time.sleep(0.1)
        
        elapsed = timer.elapsed()
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should be close to 0.1
        
        # Test manual start/stop
        timer2 = Timer()
        timer2.start()
        time.sleep(0.05)
        timer2.stop()
        
        elapsed2 = timer2.elapsed()
        assert elapsed2 >= 0.05
        assert elapsed2 < 0.1

class TestValidators:
    """Test validation functions."""
    
    def test_validate_youtube_url(self):
        """Test YouTube URL validation."""
        # Valid URLs
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
        assert validate_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ") is True
        
        # Invalid URLs
        assert validate_youtube_url("https://www.google.com") is False
        assert validate_youtube_url("not a url") is False
        assert validate_youtube_url("") is False
    
    def test_validate_playlist_name(self):
        """Test playlist name validation."""
        # Valid names
        valid, error = validate_playlist_name("My Playlist")
        assert valid is True
        assert error is None
        
        valid, error = validate_playlist_name("Rock Music 2024")
        assert valid is True
        
        # Invalid names
        valid, error = validate_playlist_name("")
        assert valid is False
        assert "cannot be empty" in error
        
        valid, error = validate_playlist_name("a" * 101)
        assert valid is False
        assert "100 characters" in error
        
        valid, error = validate_playlist_name("ab")
        assert valid is False
        assert "3 characters" in error
        
        valid, error = validate_playlist_name("test/playlist")
        assert valid is False
        assert "cannot contain" in error
    
    def test_validate_search_query(self):
        """Test search query validation."""
        # Valid queries
        valid, error = validate_search_query("test song")
        assert valid is True
        assert error is None
        
        # Invalid queries
        valid, error = validate_search_query("")
        assert valid is False
        assert "cannot be empty" in error
        
        valid, error = validate_search_query("a" * 501)
        assert valid is False
        assert "500 characters" in error
        
        valid, error = validate_search_query("   ")
        assert valid is False
        assert "cannot be empty" in error
        
        valid, error = validate_search_query("<><><>")
        assert valid is False
        assert "invalid characters" in error
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file/with\\bad:chars") == "file_with_bad_chars"
        assert sanitize_filename("a" * 300) == "a" * 252 + "..."
        assert sanitize_filename("  spaced  ") == "spaced"
    
    def test_validate_volume(self):
        """Test volume validation."""
        # Valid volumes
        valid, error = validate_volume(0.5)
        assert valid is True
        assert error is None
        
        valid, error = validate_volume(0.0)
        assert valid is True
        
        valid, error = validate_volume(1.0)
        assert valid is True
        
        # Invalid volumes
        valid, error = validate_volume(-0.1)
        assert valid is False
        assert "between 0.0 and 1.0" in error
        
        valid, error = validate_volume(1.1)
        assert valid is False
        assert "between 0.0 and 1.0" in error
        
        valid, error = validate_volume("invalid")
        assert valid is False
        assert "must be a number" in error
    
    def test_validate_duration(self):
        """Test duration validation."""
        # Valid durations
        valid, error = validate_duration(180)
        assert valid is True
        assert error is None
        
        valid, error = validate_duration(0)
        assert valid is True
        
        # Invalid durations
        valid, error = validate_duration(-1)
        assert valid is False
        assert "cannot be negative" in error
        
        valid, error = validate_duration(3600 * 4)  # 4 hours
        assert valid is False
        assert "cannot exceed" in error
        
        valid, error = validate_duration("invalid")
        assert valid is False
        assert "must be an integer" in error

class TestChecks:
    """Test permission check functions."""
    
    @pytest.mark.asyncio
    async def test_is_dj_or_admin_admin_user(self):
        """Test DJ check with admin user."""
        # Create mock objects
        mock_ctx = Mock()
        mock_user = Mock()
        mock_user.guild_permissions = Mock()
        mock_user.guild_permissions.administrator = True
        mock_ctx.author = mock_user
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = 123456
        
        # Get the check function
        check_func = is_dj_or_admin()
        predicate = check_func.predicate
        
        # Test with admin user
        with patch('src.core.music_manager.music_manager.get_dj_role_id', return_value=None):
            result = await predicate(mock_ctx)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_dj_or_admin_dj_user(self):
        """Test DJ check with DJ role user."""
        # Create mock objects
        mock_ctx = Mock()
        mock_user = Mock()
        mock_user.guild_permissions = Mock()
        mock_user.guild_permissions.administrator = False
        mock_user.roles = []
        mock_ctx.author = mock_user
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = 123456
        
        # Create mock DJ role
        mock_dj_role = Mock()
        mock_dj_role.id = 555555
        mock_user.roles = [mock_dj_role]
        mock_ctx.guild.get_role.return_value = mock_dj_role
        
        # Get the check function
        check_func = is_dj_or_admin()
        predicate = check_func.predicate
        
        # Test with DJ role user
        with patch('src.core.music_manager.music_manager.get_dj_role_id', return_value=555555):
            result = await predicate(mock_ctx)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_dj_or_admin_no_role(self):
        """Test DJ check with no DJ role set."""
        # Create mock objects
        mock_ctx = Mock()
        mock_user = Mock()
        mock_user.guild_permissions = Mock()
        mock_user.guild_permissions.administrator = False
        mock_ctx.author = mock_user
        mock_ctx.guild = Mock()
        mock_ctx.guild.id = 123456
        
        # Get the check function
        check_func = is_dj_or_admin()
        predicate = check_func.predicate
        
        # Test with no DJ role set (should allow everyone)
        with patch('src.core.music_manager.music_manager.get_dj_role_id', return_value=None):
            result = await predicate(mock_ctx)
            assert result is True

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_decorator(self):
        """Test rate limiting decorator."""
        from src.utils.helpers import rate_limit
        
        call_count = 0
        
        @rate_limit(calls=2, period=1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return call_count
        
        # First two calls should go through immediately
        start_time = time.time()
        result1 = await test_function()
        result2 = await test_function()
        first_two_time = time.time() - start_time
        
        assert result1 == 1
        assert result2 == 2
        assert first_two_time < 0.1  # Should be very fast
        
        # Third call should be rate limited
        start_time = time.time()
        result3 = await test_function()
        third_call_time = time.time() - start_time
        
        assert result3 == 3
        assert third_call_time >= 0.9  # Should wait almost 1 second

class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_success(self):
        """Test retry decorator with successful function."""
        from src.utils.helpers import retry
        
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_eventual_success(self):
        """Test retry decorator with eventual success."""
        from src.utils.helpers import retry
        
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Not ready yet")
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts(self):
        """Test retry decorator reaching max attempts."""
        from src.utils.helpers import retry
        
        call_count = 0
        
        @retry(max_attempts=2, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        with pytest.raises(Exception) as exc_info:
            await test_function()
        
        assert "Always fails" in str(exc_info.value)
        assert call_count == 2