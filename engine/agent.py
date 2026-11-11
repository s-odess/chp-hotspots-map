import os
import json
import time
import base64
import requests
from dotenv import load_dotenv
from google import genai

# ── Configuration ──────────────────────────────────────────────────────────────

# Set True to clear existing summaries and regenerate fresh each run.
# Use for demos and recordings. Set False in production to save quota.
FORCE_REFRESH = True

MAX_PER_RUN = 3

FILE_PATH    = "live_hotspots.json"

# ── Auth ───────────────────────────────────────────────────────────────────────

if os.path.exists(".env.txt"):
    load_dotenv(".env.txt")
else:
    load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("[-] Structural Error: GEMINI_API_KEY is missing from environment.")
    exit(1)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO  = os.getenv("GITHUB_REPO")

# ── Constants ──────────────────────────────────────────────────────────────────

COORD_KEYS = {
    "Latitude", "Longitude", "latitude", "longitude", "lat", "lon", "Summary"
}

LOCATION_RETRY_PHRASES = (
    "don't have the specific location details",
    "don't have specifics on the location",
    "do not have the specific location details",
    "do not have specifics on the location",
    "lack location specifics",
    "location name is missing",
    "location is missing",
    "no text-based highway",
)

# ── Load Records ───────────────────────────────────────────────────────────────

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

if FORCE_REFRESH:
    for incident in incidents:
        incident.pop("Summary", None)
    print(f"[*] FORCE_REFRESH active — cleared existing summaries for fresh generation.")

# ── Helpers ────────────────────────────────────────────────────────────────────

def is_valid(incident):
    return (
        incident.get("Latitude") not in ("Unknown", None, "") and
        incident.get("Longitude") not in ("Unknown", None, "")
    )


def get_location_string(incident):
    for key in ("Location", "location", "Area", "area"):
        val = incident.get(key, "")
        if val and str(val).strip().lower() not in ("unknown", "n/a", "", "details"):
            return str(val).strip()
    return ""


def narrative_context(incident):
    """Strip coordinates — Gemini should reason from dispatch text, not GPS."""
    return {k: v for k, v in incident.items() if k not in COORD_KEYS}


def summary_needs_retry(summary):
    if not summary:
        return False
    lower = summary.lower()
    return any(phrase in lower for phrase in LOCATION_RETRY_PHRASES)


def summary_is_finished(summary):
    if not summary or summary == "Pending AI analysis...":
        return False
    if summary.startswith("Error:"):
        return False
    if "NEWS DESK" in summary.upper():
        return False
    if summary_needs_retry(summary):
        return False
    return True

# ── Gemini Triage ──────────────────────────────────────────────────────────────

def get_triage(incident, retries=3):
    context  = narrative_context(incident)
    location = get_location_string(incident)

    if location:
        location_instruction = (
            f'You have been provided with the Location: "{location}" '
            "(e.g., a highway, intersection, or landmark). "
            "You MUST weave this location naturally into your narrative so drivers "
            "know exactly where the incident is. Do not say location details are missing."
        )
    else:
        location_instruction = (
            "No street or highway name was captured for this record. "
            "Describe the hazard and what drivers should do without mentioning missing location data."
        )

    prompt = f"""You are a calm, human-friendly traffic narrator helping everyday drivers understand CHP highway incidents.

Your job: turn raw dispatch information into a short, conversational story (2-4 sentences) that explains what is happening on the road and what drivers might notice.

{location_instruction}

Rules:
- Write in plain, natural English — like you're telling a friend, not reading a police blotter.
- Translate police codes and jargon into everyday language (e.g., 23103 = reckless driving, 118 = traffic collision).
- When Location is provided, name it early in the story (e.g., "On I-5 north near ...").
- Do NOT use headlines, labels, or templates (no "NEWS DESK ALERT", no bullet lists, no ALL CAPS).
- Do NOT include latitude, longitude, GPS numbers, or coordinate pairs.
- Do NOT say you lack location specifics or that location details are missing.
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
            print(f"    [!] API Exception: {error_msg}")
            if "503" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                wait = (attempt + 1) * 15
                print(f"    [!] Server load — retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise RuntimeError("API failed to respond after maximum retries.")

# ── GitHub Sync ────────────────────────────────────────────────────────────────

def push_to_github(data_list):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[-] Skipping GitHub sync: tokens not configured.")
        return

    print("[*] Contacting GitHub REST API...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    encoded = base64.b64encode(
        json.dumps(data_list, indent=4).encode("utf-8")
    ).decode("utf-8")

    sha = None
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload = {
        "message": "Pipeline Auto-Update: Synchronizing telemetry layer data feeds",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    put = requests.put(api_url, headers=headers, json=payload)
    if put.status_code in (200, 201):
        print("[SUCCESS] GitHub sync complete.")
    else:
        print(f"[-] GitHub push failed: {put.status_code} - {put.text}")

# ── Main Loop ──────────────────────────────────────────────────────────────────

print("[+] Commencing record evaluation loop...")
analyzed_count = 0

for i, incident in enumerate(incidents):
    if analyzed_count >= MAX_PER_RUN:
        print(f"[!] Reached per-run limit of {MAX_PER_RUN}. Saving quota.")
        break

    summary = incident.get("Summary", "")
    if summary_is_finished(summary):
        continue

    if summary_needs_retry(summary):
        print(f"[*] Re-processing incomplete summary (incident {i+1})...")

    if not is_valid(incident):
        continue

    loc = get_location_string(incident)
    print(f"\n{'='*56}")
    print(f"  Incident {i+1}/{len(incidents)} — {loc or 'Location unavailable'}")
    print(f"{'='*56}")

    try:
        summary_text = get_triage(incident)
        incident["Summary"] = summary_text
        analyzed_count += 1
        print(f"  {summary_text}\n")
        time.sleep(4.5)

    except Exception as core_error:
        print(f"[!] AI pipeline error: {core_error}")
        print("[*] Halting summarization. Saving current state...")
        if "Summary" not in incident:
            incident["Summary"] = "Narrative queued: awaiting next cycle."
        break

# ── Save & Sync ────────────────────────────────────────────────────────────────

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(incidents, f, indent=4)
print("\n[+] Records saved to live_hotspots.json")
push_to_github(incidents)
