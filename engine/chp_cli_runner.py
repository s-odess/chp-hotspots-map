from playwright.sync_api import sync_playwright
from google import genai
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.txt")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CHP_TRAFFIC_URL = "https://cad.chp.ca.gov/Traffic.aspx"

def get_ai_summary(text):
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Summarize this traffic dispatch into one plain English sentence: {text}"
        )
        return response.text.strip()
    except:
        return "Summary unavailable."

print("[*] Starting extraction...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(CHP_TRAFFIC_URL)
    
    # Select search, click Go
    page.select_option("select[name='ddlSearches']", "2")
    page.click("input[name='btnSearchGo']")
    page.wait_for_load_state("networkidle")
    
    data = []
    # Find all 'Details' links
    links = page.locator("a:has-text('Details')").all()
    
    for i in range(min(3, len(links))):
        print(f" -> Processing incident {i+1}...")
        # Re-fetch links to avoid stale element errors after navigation
        links = page.locator("a:has-text('Details')").all()
        links[i].click()
        page.wait_for_load_state("networkidle")
        
        # Get all text from the page body instead of hunting for one specific table
        content = page.locator("body").inner_text()
        summary = get_ai_summary(content[:500]) # Send chunk of text to Gemini
        
        data.append({"Raw": content[:200], "Summary": summary})
        
        # Go back to list
        page.go_back()
        page.wait_for_load_state("networkidle")

    browser.close()
    
with open("live_hotspots.json", "w") as f:
    json.dump(data, f, indent=4)

print("[+] Done. Check live_hotspots.json.")