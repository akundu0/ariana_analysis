"""
Process raw data into clean CSVs for the dashboard.
Merges Spotify audio features, Kworb stream counts, and metadata.
Outputs: data/processed/songs.csv, data/processed/albums.csv
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import (
    AUDIO_FEATURES,
    DATA_MANUAL,
    DATA_PROCESSED,
    DATA_RAW,
    KEY_NAMES,
    KNOWN_SINGLES,
    MODE_NAMES,
    STUDIO_ALBUMS,
)


def load_spotify_data() -> pd.DataFrame:
    """Load and flatten the raw Spotify tracks JSON into a DataFrame."""
    path = DATA_RAW / "spotify_tracks.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/fetch_tracks.py first."
        )

    with open(path) as f:
        raw = json.load(f)

    rows = []
    for album_name, album_data in raw.items():
        for track in album_data["tracks"]:
            row = {
                "track_name": track["track_name"],
                "track_id": track["track_id"],
                "album_name": album_name,
                "album_id": album_data["album_id"],
                "release_date": album_data["release_date"],
                "album_image": album_data["album_image"],
                "track_number": track["track_number"],
                "total_album_tracks": album_data["total_tracks"],
                "duration_ms": track["duration_ms"],
                "explicit": track["explicit"],
                "artists": ", ".join(track["artists"]),
                "is_collaboration": track["is_collaboration"],
                "popularity": track["popularity"],
            }

            # Flatten audio features
            af = track.get("audio_features")
            if af:
                for feat in AUDIO_FEATURES:
                    row[feat] = af.get(feat)
                row["key"] = af.get("key", -1)
                row["mode"] = af.get("mode", -1)
                row["time_signature"] = af.get("time_signature")

            rows.append(row)

    return pd.DataFrame(rows)


def load_kworb_streams() -> dict[str, int]:
    """Load Kworb stream counts. Returns dict of track_name_lower -> streams."""
    path = DATA_RAW / "kworb_streams.json"
    if not path.exists():
        print(f"WARNING: {path} not found. Run scripts/fetch_streams.py first.")
        print("Falling back to Spotify popularity scores only.")
        return {}

    with open(path) as f:
        raw = json.load(f)

    # Build lookup by both track name (lowercase) and Spotify ID
    streams_by_name = {}
    streams_by_id = {}
    for key, data in raw.items():
        if data.get("streams"):
            streams_by_name[key.lower()] = data["streams"]
            if data.get("spotify_id"):
                streams_by_id[data["spotify_id"]] = data["streams"]

    return streams_by_name, streams_by_id


def load_user_top_tracks() -> pd.DataFrame | None:
    """Load user's top Ariana tracks if available."""
    path = DATA_RAW / "user_top_tracks.json"
    if not path.exists():
        print(f"NOTE: {path} not found. Personal taste data will be unavailable.")
        return None

    with open(path) as f:
        raw = json.load(f)

    rows = []
    for time_range, data in raw.items():
        for i, track in enumerate(data["ariana_tracks"]):
            rows.append(
                {
                    "track_id": track["track_id"],
                    "track_name": track["track_name"],
                    "album_name": track["album_name"],
                    "time_range": time_range,
                    "rank_in_top": i + 1,
                    "popularity": track["popularity"],
                }
            )

    if not rows:
        return None

    return pd.DataFrame(rows)


