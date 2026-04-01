import joblib
import numpy as np
import sys
import webbrowser
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.model_manager import ModelManager
from modules.sos_alert import SOSAlertSystem
from modules.gps_tracker import get_location
from modules.non_response_detector import NonResponseDetector
from modules.distraction_detector import DistractionDetector
from modules.closure_detector import ClosureDetector
from modules.blink_detector import BlinkDetector
from modules.behavior_logger import BehaviorLogger

import time
import pygame
import cv2
import mediapipe as mp

from modules.eye_extractor import extract_eye_points
from modules.ear_calculator import calculate_ear
from modules.yolo_detector import YOLODetector


# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# Initialize detectors
yolo_detector = YOLODetector()
logger = BehaviorLogger()
blink_detector = BlinkDetector()
closure_detector = ClosureDetector()
distraction_detector = DistractionDetector()
non_response_detector = NonResponseDetector()
sos_system = SOSAlertSystem(cooldown=60)


import os
import time

model_manager = ModelManager("driver_risk_model.pkl")


# Start webcam
cap = cv2.VideoCapture(0)


# Initialize pygame mixer
pygame.mixer.init()
pygame.mixer.music.load("alarm.wav")

alarm_on = False


# Dashboard state variables
drowsiness_status = "NORMAL"
phone_status = "NOT DETECTED"
system_status = "SAFE"


# Behavioral variables
phone_detected = False
phone_start_time = 0

PHONE_TIME_THRESHOLD = 3
EAR_THRESHOLD = 0.20

ear = 0.0
blink_count = 0
closure_duration = 0.0
distraction_duration = 0.0
risk_score = 0.0
risk_level = "LOW"
map_opened = False
last_lat = None
last_lon = None
last_map_link = None

# ADD THESE TWO LINES
GPS_COOLDOWN = 10  # seconds between GPS updates
last_gps_time = 0



