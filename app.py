import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="CHP Live Hotspots", layout="wide")
st.title("CHP Live Telemetry Map")

# Update with your actual GitHub username
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def get_clean_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            
            # Clean and isolate coordinates
            df['lat'] = pd.to_numeric(df['Latitude'], errors='coerce')
            df['lon'] = pd.to_numeric(df['Longitude'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            
            # Cursor Fix #1: Clear the internal pandas index to prevent mapping drops
            df = df.reset_index(drop=True)
            return df
        return None
    except Exception:
        return None

df = get_clean_data()

if df is not None and not df.empty:
    # Cursor Fix #2: Map is placed completely outside columns at the top level
    # Cursor Fix #3: Explicitly define parameters and set a locked height
    st.map(df, latitude='lat', longitude='lon', height=500)
    
    st.markdown("---")
    
    # Place your table and text side-by-side BELOW the full-width map
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Current Dispatch Feed")
        st.dataframe(df[['Incident_No', 'Time', 'Type']], width=None)
        
    with col2:
        st.subheader("Incident Summaries")
        for idx, row in df.iterrows():
            st.write(f"**{row['Time']} - {row['Type']}:** {row['Summary']}")
else:
    st.warning("Data pipeline active. Waiting for clean coordinate data from the scraper...")
