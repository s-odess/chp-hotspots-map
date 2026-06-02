import streamlit as st
import pandas as pd
import requests

# 1. Set full viewport layout configuration
st.set_page_config(page_title="CHP Live Hotspots", layout="wide")
st.title("CHP Live Telemetry Map")

# !!! REPLACE 'YOUR_USERNAME' WITH YOUR ACTUAL GITHUB USERNAME !!!
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def get_clean_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            
            # Coerce coordinates into numeric formats, turning errors into NaNs
            df['lat'] = pd.to_numeric(df['Latitude'], errors='coerce')
            df['lon'] = pd.to_numeric(df['Longitude'], errors='coerce')
            
            # Drop rows missing coordinates completely
            df = df.dropna(subset=['lat', 'lon'])
            
            # Cursor Fix: Clear out pandas index to normalize rendering coordinates
            df = df.reset_index(drop=True)
            return df
        return None
    except Exception:
        return None

# Fetch data payload
df = get_clean_data()

if df is not None and not df.empty:
    # Cursor Fix #1: Render map completely outside layout columns to prevent pixel-collapsing
    # Cursor Fix #2: Map using explicit coordinate column parameters and an locked height
    st.map(df, latitude='lat', longitude='lon', height=500)
    
    st.markdown("---")
    
    # Structural separation layout wrapper below the map element
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Current Dispatch Feed")
        
        # Cursor Defensive Safety: Only attempt to render columns that exist in the payload
        feed_cols = [c for c in ("Incident_No", "Time", "Type") if c in df.columns]
        
        # Strict Sizing Fix: Explicitly use width='stretch' to expand across container
        # Completely avoids the broken 'width=None' input or deprecated container arguments
        st.dataframe(df[feed_cols] if feed_cols else df, width='stretch', hide_index=True)
        
    with col2:
        st.subheader("Incident Summaries")
        # Check if Summary column exists before running row loops
        if 'Summary' in df.columns:
            for idx, row in df.iterrows():
                st.write(f"**{row.get('Time', 'N/A')} - {row.get('Type', 'Incident')}:** {row['Summary']}")
        else:
            st.info("Detailed narratives are currently parsing...")
else:
    st.warning("Data pipeline active. Waiting for clean coordinate data from the scraping engine...")
