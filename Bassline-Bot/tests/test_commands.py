"""Tests for Discord commands."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import discord
from discord.ext import commands

from src.commands.music_commands import MusicCommands
from src.commands.admin_commands import AdminCommands
from src.commands.utility_commands import UtilityCommands

@pytest.fixture
def mock_bot():
    """Create a mock Discord bot."""
    bot = Mock(spec=commands.Bot)
    bot.user = Mock()
    bot.user.id = 987654321
    bot.user.avatar = Mock()
    bot.user.avatar.url = "https://cdn.discordapp.com/avatars/987654321/avatar.png"
    bot.guilds = []
    bot.latency = 0.05
    bot.is_ready.return_value = True
    bot.is_closed.return_value = False
    return bot

@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = Mock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    guild.me = Mock()
    guild.me.guild_permissions = Mock()
    guild.me.guild_permissions.administrator = True
    guild.system_channel = None
    guild.voice_client = None
    return guild

@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = Mock(spec=discord.Member)
    user.id = 111111111
    user.display_name = "TestUser"
    user.mention = "<@111111111>"
    user.guild_permissions = Mock()
    user.guild_permissions.administrator = False
    user.voice = Mock()
    user.voice.channel = Mock()
    user.voice.channel.name = "General"
    return user

@pytest.fixture
def mock_interaction(mock_guild, mock_user):
    """Create a mock Discord interaction."""
    interaction = Mock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = mock_user
    interaction.channel = Mock()
    interaction.response = Mock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    return interaction

class TestMusicCommands:
    """Test music commands."""
    
    @pytest.mark.asyncio
    async def test_play_command_success(self, mock_bot, mock_interaction):
        """Test successful play command."""
        music_cog = MusicCommands(mock_bot)
        
        with patch('src.utils.validators.validate_search_query', return_value=(True, None)):
            with patch('src.utils.discord_voice.join_voice_channel') as mock_join:
                with patch('src.utils.youtube.youtube_manager.get_info') as mock_youtube:
                    with patch('src.core.music_manager.music_manager.is_playing', return_value=False):
                        with patch.object(music_cog, '_play_track') as mock_play_track:
                            
                            # Setup mocks
                            mock_join.return_value = Mock()
                            mock_youtube.return_value = {
                                'title': 'Test Song',
                                'url': 'https://youtube.com/watch?v=test',
                                'duration': 180,
                                'thumbnail': 'https://img.youtube.com/test.jpg',
                                'uploader': 'Test Uploader'
                            }
                            mock_play_track.return_value = None
                            
                            # Execute command
                            await music_cog.play(mock_interaction, "test song")
                            
                            # Verify
                            mock_interaction.response.defer.assert_called_once()
                            mock_play_track.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_command_user_not_in_voice(self, mock_bot, mock_interaction):
        """Test play command when user not in voice channel."""
        mock_interaction.user.voice = None
        music_cog = MusicCommands(mock_bot)
        
        with patch('src.utils.validators.validate_search_query', return_value=(True, None)):
            await music_cog.play(mock_interaction, "test song")
            
            mock_interaction.followup.send.assert_called_once()
            args, kwargs = mock_interaction.followup.send.call_args
            assert "must be in a voice channel" in args[0]
    
    @pytest.mark.asyncio
    async def test_skip_command(self, mock_bot, mock_interaction):
        """Test skip command."""
        music_cog = MusicCommands(mock_bot)
        
        with patch('src.core.music_manager.music_manager.voice_clients') as mock_clients:
            with patch('src.core.music_manager.music_manager.get_now_playing') as mock_now_playing:
                
                # Setup mocks
                mock_vc = Mock()
                mock_vc.is_playing.return_value = True
                mock_clients.get.return_value = mock_vc
                
                mock_track = Mock()
                mock_track.title = "Test Song"
                mock_now_playing_obj = Mock()
                mock_now_playing_obj.track = mock_track
                mock_now_playing.return_value = mock_now_playing_obj
                
                # Execute command
                await music_cog.skip(mock_interaction)
                
                # Verify
                mock_vc.stop.assert_called_once()
                mock_interaction.response.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_queue_command_empty(self, mock_bot, mock_interaction):
        """Test queue command with empty queue."""
        music_cog = MusicCommands(mock_bot)
        
        with patch('src.core.music_manager.music_manager.get_queue', return_value=[]):
            with patch('src.core.music_manager.music_manager.get_now_playing', return_value=None):
                with patch('src.core.music_manager.music_manager.get_loop_state') as mock_loop:
                    
                    mock_loop.return_value = Mock()
                    mock_loop.return_value.name = 'OFF'
                    
                    await music_cog.queue(mock_interaction)
                    
                    mock_interaction.response.send_message.assert_called_once()
                    # Check that embed was sent
                    args, kwargs = mock_interaction.response.send_message.call_args
                    assert 'embed' in kwargs

class TestAdminCommands:
    """Test admin commands."""
    
    @pytest.mark.asyncio
    async def test_set_dj_role(self, mock_bot, mock_interaction):
        """Test setting DJ role."""
        admin_cog = AdminCommands(mock_bot)
        
        # Create mock role
        mock_role = Mock(spec=discord.Role)
        mock_role.id = 555555555
        mock_role.name = "DJ"
        mock_role.mention = "<@&555555555>"
        
        with patch('src.core.music_manager.music_manager.set_dj_role') as mock_set_dj:
            await admin_cog.set_dj_role(mock_interaction, mock_role)
            
            mock_set_dj.assert_called_once_with(mock_interaction.guild.id, mock_role.id)
            mock_interaction.response.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stats_command(self, mock_bot, mock_interaction):
        """Test stats command."""
        admin_cog = AdminCommands(mock_bot)
        
        with patch('src.core.music_manager.music_manager.get_guild_stats') as mock_guild_stats:
            with patch('src.core.database_manager.db_manager') as mock_db:
                with patch('src.core.music_manager.music_manager.get_metrics') as mock_metrics:
                    
                    # Setup mocks
                    mock_guild_stats.return_value = {
                        'queue_length': 5,
                        'is_playing': True,
                        'loop_state': 'OFF',
                        'last_activity': 1234567890
                    }
                    
                    mock_db.get_usage_stats.return_value = {
                        'total_commands': 100,
                        'successful_commands': 95,
                        'unique_users': 10
                    }
                    
                    mock_db.get_guild_settings.return_value = Mock()
                    mock_metrics.return_value = {'songs_played': 50}
                    
                    await admin_cog.stats(mock_interaction)
                    
                    mock_interaction.response.defer.assert_called_once()
                    mock_interaction.followup.send.assert_called_once()

class TestUtilityCommands:
    """Test utility commands."""
    
    @pytest.mark.asyncio
    async def test_ping_command(self, mock_bot, mock_interaction):
        """Test ping command."""
        utility_cog = UtilityCommands(mock_bot)
        
        await utility_cog.ping(mock_interaction)
        
        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called_once()
        
        # Check that embed was sent with latency info
        args, kwargs = mock_interaction.followup.send.call_args
        assert 'embed' in kwargs
    
    @pytest.mark.asyncio
    async def test_info_command(self, mock_bot, mock_interaction):
        """Test info command."""
        utility_cog = UtilityCommands(mock_bot)
        
        with patch('psutil.cpu_percent', return_value=45.0):
            with patch('psutil.virtual_memory') as mock_memory:
                with patch('psutil.disk_usage') as mock_disk:
                    
                    # Setup mocks
                    mock_memory.return_value = Mock()
                    mock_memory.return_value.percent = 60.0
                    mock_disk.return_value = Mock()
                    mock_disk.return_value.percent = 25.0
                    
                    await utility_cog.info(mock_interaction)
                    
                    mock_interaction.response.send_message.assert_called_once()
                    args, kwargs = mock_interaction.response.send_message.call_args
                    assert 'embed' in kwargs
