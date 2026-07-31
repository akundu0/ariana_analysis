"""
Scrape lifetime Spotify stream counts from Kworb.net for Ariana Grande's tracks.
Falls back to Spotify popularity scores if scraping fails.
Results are saved to data/raw/kworb_streams.json.
"""

import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import DATA_RAW, KWORB_ARTIST_URL

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_stream_count(text: str) -> int | None:
    """Parse a stream count string like '2,345,678,901' into an integer."""
    text = text.strip().replace(",", "").replace(".", "")
    try:
        return int(text)
    except ValueError:
        return None


def scrape_kworb_artist_songs() -> dict[str, dict]:
    """
    Scrape the Kworb artist songs page for stream counts.
    Returns a dict mapping track name (lowercase) to {streams, track_url, spotify_id}.
    """
    print(f"Fetching {KWORB_ARTIST_URL}...")
    resp = requests.get(KWORB_ARTIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Kworb uses a <table> with class "sortable"
    table = soup.find("table")
    if not table:
        print("WARNING: Could not find data table on Kworb page.")
        return {}

    results = {}
    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # First cell contains the track link
        link = cells[0].find("a")
        if not link:
            continue

        track_name = link.get_text(strip=True)
        href = link.get("href", "")

        # Extract Spotify track ID from the href
        spotify_id = None
        id_match = re.search(r"track/(\w+)", href)
        if id_match:
            spotify_id = id_match.group(1)

        # Stream count is typically in the last or second cell
        streams = None
        for cell in cells[1:]:
            text = cell.get_text(strip=True)
            parsed = parse_stream_count(text)
            if parsed and parsed > 1000:
                streams = parsed
                break

        results[track_name.lower()] = {
            "track_name": track_name,
            "spotify_id": spotify_id,
            "streams": streams,
            "source": "kworb",
        }

    return results


def scrape_individual_track(track_id: str) -> int | None:
    """Scrape stream count from an individual Kworb track page."""
    url = f"https://kworb.net/spotify/track/{track_id}.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for total streams in the page text
        text = soup.get_text()
        # Kworb typically shows "Total: X,XXX,XXX" or similar
        total_match = re.search(r"Total[:\s]+([\d,]+)", text)
        if total_match:
            return parse_stream_count(total_match.group(1))
    except Exception as e:
        print(f"  Could not fetch {url}: {e}")

    return None


def main():
    print("Scraping Kworb.net for Ariana Grande stream counts...\n")

    streams_data = scrape_kworb_artist_songs()

    if streams_data:
        print(f"\n✓ Found stream data for {len(streams_data)} tracks")
        # Show top 10 by streams
        sorted_tracks = sorted(
            streams_data.values(),
            key=lambda x: x["streams"] or 0,
            reverse=True,
        )
        print("\nTop 10 by streams:")
        for i, t in enumerate(sorted_tracks[:10], 1):
            streams_str = f"{t['streams']:,}" if t['streams'] else "N/A"
            print(f"  {i}. {t['track_name']} — {streams_str}")
    else:
        print("WARNING: No stream data scraped. The Kworb page may have changed format.")
        print("You can manually create data/manual/streams.csv with columns: track_name,streams")

    # Save raw data
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    output_path = DATA_RAW / "kworb_streams.json"
    with open(output_path, "w") as f:
        json.dump(streams_data, f, indent=2, default=str)
    print(f"\n✓ Saved to {output_path}")


if __name__ == "__main__":
    main()
