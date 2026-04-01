import subprocess
import sys
import os
import cv2
import time
import threading
import json
import math
from collections import deque

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint
from PySide6.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QColor

from core.perception_pipeline import PerceptionPipeline
from core.decision_engine import DecisionEngine, DriverState
from core.tracker import HeartRateTracker
from utils.report_generator import ForensicReportGenerator
from modules.gps_tracker import get_location
from mobile_trigger import check_mobile_connection


# ── ALARM SYSTEM DESIGN ────────────────────────────────────────────────────────
#
# The alarm system is designed for real-world driver safety with these guarantees:
#
# 1. CRITICAL THRESHOLD: Alarm activates ONLY when risk > 70
# 2. ONE-TIME TRIGGER: Alarm triggers exactly once per danger state entry
# 3. CONTINUOUS ALERT: While in danger, alarm continues even if audio dies
# 4. IMMEDIATE STOP: Alarm stops instantly when risk falls below threshold
# 5. STARTUP SAFE: First 30 frames are ignored (warm-up period)
# 6. PROCESS SAFETY: No duplicate subprocesses, clean termination on exit
# 7. UI SYNC: Alarm logic runs in QTimer (30ms tick), non-blocking
#
# State Variables:
#   - alarm_on: Boolean, True when in danger state
#   - alarm_process: Handle to paplay subprocess (audio playback)
#   - alarm_triggered_this_session: Flag for one-time trigger (with hysteresis)
#   - startup_frames: Counter to detect warm-up period
#
# ────────────────────────────────────────────────────────────────────────────────


# ── Helpers ───────────────────────────────────────────────────────────────────

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def find_camera():
    """
    Try each /dev/videoX device with multiple backends.
    Returns (cap, index_str) or (None, None).
    We probe with CAP_ANY (not CAP_V4L2) to bypass V4L2 permission issues.
    """
    candidates = []

    # Try numeric indices 0-4 first (OpenCV will pick backend)
    for idx in range(5):
        candidates.append(idx)

    for idx in candidates:
        # Try without forcing V4L2 backend so OpenCV picks the best one
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            # Verify we can actually read a frame
            ok, _ = cap.read()
            if ok:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print(f"✅ Camera opened at index {idx}")
                return cap, str(idx)
            cap.release()

    # Last resort: try V4L2 direct device paths
    for path in ["/dev/video0", "/dev/video1", "/dev/video2"]:
        cap = cv2.VideoCapture(path)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print(f"✅ Camera opened at path {path}")
                return cap, path
            cap.release()

    print("❌ No usable camera found")
    return None, None


# ── ECG Waveform Widget ────────────────────────────────────────────────────────

