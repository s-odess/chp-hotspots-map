import streamlit as st
import pandas as pd
import requests

# 1. Set a clean page layout with a professional icon
st.set_page_config(page_title="CHP Live Dispatch Tracker", page_icon="🚨", layout="wide")

st.title("🚨 California Highway Patrol Live Telemetry")
st.caption("Real-time incident mapping and automated dispatch narratives.")

# !!! REPLACE WITH YOUR ACTUAL GITHUB USERNAME !!!
raw_url = "https://raw.githubusercontent.com/YOUR_USERNAME/chp-hotspots-map/main/live_hotspots.json"

@st.cache_data(ttl=60)
def load_dashboard_data():
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            
            # Normalize coordinates cleanly
            df['lat'] = pd.to_numeric(df['Latitude'], errors='coerce')
            df['lon'] = pd.to_numeric(df['Longitude'], errors='coerce')
            
            # Filter out broken rows silently
            df = df.dropna(subset=['lat', 'lon'])
            return df.reset_index(drop=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = load_dashboard_data()

if not df.empty:
    # 2. THE MAP: Strip away PyDeck complexity. 
    # We feed st.map ONLY the coordinates so it cannot get confused or look blank.
    st.map(df[['lat', 'lon']], height=500)
    
    st.markdown("---")
    
    # 3. DASHBOARD FEED LAYOUT
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("📋 Active Incident Log")
        display_cols = [c for c in ("Incident_No", "Time", "Type") if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df, width='stretch', hide_index=True)
        
    with col2:
        st.subheader("🤖 AI Dispatch Summaries")
        
        if 'Summary' in df.columns:
            for idx, row in df.iterrows():
                raw_summary = row['Summary']
                
                # UI Clean up: Swap the ugly "Pending" string for a clean loading state
                if "Pending AI analysis" in raw_summary:
                    formatted_summary = "⏳ *Analysis queued. Refreshing on next automated cycle...*"
                else:
                    formatted_summary = raw_summary
                
                # Render clean cards instead of technical blocks
                st.markdown(f"**{row.get('Time', 'N/A')} — {row.get('Type', 'Incident')}**")
                st.markdown(formatted_summary)
                st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info("System is initializing dispatch text parsing...")
else:
    st.info("🛰️ Connecting to live CHP feed. Map and logs will populate automatically as data streams in.")
