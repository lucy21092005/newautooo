import sys
import os
import json
from collections import deque
from utils.report_generator import ForensicReportGenerator # Import the new module
from flask import Flask, jsonify, send_file
from flask_cors import CORS
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Flask App Initialization
app = Flask(__name__)
CORS(app)  # Allows the mobile app to connect without errors

import cv2
import time
import requests
from modules.gps_tracker import get_location
from core.model_manager import ModelManager
from core.risk_evaluator import RiskEvaluator
from core.perception_pipeline import PerceptionPipeline
from safety.alarm_controller import AlarmController
from modules.behavior_logger import BehaviorLogger
from ui.dashboard_renderer import DashboardRenderer
from device_id_manager import get_device_id

from dataset_logger import log_data
from rnn_inference import predict_fatigue
from mobile_trigger import check_mobile_connection




DEVICE_ID = get_device_id()
print("Running ADMS Device:", DEVICE_ID)

print("STEP 1")
model_manager = ModelManager("driver_risk_model.pkl")

print("STEP 2")
risk_evaluator = RiskEvaluator(model_manager)

print("STEP 3")
perception_pipeline = PerceptionPipeline()

print("STEP 4")
alarm_controller = AlarmController("alarm.wav")

print("STEP 6")
logger = BehaviorLogger()

print("STEP 7")
dashboard = DashboardRenderer()

print("STEP 7.5: Initializing Forensic Systems")
report_generator = ForensicReportGenerator(output_dir="reports")
frame_buffer = deque(maxlen=20)   # The sliding window holding 20 frames
last_report_time = 0              # Cooldown timer
REPORT_COOLDOWN = 60              # Wait 60s between reports
latest_pdf_path = None            # Holds path to the most recently generated report

# Shared driver metrics — updated by the main loop, served via Flask API
driver_metrics = {
    "device_id": DEVICE_ID,
    "status": "safe",
    "risk_score": 0.15,
    "eyes_closed": False
}


# 1. The route Android reads
@app.route('/get_status', methods=['GET'])
def get_status():
    return jsonify(driver_metrics), 200


# 5. Download the latest forensic PDF report
@app.route('/get_report', methods=['GET'])
def get_report():
    global latest_pdf_path
    if latest_pdf_path is None or not os.path.exists(latest_pdf_path):
        return jsonify({"error": "No report available yet."}), 404
    return send_file(latest_pdf_path, as_attachment=True)


# ==========================================
# 🚨 DEMO / TESTING ROUTES
# ==========================================

# 2. Trigger Safe Mode
@app.route('/simulate/safe', methods=['GET'])
def simulate_safe():
    global driver_metrics
    driver_metrics.update({"status": "safe", "risk_score": 0.10, "eyes_closed": False})
    return "✅ AI simulated: Driver is SAFE."

# 3. Trigger Drowsy Mode
@app.route('/simulate/drowsy', methods=['GET'])
def simulate_drowsy():
    global driver_metrics
    driver_metrics.update({"status": "drowsy", "risk_score": 0.75, "eyes_closed": True})
    return "⚠️ AI simulated: Driver is DROWSY."

# 4. Trigger Unconscious Mode (EMERGENCY)
@app.route('/simulate/unconscious', methods=['GET'])
def simulate_unconscious():
    global driver_metrics
    driver_metrics.update({"status": "unconscious", "risk_score": 0.98, "eyes_closed": True})
    return "🚨 AI simulated: Driver is UNCONSCIOUS! App should trigger."


def process_frame(frame):
    perception_data = perception_pipeline.process(frame)
    risk_data = risk_evaluator.evaluate(perception_data)
    return perception_data, risk_data


def post_process(perception_data, risk_data):
    ear = perception_data["ear"]
    blink_count = perception_data["blink_count"]
    closure_duration = perception_data["closure_duration"]
    phone_detected = perception_data["phone_detected"]
    distraction_duration = perception_data["distraction_duration"]

    risk_score = risk_data["risk_score"]

    alarm_level = 0

    if closure_duration > 3:
        alarm_level = 100
    elif closure_duration > 2:
        alarm_level = 80
    elif phone_detected and distraction_duration > 4:
        alarm_level = 70
    elif risk_score > 70:
        alarm_level = 60

    return alarm_level



# ---------------- CAMERA ----------------






# ================= MAIN LOOP (COMMENTED AS YOU DID) =================

# try:
#
#     while True:
#
#         model_manager.check_reload()
#
#         ret, frame = cap.read()
#
#         if not ret:
#             break
#
#         frame_counter += 1
#         run_ai = frame_counter % process_every == 0
#
#         if run_ai:
#
#             frame_ai = cv2.resize(frame, (416, 416))
#
#             perception_data = perception_pipeline.process(frame_ai)
#             risk_data = risk_evaluator.evaluate(perception_data)
#
#             last_perception_data = perception_data
#             last_risk_data = risk_data
#
#             # (rest of your AI + logic remains commented exactly as you had)
#
#         # cv2.imshow("AUTO-GUARDIAN-X", frame)
#
#         # if cv2.waitKey(1) & 0xFF == 27:
#         #     break
#
# except KeyboardInterrupt:
#     print("\nCTRL+C detected. Shutting down safely...")

mobile_connected = False
frame_counter = 0

try:
    pass

except KeyboardInterrupt:
    print("\nCTRL+C detected. Shutting down safely...")

finally:
    try:
        import pygame
        pygame.mixer.quit()
    except:
        pass

    print("System stopped.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)