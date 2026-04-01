from ultralytics import YOLO
import torch

# 🔥 FULL SAFE CONTEXT (trusted model)
torch.serialization._legacy_load = torch.load

class YOLODetector:

    def __init__(self, model_path="yolov8n.pt"):

        self.model = YOLO(model_path)


    def detect(self, frame):

        results = self.model(frame)

        return results



        annotated_frame = results[0].plot()

        return annotated_frame


    def get_detected_classes(self, results):

        detected_classes = []

        for result in results:

            for box in result.boxes:

                class_id = int(box.cls[0])

                class_name = self.model.names[class_id]

                detected_classes.append(class_name)

        return detected_classes

