import os
import json
import time
import base64
import requests
from dotenv import load_dotenv
from google import genai

# 1. Load security environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
FILE_PATH = "live_hotspots.json"

if not api_key:
    print("[-] Error: GEMINI_API_KEY not found in env configuration.")
    exit(1)

client = genai.Client(api_key=api_key)

# 2. Robust Data Loading Guardrail
incidents = []
if os.path.exists(FILE_PATH) and os.path.getsize(FILE_PATH) > 0:
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            incidents = json.load(f)
        print(f"[+] Successfully loaded {len(incidents)} records from {FILE_PATH}.")
    except json.JSONDecodeError:
        print(f"[!] Warning: {FILE_PATH} was corrupted or malformed. Initializing empty dataset.")
        incidents = []
else:
    print(f"[!] Warning: {FILE_PATH} not found or empty. Initializing empty dataset.")
    incidents = []

# 3. Filtering guardrail
def is_valid(incident):
    return incident.get("Latitude") != "Unknown" and incident.get("Longitude") != "Unknown"

# 4. Triage function with retry logic
def get_triage(incident, retries=3):
    prompt = f"""
    Summarize this incident for a news desk. 
    IMPORTANT: Translate all technical police codes (like 23103, 1141, etc.) into plain, understandable English (e.g., 'Reckless Driving', 'Traffic Collision').
    Keep it concise and punchy.
    Incident Data: {incident}
    """
    for attempt in range(retries):
        try:
            return client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            ).text
        except Exception as e:
            if "503" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = (attempt + 1) * 20
                print(f"[!] Server busy. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e
    return "Error: Could not summarize incident."

def push_to_github(data_list):
    """Securely commits and pushes analyzed summaries straight to GitHub."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: GITHUB_TOKEN or GITHUB_REPO not found in environment.")
        return

    print("[*] Initiating secure summary sync to GitHub API...")
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
        "message": "Pipeline Auto-Update: Enriched incident summaries synced",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("[SUCCESS] Summaries synced to GitHub! Streamlit map updating...")
    else:
        print(f"[-] Cloud sync failed: {put_response.status_code} - {put_response.text}")

# 5. Process incidents
print(f"[+] Processing records...")
analyzed_count = 0

for i, incident in enumerate(incidents):
    if "Summary" in incident:
        continue
        
    if is_valid(incident):
        print(f"[*] Triaging incident {i+1}...")
        summary = get_triage(incident)
        incident["Summary"] = summary
        analyzed_count += 1
        print(f"[+] Summary saved locally.")
        time.sleep(4.5)  # Optimized cloud throttle

# 6. Save and Push updated data
if analyzed_count > 0 or len(incidents) > 0:
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(incidents, f, indent=4)
    print("[+] Local data backup saved successfully.")
    push_to_github(incidents)
else:
    print("[*] Zero active incidents detected. No update required.")