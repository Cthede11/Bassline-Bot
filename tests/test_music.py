### src/tests/test_music.py
"""Tests for music functionality."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.core.music_manager import MusicManager, Track, LoopState
from src.utils.youtube import YouTubeManager, YouTubeError

@pytest.fixture
def music_manager():
    """Create a fresh music manager for testing."""
    return MusicManager()

@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = Mock()
    user.id = 123456789
    user.display_name = "TestUser"
    user.mention = "<@123456789>"
    return user

@pytest.fixture
def sample_track(mock_user):
    """Create a sample track for testing."""
    return Track(
        query="test song",
        title="Test Song",
        url="https://youtube.com/watch?v=test",
        duration=180,
        thumbnail="https://img.youtube.com/vi/test/default.jpg",
        uploader="Test Uploader",
        requested_by=mock_user
    )

class TestMusicManager:
    """Test the MusicManager class."""
    
    def test_init(self, music_manager):
        """Test music manager initialization."""
        assert len(music_manager.queues) == 0
        assert len(music_manager.voice_clients) == 0
        assert len(music_manager.now_playing) == 0
        assert len(music_manager.loop_states) == 0
    
    @pytest.mark.asyncio
    async def test_add_to_queue(self, music_manager, sample_track):
        """Test adding tracks to queue."""
        guild_id = 123456
        
        # Add track to queue
        success = await music_manager.add_to_queue(guild_id, sample_track)
        assert success is True
        
        # Check queue
        queue = music_manager.get_queue(guild_id)
        assert len(queue) == 1
        assert queue[0].title == "Test Song"
    
    @pytest.mark.asyncio
    async def test_queue_limit(self, music_manager, sample_track, mock_user):
        """Test queue size limits."""
        guild_id = 123456
        
        # Mock guild settings to return small queue limit
        with patch('src.core.database_manager.db_manager.get_guild_settings') as mock_settings:
            mock_guild = Mock()
            mock_guild.max_queue_size = 2
            mock_settings.return_value = mock_guild
            
            # Add tracks up to limit
            for i in range(2):
                track = Track(
                    query=f"test song {i}",
                    title=f"Test Song {i}",
                    url=f"https://youtube.com/watch?v=test{i}",
                    duration=180,
                    thumbnail="https://img.youtube.com/vi/test/default.jpg",
                    uploader="Test Uploader",
                    requested_by=mock_user
                )
                success = await music_manager.add_to_queue(guild_id, track)
                assert success is True
            
            # Try to add one more (should fail)
            success = await music_manager.add_to_queue(guild_id, sample_track)
            assert success is False
    
    def test_get_next_track(self, music_manager, sample_track):
        """Test getting next track from queue."""
        guild_id = 123456
        
        # Add track and get it
        asyncio.run(music_manager.add_to_queue(guild_id, sample_track))
        
        next_track = music_manager.get_next_track(guild_id)
        assert next_track.title == "Test Song"
        
        # Queue should now be empty
        queue = music_manager.get_queue(guild_id)
        assert len(queue) == 0
    
    def test_shuffle_queue(self, music_manager, mock_user):
        """Test queue shuffling."""
        guild_id = 123456
        
        # Add multiple tracks
        tracks = []
        for i in range(5):
            track = Track(
                query=f"test song {i}",
                title=f"Test Song {i}",
                url=f"https://youtube.com/watch?v=test{i}",
                duration=180,
                thumbnail="https://img.youtube.com/vi/test/default.jpg",
                uploader="Test Uploader",
                requested_by=mock_user
            )
            tracks.append(track)
            asyncio.run(music_manager.add_to_queue(guild_id, track))
        
        # Get original order
        original_queue = music_manager.get_queue(guild_id)
        original_titles = [track.title for track in original_queue]
        
        # Shuffle
        music_manager.shuffle_queue(guild_id)
        
        # Get new order
        shuffled_queue = music_manager.get_queue(guild_id)
        shuffled_titles = [track.title for track in shuffled_queue]
        
        # Should have same tracks but potentially different order
        assert len(shuffled_titles) == len(original_titles)
        assert set(shuffled_titles) == set(original_titles)
    
    def test_loop_states(self, music_manager):
        """Test loop state management."""
        guild_id = 123456
        
        # Default should be OFF
        assert music_manager.get_loop_state(guild_id) == LoopState.OFF
        
        # Set to SINGLE
        music_manager.set_loop_state(guild_id, LoopState.SINGLE)
        assert music_manager.get_loop_state(guild_id) == LoopState.SINGLE
        
        # Set to QUEUE
        music_manager.set_loop_state(guild_id, LoopState.QUEUE)
        assert music_manager.get_loop_state(guild_id) == LoopState.QUEUE
    
    def test_bass_boost_toggle(self, music_manager):
        """Test bass boost functionality."""
        user_id = 123456
        
        # Default should be False
        assert music_manager.get_bass_boost(user_id) is False
        
        # Toggle on
        result = music_manager.toggle_bass_boost(user_id)
        assert result is True
        assert music_manager.get_bass_boost(user_id) is True
        
        # Toggle off
        result = music_manager.toggle_bass_boost(user_id)
        assert result is False
        assert music_manager.get_bass_boost(user_id) is False
    
    def test_clear_guild_state(self, music_manager, sample_track):
        """Test clearing guild state."""
        guild_id = 123456
        
        # Add some state
        asyncio.run(music_manager.add_to_queue(guild_id, sample_track))
        music_manager.set_loop_state(guild_id, LoopState.SINGLE)
        music_manager.update_last_activity(guild_id)
        
        # Clear state
        music_manager.clear_guild_state(guild_id)
        
        # Verify everything is cleared
        assert len(music_manager.get_queue(guild_id)) == 0
        assert music_manager.get_loop_state(guild_id) == LoopState.OFF
        assert guild_id not in music_manager.last_activity

class TestYouTubeManager:
    """Test the YouTube manager."""
    
    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful YouTube search."""
        youtube_manager = YouTubeManager()
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            # Mock successful search result
            mock_extract_info = AsyncMock(return_value={
                'entries': [
                    {
                        'id': 'test123',
                        'title': 'Test Song',
                        'webpage_url': 'https://youtube.com/watch?v=test123',
                        'duration': 180,
                        'thumbnail': 'https://img.youtube.com/vi/test123/default.jpg',
                        'uploader': 'Test Uploader',
                        'view_count': 1000000,
                        'upload_date': '20240101'
                    }
                ]
            })
            
            mock_instance = Mock()
            mock_instance.extract_info = mock_extract_info
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            with patch('asyncio.wait_for', return_value=mock_extract_info.return_value):
                results = await youtube_manager.search("test song", max_results=1)
            
            assert len(results) == 1
            assert results[0]['title'] == 'Test Song'
            assert results[0]['id'] == 'test123'
    
    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test YouTube search with no results."""
        youtube_manager = YouTubeManager()
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info = AsyncMock(return_value={'entries': []})
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            with patch('asyncio.wait_for', return_value={'entries': []}):
                results = await youtube_manager.search("nonexistent song")
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_timeout(self):
        """Test YouTube search timeout."""
        youtube_manager = YouTubeManager()
        
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            with pytest.raises(YouTubeError) as exc_info:
                await youtube_manager.search("test song")
            
            assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_info_success(self):
        """Test successful video info retrieval."""
        youtube_manager = YouTubeManager()
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_info = {
                'id': 'test123',
                'title': 'Test Song',
                'webpage_url': 'https://youtube.com/watch?v=test123',
                'url': 'https://direct-stream-url.com/audio',
                'duration': 180,
                'thumbnail': 'https://img.youtube.com/vi/test123/default.jpg',
                'uploader': 'Test Uploader',
                'formats': [
                    {
                        'url': 'https://direct-stream-url.com/audio',
                        'acodec': 'opus',
                        'vcodec': 'none',
                        'ext': 'webm'
                    }
                ]
            }
            
            mock_instance = Mock()
            mock_instance.extract_info = AsyncMock(return_value=mock_info)
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            with patch('asyncio.wait_for', return_value=mock_info):
                result = await youtube_manager.get_info("https://youtube.com/watch?v=test123")
            
            assert result['title'] == 'Test Song'
            assert result['id'] == 'test123'
            assert result['stream_url'] is not None
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        youtube_manager = YouTubeManager()
        
        # Test cache key generation
        key1 = youtube_manager._get_cache_key("test query")
        key2 = youtube_manager._get_cache_key("test query")
        key3 = youtube_manager._get_cache_key("different query")
        
        assert key1 == key2
        assert key1 != key3
        
        # Test cache validity
        current_time = time.time()
        valid_entry = {'timestamp': current_time, 'data': 'test'}
        old_entry = {'timestamp': current_time - 7200, 'data': 'test'}  # 2 hours old
        
        assert youtube_manager._is_cache_valid(valid_entry) is True
        assert youtube_manager._is_cache_valid(old_entry) is False

class TestTrack:
    """Test the Track dataclass."""
    
    def test_track_creation(self, mock_user):
        """Test track creation."""
        track = Track(
            query="test song",
            title="Test Song",
            url="https://youtube.com/watch?v=test",
            duration=180,
            thumbnail="https://img.youtube.com/vi/test/default.jpg",
            uploader="Test Uploader",
            requested_by=mock_user
        )
        
        assert track.title == "Test Song"
        assert track.duration == 180
        assert track.requested_by == mock_user
        assert track.added_at <= time.time()
        assert track.added_at > time.time() - 1  # Added within last second