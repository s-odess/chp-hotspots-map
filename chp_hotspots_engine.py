from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import re

url = "https://cad.chp.ca.gov/Traffic.aspx"

print("[1] Initializing production telemetry and deep log engine...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
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
        
        # Pull initial high-level table rows snapshot out before jumping contexts
        grid_soup = BeautifulSoup(page.content(), 'html.parser')
        main_table = grid_soup.find('table', {'id': 'gvIncidents'})
        grid_rows = main_table.find_all('tr') if main_table else []
        
        link_count = len(grid_rows) - 1 if grid_rows else 0
        print(f"[+] Found {link_count} drill-down profiles to extract.")
        
        # Pre-parse and cache baseline row features from the master table
        cached_grid_data = []
        if grid_rows:
            headers = [th.text.strip() for th in grid_rows[0].find_all('th')]
            for row in grid_rows[1:]:
                cols = [td.text.strip() for td in row.find_all('td')]
                cached_grid_data.append(dict(zip(headers, cols)))
        
        all_deep_incidents = []
        
        # Sequentially navigate back and forth to enrich each record profile
        for i in range(link_count):
            print(f" -> Transitioning into view profile {i+1}/{link_count}...")
            
            # Target the details link element dynamically to avoid stale context
            current_links = page.locator("table#gvIncidents td a:has-text('Details')")
            current_links.nth(i).click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(1.5) # Wait for the WebForm AJAX layout update to complete paint
            
            page_soup = BeautifulSoup(page.content(), 'html.parser')
            
            # --- TELEMETRY EXTRACTION LAYER ---
            latitude = "Unknown"
            longitude = "Unknown"
            
            # Find all anchor tags to match coordinate labels in link text strings
            anchors = page_soup.find_all('a')
            for anchor in anchors:
                text_content = anchor.text.strip()
                # Pattern matches standard floating numbers split by spaces (e.g. 34.2214 -117.0425)
                coord_match = re.match(r'^(-?\d+\.\d+)\s+(-?\d+\.\d+)$', text_content)
                if coord_match:
                    latitude = coord_match.group(1)
                    longitude = coord_match.group(2)
                    break
            
            # --- DETAILED NARRATIVE LOG CAPTURE ---
            # Extract everything written inside the updated form panel view context
            full_text = page_soup.get_text()
            clean_log_dump = " ".join(full_text.split())
            
            # Retrieve cached master list row features and append enriched data metrics
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
            print(f"    [✔] Successfully parsed data. Telemetry Coordinates: Lat={latitude}, Lng={longitude}")
            
            # --- VIEW STATE REVERT LOOP ---
            print(" -> Reverting page state back to master grid view...")
            page.go_back()
            page.wait_for_selector("table#gvIncidents", state="visible", timeout=10000)
            time.sleep(0.5)
            
        print("\n========================================================")
        print("[SUCCESS] COMPREHENSIVE PIPELINE DATA EXPORT COMPLETED")
        print("========================================================\n")
        
        with open("live_hotspots.json", "w", encoding="utf-8") as json_f:
            json.dump(all_deep_incidents, json_f, indent=4)
        print("Production asset data pipeline stream saved cleanly to 'live_hotspots.json'")
        
    except Exception as e:
        print(f"\n[-] Navigation loop exception encountered: {e}")
        page.screenshot(path="pipeline_loop_failure.png")
        
    print("\nClosing browser profile...")
    browser.close()