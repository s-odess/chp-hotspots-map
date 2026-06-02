import json
import os

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(layout="wide", page_title="California Highway Live Telemetry")

st.title("🚨 Live Highway Incident Telemetry")
st.subheader("Real-time automated traffic narrative & dispatcher logs")

FILE_PATH = "live_hotspots.json"
CA_LAT = (32.5, 42.1)
CA_LON = (-124.5, -114.0)
CA_VIEW = pdk.ViewState(latitude=37.0, longitude=-119.5, zoom=5.5, pitch=0)


def normalize_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept Latitude/Longitude or lat/lon; return float columns lat and lon."""
    out = frame.copy()
    if "lat" not in out.columns:
        if "Latitude" in out.columns:
            out["lat"] = pd.to_numeric(out["Latitude"], errors="coerce")
        elif "latitude" in out.columns:
            out["lat"] = pd.to_numeric(out["latitude"], errors="coerce")
    else:
        out["lat"] = pd.to_numeric(out["lat"], errors="coerce")

    if "lon" not in out.columns:
        if "Longitude" in out.columns:
            out["lon"] = pd.to_numeric(out["Longitude"], errors="coerce")
        elif "longitude" in out.columns:
            out["lon"] = pd.to_numeric(out["longitude"], errors="coerce")
    else:
        out["lon"] = pd.to_numeric(out["lon"], errors="coerce")

    return out


def filter_plottable(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "lat" not in frame.columns or "lon" not in frame.columns:
        return pd.DataFrame(columns=["lat", "lon"])
    plot = frame.dropna(subset=["lat", "lon"]).copy()
    plot = plot[(plot["lat"] != 0) & (plot["lon"] != 0)]
    plot = plot[
        plot["lat"].between(CA_LAT[0], CA_LAT[1]) & plot["lon"].between(CA_LON[0], CA_LON[1])
    ]
    return plot[["lat", "lon"]].reset_index(drop=True)


def render_california_map(plot: pd.DataFrame) -> None:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=plot,
        get_position=["lon", "lat"],
        get_fill_color=[220, 38, 38, 200],
        get_radius=8000,
        pickable=True,
    )
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=CA_VIEW,
        map_style=None,
        tooltip={"text": "Lat: {lat}\nLon: {lon}"},
    )
    st.pydeck_chart(deck, use_container_width=True, height=500)


# --- Load data ---
if os.path.exists(FILE_PATH) and os.path.getsize(FILE_PATH) > 0:
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    except Exception:
        st.error("Telemetry link establishing... (Waiting for fresh data cycle)")
        st.stop()
else:
    st.error("Initializing core database connection...")
    st.stop()

df = normalize_coordinates(df)
plot_df = filter_plottable(df)

# --- Diagnostics (toggle off later) ---
with st.expander("Map diagnostics (coordinate audit)", expanded=False):
    st.caption(
        "Scraper writes real CHP coords (not 0,0). Summaries stay 'Pending' until "
        "agent.py runs Gemini (see pipeline Actions logs)."
    )
    if plot_df.empty:
        st.warning("No points passed CA bounds filter.")
        if "lat" in df.columns and "lon" in df.columns:
            st.write("Raw lat/lon sample (before filter):", df[["lat", "lon"]].head(10))
    else:
        st.write(f"Plottable incidents: **{len(plot_df)}**")
        st.write(
            "Lat range:",
            float(plot_df["lat"].min()),
            "→",
            float(plot_df["lat"].max()),
            "| Lon range:",
            float(plot_df["lon"].min()),
            "→",
            float(plot_df["lon"].max()),
        )
        st.dataframe(plot_df.head(10), use_container_width=True, hide_index=True)

st.markdown("### Current Dispatch Feed")
if not df.empty:
    feed_cols = [c for c in ("Incident_No", "Time", "Type", "lat", "lon") if c in df.columns]
    st.dataframe(
        df[feed_cols] if feed_cols else df,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Waiting for incoming traffic stream logs...")

st.markdown("### 🗺️ Geographic Hotspots")
if not plot_df.empty:
    render_california_map(plot_df)
else:
    st.info("No California coordinates available to plot.")

col1, col2 = st.columns([1, 1])

with col2:
    st.markdown("### 📰 Live Dispatch Narratives")
    if not df.empty:
        for _, row in df.iloc[::-1].iterrows():
            summary_text = row.get("Summary", "Processing AI telemetry analysis...")
            if str(summary_text).startswith("Error:"):
                summary_text = "🔄 Queued for next scheduled AI translation cycle."
            elif summary_text == "Pending AI analysis...":
                summary_text = (
                    "🔄 Narrative pending — GitHub Actions will run the Gemini agent "
                    "on the next pipeline cycle (up to 3 summaries per run)."
                )

            incident_id = row.get("Incident_No", "Unknown ID")
            raw_type = row.get("Type", "Traffic Event")
            log_time = row.get("Time", "Recent")

            with st.container(border=True):
                st.markdown(f"**📍 Incident Log #{incident_id}**")
                st.caption(f"⏱️ {log_time} | Raw Code: {raw_type}")
                st.info(summary_text)
    else:
        st.info("Waiting for incoming traffic stream logs...")

with col1:
    st.markdown("### 📋 Full Telemetry")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No incidents loaded.")
