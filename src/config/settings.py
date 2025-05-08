# filepath: c:\Users\cthed\Desktop\spotifyPlayer\discord-spotify-bot\src\config\settings.py
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
print(f"DISCORD_TOKEN: {DISCORD_TOKEN}")  # Debugging line
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")