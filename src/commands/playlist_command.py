from discord.ext import commands
from discord import app_commands, Interaction
from discord import Object
from src.utils.discord_voice import join_voice_channel, play_song
from src.utils.music import music_manager
import asyncio
import discord
import re

class PlaylistCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist_category_name = "🎵 Custom Playlists"
        print("✅ PlaylistCommand loaded")

    @app_commands.command(name="setupplaylists", description="Create a category for storing custom playlists")
    async def setup_playlists(self, interaction: Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            category = await guild.create_category(self.playlist_category_name)

        await interaction.response.send_message(f"✅ Playlist category ready: {category.name}")

    @app_commands.command(name="createplaylist", description="Create a new playlist channel")
    async def create_playlist(self, interaction: Interaction, playlist_name: str):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            await interaction.response.send_message("⚠️ Playlist category not found. Run `/setupplaylists` first.")
            return

        channel_name = re.sub(r"[^a-z0-9-]", "", playlist_name.lower().replace(" ", "-"))
        existing = discord.utils.get(category.channels, name=channel_name)
        if existing:
            await interaction.response.send_message("⚠️ A playlist with that name already exists.")
            return

        new_channel = await guild.create_text_channel(channel_name, category=category)
        intro = (
            f"🎶 **Playlist: {playlist_name}**\n"
            f"Type song titles one per message below 👇\n"
            f"To play this playlist, use:\n"
            f"`/playlist {playlist_name}`"
        )
        await new_channel.send(intro)
        await interaction.response.send_message(f"✅ Playlist `{playlist_name}` created!")

    @app_commands.command(name="playlist", description="Play songs from a playlist channel")
    async def play_playlist(self, interaction: Interaction, playlist_name: str):
        await interaction.response.defer()
        print(f"[Debug] play_playlist called with: {playlist_name}")

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            await interaction.response.send_message("⚠️ Playlist category not found.")
            return

        mention_match = re.match(r"<#(\\d+)>", playlist_name.strip())
        if mention_match:
            channel_id = int(mention_match.group(1))
            playlist_channel = guild.get_channel(channel_id)
            print(f"[DEBUG] Resolved channel ID {channel_id} to: {playlist_channel}")
        else:
            normalized_target = re.sub(r"[^a-z0-9-]", "", playlist_name.lower().replace(" ", "-"))
            playlist_channel = None
            for ch in category.text_channels:
                print(f"[DEBUG] Raw channel name: '{ch.name}'")
                normalized_name = re.sub(r"[^a-z0-9-]", "", ch.name)
                print(f"[DEBUG] Normalized channel name: '{normalized_name}' vs target: '{normalized_target}'")
                if normalized_name == normalized_target:
                    playlist_channel = ch
                    break

        if not playlist_channel:
            print("[ERROR] Playlist channel not found.")
            await interaction.response.send_message("⚠️ Playlist not found.")
            return

        print(f"[DEBUG] Fetching messages from channel: {playlist_channel.name} (ID: {playlist_channel.id})")
        messages = [msg async for msg in playlist_channel.history(limit=200)]
        songs = [msg.content.strip() for msg in messages if not msg.author.bot and msg.content.strip()]

        print(f"[Playlist] Read {len(messages)} messages, found {len(songs)} valid songs.")
        print("Songs found:", songs)

        if not songs:
            await interaction.response.send_message("⚠️ No songs found in the playlist.")
            return

        vc = await join_voice_channel(interaction)
        if not vc:
            return
        music_manager.voice_clients[guild.id] = vc

        for track in songs:
            await music_manager.add_to_queue(guild.id, track, interaction.user)

        # Trigger playback manually if nothing is playing
        if not vc.is_playing():
            await self._play_next(interaction)

        await interaction.response.send_message(f"▶️ Now playing playlist: {playlist_channel.name} with {len(songs)} track(s).")

    async def _play_next(self, interaction: discord.Interaction):
        from src.utils.music import music_manager
        from src.utils.discord_voice import play_song

        guild_id = interaction.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        if not vc:
            return

        track, requested_by = music_manager.get_next(guild_id)

        if not track:
            await interaction.followup.send("✅ Queue ended.")
            return

        try:
            source = await play_song(
                vc,
                track,
                return_source=True,
                bass_boost=music_manager.user_bass_boost.get(requested_by.id, False)
            )
            vc.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._play_next(interaction),
                    self.bot.loop
                )
            )
            await interaction.followup.send(
                f"▶️ Now playing: {track} (requested by {requested_by.mention})"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error playing next track: {e}")

