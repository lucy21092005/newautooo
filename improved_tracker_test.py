#!/usr/bin/env python3
"""
Enhanced Heart Rate Tracker with detailed diagnostics
"""

import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import cv2
import mediapipe as mp
import numpy as np
from scipy import signal
import time

# Configuration
BUFFER_SIZE = 150
MIN_HR = 45.0
MAX_HR = 180.0

# Landmarks for rPPG
FOREHEAD = [9, 107, 66, 105, 104, 103, 67, 109, 10, 338, 297, 332, 333, 334, 335, 336]
LEFT_CHEEK = [117, 118, 119, 100, 116, 111, 120]
RIGHT_CHEEK = [346, 347, 348, 329, 345, 340, 349]

class ImprovedHeartRateTracker:
    """Improved heart rate tracker with better signal processing"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,  # Better accuracy
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except Exception as e:
            print(f"❌ Failed to init: {e}")
            self.face_mesh = None
        
        self.signal_buffer = []
        self.times = []
        self.stable_bpm = 0.0
        self.face_detected_count = 0
        
    def process_frame(self, frame):
        if self.face_mesh is None or frame is None or frame.size == 0:
            return 0.0
        
        try:
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                self.face_detected_count += 1
                for face_landmarks in results.multi_face_landmarks:
                    # Extract cheek region (more stable than forehead)
                    region_indices = LEFT_CHEEK + RIGHT_CHEEK
                    
                    pixels = []
                    for idx in region_indices:
                        if idx < len(face_landmarks.landmark):
                            lm = face_landmarks.landmark[idx]
                            x = int(lm.x * w)
                            y = int(lm.y * h)
                            x = max(0, min(w - 1, x))
                            y = max(0, min(h - 1, y))
                            if 0 <= y < h and 0 <= x < w:
                                pixel_val = frame[y, x, :]
                                pixels.append(pixel_val)
                    
                    if len(pixels) > 0:
                        pixels = np.array(pixels, dtype=np.float32)
                        # Green channel (standard for rPPG)
                        green_vals = pixels[:, 1]
                        normalized = np.mean(green_vals) / (np.mean(pixels) + 1e-6)
                        
                        self.signal_buffer.append(normalized)
                        self.times.append(time.time())
                        
                        if len(self.signal_buffer) > BUFFER_SIZE:
                            self.signal_buffer.pop(0)
                            self.times.pop(0)
                        
                        if len(self.signal_buffer) == BUFFER_SIZE:
                            self._calculate_bpm()
            
            return self.stable_bpm
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error: {e}")
            return self.stable_bpm
    
    def _calculate_bpm(self):
        try:
            if len(self.times) < 2:
                return
            
            time_elapsed = self.times[-1] - self.times[0]
            if time_elapsed <= 0:
                return
            
            actual_fps = BUFFER_SIZE / time_elapsed
            signal_array = np.array(self.signal_buffer, dtype=np.float64)
            
            # Preprocessing
            signal_array = signal_array - np.mean(signal_array)
            
            # Smooth
            window_len = 11 if len(signal_array) >= 11 else (len(signal_array) - 1) if len(signal_array) % 2 == 0 else len(signal_array)
            if window_len < 5:
                window_len = 5
            if window_len % 2 == 0:
                window_len += 1
            
            smoothed = signal.savgol_filter(signal_array, window_len, 2)
            detrended = signal.detrend(smoothed)
            
            # Bandpass filter
            nyquist = actual_fps / 2.0
            low_norm = (MIN_HR / 60.0) / nyquist
            high_norm = (MAX_HR / 60.0) / nyquist
            low_norm = max(0.001, min(0.999, low_norm))
            high_norm = max(0.001, min(0.999, high_norm))
            
            if low_norm >= high_norm:
                high_norm = low_norm + 0.05
            if high_norm > 0.999:
                high_norm = 0.999
            
            try:
                b, a = signal.butter(4, [low_norm, high_norm], btype='band')
                filtered = signal.filtfilt(b, a, detrended)
            except:
                filtered = detrended
            
            # FFT
            fft_data = np.fft.rfft(filtered)
            fft_freqs = np.fft.rfftfreq(len(filtered), 1.0 / actual_fps)
            
            magnitude = np.abs(fft_data[1:])
            freqs = fft_freqs[1:]
            
            hr_min_freq = MIN_HR / 60.0
            hr_max_freq = MAX_HR / 60.0
            valid_mask = (freqs >= hr_min_freq) & (freqs <= hr_max_freq)
            
            if np.sum(valid_mask) > 0:
                valid_mag = magnitude[valid_mask]
                valid_freqs = freqs[valid_mask]
                peak_idx = np.argmax(valid_mag)
                peak_freq = valid_freqs[peak_idx]
                raw_bpm = peak_freq * 60.0
                
                if 40 <= raw_bpm <= 200:
                    if self.stable_bpm == 0.0:
                        self.stable_bpm = raw_bpm
                    else:
                        self.stable_bpm = 0.1 * raw_bpm + 0.9 * self.stable_bpm  # More responsive
                    
                    if self.verbose:
                        print(f"  ✓ Raw: {raw_bpm:.1f} BPM | Stable: {self.stable_bpm:.1f} BPM | FPS: {actual_fps:.1f}")
        except Exception as e:
            if self.verbose:
                print(f"  ❌ BPM calc error: {e}")
    
    def get_heart_rate(self):
        return self.stable_bpm
    
    def get_heart_status(self):
        bpm = self.stable_bpm
        if bpm == 0:
            return "NO_SIGNAL"
        elif bpm < 60:
            return "LOW"
        elif bpm <= 100:
            return "NORMAL"
        elif bpm <= 120:
            return "HIGH"
        else:
            return "VERY_HIGH"


if __name__ == "__main__":
    print("=" * 70)
    print("IMPROVED HEART RATE TRACKER TEST")
    print("=" * 70)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        exit(1)
    
    print("✅ Camera opened")
    
    # Create tracker
    tracker = ImprovedHeartRateTracker(verbose=True)
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            bpm = tracker.process_frame(frame)
            status = tracker.get_heart_status()
            
            # Display every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                buffer_fill = len(tracker.signal_buffer)
                print(f"Frame {frame_count:4d} | Buffer: {buffer_fill:3d}/150 | BPM: {bpm:6.1f} | Status: {status:10s} | FPS: {fps:.1f}")
            
            # Show result on frame
            if frame_count > 150:  # Wait for buffer to fill
                h, w = frame.shape[:2]
                text = f"BPM: {bpm:.0f} ({status})"
                cv2.putText(frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
            
            cv2.imshow('Heart Rate Tracker', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 70)
        print(f"Final BPM: {tracker.get_heart_rate():.1f}")
        print(f"Final Status: {tracker.get_heart_status()}")
        print(f"Faces detected: {tracker.face_detected_count}")
        print(f"Frames processed: {frame_count}")
