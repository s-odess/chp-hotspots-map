from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from google import genai
import json
import re
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.txt")

# Initialize the new Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CHP_TRAFFIC_URL = "https://cad.chp.ca.gov/Traffic.aspx"
FILE_PATH = "live_hotspots.json"

def translate_log_with_gemini(raw_text):
    """Passes the raw dispatch log to Gemini for natural language translation."""
    if not raw_text or raw_text == "Log details unavailable.":
        return "No dispatch data available to summarize."
    
    prompt = f"""
    You are a logistics and telemetry expert. Translate this raw California Highway Patrol 
    dispatch log into a clear, one-sentence summary of the current situation. 
    Remove all police jargon and timestamps. 
    
    Raw Log: {raw_text}
    """
    try:
        # Updated syntax for the new google-genai package
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"AI Translation Error: {e}"

def extract_field_by_label(soup, label_regex):
    """Resiliently extracts tabular values adjacent to text labels on the detail page."""
    for element in soup.find_all(["td", "th", "span", "b", "div"]):
        text = element.get_text(strip=True)
        if re.search(label_regex, text, re.I):
            sibling = element.find_next_sibling(["td", "th"])
            if sibling:
                return " ".join(sibling.get_text(" ", strip=True).split())
            parent_cell = element if element.name in ["td", "th"] else element.find_parent(["td", "th"])
            if parent_cell:
                sibling_cell = parent_cell.find_next_sibling(["td", "th"])
                if sibling_cell:
                    return " ".join(sibling_cell.get_text(" ", strip=True).split())
    return "Unknown"

print("==================================================")
print("[*] INITIATING CHP TELEMETRY & AI PIPELINE [*]")
print("==================================================")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = context.new_page()
    
    print("\n[1] Navigating to CHP CAD system...")
    page.goto(CHP_TRAFFIC_URL, wait_until="networkidle", timeout=30000)
    
    print("[2] Engaging Hot Spots view...")
    page.locator("select[name='ddlSearches']").select_option(value="2")
    page.locator("input[name='btnSearchGo']").click()
    
    page.wait_for_selector("table#gvIncidents", state="visible", timeout=15000)
    
    row_count = page.locator("table#gvIncidents td a:has-text('Details')").count()
    demo_limit = min(3, row_count)
    print(f"[3] Found active incidents. Extracting and translating top {demo_limit}...\n")

    processed_data = []

    for i in range(demo_limit):
        print(f" -> Processing incident row {i+1}/{demo_limit}...")
        
        # Dynamically locate the link row directly on each pass
        detail_link = page.locator("table#gvIncidents td a:has-text('Details')").nth(i)
        
        try:
            # Standard click, same-tab navigation
            detail_link.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1.5) 
            
            detail_soup = BeautifulSoup(page.content(), "html.parser")
            
            incident_no = extract_field_by_label(detail_soup, r"Incident No")
            location = extract_field_by_label(detail_soup, r"\b(Location|Loc\.?|Area)\b")
            
            lat, lng = "Unknown", "Unknown"
            for link_element in detail_soup.find_all("a"):
                coord_match = re.match(r"^(-?\d+\.\d+)\s+(-?\d+\.\d+)$", link_element.get_text(strip=True))
                if coord_match:
                    lat, lng = coord_match.group(1), coord_match.group(2)
                    break
            
            detail_table = detail_soup.find("table", {"id": "gvIncidentDetails"})
            if detail_table:
                log_lines = []
                for row in detail_table.find_all("tr"):
                    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                    line_text = " ".join(cells).strip()
                    if line_text:
                        log_lines.append(line_text)
                raw_details = " | ".join(log_lines)
            else:
                raw_details = "Log details unavailable."
            
            print(f"--- INCIDENT: {incident_no} ---")
            print(f"LOCATION: {location} (Lat: {lat}, Lng: {lng})")
            print(f"RAW LOG:  {raw_details[:120]}...")
            
            print(">> Triggering AI Translation...")
            summary = translate_log_with_gemini(raw_details)
            print(f"AI SUMMARY: {summary}\n")
            
            processed_data.append({
                "Incident_No": incident_no,
                "Location": location,
                "Latitude": lat,
                "Longitude": lng,
                "Raw_Details": raw_details,
                "AI_Summary": summary
            })
            
            # Navigate back to the index view and wait for the grid to reload
            page.go_back()
            page.wait_for_load_state("networkidle")
            page.wait_for_selector("table#gvIncidents", state="visible", timeout=15000)
            
        except Exception as row_err:
            print(f"    [!] Error extracting data on row {i+1}: {row_err}")
            # Ensure we get back to the main page even if extraction fails
            page.goto(CHP_TRAFFIC_URL)
            page.locator("select[name='ddlSearches']").select_option(value="2")
            page.locator("input[name='btnSearchGo']").click()
            page.wait_for_selector("table#gvIncidents", state="visible")
            continue

    browser.close()

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(processed_data, f, indent=4)

print("==================================================")
print(f"[+] PIPELINE COMPLETE. Data saved to {FILE_PATH}")
print("==================================================")