import os
import json
import time

# Get telemetry file path
TELEMETRY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "shared",
    "dashboard_data.json"
)

print("Telemetry Reader Started")
print("Reading from:", TELEMETRY_FILE)
print("----------------------------------")

while True:

    try:
        with open(TELEMETRY_FILE, "r") as f:
            data = json.load(f)

        print("\nLIVE TELEMETRY DATA:")
        print("EAR:", data.get("ear"))
        print("Blink Count:", data.get("blink_count"))
        print("Closure Duration:", data.get("closure_duration"))
        print("Phone Detected:", data.get("phone_detected"))
        print("Distraction Duration:", data.get("distraction_duration"))
        print("Risk Score:", data.get("risk_score"))
        print("Risk Level:", data.get("risk_level"))
        print("System Status:", data.get("system_status"))
        print("SOS Active:", data.get("sos_active"))

    except Exception as e:
        print("Waiting for telemetry data...")

    time.sleep(1)
