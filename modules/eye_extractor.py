# modules/eye_extractor.py

LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


def extract_eye_points(face_landmarks, frame_width, frame_height):

    left_eye = []
    right_eye = []

    # Extract left eye points
    for idx in LEFT_EYE_INDICES:
        x = int(face_landmarks.landmark[idx].x * frame_width)
        y = int(face_landmarks.landmark[idx].y * frame_height)
        left_eye.append((x, y))

    # Extract right eye points
    for idx in RIGHT_EYE_INDICES:
        x = int(face_landmarks.landmark[idx].x * frame_width)
        y = int(face_landmarks.landmark[idx].y * frame_height)
        right_eye.append((x, y))

    return left_eye, right_eye
