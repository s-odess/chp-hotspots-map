import os
import subprocess
import sys
import time

# The CHP dashboard refreshes its data about every 60 seconds.
# Each run summarizes at most three incidents, so a short interval does not exhaust the quota quickly.
INTERVAL = 180

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("Extraction", os.path.join("engine", "chp_hotspots_engine.py")),
    ("Summarization", os.path.join("engine", "agent.py")),
]


def run_step(label, script):
    print(f" -> {label}: {script}")
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[!] {label} exited with code {result.returncode}")
        print(result.stdout[-1500:])
        print(result.stderr[-1500:])
        return False
    return True


print("CHP incident pipeline: local loop")
print(f"Interval: every {INTERVAL} seconds. Press Ctrl+C to stop.\n")

try:
    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting cycle")
        for label, script in STEPS:
            if not run_step(label, script):
                print("[!] Cycle stopped early. The next cycle will retry.")
                break
        else:
            print("[+] Cycle complete.")

        print(f"Sleeping {INTERVAL} seconds.\n")
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nStopped by user.")
    sys.exit(0)
