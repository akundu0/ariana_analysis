# Ariana Grande Song Success Analysis

Analyze audio features (BPM, energy, tone, danceability, etc.) of Ariana Grande's 7 studio albums, correlate them with Spotify stream counts, compare albums holistically, and profile your personal listening taste — all visualized in an interactive Streamlit dashboard.

## Albums Analyzed

| Album | Year |
|---|---|
| Yours Truly | 2013 |
| My Everything | 2014 |
| Dangerous Woman | 2016 |
| Sweetener | 2018 |
| thank u, next | 2019 |
| Positions | 2020 |
| eternal sunshine | 2024 |

## Setup

### 1. Prerequisites
- Python 3.10+
- A [Spotify Developer](https://developer.spotify.com/dashboard) app
- A free [FreqBlog API key](https://api.freqblog.com/dashboard) (1,000 req/mo free — we only need ~93)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Spotify Credentials
Copy the example env file and fill in your credentials:
```bash
cp .env.example .env
```
Edit `.env` with your Spotify app's Client ID, Client Secret, and FreqBlog API key.

In your Spotify Developer Dashboard, set the redirect URI to:
```
http://127.0.0.1:8888/callback
```

> **Note:** Spotify no longer allows `localhost` in redirect URIs. Use `127.0.0.1` instead.

> **Note:** Spotify deprecated their `audio_features` endpoint for new apps (Nov 2024).
> Audio features (BPM, energy, danceability, valence, etc.) are fetched from the
> [FreqBlog API](https://freqblog.com/) instead — a free drop-in replacement.

### 4. Fetch Data
Run the data collection scripts in order:
```bash
# Fetch all album tracks + audio features from Spotify
python scripts/fetch_tracks.py

# Scrape stream counts from Kworb.net
python scripts/fetch_streams.py

# (Optional) Fetch your personal top tracks via OAuth
python scripts/fetch_user_top.py

# Process and merge all data
python scripts/process_data.py
```

### 5. Launch Dashboard
```bash
streamlit run dashboard/app.py
```

## Dashboard Pages

- **Overview** — Key metrics, top songs table, album breakdown
- **Song Analysis** — Scatter plots, correlation heatmap, feature distributions, singles vs deep cuts
- **Album Analysis** — Radar charts, sound evolution timeline, album deep dives
- **Personal Taste** — Your listening profile vs global averages (requires OAuth step)
- **Insights** — Top correlates of success, collaboration impact, key/mode analysis, duration sweet spot

## Project Structure

```
ariana_analysis/
├── .env                  # Spotify credentials (gitignored)
├── requirements.txt
├── data/
│   ├── raw/              # Cached API responses
│   ├── processed/        # Clean CSVs for the dashboard
│   └── manual/           # Hand-curated data
├── scripts/
│   ├── fetch_tracks.py   # Spotify API → albums/tracks/features
│   ├── fetch_streams.py  # Kworb.net scraper
│   ├── fetch_user_top.py # OAuth → personal top tracks
│   └── process_data.py   # Merge + clean + aggregate
├── dashboard/
│   └── app.py            # Streamlit dashboard
└── utils/
    └── helpers.py         # Shared constants & utilities
```

## Tech Stack

- **spotipy** — Spotify API (track metadata, popularity, user top tracks)
- **FreqBlog API** — Audio features (BPM, energy, danceability, valence, etc.)
- **requests + BeautifulSoup** — Web scraping (Kworb.net stream counts)
- **pandas** — Data processing
- **plotly** — Interactive charts
- **streamlit** — Dashboard framework
- **scikit-learn** — Correlation analysis