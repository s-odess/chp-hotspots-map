import os
import json
import time
import base64
import requests
from dotenv import load_dotenv
from google import genai

# 1. Flexible Environment Loading (Handles local file or direct cloud RAM environment)
if os.path.exists(".env.txt"):
    load_dotenv(".env.txt")
else:
    load_dotenv()

# Verify variable integrity before proceeding
if not os.getenv("GEMINI_API_KEY"):
    print("[-] Structural Error: GEMINI_API_KEY is missing from environment.")
    exit(1)

# Auto-detects GEMINI_API_KEY natively from system environment variables
client = genai.Client()

FILE_PATH = "live_hotspots.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

# 2. Robust Data Loading Guardrail
incidents = []
if os.path.exists(FILE_PATH) and os.path.getsize(FILE_PATH) > 0:
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            incidents = json.load(f)
        print(f"[+] Successfully loaded {len(incidents)} records from {FILE_PATH}.")
    except json.JSONDecodeError:
        print(f"[!] Warning: {FILE_PATH} was corrupted or empty. Initializing empty array.")
        incidents = []
else:
    print(f"[!] Warning: {FILE_PATH} not found. Initializing empty array.")
    incidents = []

# 3. Filtering guardrail
def is_valid(incident):
    return incident.get("Latitude") != "Unknown" and incident.get("Longitude") != "Unknown"

# 4. Triage function with strict error escalation
def get_triage(incident, retries=3):
    prompt = f"""
    Summarize this incident for a news desk. 
    IMPORTANT: Translate all technical police codes (like 23103, 1141, etc.) into plain, understandable English (e.g., 'Reckless Driving', 'Traffic Collision').
    Keep it concise and punchy.
    Incident Data: {incident}
    """
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"[!] API Exception encountered: {error_msg}")
            
            # Catch transient network rate throttles or server busy states
            if "503" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                wait = (attempt + 1) * 15
                print(f"[!] Rate limit or server load. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                # If it's a key configuration or authentication error, stop immediately!
                raise e
                
    raise RuntimeError("API failed to respond after multiple retries.")

def push_to_github(data_list):
    """Securely commits and pushes data directly back into the repository timeline."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: Missing Git environment tokens.")
        return

    print("[*] Contacting GitHub REST API to synchronize data layer...")
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
        "message": "Pipeline Auto-Update: Synchronizing telemetry layer data feeds",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("[SUCCESS] Production dataset pushed! Streamlit synchronization complete.")
    else:
        print(f"[-] Data push rejected: {put_response.status_code} - {put_response.text}")

# 5. Process incidents
print(f"[+] Commencing record evaluation loop...")
analyzed_count = 0

for i, incident in enumerate(incidents):
    # Clear out previous error strings so the engine can regenerate them cleanly
    if "Summary" in incident and incident["Summary"].startswith("Error:"):
        del incident["Summary"]

    if "Summary" in incident:
        continue
        
    if is_valid(incident):
        print(f"[*] Dispatching data packet to Gemini Agent (Incident {i+1}/{len(incidents)})...")
        try:
            summary = get_triage(incident)
            incident["Summary"] = summary
            analyzed_count += 1
            print(f"[+] Step successful. Summary verified.")
            time.sleep(4.5)  # Safe cloud pacing pacing
        except Exception as core_error:
            print(f"[-] Critical failure encountered: {core_error}")
            print("[-] Halted pipeline to preserve existing local data records.")
            exit(1)

# 6. Save and Push updated data
if analyzed_count > 0:
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(incidents, f, indent=4)
    print("[+] Core structural save complete. Launching sync...")
    push_to_github(incidents)
else:
    print("[*] Telemetry state matches cloud record. Syncing operational baseline...")
    push_to_github(incidents)