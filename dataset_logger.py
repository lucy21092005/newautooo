import csv
import os
import time

FILE_PATH = "driver_dataset.csv"

# Create file with header if not exists
if not os.path.exists(FILE_PATH):
    with open(FILE_PATH, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "ear",
            "blink_count",
            "closure_duration",
            "phone_detected",
            "distraction_duration",
            "label"
        ])

def log_data(ear, blink, closure, phone, distraction, label):
    with open(FILE_PATH, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            round(time.time(), 2),
            ear,
            blink,
            closure,
            int(phone),
            distraction,
            label
        ])