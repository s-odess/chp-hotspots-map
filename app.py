import streamlit as st
import pandas as pd
import json
import os

# Set a wide, professional layout to support columns
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

# 2. Pre-process and clean data for mapping
if "Latitude" in df.columns and "Longitude" in df.columns:
    map_df = df.copy()
    # Force coordinates to numeric decimals, converting errors or "Unknowns" into NaN
    map_df['Latitude'] = pd.to_numeric(map_df['Latitude'], errors='coerce')
    map_df['Longitude'] = pd.to_numeric(map_df['Longitude'], errors='coerce')
    
    # Drop rows that do not have valid GPS numbers
    map_df = map_df.dropna(subset=['Latitude', 'Longitude'])
else:
    map_df = pd.DataFrame(columns=['Latitude', 'Longitude'])

# Create our side-by-side layout (60% Map, 40% News Feed)
col1, col2 = st.columns([3, 2])

# ==========================================
# COLUMN 1: THE GEOSPATIAL MAP LAYER
# ==========================================
with col1:
    st.markdown("### 🗺️ Geographic Hotspots")
    if not map_df.empty:
        # Explicit column parameters override Streamlit's default lowercase strictness
        st.map(
            map_df, 
            latitude="Latitude", 
            longitude="Longitude", 
            zoom=6
        )
    else:
        st.info("No active geo-coordinates available in this frame.")

# ==========================================
# COLUMN 2: THE LIVE NEWS TICKER (No drill-downs!)
# ==========================================
with col2:
    st.markdown("### 📰 Live Dispatch Narratives")
    
    # Reverse the order so the newest items show up at the top
    for index, row in df.iloc[::-1].iterrows():
        # Handle empty/missing summary text gracefully
        summary_text = row.get("Summary", "Processing AI telemetry analysis...")
        
        # If the item currently holds an old execution error string, present it cleanly
        if str(summary_text).startswith("Error:"):
            summary_text = "🔄 Queued for next scheduled AI translation cycle."
            
        location = row.get("Location", "Unknown Location")
        raw_type = row.get("Incident Type", "Traffic Event")
        log_time = row.get("Time", "Recent")

        # Build an independent visual container block for each narrative card
        with st.container(border=True):
            st.markdown(f"**📍 {location}**")
            st.caption(f"⏱️ {log_time} | Raw Code: {raw_type}")
            
            # Use the info banner styling to expose the clean narrative text instantly
            st.info(summary_text)