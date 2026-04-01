import cv2
import mediapipe as mp


from modules.yolo_detector import YOLODetector
from modules.eye_extractor import extract_eye_points
from modules.ear_calculator import calculate_ear
from modules.blink_detector import BlinkDetector
from modules.closure_detector import ClosureDetector
from modules.distraction_detector import DistractionDetector
from modules.non_response_detector import NonResponseDetector

from config.settings import EAR_THRESHOLD


class PerceptionPipeline:

    def __init__(self):

        # Threshold
        self.ear_threshold = EAR_THRESHOLD

        # MediaPipe init (optimized)
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

        

        
        # YOLO skip settings (FIXED POSITION)
        self.yolo_skip = 2
        self.yolo_count = 0
        self.last_phone_detected = False

        # Detectors
        self.yolo_detector = YOLODetector()
        self.blink_detector = BlinkDetector()
        self.closure_detector = ClosureDetector()
        self.distraction_detector = DistractionDetector()
        self.non_response_detector = NonResponseDetector()

        # Frame skip settings (IMPORTANT)
        self.frame_skip = 1
        self.frame_count = 0

        # Store last valid result
        self.last_result = {
            "ear": 0.0,
            "blink_count": 0,
            "closure_duration": 0.0,
            "phone_detected": False,
            "distraction_duration": 0.0,
            "non_responsive": False,
            "drowsiness_status": "NORMAL",
            "phone_status": "NOT DETECTED"
        }


    def process(self, frame):

        # Frame skipping logic
        self.frame_count += 1

        if self.frame_count % self.frame_skip != 0:
            return self.last_result


        # Default values
        ear = 0.0
        blink_count = 0
        closure_duration = 0.0
        phone_detected = False
        distraction_duration = 0.0
        non_responsive = False

        drowsiness_status = "NORMAL"
        phone_status = "NOT DETECTED"


        # YOLO detection (skipped independently)
        self.yolo_count += 1

        if self.yolo_count % self.yolo_skip == 0:

            yolo_results = self.yolo_detector.detect(frame)
            detected_classes = self.yolo_detector.get_detected_classes(yolo_results)

            self.last_phone_detected = "cell phone" in detected_classes


        phone_detected = self.last_phone_detected

        if phone_detected:
            phone_status = "DETECTED"

        distraction_duration = self.distraction_detector.update(phone_detected)


        # MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)


        if results.multi_face_landmarks:

            self.non_response_detector.update_face_status(True)

            face_landmarks = results.multi_face_landmarks[0]

            h, w, _ = frame.shape

            left_eye, right_eye = extract_eye_points(face_landmarks, w, h)

            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)

            ear = (left_ear + right_ear) / 2.0


            if ear < self.ear_threshold:
                drowsiness_status = "DROWSY"


            blink_count = self.blink_detector.update(ear)

            if self.blink_detector.blink_detected:
                self.non_response_detector.update_blink_event()


            closure_duration = self.closure_detector.update(ear)

            eyes_closed = ear < self.ear_threshold

            self.non_response_detector.update_eye_state(eyes_closed)

        else:

            self.non_response_detector.update_face_status(False)


        non_responsive = self.non_response_detector.check_non_responsive()


        # Final result
        result = {
            "ear": ear,
            "blink_count": blink_count,
            "closure_duration": closure_duration,
            "phone_detected": phone_detected,
            "distraction_duration": distraction_duration,
            "non_responsive": non_responsive,
            "drowsiness_status": drowsiness_status,
            "phone_status": phone_status
        }


        # Save result for skipped frames
        self.last_result = result

        return result
