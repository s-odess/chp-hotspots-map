import requests
from bs4 import BeautifulSoup
import urllib.parse

url = "https://cad.chp.ca.gov/Traffic.aspx"

# Define headers that perfectly mirror a human Windows desktop browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Origin": "https://cad.chp.ca.gov",
    "Referer": "https://cad.chp.ca.gov/Traffic.aspx",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Create a persistent session to maintain ASP.NET session cookies automatically
session = requests.Session()

print("[1] Executing initial GET request to harvest cookie session and state tokens...")
try:
    response1 = session.get(url, headers=headers, timeout=15)
    if response1.status_code != 200:
        print(f"[-] Initial connection failed with status code: {response1.status_code}")
        exit()
        
    soup = BeautifulSoup(response1.text, 'html.parser')
    
    # Extract the cryptographic state keys safely
    viewstate = soup.find('input', {'id': '__VIEWSTATE'})
    viewstate_gen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
    event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
    
    if not viewstate:
        print("[-] Target viewstate elements missing. The page layout may have altered.")
        exit()
        
    vs_val = viewstate.get('value', '')
    vsg_val = viewstate_gen.get('value', '') if viewstate_gen else ''
    ev_val = event_validation.get('value', '') if event_validation else ''
    
    print(f"[+] Successfully harvested ViewState Token (Length: {len(vs_val)})")
    print(f"[+] Successfully harvested EventValidation Token (Length: {len(ev_val)})")
    
    # Construct the precise form-payload mapping the 'Border' communication center selection
    payload = {
        "__EVENTTARGET": "ddlCenter",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": vs_val,
        "__VIEWSTATEGENERATOR": vsg_val,
        "__EVENTVALIDATION": ev_val,
        "ddlCenter": "Border",
        "SearchTextBox": "",
        "ddlType": "All",
        "ddlMedia": "All"
    }
    
    print("\n[2] Executing programmatic POST postback transaction...")
    response2 = session.post(url, headers=headers, data=payload, timeout=15)
    
    print(f"[+] Server Handshake Complete. Response Status Code: {response2.status_code}")
    
    # Check if the response contains the incident grid
    soup2 = BeautifulSoup(response2.text, 'html.parser')
    grid_table = soup2.find('table', {'class': 'Grid'})
    
    if grid_table:
        print("\n========================================================")
        print("🎉 SUCCESS: CRACKED THE ASP.NET CRYPTO LAYER!")
        print("The data table was populated purely via server requests.")
        print("========================================================\n")
        
        # Pull a clean sample row to verify data parsing stability
        rows = grid_table.find_all('tr')
        print(f"Total live incident rows captured: {len(rows) - 1}")
    else:
        print("\n[-] Handshake failed to populate data grid.")
        print("The server processed the tokens but returned the default blank page.")
        print("We will evaluate this response using secondary LLMs to dissect the mismatch.")
        
except Exception as e:
    print(f"\n[-] Network anomaly or timeout encountered: {e}")
