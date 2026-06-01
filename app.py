import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="CHP Live Hotspots", layout="wide")
st.title("CHP Live Telemetry Map")

raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def get_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

data = get_data()

if data:
    df = pd.DataFrame(data)
    
    # 1. Force data into numeric format (replace errors with NaN)
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    
    # 2. Drop any rows where lat/lon could not be converted
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # 3. Rename columns exactly as st.map() expects
    df = df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    
    # 4. Final verification: Check if there is data left
    if not df.empty:
        st.map(df)
        st.subheader("Current Dispatch Feed")
        st.dataframe(df[['Incident_No', 'Time', 'Type', 'Summary']])
    else:
        st.error("Data loaded, but no valid Latitude/Longitude coordinates found to map.")
else:
    st.warning("Data is currently loading or empty.")
