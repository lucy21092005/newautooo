# 🧠 DECISION ENGINE - System Logic Flow Fixed

**Status**: ✅ **IMPLEMENTED**  
**Date**: 2026-03-31  
**What Changed**: Added core Decision Engine with proper state machine + time buffering

---

## 🎯 Problem Fixed

**Before**:
```
Detection → Immediate Alarm
(False positives, no validation, no state tracking)
```

**After**:
```
Detection → Time Validation → Data Fusion → Readiness Score → State Machine → Action
(Proper decision flow with temporal validation and state transitions)
```

---

## ✅ What Was Implemented

### 1. **Created `core/decision_engine.py`** (350+ lines)

New file with:
- **Time Buffering**: Validates signals over 30-50 frames before triggering
- **Data Fusion**: Combines EAR, phone detection, eye closure, responsiveness
- **Readiness Score**: Single 0-100 metric fusing all signals
- **State Machine**: NORMAL → WARNING → DANGER → CRITICAL
- **Action Logic**: Triggers alarm/SOS based on state + duration

### 2. **Updated `pyqt_app.py`**

- Added `DecisionEngine` import
- Instantiate decision engine in `__init__()`
- Call `decision_engine.process(perception)` for each frame
- Use decision outputs (state, readiness score, actions) instead of raw signals
- Reset decision engine on monitoring start

### 3. **Key Changes to Alarm Logic**

**OLD**:
```python
if risk > 70:  # Direct threshold
    trigger_alarm()
```

**NEW**:
```python
decision = decision_engine.process(perception)
if decision["trigger_alarm"]:  # Based on state + duration
    trigger_alarm()
```

---

## 🔧 Core Logic Flow (8 Stages)

### Stage 1: Temporal Buffering
```python
if drowsy_frame_count >= 48 frames:  # ~2 seconds
    is_drowsy = True
```
Prevents false positives from momentary glitches.

### Stage 2: Feature Extraction
Validates each signal:
- `is_drowsy` (EAR < threshold for 48+ frames)
- `is_eyes_closed` (closure_duration > 0.5s for 48+ frames)
- `is_distracted` (phone detected for 24+ frames)
- `is_no_response` (no face/blink for 30+ frames)

### Stage 3: Data Fusion (Readiness Score)
```python
readiness = 100
readiness -= 30  # if drowsy
readiness -= 40  # if eyes closed
readiness -= 25  # if distracted
readiness -= 35  # if no response
# Clamp to 0-100
```

### Stage 4: State Classification
```python
if readiness >= 70:
    state = NORMAL
elif readiness >= 50:
    state = WARNING
elif readiness >= 30:
    state = DANGER
else:
    state = CRITICAL
```

### Stage 5: State Transitions
Track:
- Current state
- Previous state
- Duration in current state (frame count)

### Stage 6: Action Decision
```python
if state == CRITICAL and duration > 750 frames:
    trigger_sos()
elif state == DANGER and duration > 48 frames:
    trigger_alarm()
elif state == WARNING and duration > 30 frames:
    trigger_warning()
else:
    no_action()
```

---

## 📊 Decision Engine Output

Each frame returns:
```python
{
    # Core metrics
    "readiness_score": 0-100,      # Lower = more risk
    "driver_state": "NORMAL|WARNING|DANGER|CRITICAL",
    "state_changed": bool,          # Did state change this frame?
    "state_duration_frames": int,   # How long in current state?
    
    # Validated signals (time-buffered)
    "is_drowsy": bool,
    "is_eyes_closed": bool,
    "is_distracted": bool,
    "is_no_response": bool,
    
    # Debug info
    "drowsy_frame_count": int,
    "closure_frame_count": int,
    "distracted_frame_count": int,
    "no_response_frame_count": int,
    
    # Actions
    "trigger_alarm": bool,
    "trigger_sos": bool,
    "trigger_warning_alert": bool,
    "action_reason": str,
}
```

---

## 🔀 State Machine Diagram

```
                    [NORMAL]
                    (>=70%)
                        ↓
                 [Risk detected]
                        ↓
                    [WARNING]
                    (50-70%)
                        ↓
              [No response / 30s pass]
                        ↓
                    [DANGER]
                    (30-50%)
                   [Alarm after 2s]
                        ↓
              [Critical state / 30s pass]
                        ↓
                   [CRITICAL]
                    (<30%)
                   [SOS after 30s]
```

---

## ⚙️ Thresholds (Configurable)

| Threshold | Value | Meaning |
|-----------|-------|---------|
| `DROWSY_FRAME_THRESHOLD` | 48 | ~2 sec of drowsiness = trigger |
| `CLOSURE_FRAME_THRESHOLD` | 48 | ~2 sec eyes closed = trigger |
| `DISTRACTED_FRAME_THRESHOLD` | 24 | ~1 sec distracted = trigger |
| `NO_RESPONSE_FRAME_THRESHOLD` | 30 | ~1.25 sec no response = trigger |
| `WARNING_READINESS_SCORE` | 70 | Readiness below this = WARNING |
| `DANGER_READINESS_SCORE` | 50 | Readiness below this = DANGER |
| `CRITICAL_READINESS_SCORE` | 30 | Readiness below this = CRITICAL |
| `ALARM_TRIGGER_DURATION_FRAMES` | 48 | Alarm after 2s in DANGER |
| `SOS_TRIGGER_DURATION_FRAMES` | 750 | SOS after 30s in CRITICAL |