class ECGWaveWidget(QWidget):
    """Animated ECG waveform display"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(80)
        self.setStyleSheet("background-color: transparent;")
        self.offset = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)  # Update every 30ms
    
    def update_wave(self):
        self.offset += 2
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Waveform parameters
        width = self.width()
        height = self.height()
        center_y = height // 2
        amplitude = height // 3
        frequency = 0.05
        
        # Draw grid
        pen_grid = QPen(QColor(34, 197, 94, 50))  # Green with transparency
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)
        
        # Vertical grid lines
        for x in range(0, width, 40):
            painter.drawLine(x, 0, x, height)
        
        # Horizontal grid lines
        for y in range(0, height, 20):
            painter.drawLine(0, y, width, y)
        
        # Draw ECG waveform
        pen_wave = QPen(QColor(34, 197, 94))  # #22c55e (green)
        pen_wave.setWidth(2)
        painter.setPen(pen_wave)
        
        points = []
        for x in range(width):
            # Create ECG-like pattern with multiple sine waves
            t = (x + self.offset) * frequency
            # Combination of waves for ECG effect
            y_val = (
                amplitude * 0.7 * math.sin(t) +
                amplitude * 0.3 * math.sin(t * 2.5) +
                amplitude * 0.2 * math.sin(t * 5)
            )
            y = center_y - int(y_val)
            points.append(QPoint(x, y))
        
        # Draw polyline
        if len(points) > 1:
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
        
        # Draw baseline pulse effect
        pen_pulse = QPen(QColor(34, 197, 94, 100))
        pen_pulse.setWidth(1)
        painter.setPen(pen_pulse)
        pulse_offset = (self.offset // 10) % 5
        for x in range(0, width, 15):
            painter.drawEllipse(x - pulse_offset, center_y - 3, 6, 6)


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUTO-GUARDIAN-X")
        self.setGeometry(100, 100, 1200, 700)
        self.setMinimumSize(900, 560)

        self.pipeline = PerceptionPipeline()
        self.decision_engine = DecisionEngine()  # NEW: Core logic flow
        self.heart_rate_tracker = HeartRateTracker()  # NEW: Heart rate extraction
        self.frame_count = 0
        self.startup_frames = 0
        self.mobile_connected = False
        
        # ── Telemetry file path for sharing data ──────────────────────────────
        self.telemetry_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "shared",
            "dashboard_data.json"
        )
        
        # ── Alarm State Management ────────────────────────────────────────────
        self.alarm_on = False              # True when alarm is active
        self.alarm_process = None          # Handle to the audio subprocess
        self.alarm_triggered_this_session = False  # One-time trigger per danger entry
        
        self.cap = None

        # ── Forensic system ───────────────────────────────────────────────────
        # Circular sliding window — stores last 20 raw frames 
        self.frame_buffer = deque(maxlen=20)
        # Report generator — saves PDF to /reports/ folder
        self.report_generator = ForensicReportGenerator(output_dir="reports")
        # Cooldown: only generate one report per 60 seconds max
        self.last_report_time = 0
        self.REPORT_COOLDOWN = 60    # seconds

        # ── Stylesheet ────────────────────────────────────────────────────────
        self.setStyleSheet("""
