import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from src.config.settings import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
print(f"Module path: {__file__}")

def get_spotify_playlist_tracks(playlist_url):
    print("Fetching tracks from Spotify...")

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))

        results = sp.playlist_tracks(playlist_url)
        print(f"Spotify returned {len(results['items'])} items.")

        tracks = []
        for item in results['items']:
            track = item['track']
            track_name = f"{track['name']} - {track['artists'][0]['name']}"
            print(f"Track found: {track_name}")
            tracks.append(track_name)

        return tracks

    except Exception as e:
        print(f"Spotify API error: {e}")
        return []
