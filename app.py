import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="CHP Live", layout="wide")
st.title("CHP Live Telemetry Map")

# 1. Update this to your ACTUAL repo URL
# Ensure this file is public in your GitHub repository
raw_url = "https://raw.githubusercontent.com/YOUR_USERNAME/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def get_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: Received status code {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

data = get_data()

if isinstance(data, str):
    st.error(f"Failed to load data: {data}")
    st.write("Check if your JSON file is public and the URL is correct.")
elif data:
    df = pd.DataFrame(data)
    
    # 2. Convert and Clean
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # 3. Rename columns for map
    df = df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    
    # 4. Simple rendering (NO width arguments to avoid crashes)
    st.map(df)
    st.dataframe(df[['Incident_No', 'Time', 'Type', 'Summary']])
else:
    st.warning("No data found in JSON file.")
