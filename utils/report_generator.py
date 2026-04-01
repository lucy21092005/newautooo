import os
import cv2
from fpdf import FPDF           # fpdf2 uses same import name — compatible
from datetime import datetime


class ForensicReportGenerator:
    """
    Generates a local PDF forensic report whenever a critical driver event occurs.
    Called from pyqt_app.py when risk score crosses the CRITICAL threshold.

    Inputs (passed to .generate()):
        perception_data  — dict from PerceptionPipeline.process()
        risk_data        — dict from RiskEvaluator.evaluate()  (or pyqt_app scores)
        key_frames       — list of OpenCV BGR frames from the circular buffer
        location         — (lat, lon) tuple from gps_tracker, or "Unknown"

    Output:
        Saves a PDF to /reports/ directory and returns the file path.
    """

    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)     # create folder if missing

    # ── Main entry point ──────────────────────────────────────────────────────

    def generate(self, perception_data, risk_data, key_frames, location="Unknown"):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_filename = os.path.join(self.output_dir, f"Forensic_Report_{timestamp}.pdf")

        # ── Step 1: Save key frames as temp JPEGs (fpdf can't embed raw ndarray) ──
        saved_image_paths = []
        for i, frame in enumerate(key_frames):
            img_path = os.path.join(self.output_dir, f"temp_evidence_{timestamp}_{i}.jpg")
            cv2.imwrite(img_path, frame)
            saved_image_paths.append(img_path)

        # ── Step 2: Build the PDF ─────────────────────────────────────────────
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(0, 10, "AUTO-GUARDIAN-X: FORENSIC EVENT REPORT", ln=True, align="C")
        pdf.ln(4)
        pdf.set_draw_color(30, 58, 95)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # Event details
        pdf.set_font("Helvetica", size=11)
        pdf.set_fill_color(240, 245, 255)

        def row(label, value):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(55, 8, label, ln=False)
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 8, str(value), ln=True)

        row("Date & Time :", datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        row("Location    :", location if isinstance(location, str)
                             else f"Lat {location[0]:.4f}, Lon {location[1]:.4f}")
        row("Event Type  :", "Driver Unresponsive - CRITICAL")
        row("Risk Level  :", f"{risk_data.get('risk_level', 'HIGH')}  "
                             f"(Score: {risk_data.get('risk_score', 'N/A')})")
        pdf.ln(5)

        # Behavioral indicators section
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, "Behavioral Indicators", ln=True)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_font("Helvetica", size=10)
        closure   = perception_data.get("closure_duration", 0.0)
        distract  = perception_data.get("distraction_duration", 0.0)
        phone     = perception_data.get("phone_status", "NOT DETECTED")
        ear_val   = perception_data.get("ear", 0.0)
        non_resp  = perception_data.get("non_responsive", False)

        pdf.cell(0, 7, f"  -  Eye Closure Duration   : {closure:.2f} sec", ln=True)
        pdf.cell(0, 7, f"  -  Distraction Duration   : {distract:.2f} sec", ln=True)
        pdf.cell(0, 7, f"  -  Phone Detected         : {phone}", ln=True)
        pdf.cell(0, 7, f"  -  EAR Value              : {ear_val:.3f}", ln=True)
        pdf.cell(0, 7, f"  -  Non-Responsive Flag    : {non_resp}", ln=True)
        pdf.cell(0, 7, f"  -  Heart Rate (simulated) : 72 BPM", ln=True)
        pdf.ln(6)

        # ── Step 3: Evidence images ───────────────────────────────────────────
        if saved_image_paths:
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, "Photographic Evidence (Frames from event window):", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            # Lay up to 3 images side by side (60mm wide each)
            x_start = 10
            y_start = pdf.get_y()
            for i, img_path in enumerate(saved_image_paths[:3]):
                x = x_start + (i * 65)
                pdf.image(img_path, x=x, y=y_start, w=60, h=45)

            pdf.ln(55)  # skip past image row
            pdf.set_font("Helvetica", style="I", size=8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 6, f"  {len(saved_image_paths)} frame(s) captured from circular buffer.", ln=True)
            pdf.set_text_color(0, 0, 0)

        # ── Step 4: Footer ────────────────────────────────────────────────────
        pdf.ln(8)
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Generated by AUTO-GUARDIAN-X  |  Forensic Evidence Document  |  Do not alter.",
                 ln=True, align="C")
        pdf.set_text_color(0, 0, 0)

        # ── Step 5: Save PDF + clean up temp images ───────────────────────────
        pdf.output(pdf_filename)

        for img_path in saved_image_paths:
            if os.path.exists(img_path):
                os.remove(img_path)

        print(f"[FORENSIC] ✅ Report saved → {pdf_filename}")
        return pdf_filename