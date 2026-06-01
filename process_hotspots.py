from bs4 import BeautifulSoup
import json
import os
import base64
import requests
from dotenv import load_dotenv

# Load environment variables from our secure local file
load_dotenv(".env.txt")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # format: "username/repo-name"
FILE_PATH = "live_hotspots.json"

def push_to_github(data_list):
    """Automatically commits and pushes live_hotspots.json to GitHub API."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping GitHub Sync: GITHUB_TOKEN or GITHUB_REPO not found in environment.")
        return

    print("[*] Initiating secure postback sync to GitHub...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Convert our fresh data to formatted JSON text
    json_content = json.dumps(data_list, indent=4)
    # GitHub requires file contents to be base64 encoded
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

    # Step A: Check if the file already exists on GitHub to get its 'sha' fingerprint
    sha = None
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get("sha")

    # Step B: Prepare payload for the commit
    payload = {
        "message": "🔄 Pipeline Auto-Update: Refreshing live dispatch hotspots",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha  # Required if updating an existing file

    # Step C: Send the commit to GitHub
    put_response = requests.put(url, headers=headers, json=payload)
    
    if put_response.status_code in [200, 201]:
        print("[🚀] GitHub sync complete! Streamlit map will refresh momentarily.")
    else:
        print(f"[-] GitHub sync failed: {put_response.status_code} - {put_response.text}")


# --- Original Parsing Logic ---
print("[*] Opening local data payload: live_hotspots_data.html...")
try:
    with open("live_hotspots_data.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(f"<table>{html_content}</table>", 'html.parser')
    rows = soup.find_all('tr')

    if not rows:
        print("[-] Error: No data rows found inside the file.")
        exit()

    headers = [th.text.strip() for th in rows[0].find_all('th')]
    
    incidents = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) == len(headers):
            incident_data = {}
            for header, col in zip(headers, cols):
                clean_value = " ".join(col.text.split())
                incident_data[header] = clean_value
            incidents.append(incident_data)

    print(f"[+] Successfully structured {len(incidents)} live incident records.")

    # Save locally first
    with open(FILE_PATH, "w", encoding="utf-8") as json_f:
        json.dump(incidents, json_f, indent=4)
    print(f"[🎉] JSON Pipeline complete. File written to '{FILE_PATH}'")
    
    if incidents:
        print("\n[ Sample Structured Record ]")
        print(json.dumps(incidents[0], indent=2))

    # --- Trigger our new cloud synchronization ---
    push_to_github(incidents)

except Exception as e:
    print(f"[-] Pipeline processing failed: {e}")