import json
import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CHP Live Dispatch Tracker", page_icon="🚨", layout="wide")

st.title("🚨 California Highway Patrol Live Telemetry")
st.caption("Real-time incident mapping and automated dispatch narratives.")

# !!! REPLACE WITH YOUR ACTUAL GITHUB USERNAME !!!
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"
LOCAL_JSON = "live_hotspots.json"


def standardize_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    """
    live_hotspots.json uses 'Latitude' and 'Longitude' (strings).
    Force lowercase 'lat' / 'lon' for Streamlit's map.
    """
    df = frame.copy()

    if "Latitude" in df.columns:
        df["lat"] = pd.to_numeric(df["Latitude"], errors="coerce")
    elif "latitude" in df.columns:
        df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    elif "lat" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")

    if "Longitude" in df.columns:
        df["lon"] = pd.to_numeric(df["Longitude"], errors="coerce")
    elif "longitude" in df.columns:
        df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    elif "lon" in df.columns:
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    return df


def _fetch_records() -> list:
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

    df = standardize_coordinates(df)
    df = df.dropna(subset=["lat", "lon"])
    return df.reset_index(drop=True)


df = load_dashboard_data()

if not df.empty:
    st.map(df, height=500)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📋 Active Incident Log")
        display_cols = [c for c in ("Incident_No", "Time", "Type") if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df, width="stretch", hide_index=True)

    with col2:
        st.subheader("🤖 AI Dispatch Summaries")

        if "Summary" in df.columns:
            for _, row in df.iterrows():
                raw_summary = row["Summary"]

                if "Pending AI analysis" in raw_summary:
                    formatted_summary = "⏳ *Analysis queued. Refreshing on next automated cycle...*"
                else:
                    formatted_summary = raw_summary

                st.markdown(f"**{row.get('Time', 'N/A')} — {row.get('Type', 'Incident')}**")
                st.markdown(formatted_summary)
                st.markdown(" ", unsafe_allow_html=True)
        else:
            st.info("System is initializing dispatch text parsing...")
else:
    st.info("🛰️ Connecting to live CHP feed. Map and logs will populate automatically as data streams in.")
