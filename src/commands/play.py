import asyncio
from discord.ext import commands
from src.utils.spotify import get_spotify_playlist_tracks
from src.utils.discord_voice import join_voice_channel, play_song
from src.utils.music import MusicManager

music_manager = MusicManager()

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
            tracks = get_spotify_playlist_tracks(query) if "spotify.com/playlist" in query else [query]
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
            await ctx.send(f"▶️ Now playing: {first_track}")
        except Exception as e:
            await ctx.send(f"❌ Error playing: {e}")
            return

        # Play + attach after handler
        def after_playing(_):
            fut = asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        vc.play(source, after=after_playing)

        # Queue the rest
        for track in rest_of_tracks:
            await music_manager.add_to_queue(guild_id, track)

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
        queue = music_manager.get_queue(guild_id)

        if not queue:
            await ctx.send("✅ Queue ended.")
            music_manager.preloaded_source.pop(guild_id, None)
            return

        next_track = queue.pop(0)
        await ctx.send(f"🎶 Now playing: {next_track}")
        music_manager.now_playing[guild_id] = next_track

        # Use preloaded source if it exists
        source = music_manager.preloaded_source.get(guild_id)
        if not source:
            source = await play_song(vc, next_track, return_source=True)

        # Clear the preloaded one now that we're using it
        music_manager.preloaded_source[guild_id] = None

        # Start loading the following track while this one plays
        if queue:
            following_track = queue[0]
            async def preload():
                try:
                    preloaded = await play_song(vc, following_track, return_source=True)
                    music_manager.preloaded_source[guild_id] = preloaded
                except Exception as e:
                    print(f"⚠️ Failed to preload: {e}")

            asyncio.create_task(preload())

        def after_playing(_):
            fut = asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        vc.play(source, after=after_playing)




    @commands.command(name="skip")
    async def skip(self, ctx):
        music_manager.skip(ctx.guild.id)
        await ctx.send("⏭️ Skipped!")

    @commands.command(name="pause")
    async def pause(self, ctx):
        music_manager.pause(ctx.guild.id)
        await ctx.send("⏸️ Paused.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        music_manager.resume(ctx.guild.id)
        await ctx.send("▶️ Resumed.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        music_manager.shuffle_queue(ctx.guild.id)
        await ctx.send("🔀 Queue shuffled.")

    @commands.command(name="queue")
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        queue = music_manager.get_queue(guild_id)

        if not queue:
            await ctx.send("📭 The queue is empty.")
            return

        queue_display = "\n".join([f"{i+1}. {track}" for i, track in enumerate(queue[:10])])
        if len(queue) > 10:
            queue_display += f"\n...and {len(queue) - 10} more."

        await ctx.send(f"📜 **Upcoming Tracks:**\n{queue_display}")

    @commands.command(name="clear")
    async def clear(self, ctx):
        guild_id = ctx.guild.id
        music_manager.clear_queue(guild_id)
        await ctx.send("🧹 Cleared the queue and stopped the current track.")
