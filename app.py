import json
import os

import pandas as pd
import requests
import streamlit as st

# 1. Set a clean page layout with a professional icon
st.set_page_config(page_title="CHP Live Dispatch Tracker", page_icon="🚨", layout="wide")

st.title("🚨 California Highway Patrol Live Telemetry")
st.caption("Real-time incident mapping and automated dispatch narratives.")

# !!! REPLACE WITH YOUR ACTUAL GITHUB USERNAME !!!
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"
LOCAL_JSON = "live_hotspots.json"

LAT_ALIASES = ("Latitude", "latitude", "lat", "LAT")
LON_ALIASES = ("Longitude", "longitude", "lon", "LON")


def _column_lookup(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    """Return the real column name in frame for any alias (exact or case-insensitive)."""
    lower_to_actual = {str(col).lower(): col for col in frame.columns}
    for alias in aliases:
        if alias in frame.columns:
            return alias
        match = lower_to_actual.get(alias.lower())
        if match is not None:
            return match
    return None


def _attach_lat_lon(frame: pd.DataFrame) -> pd.DataFrame:
    """Map any latitude/longitude column variant to normalized lat/lon (no row drops)."""
    out = frame.copy()
    lat_col = _column_lookup(out, LAT_ALIASES)
    lon_col = _column_lookup(out, LON_ALIASES)

    if lat_col is not None:
        out["lat"] = pd.to_numeric(out[lat_col], errors="coerce")
    else:
        out["lat"] = pd.NA

    if lon_col is not None:
        out["lon"] = pd.to_numeric(out[lon_col], errors="coerce")
    else:
        out["lon"] = pd.NA

    return out


def _fetch_records() -> list:
    """Load JSON array from GitHub raw URL, then local repo file as fallback."""
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, list) and payload:
                return payload
    except Exception:
        pass

    if os.path.exists(LOCAL_JSON) and os.path.getsize(LOCAL_JSON) > 0:
        try:
            with open(LOCAL_JSON, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list) and payload:
                return payload
        except (json.JSONDecodeError, OSError):
            pass

    return []


@st.cache_data(ttl=60)
def load_dashboard_data() -> pd.DataFrame:
    records = _fetch_records()
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = _attach_lat_lon(df)
    # Keep every incident row for the feed/summaries; map uses lat/lon where present.
    return df.reset_index(drop=True)


df = load_dashboard_data()

if not df.empty:
    # 2. THE MAP: Strip away PyDeck complexity.
    # We feed st.map ONLY the coordinates so it cannot get confused or look blank.
    st.map(df[["lat", "lon"]], height=500)

    st.markdown("---")

    # 3. DASHBOARD FEED LAYOUT
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📋 Active Incident Log")
        display_cols = [c for c in ("Incident_No", "Time", "Type") if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df, width="stretch", hide_index=True)

    with col2:
        st.subheader("🤖 AI Dispatch Summaries")

        if "Summary" in df.columns:
            for idx, row in df.iterrows():
                raw_summary = row["Summary"]

                # UI Clean up: Swap the ugly "Pending" string for a clean loading state
                if "Pending AI analysis" in raw_summary:
                    formatted_summary = "⏳ *Analysis queued. Refreshing on next automated cycle...*"
                else:
                    formatted_summary = raw_summary

                # Render clean cards instead of technical blocks
                st.markdown(f"**{row.get('Time', 'N/A')} — {row.get('Type', 'Incident')}**")
                st.markdown(formatted_summary)
                st.markdown(" ", unsafe_allow_html=True)
        else:
            st.info("System is initializing dispatch text parsing...")
else:
    st.info("🛰️ Connecting to live CHP feed. Map and logs will populate automatically as data streams in.")
