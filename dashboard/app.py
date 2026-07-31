"""
Ariana Grande Song Success Analysis — Streamlit Dashboard
Multi-page app: Overview, Song Analysis, Album Analysis, Personal Taste, Insights
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import (
    ALBUM_COLORS,
    AUDIO_FEATURES,
    KEY_NAMES,
    RADAR_FEATURES,
    STUDIO_ALBUMS,
    DATA_PROCESSED,
)

# --- Page Config ---
st.set_page_config(
    page_title="Ariana Grande Analysis",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #f8b4c8, #c9a0dc, #87ceeb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid rgba(248, 180, 200, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Data Loading ---
@st.cache_data
def load_songs():
    path = DATA_PROCESSED / "songs.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    # Ensure album ordering
    album_order = list(STUDIO_ALBUMS.keys())
    df["album_name"] = pd.Categorical(df["album_name"], categories=album_order, ordered=True)
    return df


@st.cache_data
def load_albums():
    path = DATA_PROCESSED / "albums.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    album_order = list(STUDIO_ALBUMS.keys())
    df["album_name"] = pd.Categorical(df["album_name"], categories=album_order, ordered=True)
    return df.sort_values("year")


@st.cache_data
def load_user_top():
    path = DATA_PROCESSED / "user_top_tracks.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def get_stream_col(df):
    """Return the best available popularity/stream column."""
    if "streams" in df.columns and df["streams"].notna().any():
        return "streams"
    return "popularity"


# --- Sidebar ---
st.sidebar.markdown('<p class="main-header">Ariana Grande</p>', unsafe_allow_html=True)
st.sidebar.markdown("### Song Success Analysis")

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Song Analysis", "Album Analysis", "Personal Taste", "Insights"],
    index=0,
)

songs = load_songs()
albums = load_albums()
user_top = load_user_top()

if songs is None:
    st.error(
        "No processed data found. Run the data pipeline first:\n\n"
        "```bash\n"
        "python scripts/fetch_tracks.py\n"
        "python scripts/fetch_streams.py\n"
        "python scripts/process_data.py\n"
        "```"
    )
    st.stop()

stream_col = get_stream_col(songs)

# Sidebar filters
st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
selected_albums = st.sidebar.multiselect(
    "Albums",
    options=songs["album_name"].cat.categories.tolist(),
    default=songs["album_name"].cat.categories.tolist(),
)

year_range = st.sidebar.slider(
    "Release Year",
    int(songs["year"].min()),
    int(songs["year"].max()),
    (int(songs["year"].min()), int(songs["year"].max())),
)

show_singles_only = st.sidebar.checkbox("Singles only", value=False)

# Apply filters
filtered = songs[
    (songs["album_name"].isin(selected_albums))
    & (songs["year"] >= year_range[0])
    & (songs["year"] <= year_range[1])
]
if show_singles_only:
    filtered = filtered[filtered["is_single"] == True]

album_color_map = ALBUM_COLORS


# ============================================================
# PAGE: OVERVIEW
# ============================================================
if page == "Overview":
    st.markdown('<h1 class="main-header">Overview</h1>', unsafe_allow_html=True)
    st.markdown("Analyzing audio features across Ariana Grande's 7 studio albums to uncover what makes a pop song successful.")

    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Albums", songs["album_name"].nunique())
    with col2:
        st.metric("Tracks", len(songs))
    with col3:
        st.metric("Singles", int(songs["is_single"].sum()))
    with col4:
        st.metric("Collabs", int(songs["is_collaboration"].sum()))
    with col5:
        if stream_col == "streams" and songs["streams"].notna().any():
            total = songs["streams"].sum()
            if total >= 1e9:
                st.metric("Total Streams", f"{total/1e9:.1f}B")
            else:
                st.metric("Total Streams", f"{total/1e6:.0f}M")
        else:
            st.metric("Avg Popularity", f"{songs['popularity'].mean():.0f}")

    st.markdown("---")

    # Top songs table
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Top Songs")
        sort_by = stream_col
        top_songs = (
            songs.nlargest(15, sort_by)[
                ["track_name", "album_name", sort_by, "energy", "valence", "danceability", "is_single"]
            ]
            .reset_index(drop=True)
        )
        top_songs.index += 1
        if sort_by == "streams":
            top_songs["streams"] = top_songs["streams"].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A"
            )
        st.dataframe(top_songs, use_container_width=True, height=500)

    with col_right:
        st.subheader("Album Breakdown")
        album_counts = songs.groupby("album_name", observed=True).size().reset_index(name="tracks")
        fig = px.bar(
            album_counts,
            x="album_name",
            y="tracks",
            color="album_name",
            color_discrete_map=album_color_map,
            labels={"album_name": "Album", "tracks": "Track Count"},
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

        # Popularity distribution
        st.subheader("Popularity Distribution")
        fig2 = px.histogram(
            songs,
            x="popularity",
            nbins=20,
            color="album_name",
            color_discrete_map=album_color_map,
            labels={"popularity": "Spotify Popularity", "album_name": "Album"},
        )
        fig2.update_layout(barmode="stack", height=300)
        st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# PAGE: SONG ANALYSIS
# ============================================================
elif page == "Song Analysis":
    st.markdown('<h1 class="main-header">Song Analysis</h1>', unsafe_allow_html=True)
    st.markdown(f"Explore how audio features correlate with {'streams' if stream_col == 'streams' else 'popularity'} across **{len(filtered)}** tracks.")

    # Feature selector
    col1, col2 = st.columns([1, 1])
    with col1:
        x_feature = st.selectbox(
            "X-Axis Feature",
            AUDIO_FEATURES,
            index=AUDIO_FEATURES.index("energy"),
        )
    with col2:
        y_feature = st.selectbox(
            "Y-Axis Feature",
            [stream_col] + AUDIO_FEATURES,
            index=0,
        )

    # Scatter plot
    scatter_data = filtered.dropna(subset=[x_feature, y_feature])
    size_col = "popularity" if scatter_data["popularity"].notna().all() else None
    fig = px.scatter(
        scatter_data,
        x=x_feature,
        y=y_feature,
        color="album_name",
        color_discrete_map=album_color_map,
        hover_data=["track_name", "album_name", "popularity"],
        size=size_col,
        size_max=15,
        trendline="ols",
        labels={"album_name": "Album"},
        title=f"{x_feature.title()} vs {y_feature.title()}",
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Correlation heatmap + Feature distributions
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Feature Correlation Heatmap")
        corr_features = [f for f in AUDIO_FEATURES if f in filtered.columns]
        if stream_col in filtered.columns:
            corr_features = [stream_col] + corr_features
        corr_df = filtered[corr_features].dropna()
        if len(corr_df) > 2:
            corr_matrix = corr_df.corr()
            fig_heatmap = px.imshow(
                corr_matrix,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                title="Feature Correlations",
            )
            fig_heatmap.update_layout(height=500)
            st.plotly_chart(fig_heatmap, use_container_width=True)

    with col_right:
        st.subheader("Feature Distribution")
        dist_feature = st.selectbox(
            "Select feature",
            AUDIO_FEATURES,
            index=AUDIO_FEATURES.index("valence"),
            key="dist_feature",
        )
        fig_dist = px.histogram(
            filtered,
            x=dist_feature,
            color="album_name",
            color_discrete_map=album_color_map,
            marginal="box",
            nbins=25,
            title=f"Distribution of {dist_feature.title()}",
        )
        fig_dist.update_layout(height=500, barmode="overlay")
        fig_dist.update_traces(opacity=0.7)
        st.plotly_chart(fig_dist, use_container_width=True)

    # Singles vs Deep Cuts
    st.markdown("---")
    st.subheader("Singles vs. Deep Cuts")
    col1, col2 = st.columns([1, 1])

    singles_data = filtered.copy()
    singles_data["type"] = singles_data["is_single"].map({True: "Single", False: "Deep Cut"})

    with col1:
        fig_box = px.box(
            singles_data,
            x="type",
            y=stream_col,
            color="type",
            color_discrete_map={"Single": "#f8b4c8", "Deep Cut": "#87ceeb"},
            title=f"{'Streams' if stream_col == 'streams' else 'Popularity'}: Singles vs Deep Cuts",
            points="all",
        )
        fig_box.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    with col2:
        # Compare average features
        single_means = singles_data.groupby("type")[RADAR_FEATURES].mean()
        fig_comp = go.Figure()
        for stype in ["Single", "Deep Cut"]:
            if stype in single_means.index:
                fig_comp.add_trace(
                    go.Scatterpolar(
                        r=single_means.loc[stype].values.tolist() + [single_means.loc[stype].values[0]],
                        theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
                        fill="toself",
                        name=stype,
                        opacity=0.6,
                    )
                )
        fig_comp.update_layout(
            title="Audio Profile: Singles vs Deep Cuts",
            polar=dict(radialaxis=dict(range=[0, 1])),
            height=400,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # Full data table
    st.markdown("---")
    st.subheader("Full Track Data")
    display_cols = ["track_name", "album_name", stream_col, "energy", "valence",
                    "danceability", "tempo", "acousticness", "loudness",
                    "duration_min", "key_mode", "is_single", "is_collaboration"]
    display_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(
        filtered[display_cols].sort_values(stream_col, ascending=False).reset_index(drop=True),
        use_container_width=True,
        height=400,
    )


# ============================================================
# PAGE: ALBUM ANALYSIS
# ============================================================
elif page == "Album Analysis":
    st.markdown('<h1 class="main-header">Album Analysis</h1>', unsafe_allow_html=True)
    st.markdown("Compare Ariana's 7 studio albums and track the evolution of her sound.")

    if albums is None:
        st.warning("Album data not available. Run process_data.py first.")
        st.stop()

    # Album radar comparison
    st.subheader("Album Audio Profiles")
    selected_compare = st.multiselect(
        "Select albums to compare",
        options=list(STUDIO_ALBUMS.keys()),
        default=list(STUDIO_ALBUMS.keys()),
        key="album_compare",
    )

    if selected_compare:
        fig_radar = go.Figure()
        for album_name in selected_compare:
            album_songs = songs[songs["album_name"] == album_name]
            if album_songs.empty:
                continue
            means = album_songs[RADAR_FEATURES].mean()
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=means.values.tolist() + [means.values[0]],
                    theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
                    fill="toself",
                    name=album_name,
                    line_color=ALBUM_COLORS.get(album_name),
                    opacity=0.6,
                )
            )
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(range=[0, 1])),
            height=500,
            title="Radar Comparison of Album Audio Profiles",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")

    # Feature evolution timeline
    st.subheader("Sound Evolution Over Time")
    evo_features = st.multiselect(
        "Select features to track",
        RADAR_FEATURES + ["tempo", "loudness"],
        default=["energy", "valence", "danceability"],
        key="evo_features",
    )

    if evo_features:
        album_means = songs.groupby(["album_name", "year"], observed=True)[evo_features].mean().reset_index()
        album_means = album_means.sort_values("year")

        fig_evo = go.Figure()
        for feat in evo_features:
            fig_evo.add_trace(
                go.Scatter(
                    x=album_means["year"],
                    y=album_means[feat],
                    mode="lines+markers",
                    name=feat.title(),
                    text=album_means["album_name"],
                    hovertemplate="%{text}<br>%{y:.2f}<extra></extra>",
                )
            )
        fig_evo.update_layout(
            title="How Ariana's Sound Has Evolved",
            xaxis_title="Year",
            yaxis_title="Feature Value",
            height=400,
        )
        st.plotly_chart(fig_evo, use_container_width=True)

    st.markdown("---")

    # Album bar charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Average Features by Album")
        bar_feature = st.selectbox(
            "Feature",
            AUDIO_FEATURES,
            index=AUDIO_FEATURES.index("energy"),
            key="album_bar_feature",
        )
        album_bar = songs.groupby("album_name", observed=True)[bar_feature].mean().reset_index()
        fig_bar = px.bar(
            album_bar,
            x="album_name",
            y=bar_feature,
            color="album_name",
            color_discrete_map=album_color_map,
            title=f"Average {bar_feature.title()} by Album",
        )
        fig_bar.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("Album Popularity / Streams")
        pop_col = stream_col
        album_pop = songs.groupby("album_name", observed=True)[pop_col].agg(["mean", "sum"]).reset_index()
        album_pop.columns = ["album_name", f"avg_{pop_col}", f"total_{pop_col}"]

        pop_metric = st.radio("Metric", ["Average", "Total"], horizontal=True, key="pop_metric")
        y_col = f"avg_{pop_col}" if pop_metric == "Average" else f"total_{pop_col}"

        fig_pop = px.bar(
            album_pop,
            x="album_name",
            y=y_col,
            color="album_name",
            color_discrete_map=album_color_map,
            title=f"{pop_metric} {'Streams' if pop_col == 'streams' else 'Popularity'} by Album",
        )
        fig_pop.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_pop, use_container_width=True)

    # Per-album track breakdown
    st.markdown("---")
    st.subheader("Album Deep Dive")
    selected_album = st.selectbox("Select album", list(STUDIO_ALBUMS.keys()), key="deep_dive")
    album_tracks = songs[songs["album_name"] == selected_album].sort_values("track_number")

    if not album_tracks.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_tracks = px.bar(
                album_tracks,
                x="track_name",
                y=stream_col,
                color="is_single",
                color_discrete_map={True: "#f8b4c8", False: "#87ceeb"},
                title=f"{selected_album} — Track {'Streams' if stream_col == 'streams' else 'Popularity'}",
                hover_data=["energy", "valence", "danceability"],
            )
            fig_tracks.update_layout(
                xaxis_tickangle=45,
                height=400,
                legend_title="Is Single",
            )
            st.plotly_chart(fig_tracks, use_container_width=True)

        with col2:
            st.markdown(f"**{selected_album}** ({STUDIO_ALBUMS[selected_album]['year']})")
            st.markdown(f"- **Tracks**: {len(album_tracks)}")
            st.markdown(f"- **Avg Energy**: {album_tracks['energy'].mean():.2f}")
            st.markdown(f"- **Avg Valence**: {album_tracks['valence'].mean():.2f}")
            st.markdown(f"- **Avg BPM**: {album_tracks['tempo'].mean():.0f}")
            st.markdown(f"- **Avg Danceability**: {album_tracks['danceability'].mean():.2f}")
            st.markdown(f"- **Singles**: {album_tracks['is_single'].sum()}")
            st.markdown(f"- **Collabs**: {album_tracks['is_collaboration'].sum()}")
            if "album_image" in album_tracks.columns:
                img = album_tracks["album_image"].iloc[0]
                if pd.notna(img):
                    st.image(img, width=200)


# ============================================================
# PAGE: PERSONAL TASTE
# ============================================================
elif page == "Personal Taste":
    st.markdown('<h1 class="main-header">Personal Taste</h1>', unsafe_allow_html=True)
    st.markdown("See how your listening habits compare to global popularity.")

    if user_top is None or user_top.empty:
        st.info(
            "No personal listening data found. Run the following to fetch your top tracks:\n\n"
            "```bash\n"
            "python scripts/fetch_user_top.py\n"
            "python scripts/process_data.py\n"
            "```"
        )
        st.markdown("---")
        st.markdown(
            "In the meantime, here's what the **average Ariana listener** profile looks like:"
        )

        # Show global average radar
        global_means = songs[RADAR_FEATURES].mean()
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=global_means.values.tolist() + [global_means.values[0]],
                theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
                fill="toself",
                name="Global Average",
                line_color="#f8b4c8",
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(range=[0, 1])),
            height=450,
            title="Average Audio Profile Across All Ariana Tracks",
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        # Time range selector
        time_range = st.selectbox(
            "Time Range",
            ["short_term", "medium_term", "long_term"],
            format_func=lambda x: {"short_term": "Last ~4 weeks", "medium_term": "Last ~6 months", "long_term": "All time"}[x],
        )

        user_filtered = user_top[user_top["time_range"] == time_range]

        if user_filtered.empty:
            st.warning(f"No Ariana tracks in your top tracks for this time range.")
        else:
            st.subheader(f"Your Top Ariana Tracks ({len(user_filtered)} found)")

            # Merge with full song data
            user_merged = user_filtered.merge(
                songs[["track_id"] + RADAR_FEATURES + ["tempo", "loudness", stream_col, "album_name"]],
                on="track_id",
                how="left",
                suffixes=("", "_global"),
            )

            # Your tracks table
            st.dataframe(
                user_merged[["rank_in_top", "track_name", "album_name"] +
                           [f for f in RADAR_FEATURES if f in user_merged.columns]].reset_index(drop=True),
                use_container_width=True,
            )

            st.markdown("---")

            # Radar: Your taste vs global average
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Your Taste vs Global Average")
                your_means = user_merged[RADAR_FEATURES].mean()
                global_means = songs[RADAR_FEATURES].mean()

                fig = go.Figure()
                fig.add_trace(
                    go.Scatterpolar(
                        r=your_means.values.tolist() + [your_means.values[0]],
                        theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
                        fill="toself",
                        name="Your Taste",
                        line_color="#f8b4c8",
                        opacity=0.7,
                    )
                )
                fig.add_trace(
                    go.Scatterpolar(
                        r=global_means.values.tolist() + [global_means.values[0]],
                        theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
                        fill="toself",
                        name="Global Average",
                        line_color="#87ceeb",
                        opacity=0.5,
                    )
                )
                fig.update_layout(
                    polar=dict(radialaxis=dict(range=[0, 1])),
                    height=450,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Your Tracks on Popularity Scatter")
                fig_scatter = px.scatter(
                    songs,
                    x="energy",
                    y=stream_col,
                    color="album_name",
                    color_discrete_map=album_color_map,
                    opacity=0.4,
                    hover_data=["track_name"],
                    title="All Tracks (your favorites highlighted)",
                )
                # Overlay user's tracks
                if not user_merged.empty:
                    fig_scatter.add_trace(
                        go.Scatter(
                            x=user_merged["energy"],
                            y=user_merged[stream_col] if stream_col in user_merged.columns else user_merged["popularity"],
                            mode="markers+text",
                            text=user_merged["track_name"],
                            textposition="top center",
                            marker=dict(size=14, color="red", symbol="star"),
                            name="Your Favorites",
                        )
                    )
                fig_scatter.update_layout(height=450)
                st.plotly_chart(fig_scatter, use_container_width=True)


# ============================================================
# PAGE: INSIGHTS
# ============================================================
elif page == "Insights":
    st.markdown('<h1 class="main-header">Insights</h1>', unsafe_allow_html=True)
    st.markdown("Key findings: what makes an Ariana Grande song successful?")

    # Top correlations with streams/popularity
    st.subheader(f"Feature Correlations with {'Streams' if stream_col == 'streams' else 'Popularity'}")

    corr_features = [f for f in AUDIO_FEATURES if f in filtered.columns]
    if stream_col in filtered.columns and filtered[stream_col].notna().sum() > 5:
        correlations = filtered[corr_features + [stream_col]].corr()[stream_col].drop(stream_col)
        correlations = correlations.sort_values(ascending=False)

        fig_corr = px.bar(
            x=correlations.values,
            y=correlations.index,
            orientation="h",
            color=correlations.values,
            color_continuous_scale="RdBu_r",
            color_continuous_midpoint=0,
            title=f"Correlation of Audio Features with {'Streams' if stream_col == 'streams' else 'Popularity'}",
            labels={"x": "Pearson Correlation", "y": "Feature"},
        )
        fig_corr.update_layout(height=400)
        st.plotly_chart(fig_corr, use_container_width=True)

        # Interpretation
        top_positive = correlations.head(3)
        top_negative = correlations.tail(3)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Strongest Positive Correlates")
            for feat, val in top_positive.items():
                direction = "higher" if val > 0 else "lower"
                st.markdown(f"- **{feat.title()}** (r = {val:.3f}): {direction} values tend to mean more streams")

        with col2:
            st.markdown("#### Strongest Negative Correlates")
            for feat, val in top_negative.items():
                direction = "higher" if val > 0 else "lower"
                st.markdown(f"- **{feat.title()}** (r = {val:.3f}): {direction} values tend to mean more streams")
    else:
        st.warning("Not enough data to compute meaningful correlations.")

    st.markdown("---")

    # Collaboration impact
    st.subheader("Does Collaboration Matter?")
    col1, col2 = st.columns(2)

    with col1:
        collab_stats = filtered.groupby("is_collaboration")[stream_col].agg(["mean", "count"]).reset_index()
        collab_stats["is_collaboration"] = collab_stats["is_collaboration"].map(
            {True: "Collaboration", False: "Solo"}
        )
        fig_collab = px.bar(
            collab_stats,
            x="is_collaboration",
            y="mean",
            color="is_collaboration",
            color_discrete_map={"Collaboration": "#c9a0dc", "Solo": "#f8b4c8"},
            title=f"Avg {'Streams' if stream_col == 'streams' else 'Popularity'}: Solo vs Collab",
            text="count",
        )
        fig_collab.update_traces(texttemplate="n=%{text}", textposition="outside")
        fig_collab.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_collab, use_container_width=True)

    with col2:
        # Track position impact
        pos_stats = filtered.groupby("position_category")[stream_col].mean().reset_index()
        fig_pos = px.bar(
            pos_stats,
            x="position_category",
            y=stream_col,
            color="position_category",
            title=f"Avg {'Streams' if stream_col == 'streams' else 'Popularity'} by Track Position",
            color_discrete_map={"Opener": "#f8b4c8", "Middle": "#c9a0dc", "Closer": "#87ceeb"},
        )
        fig_pos.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_pos, use_container_width=True)

    st.markdown("---")

    # Key/Mode analysis
    st.subheader("Key & Mode Analysis")
    col1, col2 = st.columns(2)

    with col1:
        key_counts = filtered["key_name"].value_counts().reset_index()
        key_counts.columns = ["key", "count"]
        fig_key = px.bar(
            key_counts,
            x="key",
            y="count",
            title="Distribution of Musical Keys",
            color="count",
            color_continuous_scale="Purples",
        )
        fig_key.update_layout(height=350)
        st.plotly_chart(fig_key, use_container_width=True)

    with col2:
        mode_pop = filtered.groupby("mode_name")[stream_col].mean().reset_index()
        fig_mode = px.bar(
            mode_pop,
            x="mode_name",
            y=stream_col,
            color="mode_name",
            color_discrete_map={"Major": "#f8b4c8", "Minor": "#87ceeb"},
            title=f"Avg {'Streams' if stream_col == 'streams' else 'Popularity'}: Major vs Minor",
        )
        fig_mode.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_mode, use_container_width=True)

    # Duration sweet spot
    st.markdown("---")
    st.subheader("Duration Sweet Spot")
    if "duration_min" in filtered.columns:
        fig_dur = px.scatter(
            filtered,
            x="duration_min",
            y=stream_col,
            color="album_name",
            color_discrete_map=album_color_map,
            hover_data=["track_name"],
            trendline="ols",
            title=f"Song Duration vs {'Streams' if stream_col == 'streams' else 'Popularity'}",
            labels={"duration_min": "Duration (minutes)"},
        )
        fig_dur.update_layout(height=400)
        st.plotly_chart(fig_dur, use_container_width=True)

    # Summary stats table
    st.markdown("---")
    st.subheader("Feature Summary Statistics")
    summary_features = AUDIO_FEATURES + ["popularity"]
    if "streams" in filtered.columns:
        summary_features.append("streams")
    available_features = [f for f in summary_features if f in filtered.columns]
    summary = filtered[available_features].describe().T
    summary = summary[["mean", "std", "min", "25%", "50%", "75%", "max"]]
    st.dataframe(summary.style.format("{:.2f}"), use_container_width=True)
