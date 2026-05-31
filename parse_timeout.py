import json
import re

print("====================================================")
print("🔍 DEEP INVENTORY SEARCH ON SUCCESSFUL DATA FEED")
print("====================================================\n")

try:
    with open('live_hotspots.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"[+] Successfully loaded {len(data)} records from live_hotspots.json")
    
    # Let's inspect the exact inner text captured for the first few rows
    for i, row in enumerate(data[:3]):
        print(f"\n--- Incident Record #{i+1} (ID: {row.get('No.', 'N/A')}) ---")
        log_text = row.get('Extended_Log_Details', '')
        
        if not log_text:
            print("  [-] Extended_Log_Details field is completely empty for this row.")
            continue
            
        print(f"  [Raw Text Sample (First 300 Chars)]:\n  \"{log_text[:300]}...\"")
        
        # Look for any URL fingerprints hidden inside the captured text string
        urls = re.findall(r'https?://[^\s]+', log_text)
        if urls:
            print(f"  [+] Hidden URLs detected in text: {urls}")
        else:
            print("  [-] No explicit http/https URLs found inside this text block.")
            
        # Look for raw lat/long numerical patterns (e.g., 34.xxxxx, -118.xxxxx)
        coords = re.findall(r'[-+]?\d+\.\d+,\s*[-+]?\d+\.\d+', log_text)
        if coords:
            print(f"  [+] Lat/Long coordinate patterns detected: {coords}")

except Exception as e:
    print(f"[-] Data inspection crashed: {e}")