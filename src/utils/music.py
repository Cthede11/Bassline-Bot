import asyncio
import discord
import os
import json
import time # For last_activity
from enum import Enum

# Define LoopState Enum
class LoopState(Enum):
    OFF = 0
    SINGLE = 1
    QUEUE = 2

BASS_FILE = os.path.join(os.path.dirname(__file__), 'bassboost_settings.json') # More robust path

class MusicManager:
    def __init__(self):
        self.queues = {}  # {guild_id: [(track_query, user_obj)]}
        self.voice_clients = {} # {guild_id: discord.VoiceClient}
        # now_playing stores detailed info about the current track
        self.now_playing = {}  # {guild_id: {"title": str, "duration": int, "thumbnail": str, "query": str, "start_time": float, "url": str, "requester": str, "requested_by_obj": discord.User, "uploader": str}}
        self.user_bass_boost = self._load_bassboost_settings()
        self.loop_states = {}  # {guild_id: LoopState}
        self.search_results = {} # {guild_id: list_of_search_result_dicts}
        self.last_activity = {} # {guild_id: float_timestamp}

    async def add_to_queue(self, guild_id, track_query, requested_by: discord.User):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append((track_query, requested_by))
        self.update_last_activity(guild_id)

    def get_next(self, guild_id):
        if guild_id in self.queues and self.queues[guild_id]:
            self.update_last_activity(guild_id)
            return self.queues[guild_id].pop(0)
        return None, None

    def shuffle_queue(self, guild_id):
        import random
        if guild_id in self.queues:
            random.shuffle(self.queues[guild_id])
            self.update_last_activity(guild_id)

    def is_playing(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        return vc and vc.is_playing()

    def pause(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.pause()
            self.update_last_activity(guild_id)

    def resume(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_paused():
            vc.resume()
            self.update_last_activity(guild_id)

    def skip(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.stop() # This will trigger the 'after' callback in vc.play()
        self.update_last_activity(guild_id)


    def get_queue(self, guild_id):
        return self.queues.get(guild_id, [])

    def clear_queue(self, guild_id):
        if guild_id in self.queues:
            self.queues[guild_id] = []
        self.update_last_activity(guild_id)

    def get_loop_state(self, guild_id) -> LoopState:
        return self.loop_states.get(guild_id, LoopState.OFF)

    def set_loop_state(self, guild_id, state: LoopState):
        self.loop_states[guild_id] = state
        self.update_last_activity(guild_id)
        return state

    def set_now_playing(self, guild_id, track_details: dict, requested_by_obj: discord.User):
        """
        Sets the currently playing track information.
        track_details should include: title, duration, thumbnail, query, start_time, url, uploader
        """
        self.now_playing[guild_id] = {
            **track_details,
            "requester": str(requested_by_obj.mention), # Use mention for easier display
            "requested_by_obj": requested_by_obj
        }
        self.update_last_activity(guild_id)

    def get_now_playing(self, guild_id):
        return self.now_playing.get(guild_id)

    def _load_bassboost_settings(self):
        if os.path.exists(BASS_FILE):
            try:
                with open(BASS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Bassboost settings file ({BASS_FILE}) is invalid. Resetting it.")
                return {}
        return {}

    def _save_bassboost_settings(self):
        try:
            with open(BASS_FILE, 'w') as f:
                json.dump(self.user_bass_boost, f, indent=4)
        except IOError as e:
            print(f"Error saving bassboost settings: {e}")


    def toggle_bass_boost(self, user_id): # user_id is int here
        user_id_str = str(user_id)
        current = self.user_bass_boost.get(user_id_str, False)
        self.user_bass_boost[user_id_str] = not current
        self._save_bassboost_settings()
        # self.update_last_activity(guild_id) # This should be called by the command using it with guild_id
        return self.user_bass_boost[user_id_str]

    def get_bass_boost(self, user_id): # user_id is int here
        return self.user_bass_boost.get(str(user_id), False)

    def update_last_activity(self, guild_id):
        self.last_activity[guild_id] = time.time()

    def get_last_activity(self, guild_id):
        return self.last_activity.get(guild_id)

    def clear_guild_state(self, guild_id):
        """Clears all music-related state for a guild, typically when bot leaves VC."""
        self.voice_clients.pop(guild_id, None)
        self.queues.pop(guild_id, None)
        self.now_playing.pop(guild_id, None)
        self.loop_states.pop(guild_id, None)
        self.search_results.pop(guild_id, None)
        self.last_activity.pop(guild_id, None)
        print(f"MusicManager: Cleared state for guild {guild_id}")


music_manager = MusicManager()
print("✅ MusicManager defined and instance created with new features (English Only)")