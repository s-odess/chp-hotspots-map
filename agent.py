import os
import json
import time
from dotenv import load_dotenv
from google import genai

# 1. Load security vault and client
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("[-] Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

# 2. Load data
try:
    with open("live_hotspots.json", "r", encoding="utf-8") as f:
        incidents = json.load(f)
except FileNotFoundError:
    print("[-] Error: live_hotspots.json not found.")
    exit(1)

# 3. Filtering guardrail
def is_valid(incident):
    return incident.get("Latitude") != "Unknown" and incident.get("Longitude") != "Unknown"

# 4. Triage function with retry logic
def get_triage(incident, retries=3):
    # Only one prompt definition here!
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

# 5. Process incidents
print(f"[+] Processing records...")
for i, incident in enumerate(incidents):
    if "AI_Summary" in incident:
        continue
        
    if is_valid(incident):
        print(f"[*] Triaging incident {i+1}...")
        summary = get_triage(incident)
        incident["AI_Summary"] = summary
        print(f"[+] Summary saved.")
        time.sleep(15) 

# 6. Save updated data
with open("live_hotspots.json", "w", encoding="utf-8") as f:
    json.dump(incidents, f, indent=4)

print("[+] All valid incidents processed and saved.")