import pygame
import cv2
import time
import mediapipe as mp
import numpy as np

# Initialize Face Mesh
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Initialize pygame mixer properly (Linux fix)
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()

alarm_sound = pygame.mixer.Sound("alarm.wav")
alarm_playing = False

# Eye landmark indices
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# EAR threshold
EAR_THRESHOLD = 0.21

# Frame counter
closed_frames = 0

# Drowsy frame limit
DROWSY_LIMIT = 15

# EAR calculation function
def calculate_ear(eye_points):

    vertical1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
    vertical2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
    horizontal = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))

    ear = (vertical1 + vertical2) / (2.0 * horizontal)

    return ear


# Initialize camera
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = 0

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb_frame)

    status = "AWAKE"

    if results.multi_face_landmarks:

        face_landmarks = results.multi_face_landmarks[0]

        height, width, _ = frame.shape

        left_eye_points = []
        right_eye_points = []

        # Collect eye coordinates
        for idx in LEFT_EYE:
            x = int(face_landmarks.landmark[idx].x * width)
            y = int(face_landmarks.landmark[idx].y * height)
            left_eye_points.append((x,y))

        for idx in RIGHT_EYE:
            x = int(face_landmarks.landmark[idx].x * width)
            y = int(face_landmarks.landmark[idx].y * height)
            right_eye_points.append((x,y))

        # Calculate EAR
        left_ear = calculate_ear(left_eye_points)
        right_ear = calculate_ear(right_eye_points)
        ear = (left_ear + right_ear) / 2

        cv2.putText(frame, f"EAR: {ear:.2f}", (10,90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)

        # Drowsiness logic
        if ear < EAR_THRESHOLD:
            closed_frames += 1
        else:
            closed_frames = 0

        if closed_frames >= DROWSY_LIMIT:

            status = "DROWSY"

            cv2.putText(frame, "DROWSY ALERT!", (200,200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255),4)

            if not alarm_playing:
                alarm_sound.play(-1)
                alarm_playing = True

        else:

            status = "AWAKE"

            if alarm_playing:
                alarm_sound.stop()
                alarm_playing = False


    # FPS calculation
    current_time = time.time()
    fps = 1/(current_time-prev_time) if prev_time!=0 else 0
    prev_time = current_time

    cv2.putText(frame, f"FPS: {int(fps)}", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0),2)

    cv2.putText(frame, f"Status: {status}", (10,60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0),2)

    cv2.imshow("Drowsiness Detection", frame)

    if cv2.waitKey(1)==ord('q'):
        break


cap.release()
cv2.destroyAllWindows()
