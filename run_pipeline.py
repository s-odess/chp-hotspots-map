import subprocess
import time
import sys

# Interval in seconds (e.g., 300 seconds = 5 minutes)
# The CHP dashboard naturally refreshes its data every 60 seconds
INTERVAL = 180 

print("========================================================")
print("🚀 CHP DISPATCH AGENT: COUPLING PIPELINE ORCHESTRATOR")
print(f"Tracking interval established: Every {INTERVAL} seconds")
print("========================================================\n")

try:
    while True:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] 🌀 Starting automated ingestion cycle...")
        
        # 1. Fire the Playwright Extractor
        print(" -> Ingesting live DOM layers...")
        extractor = subprocess.run(["python", "chp_hotspots_engine.py"], capture_output=True, text=True)
        
        # 2. Fire the JSON Structuring Parser
        print(" -> Structuring raw packets to JSON...")
        parser = subprocess.run(["python", "process_hotspots.py"], capture_output=True, text=True)
        
        # Print a quick summary status to the main console log
        if "SUCCESS" in extractor.stdout and "complete" in parser.stdout:
            print(f"[✔] Cycle Complete: Data synchronized successfully.")
        else:
            print("[!] Warning: One or more pipeline stages reported a synchronization anomaly.")
            print(extractor.stdout)
            print(parser.stdout)
            
        print(f"💤 Sleeping for {INTERVAL} seconds before next check. Press Ctrl+C to terminate.\n")
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\n[-] Orchestrator shutdown command received. Terminating data streams safely...")
    sys.exit(0)