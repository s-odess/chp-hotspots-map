from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import re
import os
import base64
import requests
from dotenv import load_dotenv

# Load security environment configurations
load_dotenv(".env.txt")

url = "https://cad.chp.ca.gov/Traffic.aspx"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
FILE_PATH = "live_hotspots.json"

def push_to_github(data_list):
    """Securely commits and pushes data straight to the GitHub repository API."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: GITHUB_TOKEN or GITHUB_REPO not found.")
        return

    print("[*] Initiating secure postback sync to GitHub API...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    json_content = json.dumps(data_list, indent=4)
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

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
        print("[SUCCESS] GitHub cloud sync complete!")
    else:
        print(f"[-] Cloud sync failed: {put_response.status_code} - {put_response.text}")

print("[1] Initializing production telemetry engine...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    
    print(f"[2] Connecting to dashboard: {url}")
    # Force wait for network idle to ensure the initial JS framework loads
    page.goto(url, wait_until="networkidle")
    
    print("[3] Waiting for UI layout...")
    dropdown = page.locator("select[name='ddlSearches']")
    dropdown.wait_for(state="visible")
    
    print("[4] Modifying view state to 'Hot Spots'...")
    dropdown.select_option(value="2")
    page.locator("input[name='btnSearchGo']").click()
    
    # CLOUD FIX: Wait specifically for the table to populate, not just exist
    print("[5] Synchronizing baseline data grid...")
    page.wait_for_selector("table#gvIncidents", state="visible")
    page.wait_for_load_state("networkidle")
    
    grid_soup = BeautifulSoup(page.content(), 'html.parser')
    main_table = grid_soup.find('table', {'id': 'gvIncidents'})
    
    grid_rows = main_table.find_all('tr')[1:] if main_table else []
    
    # HARDCODED FIX: Grab exact indexes to avoid clicking the 'Details' button (col 0)
    cached_grid_data = []
    for row in grid_rows:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) >= 4:
            cached_grid_data.append({
                "Incident_No": cols[1],
                "Time": cols[2],
                "Type": cols[3]
            })
        else:
            cached_grid_data.append({
                "Incident_No": "Unknown ID",
                "Time": "Unknown Time",
                "Type": "Unknown Type"
            })
    
    all_deep_incidents = []
    
    for i in range(len(grid_rows)):
        print(f" -> Extracting profile {i+1}/{len(grid_rows)}...")
        
        # Retrieve the pre-cached metadata for this specific row
        row_data = cached_grid_data[i]
        
        # Click the specific link for this row
        page.locator("table#gvIncidents td a:has-text('Details')").nth(i).click()
        
        # CLOUD FIX: Explicit wait for dynamic content to finish rendering
        page.wait_for_load_state("networkidle")
        time.sleep(2) 
        
        page_soup = BeautifulSoup(page.content(), 'html.parser')
        
        # Extract Coordinates
        lat, lng = "Unknown", "Unknown"
        for anchor in page_soup.find_all('a'):
            coord_match = re.match(r'^(-?\d+\.\d+)\s+(-?\d+\.\d+)$', anchor.text.strip())
            if coord_match:
                lat, lng = coord_match.group(1), coord_match.group(2)
                break
        
        # Build the final fully mapped record
        all_deep_incidents.append({
            "Incident_No": row_data.get("Incident_No", "Unknown ID"),
            "Time": row_data.get("Time", "Unknown Time"),
            "Type": row_data.get("Type", "Unknown Type"),
            "Latitude": lat,
            "Longitude": lng,
            "Summary": "Pending AI analysis..."
        })
        
        page.go_back()
        page.wait_for_selector("table#gvIncidents", state="visible")
        
    # Final data save and sync
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_deep_incidents, f, indent=4)
        
    push_to_github(all_deep_incidents)
    browser.close()
