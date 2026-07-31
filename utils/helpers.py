"""Shared constants, album metadata, and utility functions."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_MANUAL = PROJECT_ROOT / "data" / "manual"

# --- Spotify ---
ARIANA_ARTIST_ID = "66CXWjxzNUsdJxJ2JdwvnR"

# Standard (non-deluxe) studio album Spotify IDs
STUDIO_ALBUMS = {
    "Yours Truly": {
        "id": "6vEyHuMExPhGmEJFhkGbCj",
        "year": 2013,
        "color": "#f8b4c8",
    },
    "My Everything": {
        "id": "3OZgEACvHydlQWpXEauaC9",
        "year": 2014,
        "color": "#c9a0dc",
    },
    "Dangerous Woman": {
        "id": "3pdKXIS7mILreNYnJnGkr1",
        "year": 2016,
        "color": "#2c2c2c",
    },
    "Sweetener": {
        "id": "3tx8gQqWbGwqIGZHqDNrGe",
        "year": 2018,
        "color": "#f5c16c",
    },
    "thank u, next": {
        "id": "2fYhqwDWXjbpjaIJPEfKFw",
        "year": 2019,
        "color": "#e8d5d0",
    },
    "Positions": {
        "id": "3euz4vS7ezKGnNSwgyvKcd",
        "year": 2020,
        "color": "#8b6f5e",
    },
    "eternal sunshine": {
        "id": "5EYKrEDnKhhcNxGedaRQeK",
        "year": 2024,
        "color": "#87ceeb",
    },
}

# Audio feature columns used in analysis
AUDIO_FEATURES = [
    "danceability",
    "energy",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "loudness",
    "duration_ms",
]

# Radar chart features (normalized 0-1 range)
RADAR_FEATURES = [
    "danceability",
    "energy",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
]

# Known singles (track names, lowercase for matching)
KNOWN_SINGLES = {
    "Yours Truly": [
        "the way",
        "baby i",
        "right there",
    ],
    "My Everything": [
        "problem",
        "break free",
        "bang bang",
        "love me harder",
        "one last time",
    ],
    "Dangerous Woman": [
        "dangerous woman",
        "into you",
        "side to side",
        "everyday",
        "be alright",
    ],
    "Sweetener": [
        "no tears left to cry",
        "the light is coming",
        "god is a woman",
        "breathin",
    ],
    "thank u, next": [
        "thank u, next",
        "7 rings",
        "break up with your girlfriend, i'm bored",
        "imagine",
    ],
    "Positions": [
        "positions",
        "34+35",
        "pov",
    ],
    "eternal sunshine": [
        "yes, and?",
        "we can't be friends (wait for your love)",
        "the boy is mine",
        "eternal sunshine",
    ],
}

# Kworb URL
KWORB_ARTIST_URL = "https://kworb.net/spotify/artist/66CXWjxzNUsdJxJ2JdwvnR_songs.html"

# Color palette for the dashboard
ALBUM_COLORS = {name: info["color"] for name, info in STUDIO_ALBUMS.items()}

# Key names mapping (Spotify uses integers 0-11)
KEY_NAMES = {
    0: "C", 1: "C#/Db", 2: "D", 3: "D#/Eb", 4: "E", 5: "F",
    6: "F#/Gb", 7: "G", 8: "G#/Ab", 9: "A", 10: "A#/Bb", 11: "B",
    -1: "Unknown",
}

MODE_NAMES = {0: "Minor", 1: "Major"}


def get_spotify_client_credentials():
    """Create a spotipy client using Client Credentials flow."""
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        )
    )


def get_spotify_user_auth():
    """Create a spotipy client using Authorization Code flow (for user data)."""
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
            scope="user-top-read",
        )
    )
