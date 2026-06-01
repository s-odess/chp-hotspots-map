import streamlit as st
import pandas as pd
import json
import os

# Set a wide, professional dashboard layout
st.set_page_config(layout="wide", page_title="California Freeway Live Telemetry")

st.title("🚨 Live Freeway Incident Telemetry")
st.subheader("Real-time automated traffic narrative & dispatcher logs")

FILE_PATH = "live_hotspots.json"

# 1. Load the live production dataset
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

# 2. Pre-process and clean data for mapping
# Filter out rows missing geographic coordinates
map_df = df.dropna(subset=['Latitude', 'Longitude']).copy()
map_df['Latitude'] = pd.to_numeric(map_df['Latitude'], errors='coerce')
map_df['Longitude'] = pd.to_numeric(map_df['Longitude'], errors='coerce')
map_df = map_df.dropna(subset=['Latitude', 'Longitude'])

# Create our side-by-side executive column layout
col1, col2 = st.columns([3, 2])

# ==========================================
# COLUMN 1: THE GEOSPATIAL MAP LAYER
# ==========================================
with col1:
    st.markdown("### 🗺️ Geographic Hotspots")
    if not map_df.empty:
        # Streamlit's native interactive map
        st.map(map_df, latitude="Latitude", longitude="Longitude", zoom=6)
    else:
        st.info("No active geo-coordinates available in this frame.")

# ==========================================
# COLUMN 2: THE LIVE NEWS TICKER (No drill-downs!)
# ==========================================
with col2:
    st.markdown("### 📰 Live Dispatch Narratives")
    
    # Reverse the list so the newest incidents appear at the top of the feed
    for index, row in df.iloc[::-1].iterrows():
        # Fetch the narrative summary, fall back gracefully if it hasn't generated yet
        summary_text = row.get("Summary", "Processing AI telemetry analysis...")
        
        # Determine if it's an error string, keep UI clean if so
        if str(summary_text).startswith("Error:"):
            summary_text = "🔄 Queued for next reporting cycle."
            
        # Get basic descriptive data points to frame the card header
        location = row.get("Location", "Unknown Location")
        raw_type = row.get("Incident Type", "Traffic Event")
        log_time = row.get("Time", "Recent")

        # Render a clean, stylized visual container card for every single narrative
        with st.container(border=True):
            st.markdown(f"**📍 {location}**")
            st.caption(f"⏱️ {log_time} | Raw Code: {raw_type}")
            
            # Highlight the AI translated narrative text so it jumps out immediately
            st.info(summary_text)