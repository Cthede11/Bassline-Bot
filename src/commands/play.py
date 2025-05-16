from discord.ext import commands
from discord import app_commands, Interaction
from discord import Object
from src.utils.discord_voice import join_voice_channel, play_song
from src.utils.music import music_manager
import asyncio

class PlayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="play", description="Play a song by name or URL")
    async def play(self, interaction: Interaction, query: str):
        await interaction.response.defer()
        guild_id = interaction.guild.id
        music_manager.voice_clients[guild_id] = await join_voice_channel(interaction)
        vc = music_manager.voice_clients[guild_id]

        tracks = [query]
        if not tracks:
            await interaction.followup.send("⚠️ No tracks found.")
            return

        first_track = tracks[0]
        rest_of_tracks = tracks[1:]

        try:
            bass_boost = music_manager.get_bass_boost(interaction.user.id)
            source = await play_song(vc, first_track, return_source=True, bass_boost=bass_boost)


            music_manager.now_playing[guild_id] = first_track
            print(f"🎵 Now playing: {first_track} (requested by {interaction.user})")
            await interaction.followup.send(f"▶️ Now playing: {first_track} (requested by {interaction.user.mention})")
        except Exception as e:
            await interaction.followup.send(f"❌ Error playing: {e}")
            return

        def after_playing(_):
            fut = asyncio.run_coroutine_threadsafe(self._play_next(interaction), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        vc.play(source, after=after_playing)

        for track in rest_of_tracks:
            await music_manager.add_to_queue(guild_id, track, interaction.user)

        if rest_of_tracks:
            await interaction.followup.send(f"✅ Queued {len(rest_of_tracks)} more track(s).")

            async def preload():
                try:
                    preload_source = await play_song(vc, rest_of_tracks[0], return_source=True)
                    music_manager.preloaded_source[guild_id] = preload_source
                except Exception as e:
                    print(f"⚠️ Preloading failed: {e}")

            asyncio.create_task(preload())

    async def _play_next(self, interaction: Interaction):
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


    @app_commands.command(name="queue", description="Show the current song queue")
    async def queue(self, interaction: Interaction):
        guild_id = interaction.guild.id
        queue = music_manager.get_queue(guild_id)
        if not queue:
            await interaction.response.send_message("📭 The queue is currently empty.")
            return

        msg = "**🎶 Upcoming Songs:**\n"
        for i, (track, user) in enumerate(queue, start=1):
            msg += f"{i}. {track} (requested by {user.mention})\n"
        await interaction.response.send_message(msg)

    @app_commands.command(name="skip", description="Skip the currently playing song")
    async def skip(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.skip(guild_id)
        await interaction.response.send_message("⏭️ Skipped.")

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.pause(guild_id)
        await interaction.response.send_message("⏸️ Paused.")

    @app_commands.command(name="resume", description="Resume the current song")
    async def resume(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.resume(guild_id)
        await interaction.response.send_message("▶️ Resumed.")

    @app_commands.command(name="shuffle", description="Shuffle the current queue")
    async def shuffle(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.shuffle_queue(guild_id)
        await interaction.response.send_message("🔀 Queue shuffled.")

    @app_commands.command(name="clear", description="Clear the current queue")
    async def clear(self, interaction: Interaction):
        guild_id = interaction.guild.id
        music_manager.clear_queue(guild_id)
        await interaction.response.send_message("🗑️ Queue cleared and playback stopped.")

    from discord import Interaction

    @app_commands.command(name="bassboost", description="Toggle bass boost for yourself")
    async def bassboost(self, interaction: Interaction):
        from src.utils.music import music_manager

        try:
            state = music_manager.toggle_bass_boost(interaction.user.id)
            emoji = "🔊" if state else "🔈"
            await interaction.response.send_message(
                f"{emoji} Bass Boost {'enabled' if state else 'disabled'} for {interaction.user.mention}"
            )
        except Exception as e:
            print(f"[ERROR] Bass boost toggle failed: {e}")
            await interaction.response.send_message("❌ Failed to toggle bass boost.")