---

## 🎛️ How to Adjust Behavior

### Make System More Sensitive
```python
# Reduce frame thresholds
engine.DROWSY_FRAME_THRESHOLD = 24      # 1 sec instead of 2
engine.ALARM_TRIGGER_DURATION_FRAMES = 24  # Alarm faster
```

### Make System More Lenient
```python
# Increase frame thresholds
engine.DROWSY_FRAME_THRESHOLD = 96      # 4 sec instead of 2
engine.ALARM_TRIGGER_DURATION_FRAMES = 120  # Wait longer
```

### Adjust Score Weights
```python
# Make drowsiness more severe
# In _calculate_readiness_score:
if features["is_drowsy"]:
    readiness -= 50  # Instead of 30
```

---

## 📈 Example Scenarios

### Scenario 1: Brief Blink
```
Frame 1: EAR < threshold
Frame 2-47: buffering...
Frame 48: Not enough frames yet, drowsy_count = 1
Result: is_drowsy = False (buffer resets quickly)
Alarm: NO
```

### Scenario 2: 2-Second Eye Closure
```
Frame 1-48: EAR < threshold (continuous)
Frame 49: drowsy_frame_count >= 48
Result: is_drowsy = True
Readiness score: 100 - 40 = 60 (DANGER state)
Frame 50-96: Sustained in DANGER
Frame 97: state_duration >= 48 frames
Result: trigger_alarm = True
Alarm: YES (after 2 seconds)
```

### Scenario 3: Phone Detection
```
Frame 1-24: Phone not detected
Frame 25: Phone detected
Frame 26-48: Phone detected (buffering)
Frame 49: distracted_frame_count >= 24
Result: is_distracted = True
Readiness score: 100 - 25 = 75 (WARNING state)
Result: trigger_warning_alert = True
Alarm: NO (warning only)
```

### Scenario 4: Critical No-Response
```
Frame 1-30: Face not detected (no_response_detector active)
Frame 31: no_response_frame_count >= 30
Result: is_no_response = True
Readiness score: 100 - 35 = 65 (WARNING → overridden to CRITICAL)
Frame 32-780: No response continues
Frame 781: state_duration >= 750 frames (30+ seconds)
Result: trigger_sos = True
Action: SOS call + alarm
```

---

## 🧪 Testing the New System

### Test 1: Verify Time Buffering
1. Close your eyes briefly (< 1 sec)
2. Verify: No alarm
3. Close your eyes for 2+ secs
4. Verify: Alarm triggers

### Test 2: Verify State Machine
1. Start clean: Should see "SAFE" (NORMAL state)
2. Be slightly drowsy: Should see "WARNING" (no alarm)
3. Close eyes for 2s: Should see "DANGER" + alarm

### Test 3: Verify State Duration
1. Hold drowsy state for 2+ seconds
2. Verify: Single alarm, not repeated every frame

### Test 4: Verify Recovery
1. While alarming, wake up (normal EAR)
2. Verify: Alarm stops immediately

---

## 🔍 Debug Output

Monitor console for:
```
[ALARM] CRITICAL DANGER DETECTED! - DANGER state for 50 frames
[ALARM] Restarting audio - State recovered to WARNING
⚠️  [WARNING] WARNING state for 35 frames
🚨🚨 [SOS] EMERGENCY TRIGGERED - CRITICAL state for 800 frames
```

---

## 📝 Files Modified

1. **Created**: `/core/decision_engine.py` (350+ lines)
2. **Modified**: `/pyqt_app.py`
   - Added decision engine import
   - Instantiate in `__init__()`
   - Use `decision_engine.process()` in `update_data()`
   - Trigger alarms based on decision outputs
   - Reset engine on start_monitoring()

---

## ✨ Key Improvements

✅ **Proper State Machine**: NORMAL → WARNING → DANGER → CRITICAL  
✅ **Temporal Validation**: No false positives from glitches  
✅ **Data Fusion**: Single readiness score from all signals  
✅ **Duration Tracking**: Actions based on how long in state  
✅ **Configurable Thresholds**: Easy to adjust sensitivity  
✅ **Debug Friendly**: Clear state transitions and action reasons  
✅ **Scalable**: Easy to add new signals (heart rate, etc.)  

---

## 🚀 Next Steps

1. Test all scenarios in real conditions
2. Adjust thresholds based on feedback
3. Add heart rate anomaly detection
4. Integrate mobile app SOS calls
5. Add haptic/visual alerts for WARNING state

---

**System now follows proper logic flow**: Sense → Analyze → Decide → Act ✅
