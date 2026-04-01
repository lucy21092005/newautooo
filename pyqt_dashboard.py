import sys
import cv2
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms"
# IMPORT YOUR BACKEND
from main import process_frame, post_process


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUTO-GUARDIAN-X")
        self.setGeometry(100, 100, 800, 600)

        # Camera
        self.cap = cv2.VideoCapture(0)

        # UI Elements
        self.video_label = QLabel()
        self.status_label = QLabel("Status: ---")
        self.risk_label = QLabel("Risk: 0%")

        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.risk_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Buttons
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

    def start(self):
        self.timer.start(30)

    def stop(self):
        self.timer.stop()

    def update_frame(self):
        ret, frame = self.cap.read()

        if ret:
            frame_ai = cv2.resize(frame, (416, 416))

            perception, risk = process_frame(frame_ai)
            alarm = post_process(perception, risk)

            risk_score = risk["risk_score"]

            # Status Logic
            if risk_score < 30:
                status = "SAFE"
            elif risk_score < 70:
                status = "WARNING"
            else:
                status = "DANGER"

            self.risk_label.setText(f"Risk: {int(risk_score)}%")
            self.status_label.setText(f"Status: {status}")

            # Convert to Qt Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            qt_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())