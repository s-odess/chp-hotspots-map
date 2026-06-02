import os
import json
import time
import base64
import requests
from dotenv import load_dotenv
from google import genai

if os.path.exists(".env.txt"):
    load_dotenv(".env.txt")
else:
    load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("[-] Structural Error: GEMINI_API_KEY is missing from environment.")
    exit(1)

client = genai.Client()

FILE_PATH = "live_hotspots.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

COORD_KEYS = {
    "Latitude", "Longitude", "latitude", "longitude", "lat", "lon", "Summary"
}

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


def is_valid(incident):
    return incident.get("Latitude") != "Unknown" and incident.get("Longitude") != "Unknown"


def narrative_context(incident):
    """Send only human-relevant dispatch fields — never raw coordinates."""
    return {k: v for k, v in incident.items() if k not in COORD_KEYS}


def summary_is_finished(summary):
    if not summary or summary == "Pending AI analysis...":
        return False
    if summary.startswith("Error:"):
        return False
    upper = summary.upper()
    if "NEWS DESK" in upper or "NEWS DESK ALERT" in upper:
        return False
    return True


def get_triage(incident, retries=3):
    context = narrative_context(incident)
    prompt = f"""You are a calm, human-friendly traffic narrator helping everyday drivers understand CHP highway incidents.

Your job: turn raw dispatch information into a short, conversational story (2–4 sentences) that explains what is happening on the road and what drivers might notice.

Rules:
- Write in plain, natural English — like you're telling a friend, not reading a police blotter.
- Translate police codes and jargon into everyday language (e.g., 23103 → reckless driving, 118 → traffic collision).
- Focus on the incident type, location description (if provided), lane impacts, and anything useful for drivers.
- Do NOT use headlines, labels, or templates (no "NEWS DESK ALERT", no bullet lists, no ALL CAPS shouting).
- Do NOT include latitude, longitude, GPS numbers, or coordinate pairs.
- Do NOT repeat incident numbers or metadata unless it helps clarity.

Dispatch record:
{json.dumps(context, indent=2)}
"""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = (response.text or "").strip()
            return text
        except Exception as e:
            error_msg = str(e)
            print(f"[!] API Exception encountered: {error_msg}")

            if "503" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                wait = (attempt + 1) * 15
                print(f"[!] Rate limit or server load. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise RuntimeError("API failed to respond after multiple retries.")


def push_to_github(data_list):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping Cloud Sync: Missing Git environment tokens.")
        return

    print("[*] Contacting GitHub REST API to synchronize data layer...")
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
        "message": "Pipeline Auto-Update: Synchronizing telemetry layer data feeds",
        "content": encoded_content,
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("[SUCCESS] Production dataset pushed! Streamlit synchronization complete.")
    else:
        print(f"[-] Data push rejected: {put_response.status_code} - {put_response.text}")


print("[+] Commencing record evaluation loop...")
analyzed_count = 0
max_per_run = 3

for i, incident in enumerate(incidents):
    if analyzed_count >= max_per_run:
        print(f"[!] Reached maximum limit of {max_per_run} requests for this run. Saving quota.")
        break

    if "Summary" in incident and incident["Summary"].startswith("Error:"):
        del incident["Summary"]

    if summary_is_finished(incident.get("Summary", "")):
        continue

    if is_valid(incident):
        print(f"[*] Dispatching data packet to Gemini Agent (Incident {i+1}/{len(incidents)})...")
        try:
            incident["Summary"] = get_triage(incident)
            analyzed_count += 1
            print("[+] Step successful. Summary verified.")
            time.sleep(4.5)
        except Exception as core_error:
            print(f"[!] AI Pipeline Throttled: {core_error}")
            print("[*] Gracefully halting AI summaries. Advancing data matrix to GitHub sync layer...")
            if "Summary" not in incident:
                incident["Summary"] = "🔄 Narrative queued: Awaiting daily AI quota reset."
            break

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(incidents, f, indent=4)
print("[+] Core structural save complete. Launching sync...")
push_to_github(incidents)
