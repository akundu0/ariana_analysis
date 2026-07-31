"""
Fetch all tracks and audio features for Ariana Grande's 7 studio albums.

Track metadata + popularity come from the Spotify API.
Audio features (BPM, energy, danceability, valence, etc.) come from the
FreqBlog API — a free drop-in replacement for Spotify's audio_features
endpoint, which was deprecated for new apps in November 2024.

Results are cached as JSON in data/raw/.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import (
    ARIANA_ARTIST_ID,
    STUDIO_ALBUMS,
    DATA_RAW,
    get_spotify_client_credentials,
)

FREQBLOG_BASE = "https://api.freqblog.com"


def fetch_album_tracks(sp, album_id: str) -> list[dict]:
    """Fetch all tracks for a given album ID."""
    results = sp.album_tracks(album_id, limit=50)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    return tracks


def fetch_audio_features_freqblog(track_name: str, artist: str = "Ariana Grande") -> dict | None:
    """Fetch audio features from FreqBlog API (free Spotify audio_features replacement)."""
    api_key = os.getenv("FREQBLOG_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.get(
            f"{FREQBLOG_BASE}/lookup",
            params={"track": track_name, "artist": artist},
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Map FreqBlog fields to Spotify-compatible field names
            return {
                "danceability": data.get("danceability"),
                "energy": data.get("energy"),
                "key": data.get("key_int", -1),
                "loudness": data.get("loudness_db"),
                "mode": data.get("mode"),
                "speechiness": data.get("speechiness"),
                "acousticness": data.get("acousticness"),
                "instrumentalness": data.get("instrumentalness"),
                "liveness": data.get("liveness"),
                "valence": data.get("valence"),
                "tempo": data.get("bpm"),
                "time_signature": data.get("time_signature"),
                "duration_ms": data.get("duration_ms"),
                "mood": data.get("mood"),
                "_source": "freqblog",
            }
        elif resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 5))
            print(f"    Rate limited, waiting {retry_after}s...")
            time.sleep(retry_after)
            return fetch_audio_features_freqblog(track_name, artist)
        else:
            print(f"    FreqBlog {resp.status_code} for '{track_name}'")
            return None
    except Exception as e:
        print(f"    FreqBlog error for '{track_name}': {e}")
        return None


def fetch_audio_features_spotify(sp, track_ids: list[str]) -> list[dict | None]:
    """Try Spotify's audio_features endpoint (works for existing extended-mode apps only)."""
    all_features = []
    try:
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            features = sp.audio_features(batch)
            all_features.extend(features)
            time.sleep(0.1)
    except Exception as e:
        print(f"  Spotify audio_features unavailable (expected for new apps): {e}")
        return [None] * len(track_ids)
    return all_features


def fetch_full_tracks(sp, track_ids: list[str]) -> list[dict]:
    """Fetch full track objects (for popularity) in batches of 50."""
    all_tracks = []
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i : i + 50]
        results = sp.tracks(batch)
        all_tracks.extend(results["tracks"])
        time.sleep(0.1)
    return all_tracks


def discover_album_ids(sp) -> dict[str, str]:
    """Dynamically find album IDs from Spotify's artist page, matching by name."""
    discovered = {}
    results = sp.artist_albums(ARIANA_ARTIST_ID, album_type="album", limit=50)
    albums = results["items"]
    while results["next"]:
        results = sp.next(results)
        albums.extend(results["items"])

    target_names = {name.lower(): name for name in STUDIO_ALBUMS}
    for album in albums:
        name_lower = album["name"].lower()
        if name_lower in target_names:
            canonical = target_names[name_lower]
            if canonical not in discovered:
                discovered[canonical] = album["id"]

    return discovered


def main():
    print("Connecting to Spotify API...")
    sp = get_spotify_client_credentials()

    # Try to discover album IDs dynamically, fall back to hardcoded
    print("Discovering album IDs from Spotify...")
    discovered_ids = discover_album_ids(sp)

    all_data = {}

    for album_name, album_info in STUDIO_ALBUMS.items():
        album_id = discovered_ids.get(album_name, album_info["id"])
        if album_name in discovered_ids:
            print(f"\nFetching: {album_name} ({album_info['year']}) [discovered ID: {album_id}]")
        else:
            print(f"\nFetching: {album_name} ({album_info['year']}) [using hardcoded ID: {album_id}]")

        # Get album metadata
        try:
            album_meta = sp.album(album_id)
        except Exception as e:
            print(f"  ERROR fetching album: {e}")
            print(f"  Skipping {album_name}")
            continue

        # Get tracks
        tracks = fetch_album_tracks(sp, album_id)
        track_ids = [t["id"] for t in tracks]
        print(f"  Found {len(tracks)} tracks")

        # Get full track details (for popularity)
        full_tracks = fetch_full_tracks(sp, track_ids)

        # Get audio features — try Spotify first, fall back to FreqBlog
        print("  Fetching audio features...")
        spotify_features = fetch_audio_features_spotify(sp, track_ids)
        has_spotify_features = any(f is not None for f in spotify_features)

        if has_spotify_features:
            print("  Using Spotify audio_features (extended mode app)")
        else:
            print("  Spotify audio_features unavailable, using FreqBlog API...")

        # Combine into structured data
        album_data = {
            "album_name": album_name,
            "album_id": album_id,
            "release_date": album_meta["release_date"],
            "album_image": album_meta["images"][0]["url"] if album_meta["images"] else None,
            "total_tracks": album_meta["total_tracks"],
            "tracks": [],
        }

        for i, (track, full_track, sp_features) in enumerate(
            zip(tracks, full_tracks, spotify_features)
        ):
            # Use Spotify features if available, otherwise FreqBlog
            if sp_features:
                features = sp_features
            else:
                artist_name = track["artists"][0]["name"] if track["artists"] else "Ariana Grande"
                features = fetch_audio_features_freqblog(track["name"], artist_name)
                if features:
                    print(f"    ✓ FreqBlog: {track['name']}")
                else:
                    print(f"    ✗ No features: {track['name']}")
                time.sleep(0.3)

            track_data = {
                "track_name": track["name"],
                "track_id": track["id"],
                "track_number": track["track_number"],
                "duration_ms": track["duration_ms"],
                "explicit": track.get("explicit", False),
                "artists": [a["name"] for a in track["artists"]],
                "is_collaboration": len(track["artists"]) > 1,
                "popularity": full_track["popularity"] if full_track else None,
                "audio_features": features if features else {},
            }
            album_data["tracks"].append(track_data)

        all_data[album_name] = album_data
        print(f"  ✓ {album_name} complete")
        time.sleep(0.2)

    # Save raw data
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    output_path = DATA_RAW / "spotify_tracks.json"
    with open(output_path, "w") as f:
        json.dump(all_data, f, indent=2)

    total_tracks = sum(len(a["tracks"]) for a in all_data.values())
    print(f"\n✓ Saved {total_tracks} tracks across {len(all_data)} albums to {output_path}")


if __name__ == "__main__":
    main()
