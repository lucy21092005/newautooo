import sys
import os
import json

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer


# Panel class (ONLY handles panel visuals)
class Panel(QFrame):

    def __init__(self, title):
        super().__init__()

        self.setFrameShape(QFrame.Box)

        self.setStyleSheet("""
            QFrame {
                border: 2px solid #00ffcc;
                border-radius: 10px;
                background-color: #111827;
            }
        """)

        layout = QGridLayout()

        self.title = QLabel(title)
        self.title.setStyleSheet("""
            color: #00ffcc;
            font-size: 18px;
            font-weight: bold;
        """)

        layout.addWidget(self.title, 0, 0)

        self.setLayout(layout)


# Main Dashboard Class
class AutoGuardianDashboard(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUTO-GUARDIAN-X Dashboard")
        self.setGeometry(100, 100, 1200, 700)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #020617;
            }

            QLabel {
                color: white;
                font-size: 16px;
            }
        """)

        # Telemetry file path
        self.telemetry_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "shared",
            "dashboard_data.json"
        )

        # Frame file path
        self.frame_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "shared",
            "frame.jpg"
        )

        # Main container
        container = QWidget()
        layout = QGridLayout()

        # Create panels
        self.camera_panel = Panel("Camera Feed")
        self.fatigue_panel = Panel("Fatigue Metrics")
        self.distraction_panel = Panel("Distraction Metrics")
        self.risk_panel = Panel("Risk Analysis")
        self.status_panel = Panel("System Status")
        self.gps_panel = Panel("GPS Location")

        # Camera label
        self.camera_label = QLabel("No Camera Feed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)

        # Other labels
        self.fatigue_label = QLabel(
            "EAR: --\nBlink Count: --\nClosure Duration: --"
        )

        self.distraction_label = QLabel(
            "Phone Detected: --\nDistraction Duration: --"
        )

        self.risk_label = QLabel(
            "Risk Score: --\nRisk Level: --"
        )

        self.status_label = QLabel(
            "System Status: MONITORING"
        )

        self.gps_label = QLabel(
            "Latitude: --\nLongitude: --"
        )

        # Add labels to panels
        self.camera_panel.layout().addWidget(self.camera_label)
        self.fatigue_panel.layout().addWidget(self.fatigue_label)
        self.distraction_panel.layout().addWidget(self.distraction_label)
        self.risk_panel.layout().addWidget(self.risk_label)
        self.status_panel.layout().addWidget(self.status_label)
        self.gps_panel.layout().addWidget(self.gps_label)

        # Layout positioning
        layout.addWidget(self.camera_panel, 0, 0, 2, 2)
        layout.addWidget(self.fatigue_panel, 0, 2)
        layout.addWidget(self.distraction_panel, 1, 2)
        layout.addWidget(self.risk_panel, 2, 0)
        layout.addWidget(self.status_panel, 2, 1, 1, 2)
        layout.addWidget(self.gps_panel, 3, 0, 1, 3)

        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timer setup
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(200)


    # Dashboard update function
    def update_dashboard(self):

        # Update telemetry data
        if os.path.exists(self.telemetry_file):

            try:

                with open(self.telemetry_file, "r") as f:
                    data = json.load(f)

                # Fatigue panel
                self.fatigue_label.setText(
                    f"EAR: {data.get('ear', 0):.2f}\n"
                    f"Blink Count: {data.get('blink_count', 0)}\n"
                    f"Closure Duration: {data.get('closure_duration', 0):.2f}"
                )

                # Distraction panel
                phone = "YES" if data.get("phone_detected") else "NO"

                self.distraction_label.setText(
                    f"Phone Detected: {phone}\n"
                    f"Distraction Duration: {data.get('distraction_duration', 0):.2f}"
                )

                # Risk panel
                self.risk_label.setText(
                    f"Risk Score: {data.get('risk_score', 0):.2f}%\n"
                    f"Risk Level: {data.get('risk_level', '--')}"
                )

                # Status panel
                self.status_label.setText(
                    f"System Status: {data.get('system_status', '--')}"
                )

                # GPS panel
                lat = data.get("latitude")
                lon = data.get("longitude")

                if lat is not None and lon is not None:

                    self.gps_label.setText(
                        f"Latitude: {lat:.6f}\nLongitude: {lon:.6f}"
                    )

                else:

                    self.gps_label.setText("GPS: Not Available")

            except Exception as e:
                print("Telemetry read error:", e)


        # Update camera feed
        if os.path.exists(self.frame_file):

            pixmap = QPixmap(self.frame_file)

            if not pixmap.isNull():

                scaled_pixmap = pixmap.scaled(
                    self.camera_label.width(),
                    self.camera_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                self.camera_label.setPixmap(scaled_pixmap)


# Main function
def main():

    app = QApplication(sys.argv)

    dashboard = AutoGuardianDashboard()
    dashboard.show()

    sys.exit(app.exec_())


# Entry point
if __name__ == "__main__":
    main()
