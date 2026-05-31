from playwright.sync_api import sync_playwright
import time

url = "https://cad.chp.ca.gov/Traffic.aspx"

print("Initializing Target Search & Hot Spots Network Sniffer...")
with sync_playwright() as p:
    # Open visible browser instance
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    def handle_response(response):
        # Only inspect requests returning from the CHP domain, ignoring analytics tracking
        if "cad.chp.ca.gov" in response.url and response.request.method == "POST":
            print(f"\n[⚡ DATA PACKET INTERCEPTED]")
            print(f"Target URL: {response.url}")
            print(f"HTTP Status: {response.status}") # Corrected from status_code
            
            try:
                # Catch the payload variables the browser is packaging up
                payload_sent = response.request.post_data
                print(f"Sent Payload Sample:\n{payload_sent[:250]}...\n")
                
                # Sniff the text returned by the server
                returned_html = response.text()
                
                # Check what type of data container came back from the server
                if "Grid" in returned_html or "HotSpot" in returned_html or "Panel" in returned_html:
                    filename = f"hotspot_network_capture_{int(time.time())}.html"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(returned_html)
                    print(f"🎯 SUCCESS: Caught a structural data update! Saved to '{filename}'")
            except Exception as e:
                print(f"Could not read packet contents: {e}")

    # Attach our listener to the network pipeline
    page.on("response", handle_response)

    print(f"Navigating to dashboard: {url}")
    page.goto(url)

    print("\n========================================================")
    print("ACTION REQUIRED IN BROWSER WINDOW:")
    print("1. Locate the second dropdown from the right (Search dropdown).")
    print("2. Click it and select the 'Hot Spots' option.")
    print("3. Wait for the map or data grids to refresh on your screen.")
    print("========================================================\n")

    # Giving you 45 seconds to perform the Hot Spot drill-down workflow
    print("Python wiretap active. Awaiting your browser selections...")
    time.sleep(45)
    
    print("\nClosing capture session...")
    browser.close()