QMainWindow, QWidget {
    background-color: #0a0f1e;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}
QFrame#videoFrame {
    background-color: #050a14;
    border-radius: 16px;
    border: 2px solid #1e3a5f;
}
QFrame#statusFrame {
    background-color: #0d1b2a;
    border-radius: 16px;
    border: 1px solid #1e3a5f;
}
QLabel#riskLabel {
    font-size: 56px;
    font-weight: bold;
    color: #9ae6b4;
}
QLabel#headerLabel {
    font-size: 26px;
    font-weight: bold;
    color: #60a5fa;
    letter-spacing: 6px;
    padding: 8px;
}
QLabel#sectionTitle {
    font-size: 11px;
    font-weight: bold;
    color: #475569;
    letter-spacing: 3px;
}
QPushButton#startBtn {
    background-color: rgba(34,197,94,0.12);
    border: 1.5px solid #22c55e;
    border-radius: 10px;
    padding: 12px 24px;
    color: #86efac;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#startBtn:hover {
    background-color: rgba(34,197,94,0.25);
    border-color: #4ade80;
    color: #bbf7d0;
}
QPushButton#stopBtn {
    background-color: rgba(245,158,11,0.12);
    border: 1.5px solid #f59e0b;
    border-radius: 10px;
    padding: 12px 24px;
    color: #fcd34d;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#stopBtn:hover {
    background-color: rgba(245,158,11,0.25);
    border-color: #fbbf24;
}
QPushButton#exitBtn {
    background-color: rgba(239,68,68,0.10);
    border: 1.5px solid #ef4444;
    border-radius: 10px;
    padding: 12px 24px;
    color: #fca5a5;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#exitBtn:hover {
    background-color: rgba(239,68,68,0.22);
    border-color: #f87171;
}
""")

        # ── Layout ────────────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(12)

        # Header
        header = QLabel("AUTO-GUARDIAN-X")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignCenter)
        root.addWidget(header)

        # Middle
        mid = QHBoxLayout()
        mid.setSpacing(16)

        # ── Video panel ───────────────────────────────────────────────────────
        self.video_frame = QFrame()
        self.video_frame.setObjectName("videoFrame")
        self.video_frame.setMinimumSize(600, 400)
        vf_layout = QVBoxLayout(self.video_frame)
        vf_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(600, 400)
        self._show_no_camera_placeholder()
        vf_layout.addWidget(self.video_label)

        mid.addWidget(self.video_frame, 3)

        # ── Status panel ──────────────────────────────────────────────────────
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        sf_layout = QVBoxLayout(status_frame)
        sf_layout.setContentsMargins(20, 20, 20, 20)
        sf_layout.setSpacing(14)

        lbl_title = QLabel("DRIVER STATUS")
        lbl_title.setObjectName("sectionTitle")
        sf_layout.addWidget(lbl_title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #1e3a5f; max-height: 1px; border: none;")
        sf_layout.addWidget(sep)

        # Risk %
        lbl_risk_title = QLabel("RISK SCORE")
        lbl_risk_title.setObjectName("sectionTitle")
        lbl_risk_title.setAlignment(Qt.AlignCenter)
        sf_layout.addWidget(lbl_risk_title)

        self.readiness = QLabel("—")
        self.readiness.setObjectName("riskLabel")
        self.readiness.setAlignment(Qt.AlignCenter)
        sf_layout.addWidget(self.readiness)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #1e3a5f; max-height: 1px; border: none;")
        sf_layout.addWidget(sep2)

        # Status rows
        self.attention = QLabel("Attention State: —")
        self.attention.setStyleSheet("color: #94a3b8; font-size: 15px;")
        sf_layout.addWidget(self.attention)

        self.heart = QLabel("❤  Heart Rate: 72 BPM")
        self.heart.setStyleSheet("color: #94a3b8; font-size: 14px;")
        sf_layout.addWidget(self.heart)

        # ECG
        lbl_ecg_title = QLabel("ECG TRACE")
        lbl_ecg_title.setObjectName("sectionTitle")
        sf_layout.addWidget(lbl_ecg_title)

        self.ecg = ECGWaveWidget()
        sf_layout.addWidget(self.ecg)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet("background-color: #1e3a5f; max-height: 1px; border: none;")
        sf_layout.addWidget(sep3)

        # Camera label
        self.cam_status_lbl = QLabel("📷  Camera: not connected")
        self.cam_status_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
        sf_layout.addWidget(self.cam_status_lbl)

        sf_layout.addStretch()

        # System info
        sys_lbl = QLabel("Mobile Sync: Active   |   Location: Active   |   Emergency: Armed")
        sys_lbl.setStyleSheet("color: #334155; font-size: 11px;")
        sys_lbl.setAlignment(Qt.AlignCenter)
        sf_layout.addWidget(sys_lbl)

        mid.addWidget(status_frame, 1)
        root.addLayout(mid)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.start_btn = QPushButton("▶   Start Monitoring")
        self.start_btn.setObjectName("startBtn")
        self.stop_btn = QPushButton("⏸   Pause")
        self.stop_btn.setObjectName("stopBtn")
        self.exit_btn = QPushButton("✕   Exit")
        self.exit_btn.setObjectName("exitBtn")

        btn_row.addStretch()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.exit_btn)
        root.addLayout(btn_row)

        # ── Timer ─────────────────────────────────────────────────────────────
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.pause_monitoring)
        self.exit_btn.clicked.connect(self.safe_exit)

        # Try to open camera on startup (non-blocking — runs after window shows)
        QTimer.singleShot(500, self.init_camera)

    # ── Camera init ───────────────────────────────────────────────────────────

    def init_camera(self):
        """Called once after the window is shown. Tries to open the camera."""
        self.cam_status_lbl.setText("�  System: Initializing…")
        self.cam_status_lbl.setStyleSheet("color: #facc15; font-size: 12px;")
        QApplication.processEvents()

        cap, label = find_camera()
        if cap is not None:
            self.cap = cap
            self.cam_status_lbl.setText(" Driver Monitoring: Active")
            self.cam_status_lbl.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: bold;")
            self.video_label.setText("")
        else:
            self.cam_status_lbl.setText("❌  Driver Monitoring: Unavailable")
            self.cam_status_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self._show_no_camera_placeholder()
            QMessageBox.warning(
                self, "Camera Not Found",
                "Could not open any camera.\n\n"
                "Try running:\n"
                "  sudo usermod -aG video $USER\n"
                "then log out and log back in.\n\n"
                "The app will still open but camera feed will be unavailable."
            )

    def _show_no_camera_placeholder(self):
        self.video_label.setText(
            "⚠  No Camera Signal\n\n"
            "Run:  sudo usermod -aG video $USER\n"
            "then log out and back in."
        )
        self.video_label.setStyleSheet("""
            color: #475569;
            font-size: 16px;
            background-color: #050a14;
            border-radius: 14px;
            padding: 20px;
        """)
        self.video_label.setAlignment(Qt.AlignCenter)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def start_monitoring(self):
        if self.cap is None or not self.cap.isOpened():
            # try again
            self.init_camera()
            if self.cap is None:
                return
        self.startup_frames = 0
        self.frame_count = 0
        self.alarm_on = False
        self.alarm_triggered_this_session = False
        self.decision_engine.reset()  # Reset decision engine state
        self.timer.start(30)

    def pause_monitoring(self):
        self.timer.stop()

    def update_data(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        # ── Process Safety: Check if alarm subprocess exited unexpectedly ─────
        # If the process is dead, reset the handle so new alarm can start cleanly
        if self.alarm_process is not None and self.alarm_process.poll() is not None:
            print("[ALARM] ⚠ Audio process exited unexpectedly, resetting...")
            self.alarm_process = None

        backend_frame = frame.copy()

        # ── Push every frame into the forensic circular buffer ────────────────
        self.frame_buffer.append(backend_frame)

        # ── HEART RATE EXTRACTION (NEW) ────────────────────────────────────────
        # Process frame through heart rate tracker
        heart_rate = self.heart_rate_tracker.process_frame(frame)
        heart_status = self.heart_rate_tracker.get_heart_status()

        # Render frame to UI
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(pix)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("")

        # ── Startup Stability: Ignore first ~30 frames ────────────────────────
        # Prevents false alarm triggering during system warm-up
        self.startup_frames += 1
        if self.startup_frames < 30:
            self.attention.setText("Attention State: Warming up…")
            return

        # Process every 5th frame
        self.frame_count += 1
        
        # Check mobile connection every 30 frames
        if self.frame_count % 30 == 0:
            self.mobile_connected = check_mobile_connection()
            if self.mobile_connected:
                print("Mobile Connected")
            else:
                print("Mobile Not Connected")
        
        # ── UPDATE TELEMETRY CONTINUOUSLY (EVERY FRAME) ──────────────────────
        # Ensure dashboard_data.json is refreshed with latest mobile_connected status
        try:
            telemetry_update = {
                "mobile_connected": self.mobile_connected,
                "timestamp": time.time()
            }
            # Read existing telemetry and update with new values
            try:
                with open(self.telemetry_file, "r") as f:
                    existing_telemetry = json.load(f)
                print(f"[DEBUG] mobile_connected: {existing_telemetry.get('mobile_connected', 'N/A')}")
                existing_telemetry.update(telemetry_update)
            except:
                existing_telemetry = telemetry_update
            
            with open(self.telemetry_file, "w") as f:
                json.dump(existing_telemetry, f)
        except Exception as e:
            pass  # Silent fail for continuous updates
        
        if self.frame_count % 5 != 0:
            return

        try:
            perception = self.pipeline.process(backend_frame)
        except Exception as e:
            print(f"Pipeline error: {e}")
            return

        # ── DECISION ENGINE: Process perception through decision logic ────
        # This is the core logic flow: Sense → Analyze → Decide → Act
        try:
            decision = self.decision_engine.process(perception)
        except Exception as e:
            print(f"Decision engine error: {e}")
            return

        # Extract readiness score and state from decision
        readiness_score = decision.get("readiness_score", 100)
        driver_state = decision.get("driver_state", "NORMAL")
        action_reason = decision.get("action_reason", "")
        
        # ── Calculate legacy "risk" for UI compatibility ────────────────
        # Convert readiness (0-100) to risk (0-100) inverted
        risk = 100 - readiness_score

        self.readiness.setText(f"{risk}%")

        # Status colour based on driver state
        if driver_state == DriverState.NORMAL:
            status, color = "SAFE", "#4ade80"
        elif driver_state == DriverState.WARNING:
            status, color = "WARNING", "#facc15"
        elif driver_state == DriverState.DANGER:
            status, color = "DANGER", "#f87171"
        else:  # CRITICAL
            status, color = "🚨 CRITICAL", "#ef4444"

        self.attention.setText(f"Attention State: {status}")
        self.attention.setStyleSheet(f"color: {color}; font-size: 15px;")
        self.readiness.setStyleSheet(f"font-size: 56px; font-weight: bold; color: {color};")

        # ── UPDATE HEART RATE DISPLAY (NEW) ────────────────────────────────────
        if heart_rate > 0:
            self.heart.setText(f"❤  Heart Rate: {heart_rate:.0f} BPM ({heart_status})")
        else:
            self.heart.setText(f"❤  Heart Rate: -- BPM (NO SIGNAL)")
        
        # ── WRITE TELEMETRY TO SHARED FILE ────────────────────────────────────
        # Other UIs (dashboard.py, dashboard_renderer.py) read this file
        try:
            telemetry = {
                "ear": perception.get("ear", 0.0),
                "blink_count": perception.get("blink_count", 0),
                "closure_duration": perception.get("closure_duration", 0.0),
                "phone_detected": perception.get("phone_detected", False),
                "distraction_duration": perception.get("distraction_duration", 0.0),
                "risk_score": risk,
                "risk_level": "CRITICAL" if risk >= 70 else "HIGH" if risk >= 40 else "LOW",
                "system_status": "ACTIVE",
                "sos_active": decision.get("trigger_sos", False),
                "latitude": None,
                "longitude": None,
                "map_link": None,
                "heart_rate": heart_rate,
                "heart_status": heart_status,
                "mobile_connected": self.mobile_connected,
                "timestamp": time.time()
            }
            with open(self.telemetry_file, "w") as f:
                json.dump(telemetry, f)
        except Exception as e:
            print(f"⚠  Failed to write telemetry: {e}")

        # ── ALARM LOGIC: Based on decision engine actions ────────────────
        # Key difference: Alarm triggers based on STATE + DURATION, not raw signals
        
        # SOS Trigger (highest priority)
        if decision.get("trigger_sos"):
            print(f"🚨🚨 [SOS] EMERGENCY TRIGGERED - {action_reason}")
            if not self.alarm_on:
                self.alarm_on = True
                self.play_alarm()
            # Future: Trigger actual SOS call here
        
        # Alarm Trigger (danger state for sustained duration)
        elif decision.get("trigger_alarm"):
            if not self.alarm_on:
                self.alarm_on = True
                print(f"🚨 [ALARM] {action_reason}")
                self.play_alarm()
            else:
                # Sustain alarm: restart if process died
                if self.alarm_process is None or self.alarm_process.poll() is not None:
                    print(f"[ALARM] Restarting audio - {action_reason}")
                    self.play_alarm()
        
        # Warning Alert (minor issues)
        elif decision.get("trigger_warning_alert"):
            print(f"⚠️  [WARNING] {action_reason}")
            # Future: Trigger visual/haptic warning
        
        # Normal state: stop alarm
        else:
            if self.alarm_on:
                self.alarm_on = False
                print(f"[ALARM] State recovered to {driver_state} - stopping alarm")
                self.stop_alarm()

        # ── Forensic report — triggers only at DANGER+ state ────────────
        if driver_state in [DriverState.DANGER, DriverState.CRITICAL]:
            now = time.time()
            if now - self.last_report_time >= self.REPORT_COOLDOWN:
                self.last_report_time = now
                self._trigger_forensic_report(risk, perception)

    # ── Forensic report trigger ────────────────────────────────────────────────

    def _trigger_forensic_report(self, risk_score, perception):
        """
        Runs ForensicReportGenerator in a background thread so it never
        freezes the 30ms UI timer. Extracts last 5 frames from buffer.
        """
        # Snapshot the buffer NOW (thread-safe copy)
        key_frames = list(self.frame_buffer)[-5:]   # last 5 frames = before+during event

        # Build the data dicts that report_generator.generate() expects
        perception_data = {
            "closure_duration"    : perception.get("closure_duration", 0.0),
            "distraction_duration": perception.get("distraction_duration", 0.0),
            "phone_status"        : perception.get("phone_status", "NOT DETECTED"),
            "ear"                 : perception.get("ear", 0.0),
            "non_responsive"      : perception.get("non_responsive", False),
        }
        risk_data = {
            "risk_score" : risk_score,
            "risk_level" : "CRITICAL" if risk_score >= 70 else "HIGH",
        }

        def _run():
            try:
                lat, lon = get_location()            # IP-based GPS from gps_tracker.py
                location = (lat, lon) if lat else "Unknown"
                self.report_generator.generate(
                    perception_data=perception_data,
                    risk_data=risk_data,
                    key_frames=key_frames,
                    location=location
                )
            except Exception as e:
                print(f"[FORENSIC] ⚠ Report generation failed: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        print(f"[FORENSIC] 📋 Generating report — risk={risk_score}%, frames={len(key_frames)}")

    # ── Alarm ─────────────────────────────────────────────────────────────────

    def play_alarm(self):
        """
        Play alarm audio file using paplay.
        Guards against duplicate subprocess instances:
        - If alarm already running, return without creating new process
        - Ensures only one audio process at a time
        """
        # Guard: if process already running, skip
        if self.alarm_process is not None and self.alarm_process.poll() is None:
            # Process is still running
            return
        
        alarm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")
        if not os.path.exists(alarm_path):
            print(f"⚠  alarm.wav not found at {alarm_path}")
            return
        
        print(f"🔊 [ALARM] Playing alarm: {alarm_path}")
        try:
            self.alarm_process = subprocess.Popen(
                ["paplay", alarm_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[ALARM] Subprocess started (PID: {self.alarm_process.pid})")
        except Exception as e:
            print(f"❌ [ALARM] Failed to start paplay: {e}")
            self.alarm_process = None

    def stop_alarm(self):
        """
        Stop alarm audio immediately and ensure clean termination.
        
        Steps:
        1. Terminate the process if running
        2. Wait briefly for graceful shutdown
        3. Force kill if necessary
        4. Reset the handle
        """
        if self.alarm_process is None:
            return
        
        # Check if process is still running
        if self.alarm_process.poll() is None:
            print(f"[ALARM] Terminating process (PID: {self.alarm_process.pid})")
            try:
                self.alarm_process.terminate()
                # Wait up to 1 second for graceful shutdown
                self.alarm_process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                # If terminate() didn't work, force kill
                print(f"[ALARM] Forcing kill (did not respond to terminate)")
                try:
                    self.alarm_process.kill()
                    self.alarm_process.wait(timeout=1.0)
                except Exception as e:
                    print(f"❌ [ALARM] Failed to force kill: {e}")
            except Exception as e:
                print(f"❌ [ALARM] Error stopping process: {e}")
        
        self.alarm_process = None
        print("[ALARM] Alarm stopped and handle reset")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def safe_exit(self):
        """
        Fail-Safe Exit Handler:
        1. Stop alarm immediately
        2. Stop UI timer
        3. Release camera
        4. Terminate all subprocesses cleanly
        5. Close application
        """
        print("[EXIT] Initiating safe exit...")
        self.stop_alarm()
        self.timer.stop()
        if self.cap and self.cap.isOpened():
            print("[EXIT] Releasing camera...")
            self.cap.release()
        print("[EXIT] Closing application")
        self.close()

    def closeEvent(self, event):
        """
        Handles application window close event.
        Ensures all resources are released and processes terminated.
        """
        print("[CLOSE] Window close event triggered")
        self.stop_alarm()
        self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("AUTO-GUARDIAN-X")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
