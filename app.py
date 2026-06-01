import streamlit as st
import pandas as pd
import requests

# Set page config
st.set_page_config(page_title="CHP Live Hotspots", layout="wide")

st.title("CHP Live Telemetry Map")

# The URL to the raw JSON file on GitHub
# REPLACE 'YOUR_USERNAME' WITH YOUR ACTUAL GITHUB USERNAME
raw_url = "https://raw.githubusercontent.com/s-odess/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=300)  # Cache for 5 minutes, then refresh
def get_latest_data():
    try:
        response = requests.get(raw_url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch data. Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Load the data
data = get_latest_data()

if data:
    df = pd.DataFrame(data)
    
    # Ensure coordinates are numeric
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    
    # Drop rows where coordinates could not be parsed
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # Display the map
    st.map(df)
    
    # Display the raw data table
    st.subheader("Recent Incident Feed")
    st.dataframe(df)
else:
    st.warning("No data available yet. Please check the Pipeline Status on GitHub.")