def flag_singles(df: pd.DataFrame) -> pd.Series:
    """Flag tracks that were released as singles."""
    is_single = pd.Series(False, index=df.index)
    for album_name, singles_list in KNOWN_SINGLES.items():
        mask = df["album_name"] == album_name
        for single_name in singles_list:
            is_single |= mask & (df["track_name"].str.lower() == single_name.lower())
    return is_single


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns for analysis."""
    df = df.copy()

    # Duration in minutes
    df["duration_min"] = df["duration_ms"] / 60000

    # Key and mode names
    df["key_name"] = df["key"].map(KEY_NAMES).fillna("Unknown")
    df["mode_name"] = df["mode"].map(MODE_NAMES).fillna("Unknown")
    df["key_mode"] = df["key_name"] + " " + df["mode_name"]

    # Album year
    df["year"] = df["album_name"].map(
        {name: info["year"] for name, info in STUDIO_ALBUMS.items()}
    )

    # Track position category
    df["position_category"] = "Middle"
    df.loc[df["track_number"] == 1, "position_category"] = "Opener"
    df.loc[
        df["track_number"] == df["total_album_tracks"], "position_category"
    ] = "Closer"

    # Singles flag
    df["is_single"] = flag_singles(df)

    return df


def compute_album_aggregates(songs_df: pd.DataFrame) -> pd.DataFrame:
    """Compute album-level aggregated statistics."""
    numeric_features = AUDIO_FEATURES + ["popularity", "duration_min"]
    available = [f for f in numeric_features if f in songs_df.columns]

    agg_dict = {f: "mean" for f in available}
    agg_dict["track_name"] = "count"
    if "streams" in songs_df.columns:
        agg_dict["streams"] = ["sum", "mean"]

    albums = songs_df.groupby("album_name").agg(agg_dict)
    albums.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in albums.columns
    ]
    albums = albums.rename(columns={"track_name_count": "track_count"})

    # Add album metadata
    for album_name, info in STUDIO_ALBUMS.items():
        if album_name in albums.index:
            albums.loc[album_name, "year"] = info["year"]
            albums.loc[album_name, "color"] = info["color"]

    albums = albums.sort_values("year")
    albums.index.name = "album_name"
    return albums.reset_index()


def main():
    print("Processing data...\n")

    # 1. Load Spotify data
    print("Loading Spotify track data...")
    songs = load_spotify_data()
    print(f"  {len(songs)} tracks loaded from {songs['album_name'].nunique()} albums")

    # 2. Load and merge stream counts
    print("Loading Kworb stream counts...")
    try:
        streams_by_name, streams_by_id = load_kworb_streams()
        if streams_by_id:
            songs["streams"] = songs["track_id"].map(streams_by_id)
            # Fallback to name matching for unmatched tracks
            unmatched = songs["streams"].isna()
            if unmatched.any():
                songs.loc[unmatched, "streams"] = songs.loc[
                    unmatched, "track_name"
                ].str.lower().map(streams_by_name)

            matched = songs["streams"].notna().sum()
            print(f"  Matched streams for {matched}/{len(songs)} tracks")
        else:
            print("  No stream data available, using popularity only")
    except Exception as e:
        print(f"  Error loading streams: {e}")

    # 3. Add derived columns
    print("Computing derived features...")
    songs = add_derived_columns(songs)

    # 4. Save songs CSV
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    songs_path = DATA_PROCESSED / "songs.csv"
    songs.to_csv(songs_path, index=False)
    print(f"\n✓ Saved songs data to {songs_path}")

    # 5. Compute and save album aggregates
    print("Computing album aggregates...")
    albums = compute_album_aggregates(songs)
    albums_path = DATA_PROCESSED / "albums.csv"
    albums.to_csv(albums_path, index=False)
    print(f"✓ Saved album data to {albums_path}")

    # 6. Save user top tracks if available
    user_top = load_user_top_tracks()
    if user_top is not None:
        user_path = DATA_PROCESSED / "user_top_tracks.csv"
        user_top.to_csv(user_path, index=False)
        print(f"✓ Saved user top tracks to {user_path}")

    # Summary
    print(f"\n{'='*50}")
    print("DATA SUMMARY")
    print(f"{'='*50}")
    print(f"Albums: {songs['album_name'].nunique()}")
    print(f"Total tracks: {len(songs)}")
    print(f"Singles: {songs['is_single'].sum()}")
    print(f"Collaborations: {songs['is_collaboration'].sum()}")
    if "streams" in songs.columns and songs["streams"].notna().any():
        print(f"Tracks with stream data: {songs['streams'].notna().sum()}")
        print(f"Total streams: {songs['streams'].sum():,.0f}")
    print(f"Year range: {songs['year'].min():.0f} – {songs['year'].max():.0f}")


if __name__ == "__main__":
    main()
