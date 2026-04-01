import cv2

cap = cv2.VideoCapture(1)   # try 1 or 2

if not cap.isOpened():
    print("Camera not opened")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("Frame failed")
        break

    cv2.imshow("Test Camera", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()