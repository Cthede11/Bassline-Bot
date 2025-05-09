import asyncio
import discord

class MusicManager:
    def __init__(self):
        self.queues = {}
        self.voice_clients = {}
        self.now_playing = {}
        self.preloaded_source = {}

    async def add_to_queue(self, guild_id, track, requested_by):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append((track, requested_by))


    def get_next(self, guild_id):
        if guild_id in self.queues and self.queues[guild_id]:
            return self.queues[guild_id].pop(0)
        return None, None


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

music_manager = MusicManager()
