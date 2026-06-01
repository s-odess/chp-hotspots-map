import streamlit as st
import pandas as pd
import json
import os

# Set a wide, professional dashboard layout
st.set_page_config(layout="wide", page_title="California Highway Live Telemetry")

st.title("🚨 Live Highway Incident Telemetry")
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

# 2. Pre-process and clean data strictly for mapping
map_df = pd.DataFrame()
if not df.empty and "Latitude" in df.columns and "Longitude" in df.columns:
    # Create clean copy containing only valid geographical coordinate matrices
    map_df = df.copy()
    
    # Force coordinates to stick to strict floating-point numbers
    map_df['latitude'] = pd.to_numeric(map_df['Latitude'], errors='coerce')
    map_df['longitude'] = pd.to_numeric(map_df['Longitude'], errors='coerce')
    
    # Drop rows that are missing coordinate values or are zero positions
    map_df = map_df.dropna(subset=['latitude', 'longitude'])
    map_df = map_df[(map_df['latitude'] != 0) & (map_df['longitude'] != 0)]

# Create our side-by-side executive column layout
col1, col2 = st.columns([3, 2])

# ==========================================
# COLUMN 1: THE GEOSPATIAL MAP LAYER
# ==========================================
with col1:
    st.markdown("### 🗺️ Geographic Hotspots")
    if not map_df.empty:
        # Streamlit perfectly renders map data objects when explicitly fed lowercase column handles
        st.map(map_df[['latitude', 'longitude']], zoom=5)
    else:
        st.info("No active geo-coordinates available in this frame.")

# ==========================================
# COLUMN 2: THE LIVE NEWS TICKER (No drill-downs!)
# ==========================================
with col2:
    st.markdown("### 📰 Live Dispatch Narratives")
    
    if not df.empty:
        # Reverse the list so the newest incidents appear at the top of the feed
        for index, row in df.iloc[::-1].iterrows():
            summary_text = row.get("Summary", "Processing AI telemetry analysis...")
            
            # Keep layout clean if item is queued for quota reset
            if str(summary_text).startswith("Error:"):
                summary_text = "🔄 Queued for next scheduled AI translation cycle."
                
            # DATA MATCH PATCH: Extract variables using keys matching the scraping engine
            incident_id = row.get("Incident_No", "Unknown ID")
            raw_type = row.get("Type", "Traffic Event")
            log_time = row.get("Time", "Recent")

            # Render an independent visual container card for every single narrative
            with st.container(border=True):
                st.markdown(f"**📍 Incident Log #{incident_id}**")
                st.caption(f"⏱️ {log_time} | Raw Code: {raw_type}")
                st.info(summary_text)
    else:
        st.info("Waiting for incoming traffic stream logs...")