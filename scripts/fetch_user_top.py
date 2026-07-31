"""
Fetch the user's top Ariana Grande tracks via Spotify OAuth.
Uses the Authorization Code flow with 'user-top-read' scope.
Results are saved to data/raw/user_top_tracks.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import ARIANA_ARTIST_ID, DATA_RAW, get_spotify_user_auth


def fetch_top_tracks(sp, time_range: str, limit: int = 50) -> list[dict]:
    """Fetch user's top tracks for a given time range."""
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    return results["items"]


def filter_ariana_tracks(tracks: list[dict]) -> list[dict]:
    """Filter tracks to only those by Ariana Grande."""
    ariana_tracks = []
    for track in tracks:
        artist_ids = [a["id"] for a in track["artists"]]
        if ARIANA_ARTIST_ID in artist_ids:
            ariana_tracks.append(
                {
                    "track_name": track["name"],
                    "track_id": track["id"],
                    "album_name": track["album"]["name"],
                    "popularity": track["popularity"],
                    "artists": [a["name"] for a in track["artists"]],
                }
            )
    return ariana_tracks


def main():
    print("Authenticating with Spotify (OAuth)...")
    print("A browser window will open for you to log in.\n")

    sp = get_spotify_user_auth()

    # Verify authentication
    user = sp.current_user()
    print(f"Logged in as: {user['display_name']}\n")

    time_ranges = {
        "short_term": "Last ~4 weeks",
        "medium_term": "Last ~6 months",
        "long_term": "All time",
    }

    user_data = {}

    for time_range, description in time_ranges.items():
        print(f"Fetching top tracks ({description})...")
        all_tracks = fetch_top_tracks(sp, time_range)
        ariana_tracks = filter_ariana_tracks(all_tracks)

        user_data[time_range] = {
            "description": description,
            "total_top_tracks": len(all_tracks),
            "ariana_tracks_count": len(ariana_tracks),
            "ariana_tracks": ariana_tracks,
        }

        print(f"  Found {len(ariana_tracks)} Ariana tracks in your top {len(all_tracks)}")
        for i, t in enumerate(ariana_tracks, 1):
            print(f"    {i}. {t['track_name']} ({t['album_name']})")

    # Save
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    output_path = DATA_RAW / "user_top_tracks.json"
    with open(output_path, "w") as f:
        json.dump(user_data, f, indent=2)

    total_ariana = sum(d["ariana_tracks_count"] for d in user_data.values())
    print(f"\n✓ Saved user top tracks to {output_path}")
    print(f"  Total Ariana tracks across all time ranges: {total_ariana}")

    if total_ariana == 0:
        print("\n⚠ No Ariana Grande tracks found in your top tracks.")
        print("  The Personal Taste page will show limited data.")
        print("  Try listening to more Ariana and re-running this script!")


if __name__ == "__main__":
    main()
