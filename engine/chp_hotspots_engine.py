from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import re
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv(".env.txt")

url = "https://cad.chp.ca.gov/Traffic.aspx"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
FILE_PATH = "live_hotspots.json"

LOCATION_GRID_KEYS = ("Location", "location", "Loc.", "Loc", "Area")


def push_to_github(data_list):
    """Securely commits and pushes data straight to the GitHub repository API."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: GITHUB_TOKEN or GITHUB_REPO not found.")
        return

    print("[*] Initiating secure postback sync to GitHub API...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    json_content = json.dumps(data_list, indent=4)
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

    sha = None
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get("sha")

    payload = {
        "message": "Pipeline Auto-Update: Refreshing live dispatch hotspots telemetry",
        "content": encoded_content,
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("[SUCCESS] GitHub cloud sync complete!")
    else:
        print(f"[-] Cloud sync failed: {put_response.status_code} - {put_response.text}")


def location_from_grid(row_data: dict) -> str:
    """Read text location from the Hot Spots grid row (header names vary)."""
    for key in LOCATION_GRID_KEYS:
        if key not in row_data:
            continue
        val = " ".join(str(row_data[key]).split()).strip()
        if val and val.lower() not in ("unknown", "n/a", "details", ""):
            return val
    return "Unknown"


def location_from_detail_page(soup: BeautifulSoup, row_data: dict) -> str:
    """Prefer detail-page Location label; fall back to grid column."""
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True).lower()
        if "location" in label:
            val = cells[1].get_text(" ", strip=True)
            if val and val.lower() not in ("unknown", "n/a"):
                return val

    for tag in soup.find_all(["span", "label", "b", "strong"]):
        label_text = tag.get_text(strip=True).lower()
        if label_text in ("location", "location:"):
            sibling = tag.find_next(["span", "td", "div"])
            if sibling:
                val = sibling.get_text(" ", strip=True)
                if val and val.lower() not in ("unknown", "n/a"):
                    return val

    body = soup.get_text("\n")
    match = re.search(r"Location\s*:?\s*(.+?)(?:\n|$)", body, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val and len(val) > 2 and val.lower() not in ("unknown", "n/a"):
            return val

    return location_from_grid(row_data)


print("[1] Initializing production telemetry engine...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    print(f"[2] Connecting to dashboard: {url}")
    page.goto(url, wait_until="networkidle")

    print("[3] Waiting for UI layout...")
    dropdown = page.locator("select[name='ddlSearches']")
    dropdown.wait_for(state="visible")

    print("[4] Modifying view state to 'Hot Spots'...")
    dropdown.select_option(value="2")
    page.locator("input[name='btnSearchGo']").click()

    print("[5] Synchronizing baseline data grid...")
    page.wait_for_selector("table#gvIncidents", state="visible")
    page.wait_for_load_state("networkidle")

    grid_soup = BeautifulSoup(page.content(), "html.parser")
    main_table = grid_soup.find("table", {"id": "gvIncidents"})

    header_row = main_table.find_all("tr")[0]
    headers = [th.text.strip() for th in header_row.find_all("th")]
    print(f"[+] Grid columns: {headers}")

    grid_rows = main_table.find_all("tr")[1:] if main_table else []

    cached_grid_data = []
    for row in grid_rows:
        cols = [td.text.strip() for td in row.find_all("td")]
        cached_grid_data.append(dict(zip(headers, cols)))

    all_deep_incidents = []

    for i in range(len(grid_rows)):
        print(f" -> Extracting profile {i+1}/{len(grid_rows)}...")
        row_data = cached_grid_data[i]

        page.locator("table#gvIncidents td a:has-text('Details')").nth(i).click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        page_soup = BeautifulSoup(page.content(), "html.parser")

        lat, lng = "Unknown", "Unknown"
        for anchor in page_soup.find_all("a"):
            coord_match = re.match(r"^(-?\d+\.\d+)\s+(-?\d+\.\d+)$", anchor.text.strip())
            if coord_match:
                lat, lng = coord_match.group(1), coord_match.group(2)
                break

        location = location_from_detail_page(page_soup, row_data)
        print(f"    Location: {location[:80]}{'...' if len(location) > 80 else ''}")

        all_deep_incidents.append({
            "Incident_No": row_data.get("No.", "Unknown"),
            "Time": row_data.get("Time", "Unknown"),
            "Type": row_data.get("Type", "Unknown"),
            "Location": location,
            "Latitude": lat,
            "Longitude": lng,
            "Summary": "Pending AI analysis...",
        })

        page.go_back()

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(all_deep_incidents, f, indent=4)
print(f"[+] Wrote {len(all_deep_incidents)} records to {FILE_PATH}")
push_to_github(all_deep_incidents)
