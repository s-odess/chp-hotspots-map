from bs4 import BeautifulSoup
import json

print("[*] Opening local data payload: live_hotspots_data.html...")
try:
    with open("live_hotspots_data.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # The file contains inner_html, so wrap it in a structural table block to parse beautifully
    soup = BeautifulSoup(f"<table>{html_content}</table>", 'html.parser')
    rows = soup.find_all('tr')

    if not rows:
        print("[-] Error: No data rows found inside the file.")
        exit()

    # 1. Map out headers dynamically
    headers = [th.text.strip() for th in rows[0].find_all('th')]
    
    # 2. Extract data records
    incidents = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) == len(headers):
            incident_data = {}
            for header, col in zip(headers, cols):
                # Clean up nested whitespace/newlines native to ASP grids
                clean_value = " ".join(col.text.split())
                incident_data[header] = clean_value
            incidents.append(incident_data)

    print(f"[+] Successfully structured {len(incidents)} live incident records.")

    # 3. Save as a production-ready JSON feed
    with open("live_hotspots.json", "w", encoding="utf-8") as json_f:
        json.dump(incidents, json_f, indent=4)
        
    print("[🎉] JSON Pipeline complete. File written to 'live_hotspots.json'")
    
    # Print the first item as a visual confirmation
    if incidents:
        print("\n[ Sample Structured Record ]")
        print(json.dumps(incidents[0], indent=2))

except Exception as e:
    print(f"[-] Pipeline processing failed: {e}")