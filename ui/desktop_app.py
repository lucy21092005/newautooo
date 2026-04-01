import sys
import os
import json 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from PIL import Image, ImageTk
import cv2


from core.perception_pipeline import PerceptionPipeline
from core.risk_evaluator import RiskEvaluator
from core.model_manager import ModelManager

# ================= INITIALIZE SYSTEM =================

model_manager = ModelManager("../driver_risk_model.pkl")
risk_evaluator = RiskEvaluator(model_manager)
pipeline = PerceptionPipeline()
#pipeline = PerceptionPipeline()


cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

running = False


def get_real_data():
    try:
        with open(TELEMETRY_FILE, "r") as f:
            data = json.load(f)
            return data
    except:
        return None


# ================= FUNCTIONS =================

def start_monitoring():
    global running
    running = True
    update_frame()


def stop_monitoring():
    global running
    running = False


def update_frame():
    global running

    if not running:
        return

    data = get_real_data()

    def update_frame():
     global running

    if not running:
        return

    ret, frame = cap.read()

    if ret:
        frame_ai = cv2.resize(frame, (416, 416))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = img.resize((600, 400))
        imgtk = ImageTk.PhotoImage(image=img)

        video_label.imgtk = imgtk
        video_label.config(image=imgtk)

        perception_data = pipeline.process(frame_ai)
        risk_data = risk_evaluator.evaluate(perception_data)

        risk_score = risk_data["risk_score"]

        if risk_score < 30:
            status_text = "SAFE"
            color = GREEN
        elif risk_score < 70:
            status_text = "WARNING"
            color = ORANGE
        else:
            status_text = "DANGER"
            color = RED

        readiness_value.config(text=f"{int(risk_score)}%", fg=color)
        attention_value.config(text=status_text, fg=color)

    else:
        readiness_value.config(text="--%", fg=TEXT_SECONDARY)
        attention_value.config(text="NO CAMERA", fg=TEXT_SECONDARY)

    # LOOP (IMPORTANT)
    root.after(100, update_frame)

    # Fake camera preview
    video_label.config(
        text="Camera Preview",
        fg=TEXT_SECONDARY,
        bg="black",
        font=("Arial", 14)
    )

    # Loop
    root.after(500, update_frame)


def on_close():
    global running
    running = False

    if cap:
        cap.release()

    cv2.destroyAllWindows()
    root.destroy()


def create_row(parent, label_text, value_text):
    row = tk.Frame(parent, bg=BG_PANEL)
    row.pack(fill="x", pady=10, padx=10)

    tk.Label(
        row,
        text=label_text,
        fg=TEXT_SECONDARY,
        bg=BG_PANEL,
        anchor="w"
    ).pack(side="left")

    value = tk.Label(
        row,
        text=value_text,
        fg=TEXT_PRIMARY,
        bg=BG_PANEL,
        anchor="e"
    )
    value.pack(side="right")

    return value


# ================= COLOR SYSTEM =================

BG_MAIN = "#0f172a"      # main background
BG_PANEL = "#1e293b"     # panels (camera + right)
BG_HEADER = "#020617"    # header + bottom

TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#94a3b8"

GREEN = "#22c55e"
ORANGE = "#f59e0b"
RED = "#ef4444"


# ================= UI SETUP =================

root = tk.Tk()
root.geometry("1100x650")
root.title("AUTO-GUARDIAN-X")

root.geometry("900x600")
root.minsize(800, 500)

# ROOT GRID CONTROL

root.rowconfigure(0, weight=0)  # Header → fixed height
root.rowconfigure(1, weight=1)  # Main → expands (MOST IMPORTANT)
root.rowconfigure(2, weight=0)  # Bottom → fixed height

root.columnconfigure(0, weight=1)  # Full width

# ===== HEADER =====
header_frame = tk.Frame(root, bg=BG_HEADER, height=50)
header_frame.grid(row=0, column=0, sticky="ew")

tk.Label(
    header_frame,
    text="AUTO-GUARDIAN-X",
    bg=BG_HEADER,
    fg="white",
    font=("Arial", 20, "bold")
).pack(pady=10)

# ===== MAIN AREA =====
main_frame = tk.Frame(root, bg=BG_MAIN)
main_frame.grid(row=1, column=0, sticky="nsew")

main_frame.columnconfigure(0, weight=3)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# Video Frame (LEFT)
video_frame = tk.Frame(main_frame, bg=BG_PANEL)
video_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)

tk.Label(
    video_frame,
    text="Live  Feed",
    bg=BG_PANEL,
    fg=TEXT_SECONDARY,
    font=("Arial", 10, "bold")
).pack(anchor="n")

video_inner_frame = tk.Frame(video_frame, bg=BG_PANEL)
video_inner_frame.pack(fill="both", expand=True, padx=5, pady=5)

video_label = tk.Label(video_inner_frame, bg=BG_PANEL)
video_label.pack(fill="both", expand=True)

# Info Frame (RIGHT)
info_frame = tk.Frame(main_frame, bg=BG_PANEL)
info_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=10)

tk.Label(
    info_frame,
    text="STATUS",
    font=("Arial", 12, "bold"),
    fg=TEXT_SECONDARY,
    bg=BG_PANEL,
    anchor="w"
).pack(fill="x", padx=10, pady=10)

metrics_frame = tk.Frame(info_frame, bg=BG_PANEL)
metrics_frame.pack(fill="both", expand=True, pady=10)

readiness_value = create_row(metrics_frame, "Driver Readiness", "0%")
heart_value = create_row(metrics_frame, "Heart Rate", "72 BPM")
attention_value = create_row(metrics_frame, "Attention State", "Focused")

# ===== CONTROL PANEL =====
control_frame = tk.Frame(root, bg=BG_HEADER, height=80)
control_frame.grid(row=2, column=0, sticky="ew")

control_frame.columnconfigure(0, weight=1)  # LEFT (info)
control_frame.columnconfigure(1, weight=1)  # RIGHT (buttons)

info_bottom_frame = tk.Frame(control_frame)
info_bottom_frame.grid(row=0, column=0, sticky="w", padx=15)

tk.Label(
    info_bottom_frame,
    text="Mobile Sync: Active\nLocation: Enabled\nEmergency: Armed",
    bg=BG_HEADER,
    fg=TEXT_SECONDARY
).pack(anchor="w")

button_frame = tk.Frame(control_frame)
button_frame.grid(row=0, column=1, sticky="e", padx=15)

start_btn = tk.Button(button_frame, text="Start", width=10, bg="#4CAF50", fg="white", relief="flat", bd=0)
stop_btn = tk.Button(button_frame, text="Stop", width=10, bg="#f0ad4e", fg="black", relief="flat", bd=0)
exit_btn = tk.Button(button_frame, text="Exit", width=10, bg="#d9534f", fg="white", relief="flat", bd=0)

# Attach commands separately (clean)
start_btn.config(command=start_monitoring)
stop_btn.config(command=stop_monitoring)
exit_btn.config(command=on_close)

start_btn.pack(side="left", padx=5, pady=10)
stop_btn.pack(side="left", padx=5, pady=10)
exit_btn.pack(side="left", padx=5, pady=10)

# ================= RUN =================

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()

if cap:
    cap.release()