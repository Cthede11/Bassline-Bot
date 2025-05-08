import asyncio
import discord

class MusicManager:
    def __init__(self):
        self.queues = {}  # guild_id -> [track strings]
        self.voice_clients = {}  # guild_id -> discord.VoiceClient
        self.now_playing = {}  # guild_id -> track
        self.preloaded_source = {}  # ✅ NEW: guild_id -> FFmpegPCMAudio

    async def add_to_queue(self, guild_id, track):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append(track)

    def get_next(self, guild_id):
        if guild_id in self.queues and self.queues[guild_id]:
            return self.queues[guild_id].pop(0)
        return None

    def shuffle_queue(self, guild_id):
        import random
        if guild_id in self.queues:
            random.shuffle(self.queues[guild_id])

    def is_playing(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        return vc and vc.is_playing()

    def pause(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.pause()

    def resume(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_paused():
            vc.resume()

    def skip(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.stop()

    def get_queue(self, guild_id):
        return self.queues.get(guild_id, [])
    
    def clear_queue(self, guild_id):
        if guild_id in self.queues:
            self.queues[guild_id] = []

        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.stop()



print("✅ MusicManager defined")
print("Available names in music.py:", dir())
