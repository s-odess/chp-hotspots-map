import streamlit as st
import pandas as pd
import requests

# Set page configuration
st.set_page_config(page_title="CHP Live Hotspots", layout="wide")

st.title("CHP Live Telemetry Map")
st.subheader("Real-time Incident Tracking")

# REPLACE 'YOUR_USERNAME' WITH YOUR ACTUAL GITHUB USERNAME
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def get_latest_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

# Load the data
data = get_latest_data()

if data:
    df = pd.DataFrame(data)
    
    # 1. Clean data
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # 2. Rename for Streamlit map
    df = df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    
    # 3. Render the Map
    st.map(df)
    
    # 4. FIXED: Use width='stretch' instead of use_container_width=True
    st.subheader("Current Dispatch Feed")
    st.dataframe(df[['Incident_No', 'Time', 'Type', 'Summary']])
    # Note: If width=None, it defaults to auto-sizing. 
    # Use width='stretch' if you want it to fill the screen.
else:
    st.warning("Data is currently syncing. Please wait...")
