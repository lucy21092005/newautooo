import os
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

import sys
import cv2

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer


class Dashboard(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUTOGUARDIAN-X")
        self.resize(1200, 700)

        # Background image
        self.bg = QLabel(self)
        self.bg.setGeometry(0, 0, 1200, 700)

        self.original_pixmap = QPixmap("dashboard_bg.jpg")
        self.bg.setPixmap(self.original_pixmap.scaled(
            1200, 700, Qt.KeepAspectRatioByExpanding))

        # Camera display area (adjust these values)
        self.camera_label = QLabel(self)
        self.camera_label.setGeometry(490, 280, 280, 180)
        self.camera_label.setStyleSheet("background-color: black;")

        # Start camera
        self.cap = cv2.VideoCapture(0)

        # Timer updates camera
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera)
        self.timer.start(30)


    def update_camera(self):

        ret, frame = self.cap.read()

        if ret:

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = frame.shape

            qt_image = QImage(
                frame.data,
                w,
                h,
                ch * w,
                QImage.Format_RGB888
            )

            pixmap = QPixmap.fromImage(qt_image)

            pixmap = pixmap.scaled(
                self.camera_label.width(),
                self.camera_label.height(),
                Qt.KeepAspectRatio
            )

            self.camera_label.setPixmap(pixmap)


    def closeEvent(self, event):
        self.cap.release()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = Dashboard()

    window.show()

    sys.exit(app.exec_())


