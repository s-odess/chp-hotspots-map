from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import re
import os
import base64
import requests
from dotenv import load_dotenv

# Load security environment configurations from your local text file
load_dotenv(".env.txt")

url = "https://cad.chp.ca.gov/Traffic.aspx"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
FILE_PATH = "live_hotspots.json"

def push_to_github(data_list):
    """Securely commits and pushes data straight to the GitHub repository API."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: GITHUB_TOKEN or GITHUB_REPO not found in environment configurations.")
        return

    print("[*] Initiating secure postback sync to GitHub API...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Format data and convert to base64 encoding requested by GitHub API
    json_content = json.dumps(data_list, indent=4)
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

    # Check if file exists on remote head to acquire its SHA hash fingerprint
    sha = None
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get("sha")

    payload = {
        "message": "Pipeline Auto-Update: Refreshing live dispatch hotspots telemetry",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("[SUCCESS] GitHub cloud sync complete! Streamlit map will refresh momentarily.")
    else:
        print(f"[-] Cloud sync failed: {put_response.status_code} - {put_response.text}")


print("[1] Initializing production telemetry and deep log engine...")
with sync_playwright() as p:
    # Set headless=True so the browser window runs completely invisibly in computer memory
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    
    print(f"[2] Connecting to dashboard: {url}")
    page.goto(url)
    
    print("[3] Waiting for UI dropdown layout to load...")
    dropdown_locator = page.locator("select[name='ddlSearches']")
    dropdown_locator.wait_for(state="visible")
    
    print("[4] Modifying view state to 'Hot Spots'...")
    dropdown_locator.select_option(value="2")
    time.sleep(1)
    
    search_button = page.locator("input[name='btnSearchGo']")
    print("[+] Form parameters verified. Clicking 'btnSearchGo'...")
    search_button.click()
    
    print("[5] Synchronizing baseline data grid...")
    try:
        table_locator = page.locator("table#gvIncidents")
        table_locator.wait_for(state="visible", timeout=15000)
        print("[SUCCESS] Master Incident Grid detected on screen!")
        
        grid_soup = BeautifulSoup(page.content(), 'html.parser')
        main_table = grid_soup.find('table', {'id': 'gvIncidents'})
        grid_rows = main_table.find_all('tr') if main_table else []
        
        link_count = len(grid_rows) - 1 if grid_rows else 0
        print(f"[+] Found {link_count} drill-down profiles to extract.")
        
        cached_grid_data = []
        if grid_rows:
            headers = [th.text.strip() for th in grid_rows[0].find_all('th')]
            for row in grid_rows[1:]:
                cols = [td.text.strip() for td in row.find_all('td')]
                cached_grid_data.append(dict(zip(headers, cols)))
        
        all_deep_incidents = []
        
        for i in range(link_count):
            print(f" -> Transitioning into view profile {i+1}/{link_count}...")
            
            current_links = page.locator("table#gvIncidents td a:has-text('Details')")
            current_links.nth(i).click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(1.5) 
            
            page_soup = BeautifulSoup(page.content(), 'html.parser')
            
            latitude = "Unknown"
            longitude = "Unknown"
            
            anchors = page_soup.find_all('a')
            for anchor in anchors:
                text_content = anchor.text.strip()
                coord_match = re.match(r'^(-?\d+\.\d+)\s+(-?\d+\.\d+)$', text_content)
                if coord_match:
                    latitude = coord_match.group(1)
                    longitude = coord_match.group(2)
                    break
            
            full_text = page_soup.get_text()
            clean_log_dump = " ".join(full_text.split())
            
            row_features = cached_grid_data[i] if i < len(cached_grid_data) else {}
            
            enriched_record = {
                "Incident_No": row_features.get("No.", "Unknown"),
                "Time": row_features.get("Time", "Unknown"),
                "Type": row_features.get("Type", "Unknown"),
                "Location_Short": row_features.get("Location", "Unknown"),
                "Location_Desc": row_features.get("Location Desc", "Unknown"),
                "Area": row_features.get("Area", "Unknown"),
                "Latitude": latitude,
                "Longitude": longitude,
                "Extended_Log_Details": clean_log_dump
            }
            all_deep_incidents.append(enriched_record)
            print(f"    [OK] Successfully parsed data. Telemetry Coordinates: Lat={latitude}, Lng={longitude}")
            
            print(" -> Reverting page state back to master grid view...")
            page.go_back()
            page.wait_for_selector("table#gvIncidents", state="visible", timeout=10000)
            time.sleep(0.5)
            
        print("\n========================================================")
        print("[SUCCESS] COMPREHENSIVE PIPELINE DATA EXPORT COMPLETED")
        print("========================================================\n")
        
        # Save local cache backup
        with open(FILE_PATH, "w", encoding="utf-8") as json_f:
            json.dump(all_deep_incidents, json_f, indent=4)
        print(f"Production asset data pipeline stream saved cleanly to '{FILE_PATH}'")
        
        # Securely push directly to the cloud interface via API bypass
        push_to_github(all_deep_incidents)
        
    except Exception as e:
        print(f"\n[-] Navigation loop exception encountered: {e}")
        
    print("\nClosing browser profile...")
    browser.close()