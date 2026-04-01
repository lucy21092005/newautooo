import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 

import cv2
import mediapipe as mp
import numpy as np
from scipy import signal
import time

# --- Configuration & Tuning ---
BUFFER_SIZE = 150       # 5 seconds of data at 30fps
FPS_ASSUMPTION = 30     
MIN_HR = 45.0           
MAX_HR = 180.0          

# --- Sensor Regions ---
FOREHEAD = [9, 107, 66, 105, 104, 103, 67, 109, 10, 338, 297, 332, 333, 334, 335, 336]
LEFT_CHEEK = [117, 118, 119, 100, 116, 111, 120]
RIGHT_CHEEK = [346, 347, 348, 329, 345, 340, 349]


class HeartRateTracker:
    """
    Silent heart rate tracker that integrates into the main perception pipeline.
    No UI, no window. Just processes frames and returns BPM values.
    """
    
    def __init__(self):
        """Initialize the tracker with MediaPipe face mesh."""
        # Initialize MediaPipe
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1, 
                refine_landmarks=True,  # Better accuracy
                min_detection_confidence=0.5, 
                min_tracking_confidence=0.5
            )
        except Exception as e:
            print(f"❌ HeartRateTracker ERROR: {e}")
            self.face_mesh = None
        
        # Signal buffers
        self.signal_buffer = []
        self.times = []
        self.stable_bpm = 0.0
        self.wave_to_plot = np.zeros(BUFFER_SIZE)
        self.last_valid_bpm = 0.0
        
    def build_bandpass_filter(self, fps, min_hr, max_hr):
        """Build bandpass filter for heart rate extraction"""
        nyquist = 0.5 * fps
        low = (min_hr / 60.0) / nyquist
        high = (max_hr / 60.0) / nyquist
        
        # Clamp frequencies to valid range
        low = max(0.001, min(0.999, low))
        high = max(0.001, min(0.999, high))
        
        if low >= high:
            high = low + 0.05
        if high > 0.999:
            high = 0.999
        
        try:
            b, a = signal.butter(4, [low, high], btype='band')
            return b, a
        except Exception as e:
            print(f"⚠️  Filter design failed: {e}")
            return None, None
    
    def process_frame(self, frame):
        """
        Extract heart rate from a frame.
        
        Args:
            frame: OpenCV BGR frame
            
        Returns:
            float: Current BPM value (0.0 if no signal)
        """
        if self.face_mesh is None:
            return 0.0
        
        try:
            if frame is None or frame.size == 0:
                return self.stable_bpm
            
            h, w, _ = frame.shape
            
            # Ensure frame is valid
            if h < 100 or w < 100:
                return self.stable_bpm
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            # Create mask for skin regions
            mask = np.zeros((h, w), dtype=np.uint8)
            face_detected = False
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    face_detected = True
                    
                    def get_region_pixels(indices):
                        """Extract pixel coordinates for a set of landmark indices"""
                        points = []
                        for idx in indices:
                            if idx < len(face_landmarks.landmark):
                                lm = face_landmarks.landmark[idx]
                                x = int(lm.x * w)
                                y = int(lm.y * h)
                                # Clamp to image bounds
                                x = max(0, min(w - 1, x))
                                y = max(0, min(h - 1, y))
                                points.append((x, y))
                        return np.array(points, np.int32) if points else None
                    
                    # Fill the mask with the key regions (forehead, cheeks)
                    regions = [
                        get_region_pixels(FOREHEAD), 
                        get_region_pixels(LEFT_CHEEK), 
                        get_region_pixels(RIGHT_CHEEK)
                    ]
                    
                    for region in regions:
                        if region is not None and len(region) > 0:
                            cv2.fillPoly(mask, [region], 255)
                
                # Extract mean color from masked region
                if np.sum(mask) > 0:
                    mean_colors = cv2.mean(frame, mask=mask)
                    b_val, g_val, r_val, _ = mean_colors
                    
                    # Use chrominance normalization (standard for rPPG)
                    total_intensity = r_val + g_val + b_val
                    
                    if total_intensity > 1:
                        # Normalize - use green channel primarily
                        normalized_value = g_val / total_intensity
                        
                        # Add to signal buffer
                        self.signal_buffer.append(normalized_value)
                        self.times.append(time.time())
                        
                        # Maintain buffer size
                        if len(self.signal_buffer) > BUFFER_SIZE:
                            self.signal_buffer.pop(0)
                            self.times.pop(0)
                        
                        # Calculate BPM when buffer is full
                        if len(self.signal_buffer) == BUFFER_SIZE:
                            self._calculate_bpm()
            
            return self.stable_bpm
            
        except Exception as e:
            # Silently handle errors to not spam logs
            return self.stable_bpm
    
    def _calculate_bpm(self):
        """Internal method to calculate BPM from the signal buffer"""
        try:
            time_elapsed = self.times[-1] - self.times[0]
            if time_elapsed <= 0:
                return  # Avoid division by zero
            
            actual_fps = BUFFER_SIZE / time_elapsed
            
            # Convert to numpy array
            signal_array = np.array(self.signal_buffer, dtype=np.float64)
            
            # Remove DC component (subtract mean)
            signal_array = signal_array - np.mean(signal_array)
            
            # Apply Savitzky-Golay filter with careful window length
            window_len = min(11, len(signal_array) - 1 if len(signal_array) % 2 == 0 else len(signal_array))
            if window_len < 5:
                window_len = 5
            if window_len % 2 == 0:  # Must be odd
                window_len += 1
            
            smoothed_signal = signal.savgol_filter(signal_array, window_length=window_len, polyorder=2)
            
            # Detrend
            detrended_signal = signal.detrend(smoothed_signal)
            
            # Build bandpass filter
            nyquist_freq = actual_fps / 2.0
            low_freq = MIN_HR / 60.0  # Hz
            high_freq = MAX_HR / 60.0  # Hz
            
            # Normalize frequencies to Nyquist
            low_normalized = low_freq / nyquist_freq
            high_normalized = high_freq / nyquist_freq
            
            # Ensure frequencies are in valid range (0, 1)
            low_normalized = max(0.001, min(0.999, low_normalized))
            high_normalized = max(0.001, min(0.999, high_normalized))
            
            if low_normalized >= high_normalized:
                high_normalized = low_normalized + 0.1
            if high_normalized > 0.999:
                high_normalized = 0.999
            
            try:
                b, a = signal.butter(4, [low_normalized, high_normalized], btype='band')
                filtered_signal = signal.filtfilt(b, a, detrended_signal)
            except Exception as e:
                print(f"⚠️  Filter design failed: {e}")
                filtered_signal = detrended_signal
            
            self.wave_to_plot = filtered_signal.copy()
            
            # FFT to find dominant frequency
            fft_data = np.fft.rfft(filtered_signal)
            fft_freqs = np.fft.rfftfreq(len(filtered_signal), 1.0 / actual_fps)
            
            # Get magnitude spectrum (skip DC component)
            magnitude = np.abs(fft_data[1:])
            freqs = fft_freqs[1:]
            
            # Find peaks in the HR range
            hr_min_freq = MIN_HR / 60.0
            hr_max_freq = MAX_HR / 60.0
            
            # Filter to HR range
            valid_indices = (freqs >= hr_min_freq) & (freqs <= hr_max_freq)
            
            if np.sum(valid_indices) > 0:
                peak_idx = np.argmax(magnitude[valid_indices])
                valid_freqs = freqs[valid_indices]
                peak_freq = valid_freqs[peak_idx]
                raw_bpm = peak_freq * 60.0
                
                # Validate BPM
                if 40 <= raw_bpm <= 200:
                    if self.stable_bpm == 0.0:
                        self.stable_bpm = raw_bpm
                    else:
                        # Exponential moving average: 10% new, 90% history (more responsive)
                        self.stable_bpm = (0.10 * raw_bpm) + (0.90 * self.stable_bpm)
                    
                    # Debug output every so often
                    if int(time.time() * 10) % 100 == 0:
                        print(f"[HR] BPM: {self.stable_bpm:.1f}, Raw: {raw_bpm:.1f}, Peak Freq: {peak_freq:.2f}Hz")
            else:
                # No valid frequencies found in HR range
                pass
                
        except Exception as e:
            print(f"⚠️  BPM calculation error: {e}")
    
    def get_heart_rate(self):
        """Get current heart rate in BPM"""
        return self.stable_bpm
    
    def get_heart_status(self):
        """Get heart rate status classification"""
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

# LEGACY: The old standalone app code was here
# Now converted to HeartRateTracker class above
# To test tracker independently, instantiate and call:
#   tracker = HeartRateTracker()
#   while True:
#       ret, frame = cap.read()
#       if ret:
#           bpm = tracker.process_frame(frame)