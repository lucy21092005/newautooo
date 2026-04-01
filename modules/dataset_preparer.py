import csv
import os
from datetime import datetime


class DatasetPreparer:

    def __init__(self):

        # Source log file
        self.log_file = "driver_behavior_log.csv"

        # Output training dataset file
        self.dataset_file = "training_dataset.csv"

        # Create dataset file if not exists
        if not os.path.exists(self.dataset_file):

            with open(self.dataset_file, mode='w', newline='') as file:

                writer = csv.writer(file)

                writer.writerow([
                    "EAR",
                    "BlinkCount",
                    "ClosureDuration",
                    "PhoneDetected",
                    "DistractionDuration",
                    "RiskScore",
                    "Label",
                    "Timestamp"
                ])


    def prepare_dataset(self):

        if not os.path.exists(self.log_file):
            print("Log file not found")
            return

        with open(self.log_file, mode='r') as log:

            reader = csv.DictReader(log)

            with open(self.dataset_file, mode='a', newline='') as dataset:

                writer = csv.writer(dataset)

                for row in reader:

                    ear = float(row["ear"])

                    blink = int(row["blink_count"])

                    closure = float(row["eye_closure_duration"])

                    phone = int(row["phone_detected"])

                    distraction = float(row["distraction_duration"])

                    risk = float(row["risk_score"])

                    timestamp = row["timestamp"]

                    # Automatic label generation
                    if risk >= 70:
                        label = "HIGH"
                    elif risk >= 40:
                        label = "MEDIUM"
                    else:
                        label = "LOW"

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    writer.writerow([
                        ear,
                        blink,
                        closure,
                        phone,
                        distraction,
                        risk,
                        label,
                        timestamp
                    ])

        print("Dataset prepared successfully")
