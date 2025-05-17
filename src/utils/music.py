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

# Define paths for settings files more robustly
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
BASS_FILE = os.path.join(SETTINGS_DIR, 'bassboost_settings.json')
DJ_ROLE_FILE = os.path.join(SETTINGS_DIR, 'dj_settings.json')


class MusicManager:
    def __init__(self):
        self.queues = {}  # {guild_id: [(track_query, user_obj)]}
        self.voice_clients = {} # {guild_id: discord.VoiceClient}
        self.now_playing = {}  # {guild_id: {"title": str, ...}} # Includes requester, uploader, etc.
        self.user_bass_boost = self._load_json_settings(BASS_FILE, {}) # Default to empty dict
        self.loop_states = {}  # {guild_id: LoopState}
        self.search_results = {} # {guild_id: list_of_search_result_dicts}
        self.last_activity = {} # {guild_id: float_timestamp}
        self.dj_roles = self._load_json_settings(DJ_ROLE_FILE, {}) # {guild_id (int): role_id (int)}

    def _load_json_settings(self, file_path, default_value):
        """Loads settings from a JSON file."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                    # Ensure guild_ids are integers for dj_roles
                    if file_path == DJ_ROLE_FILE:
                        return {int(k): int(v) for k, v in content.items() if isinstance(v, (int, str)) and str(v).isdigit()}
                    return content
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ {os.path.basename(file_path)} is invalid or corrupted ({e}). Using default.")
                return default_value
        return default_value

    def _save_json_settings(self, file_path, data):
        """Saves settings to a JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving settings to {os.path.basename(file_path)}: {e}")

    # --- DJ Role Methods ---
    def set_dj_role(self, guild_id: int, role_id: int = None):
        """Sets or clears the DJ role for a guild."""
        guild_id_str = str(guild_id) # JSON keys are strings
        if role_id is None:
            if guild_id_str in self.dj_roles:
                del self.dj_roles[guild_id_str]
        else:
            self.dj_roles[guild_id_str] = role_id
        self._save_json_settings(DJ_ROLE_FILE, self.dj_roles)
        print(f"[DJ_ROLE_UPDATE] Guild {guild_id}: DJ Role set to {role_id if role_id else 'None'}")

    def get_dj_role_id(self, guild_id: int) -> int | None:
        """Gets the DJ role ID for a guild."""
        return self.dj_roles.get(str(guild_id)) # Keys are stored as strings

    # --- Music Control Methods ---
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
        if vc and vc.is_playing(): # vc.is_playing() is true even if paused
            if not vc.is_paused(): # Check if not already paused
                vc.pause()
                self.update_last_activity(guild_id)

    def resume(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_paused():
            vc.resume()
            self.update_last_activity(guild_id)

    def skip(self, guild_id):
        vc = self.voice_clients.get(guild_id)
        if vc and (vc.is_playing() or vc.is_paused()): # Allow skip even if paused
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
        self.now_playing[guild_id] = {
            **track_details,
            "requester": requested_by_obj.mention, 
            "requested_by_obj": requested_by_obj
        }
        self.update_last_activity(guild_id)

    def get_now_playing(self, guild_id):
        return self.now_playing.get(guild_id)

    def toggle_bass_boost(self, user_id: int):
        user_id_str = str(user_id)
        current = self.user_bass_boost.get(user_id_str, False)
        self.user_bass_boost[user_id_str] = not current
        self._save_json_settings(BASS_FILE, self.user_bass_boost)
        # Note: update_last_activity for the guild should be called by the command using this
        return self.user_bass_boost[user_id_str]

    def get_bass_boost(self, user_id: int):
        return self.user_bass_boost.get(str(user_id), False)

    def update_last_activity(self, guild_id):
        self.last_activity[guild_id] = time.time()

    def get_last_activity(self, guild_id):
        return self.last_activity.get(guild_id)

    def clear_guild_state(self, guild_id):
        """Clears runtime music state for a guild, typically when bot leaves VC."""
        self.voice_clients.pop(guild_id, None)
        self.queues.pop(guild_id, None)
        self.now_playing.pop(guild_id, None)
        self.loop_states.pop(guild_id, None)
        self.search_results.pop(guild_id, None)
        self.last_activity.pop(guild_id, None)
        # DJ roles are persistent and not cleared here
        print(f"MusicManager: Cleared runtime music state for guild {guild_id}")

music_manager = MusicManager()
print("✅ MusicManager defined and instance created with DJ Role Management.")
