import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

# Set page configuration
st.set_page_config(
    page_title="CHP Live Hotspots Map",
    page_icon="🚓",
    layout="wide"
)

st.title("🚓 California Highway Patrol Live Dispatch Hotspots")
st.markdown("Real-time cluster analysis of CHP dispatch traffic and high-activity zones.")

# --- Data Loading with Defensive Fallback ---
hotspots_data = []
file_exists = os.path.exists("live_hotspots.json")

if file_exists:
    try:
        with open("live_hotspots.json", "r", encoding="utf-8") as f:
            hotspots_data = json.load(f)
    except Exception as e:
        st.error(f"Error reading data file: {e}")
else:
    st.info("📡 No live data file found (`live_hotspots.json`). Displaying base map fallback.")

# --- Metrics Dashboard Section ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Active Hotspots", value=len(hotspots_data))
with col2:
    status_indicator = "Online" if file_exists else "Waiting for Data"
    st.metric(label="Data Pipeline Status", value=status_indicator)
with col3:
    # Safely extract time from the data array
    last_update = "N/A"
    if hotspots_data and isinstance(hotspots_data, list) and len(hotspots_data) > 0:
        last_update = hotspots_data[0].get("Time", "N/A")
    st.metric(label="Last Pipeline Run", value=last_update)

st.write("---")

# Render map base focused on California
CA_CENTER = [36.7783, -119.4179]
m = folium.Map(location=CA_CENTER, zoom_start=6, tiles="CartoDB positron")

# Populate map if data is available
if hotspots_data and isinstance(hotspots_data, list):
    for hotspot in hotspots_data:
        # Match capital keys produced by chp_hotspots_engine.py
        if "Latitude" in hotspot and "Longitude" in hotspot:
            try:
                # Handle cases where value is "Unknown"
                if hotspot["Latitude"] == "Unknown" or hotspot["Longitude"] == "Unknown":
                    continue
                    
                lat = float(hotspot["Latitude"])
                lon = float(hotspot["Longitude"])
                location_name = hotspot.get("Location_Short", "Unknown Location")
                incident_type = hotspot.get("Type", "Unknown Incident")
                
                # Check for AI summary field, fall back smoothly if agent.py hasn't parsed it yet
                description = hotspot.get("AI_Summary", "Processing live dispatch telemetry...")
                
                # Create popup text layout
                popup_text = f"""
                <b>Location:</b> {location_name}<br>
                <b>Type:</b> {incident_type}<br>
                <b>AI Analysis:</b> {description}
                """
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=15,
                    popup=folium.Popup(popup_text, max_width=300),
                    color="crimson",
                    fill=True,
                    fill_color="crimson",
                    fill_opacity=0.6
                ).add_to(m)
            except (ValueError, TypeError):
                continue

# Render object frame
st_folium(m, width=None, height=550, use_container_width=True)