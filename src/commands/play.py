from discord.ext import commands
from src.utils.spotify import get_spotify_playlist_tracks
from src.utils.discord_voice import join_voice_channel, play_song
from src.utils.music import music_manager
import asyncio

class PlayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="play")
    async def play(self, ctx, *, query):
        guild_id = ctx.guild.id
        music_manager.voice_clients[guild_id] = await join_voice_channel(ctx)
        vc = music_manager.voice_clients[guild_id]

        await ctx.send("🔍 Fetching tracks...")

        try:
            if "spotify.com/playlist" in query:
                tracks = get_spotify_playlist_tracks(query)
            else:
                tracks = [query]
        except Exception as e:
            await ctx.send(f"❌ Error fetching tracks: {e}")
            return

        if not tracks:
            await ctx.send("⚠️ No tracks found.")
            return

        # Play the first track immediately
        first_track = tracks[0]
        rest_of_tracks = tracks[1:]

        try:
            source = await play_song(vc, first_track, return_source=True)
            music_manager.now_playing[guild_id] = first_track
            print(f"🎵 Now playing: {first_track} (requested by {ctx.author})")
            await ctx.send(f"▶️ Now playing: {first_track} (requested by {ctx.author.mention})")
        except Exception as e:
            await ctx.send(f"❌ Error playing: {e}")
            return

        def after_playing(_):
            fut = asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        vc.play(source, after=after_playing)

        # Queue the rest
        for track in rest_of_tracks:
            await music_manager.add_to_queue(guild_id, track, ctx.author)

        await ctx.send(f"✅ Queued {len(rest_of_tracks)} more track(s).")

        # Preload the next song if available
        if rest_of_tracks:
            async def preload():
                try:
                    preload_source = await play_song(vc, rest_of_tracks[0], return_source=True)
                    music_manager.preloaded_source[guild_id] = preload_source
                except Exception as e:
                    print(f"⚠️ Preloading failed: {e}")

            asyncio.create_task(preload())

    async def _play_next(self, ctx):
        guild_id = ctx.guild.id
        vc = music_manager.voice_clients[guild_id]
        track, requested_by = music_manager.get_next(guild_id)

        if not track:
            await ctx.send("✅ Queue ended.")
            music_manager.preloaded_source.pop(guild_id, None)
            return

        print(f"🎵 Now playing: {track} (requested by {requested_by})")
        await ctx.send(f"▶️ Now playing: {track} (requested by {requested_by.mention})")
        music_manager.now_playing[guild_id] = track

        # Use preloaded source if it exists
        source = music_manager.preloaded_source.get(guild_id)
        if not source:
            source = await play_song(vc, track, return_source=True)

        music_manager.preloaded_source[guild_id] = None

        # Preload the next song
        queue = music_manager.get_queue(guild_id)
        if queue:
            next_track, _ = queue[0]
            async def preload():
                try:
                    preload_source = await play_song(vc, next_track, return_source=True)
                    music_manager.preloaded_source[guild_id] = preload_source
                except Exception as e:
                    print(f"⚠️ Preloading failed: {e}")
            asyncio.create_task(preload())

        def after_playing(_):
            fut = asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        vc.play(source, after=after_playing)

    @commands.command(name="queue")
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        queue = music_manager.get_queue(guild_id)
        if not queue:
            await ctx.send("📭 The queue is currently empty.")
            return

        msg = "**🎶 Upcoming Songs:**\n"
        for i, (track, user) in enumerate(queue, start=1):
            msg += f"{i}. {track} (requested by {user.mention})\n"
        await ctx.send(msg)

    @commands.command(name="skip")
    async def skip(self, ctx):
        guild_id = ctx.guild.id
        music_manager.skip(guild_id)
        await ctx.send("⏭️ Skipped.")

    @commands.command(name="pause")
    async def pause(self, ctx):
        guild_id = ctx.guild.id
        music_manager.pause(guild_id)
        await ctx.send("⏸️ Paused.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        guild_id = ctx.guild.id
        music_manager.resume(guild_id)
        await ctx.send("▶️ Resumed.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        guild_id = ctx.guild.id
        music_manager.shuffle_queue(guild_id)
        await ctx.send("🔀 Queue shuffled.")

    @commands.command(name="clear")
    async def clear(self, ctx):
        guild_id = ctx.guild.id
        music_manager.clear_queue(guild_id)
        await ctx.send("🗑️ Queue cleared and playback stopped.")