while True:

         model_manager.check_reload()

        print("Model updated successfully.")


    ret, frame = cap.read()

    if not ret:
        break


    # YOLO detection
    yolo_results = yolo_detector.detect(frame)
    detected_classes = yolo_detector.get_detected_classes(yolo_results)

    print("Detected objects:", detected_classes)


    drowsy = False
    current_time = time.time()


    # Phone detection logic
    if "cell phone" in detected_classes:

        if not phone_detected:
            phone_detected = True
            phone_start_time = current_time

        elapsed_time = current_time - phone_start_time

        cv2.putText(
            frame,
            f"PHONE DETECTED ({elapsed_time:.1f}s)",
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        phone_status = "DETECTED"

        if elapsed_time >= PHONE_TIME_THRESHOLD:

            cv2.putText(
                frame,
                "DISTRACTION ALERT!",
                (30, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

    else:

        phone_status = "NOT DETECTED"
        phone_detected = False
        phone_start_time = 0


    # Update distraction duration
    distraction_duration = distraction_detector.update(phone_detected)

    print("Distraction Duration:", distraction_duration)


    # MediaPipe processing
        # MediaPipe processing
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)


    if results.multi_face_landmarks:

        non_response_detector.update_face_status(True)

        face_landmarks = results.multi_face_landmarks[0]

        h, w, _ = frame.shape

        left_eye, right_eye = extract_eye_points(face_landmarks, w, h)

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)

        ear = (left_ear + right_ear) / 2.0


        if ear < EAR_THRESHOLD:

            drowsy = True
            drowsiness_status = "DROWSY"

            cv2.putText(
                frame,
                "DROWSINESS ALERT!",
                (30, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

        else:
            drowsiness_status = "NORMAL"


        blink_count = blink_detector.update(ear)

        # Detect blink event and update non-response detector
        if blink_detector.blink_detected:
            non_response_detector.update_blink_event()


        closure_duration = closure_detector.update(ear)

        # Determine eye closed state
        eyes_closed = ear < EAR_THRESHOLD

        # Update non-response detector
        non_response_detector.update_eye_state(eyes_closed)


        cv2.putText(
            frame,
            f"EAR: {ear:.2f}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

    else:

        ear = 0.0
        closure_duration = 0.0
        non_response_detector.update_face_status(False)



    # ML Prediction FIRST
        # ML Prediction FIRST
    features = np.array([[
        ear,
        blink_count,
        closure_duration,
        int(phone_detected),
        distraction_duration
    ]])

    probabilities = model_manager.predict_proba(features)[0]
risk_score = probabilities[1] * 100


    # Default values
    lat = None
    lon = None
    map_link = None

    # Risk level classification FIRST
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
        map_opened = False

    # GPS update with cooldown protection
    if risk_level == "HIGH":

        current_time = time.time()

        if current_time - last_gps_time >= GPS_COOLDOWN:

            lat, lon = get_location()

            if lat is not None and lon is not None:

                map_link = f"https://maps.google.com/?q={lat},{lon}"

                last_lat = lat
                last_lon = lon
                last_map_link = map_link
                last_gps_time = current_time

                print("\n===== AUTO-GUARDIAN-X LOCATION ALERT =====")
                print("Risk Level:", risk_level)
                print("Latitude:", lat)
                print("Longitude:", lon)
                print("View Map:", map_link)
                print("=========================================\n")

                if not map_opened:
                    webbrowser.open(map_link)
                    map_opened = True

    # Log behavior and location
    logger.log(
        ear,
        blink_count,
        closure_duration,
        int(phone_detected),
        distraction_duration,
        risk_score,
        lat,
        lon,
        map_link
    )



    # Check non-responsive condition
    non_responsive = non_response_detector.check_non_responsive()

    if non_responsive:

        cv2.putText(
            frame,
            "NON-RESPONSIVE DETECTED!",
            (30, 460),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )



    # Choose risk level and color
    if risk_score >= 70:

        system_status = "HIGH RISK"
        risk_color = (0, 0, 255)

    elif risk_score >= 40:

        system_status = "MEDIUM RISK"
        risk_color = (0, 255, 255)

    else:

        system_status = "SAFE"
        risk_color = (0, 255, 0)


        # Risk level classification
        # Choose risk level and color
    if risk_score >= 70:

        system_status = "HIGH RISK"
        risk_color = (0, 0, 255)

    elif risk_score >= 40:

        system_status = "MEDIUM RISK"
        risk_color = (0, 255, 255)

    else:

        system_status = "SAFE"
        risk_color = (0, 255, 0)


    # Risk level classification
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
        map_opened = False



    # GPS and Google Maps link generation during HIGH risk
    if risk_level == "HIGH":

        lat, lon = get_location()

        # Location alert and Google Maps opening (final stable version)
if lat is not None and lon is not None:

    map_link = f"https://maps.google.com/?q={lat},{lon}"

    last_lat = lat
    last_lon = lon
    last_map_link = map_link

    print("\n===== AUTO-GUARDIAN-X LOCATION ALERT =====")
    print("Risk Level:", risk_level)
    print("Latitude:", lat)
    print("Longitude:", lon)
    print("View Map:", map_link)
    print("=========================================\n")

    # Open Google Maps only once per HIGH-risk event
    if not map_opened:
        webbrowser.open(map_link)
        map_opened = True




    # SOS trigger decision
    sos_triggered = False

    if (
        risk_score >= 80 or
        non_responsive or
        closure_duration >= 3 or
        distraction_duration >= 5
    ):

        # Trigger SOS system with cooldown protection
        if sos_system.trigger():
            sos_triggered = True


    # Alarm logic based on ML risk
    if risk_score >= 70:

        if not alarm_on:
            pygame.mixer.music.play(-1)
            alarm_on = True

    else:

        if alarm_on:
            pygame.mixer.music.stop()
            alarm_on = False

    # Dashboard vertical layout control
    y = 180
    gap = 25

    # Dashboard display
    cv2.putText(
        frame,
        "AUTO-GUARDIAN-X Dashboard",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2
    )
    y += gap


    # Display SOS ACTIVE if system is active
    if sos_system.is_active():

        cv2.putText(
            frame,
            "SOS ACTIVE",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            3
        )
        y += gap


    cv2.putText(
        frame,
        f"Risk Level: {risk_level}",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        risk_color,
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Drowsiness: {drowsiness_status}",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Phone: {phone_status}",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"System: {system_status}",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        risk_color,
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Blinks: {blink_count}",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Closure: {closure_duration:.2f}s",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Distraction: {distraction_duration:.2f}s",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 200, 255),
        2
    )
    y += gap

    cv2.putText(
        frame,
        f"Risk Score: {risk_score:.1f}%",
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        risk_color,
        2
    )
    y += gap


        # Show location info when HIGH risk
    if risk_level == "HIGH" and map_link is not None:

        cv2.putText(
            frame,
            "Location: Available",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )
        y += gap

        cv2.putText(
            frame,
            "Map: Ready",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )
        y += gap


        cv2.putText(
            frame,
            "View Map: maps.google.com",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )
        y += gap
        
    cv2.imshow("AUTO-GUARDIAN-X", frame)


    if cv2.waitKey(1) & 0xFF == 27:
        break


cap.release()
cv2.destroyAllWindows()
