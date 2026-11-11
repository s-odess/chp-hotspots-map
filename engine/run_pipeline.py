import subprocess
import time
import sys

# Interval in seconds (e.g., 180 seconds = 3 minutes)
INTERVAL = 180 

print("========================================================")
print("🚀 CHP DISPATCH AGENT: ORCHESTRATOR ACTIVE")
print(f"Tracking interval established: Every {INTERVAL} seconds")
print("========================================================\n")

try:
    while True:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] 🌀 Starting automated cycle...")
        
        # 1. Fire the Playwright Extractor
        print(" -> [Stage 1] Ingesting live DOM layers...")
        extractor = subprocess.run(["python", "chp_hotspots_engine.py"])
        if extractor.returncode != 0:
            print(f"\n[✘] Stage 1 failed (exit code {extractor.returncode}). Cycle stopped.")
            print(f"\n💤 Sleeping for {INTERVAL} seconds. Press Ctrl+C to terminate.\n")
            time.sleep(INTERVAL)
            continue

        # 2. Fire the AI Processing Agent
        print(" -> [Stage 2] Translating records with Gemini AI...")
        agent = subprocess.run(["python", "agent.py"])
        if agent.returncode != 0:
            print(f"\n[✘] Stage 2 failed (exit code {agent.returncode}). Cycle stopped.")
            print(f"\n💤 Sleeping for {INTERVAL} seconds. Press Ctrl+C to terminate.\n")
            time.sleep(INTERVAL)
            continue

        # 3. Report completion
        print(f"\n[✔] Cycle Complete. Data extracted & translated.")
            
        print(f"\n💤 Sleeping for {INTERVAL} seconds. Press Ctrl+C to terminate.\n")
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\n[-] Shutting down...")
    sys.exit(0)