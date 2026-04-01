#!/usr/bin/env python3
"""
Debug script to diagnose BPM reading issues
"""

import cv2
import numpy as np
from core.tracker import HeartRateTracker
import time

print("=" * 70)
print("HEART RATE TRACKER DEBUG")
print("=" * 70)

# Create tracker
tracker = HeartRateTracker()

# Try to open camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Camera not available - using synthetic frames")
    cap = None
else:
    print("✅ Camera opened")

frame_count = 0
start_time = time.time()

try:
    for i in range(300):  # Process 300 frames (~10 seconds at 30fps)
        if cap is not None:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break
        else:
            # Create synthetic frame
            frame = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
        
        frame_count += 1
        
        # Process frame
        bpm = tracker.process_frame(frame)
        status = tracker.get_heart_status()
        
        # Print diagnostics every 30 frames
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            buffer_fill = len(tracker.signal_buffer)
            print(f"Frame {frame_count:3d} | Buffer: {buffer_fill:3d}/150 | BPM: {bpm:6.1f} | Status: {status:10s}")
        
        # Small delay
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n❌ Interrupted by user")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if cap is not None:
        cap.release()

print("\n" + "=" * 70)
print("FINAL DIAGNOSTICS")
print("=" * 70)
print(f"Total frames processed: {frame_count}")
print(f"Final BPM: {tracker.get_heart_rate():.1f}")
print(f"Final Status: {tracker.get_heart_status()}")
print(f"Buffer size: {len(tracker.signal_buffer)}")
print(f"Times buffer size: {len(tracker.times)}")

# Check signal characteristics
if len(tracker.signal_buffer) > 0:
    signal_arr = np.array(tracker.signal_buffer)
    print(f"\nSignal Stats:")
    print(f"  Min: {signal_arr.min():.4f}")
    print(f"  Max: {signal_arr.max():.4f}")
    print(f"  Mean: {signal_arr.mean():.4f}")
    print(f"  Std Dev: {signal_arr.std():.4f}")
