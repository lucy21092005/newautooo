import uuid
import json
import os

DEVICE_FILE = "device_config.json"

def get_device_id():
    if os.path.exists(DEVICE_FILE):
        with open(DEVICE_FILE, "r") as f:
            data = json.load(f)
            return data["device_id"]

    device_id = "AGX-" + str(uuid.uuid4())[:6].upper()

    with open(DEVICE_FILE, "w") as f:
        json.dump({"device_id": device_id}, f)

    return device_id


if __name__ == "__main__":
    print("ADMS Device ID:", get_device_id())