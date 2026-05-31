import streamlit as st
import json
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="CHP Incident Triage")

# Load data
with open("live_hotspots.json", "r", encoding="utf-8") as f:
    incidents = json.load(f)

st.title("🚨 Live CHP Incident Triage Center")

# Create two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📍 Geospatial View")
    m = folium.Map(location=[36.7783, -119.4179], zoom_start=6)
    
    for inc in incidents:
        if inc.get("Latitude") != "Unknown":
            # Plot the marker
            folium.CircleMarker(
                location=[float(inc.get("Latitude")), float(inc.get("Longitude"))],
                radius=10,
                color="red",
                fill=True,
                popup=f"ID: {inc.get('Incident_No')}"
            ).add_to(m)
    st_folium(m, width=600, height=500)

with col2:
    st.subheader("📰 AI-Generated News Summaries")
    for inc in incidents:
        # Use AI_Summary if it exists, otherwise fallback to Raw Logs
        summary = inc.get("AI_Summary", inc.get("Extended_Log_Details", "No details available."))
        
        with st.expander(f"INCIDENT {inc.get('Incident_No')}: {inc.get('Type')}"):
            st.markdown(f"**Location:** {inc.get('Location_Short')}")
            st.markdown(f"**Triage Report:**")
            st.write(summary)