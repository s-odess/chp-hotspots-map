import streamlit as st
import pandas as pd
import requests

# Set page configuration
st.set_page_config(page_title="CHP Live Hotspots", layout="wide")

st.title("CHP Live Telemetry Map")
st.subheader("Real-time Incident Tracking")

# The URL to the raw JSON file on GitHub
# REPLACE 'YOUR_USERNAME' WITH YOUR ACTUAL GITHUB USERNAME
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)  # Refresh data every 60 seconds
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
    
    # 1. Clean and prepare data
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # 2. Rename columns for Streamlit map compatibility
    # Streamlit requires 'lat' and 'lon' columns to render the map
    df = df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    
    # 3. Render the Map
    st.map(df)
    
    # 4. Display the Data Table
    st.subheader("Current Dispatch Feed")
    st.dataframe(df[['Incident_No', 'Time', 'Type', 'Summary']], use_container_width=True)
else:
    st.warning("Data is currently syncing from the CHP engine. Please wait a moment...")
