import discord
from discord.ext import commands
import os
import re
import asyncio

class PlaylistCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist_category_name = "🎵 Custom Playlists"
        print("✅ PlaylistCommand loaded")

    @commands.command(name="setupplaylists")
    @commands.has_permissions(manage_channels=True)
    async def setup_playlists(self, ctx):
        guild = ctx.guild

        existing_category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not existing_category:
            category = await guild.create_category(self.playlist_category_name)
        else:
            category = existing_category

        await ctx.send(f"✅ Playlist category ready: {category.name}")

    @commands.command(name="createplaylist")
    async def create_playlist(self, ctx, *, playlist_name):
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)

        if not category:
            await ctx.send("⚠️ Playlist category not found. Run `!setupplaylists` first.")
            return

        channel_name = re.sub(r"[^a-z0-9-]", "", playlist_name.lower().replace(" ", "-"))
        existing = discord.utils.get(category.channels, name=channel_name)
        if existing:
            await ctx.send("⚠️ A playlist with that name already exists.")
            return

        new_channel = await guild.create_text_channel(channel_name, category=category)

        intro = (
            f"🎶 **Playlist: {playlist_name}**\n"
            f"Type song titles one per message below 👇\n"
            f"To play this playlist, use:\n"
            f"`!playplaylist {playlist_name}`"
        )
        await new_channel.send(intro)
        await ctx.send(f"✅ Playlist `{playlist_name}` created!")

    @commands.command(name="playplaylist")
    async def play_playlist(self, ctx, *, playlist_name):
        print(f"[Debug] play_playlist called with: {playlist_name}")
        from src.utils.music import music_manager
        from src.utils.discord_voice import join_voice_channel, play_song

        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=self.playlist_category_name)
        if not category:
            await ctx.send("⚠️ Playlist category not found.")
            return

        mention_match = re.match(r"<#(\d+)>", playlist_name.strip())
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
            await ctx.send("⚠️ Playlist not found.")
            return

        print(f"[DEBUG] Fetching messages from channel: {playlist_channel.name} (ID: {playlist_channel.id})")
        messages = [msg async for msg in playlist_channel.history(limit=200)]
        songs = [msg.content.strip() for msg in messages if not msg.author.bot and msg.content.strip()]

        print(f"[Playlist] Read {len(messages)} messages, found {len(songs)} valid songs.")
        print("Songs found:", songs)

        if not songs:
            await ctx.send("⚠️ No songs found in the playlist.")
            return

        # Play the first track
        vc = await join_voice_channel(ctx)
        if not vc:
            return
        music_manager.voice_clients[guild.id] = vc

        from src.utils.discord_voice import play_song

        first = songs[0]
        rest = songs[1:]

        try:
            source = await play_song(vc, first, return_source=True)
            music_manager.now_playing[guild.id] = first
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop))
            await ctx.send(f"▶️ Now playing: {first} (requested by {ctx.author.mention})")
        except Exception as e:
            await ctx.send(f"❌ Error playing: {e}")
            return

        for track in rest:
            await music_manager.add_to_queue(guild.id, track, ctx.author)
        if rest:
            await ctx.send(f"✅ Queued {len(rest)} more track(s).")

    async def _play_next(self, ctx):
        from src.utils.music import music_manager
        from src.utils.discord_voice import play_song

        guild_id = ctx.guild.id
        vc = music_manager.voice_clients.get(guild_id)
        if not vc:
            return

        track, requested_by = music_manager.get_next(guild_id)

        if not track:
            await ctx.send("✅ Queue ended.")
            return

        try:
            source = await play_song(vc, track, return_source=True)
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop))
            await ctx.send(f"▶️ Now playing: {track} (requested by {requested_by.mention})")
        except Exception as e:
            await ctx.send(f"❌ Error playing next track: {e}")
