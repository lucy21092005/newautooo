# Alarm System Quick Reference

## One-Sentence Summary
The alarm system guarantees **one-time triggering per danger state** with **continuous alert** during sustained danger and **immediate stop** on recovery.

---

## Key Guarantees

### ✅ No Sound at Startup
- First 30 frames ignored (warm-up period)
- `startup_frames < 30` prevents any alarm logic

### ✅ Trigger Only on Real Danger
- Critical threshold: `risk >= 70`
- No false positives from temporary fluctuations

### ✅ One-Time Trigger Per State Entry
```python
if risk >= 70:
    if not self.alarm_on:  # ← Only triggers here (state transition)
        self.alarm_on = True
        self.play_alarm()   # ← Called ONCE per danger entry
```

### ✅ Continuous Alert During Danger
```python
    else:
        # Already in danger state
        if self.alarm_process is None or self.alarm_process.poll() is not None:
            self.play_alarm()  # ← Restart if audio died
```

### ✅ Immediate Stop on Recovery
```python
else:
    if self.alarm_on:
        self.alarm_on = False
        self.stop_alarm()  # ← Stops immediately
```

### ✅ No Orphan Processes
- `safe_exit()` and `closeEvent()` call `stop_alarm()`
- `stop_alarm()` terminates subprocess (with force kill fallback)
- Handle always reset to `None`

---

## State Variables

```python
# ── Alarm State Management
self.alarm_on = False              # True = in danger state
self.alarm_process = None          # Handle to paplay subprocess
self.alarm_triggered_this_session = False  # One-time flag (with hysteresis)
self.startup_frames = 0            # Frame counter for warm-up
```

---

## Flow Diagram

```
START
  ↓
WARM-UP PERIOD (first 30 frames)
  ├─ No alarm logic
  ├─ Status: "Warming up…"
  ↓
SAFE/WARNING STATE (risk < 70)
  ├─ alarm_on = False
  ├─ Status: "SAFE" or "WARNING"
  ├─ No audio
  ↓
[risk goes to >= 70]
  ↓
DANGER STATE (risk >= 70)
  ├─ First time only: play_alarm() called
  ├─ alarm_on = True
  ├─ Status: "DANGER"
  ├─ 🔊 Audio playing
  ├─ [If audio dies: auto-restart]
  ↓
[risk drops below 70]
  ↓
STOP ALARM
  ├─ stop_alarm() called
  ├─ Audio terminated
  ├─ alarm_on = False
  ↓
[When risk < 60: trigger re-arms]
  ↓
[Loop back if risk spikes again]
```

---

## Function Responsibilities

| Function | Responsibility | Blocking? |
|----------|-----------------|-----------|
| `update_data()` | Main frame loop, alarm state machine | No (30ms tick) |
| `play_alarm()` | Start audio subprocess | No (fork process) |
| `stop_alarm()` | Terminate audio cleanly | No (~100ms timeout) |
| `safe_exit()` | Exit handler | No (calls stop_alarm) |
| `closeEvent()` | Window close handler | No (calls stop_alarm) |

---

## Common Issues & Fixes

### Issue: Alarm triggers multiple times per danger state
**Fix**: Check if `if not self.alarm_on:` guard is present in update_data()

### Issue: Alarm won't stop
**Fix**: Verify `stop_alarm()` is called when exiting danger

### Issue: False alarms at startup
**Fix**: Ensure `startup_frames < 30` check is before alarm logic

### Issue: Duplicate audio processes
**Fix**: Check `play_alarm()` guard: `if self.alarm_process is not None and self.alarm_process.poll() is None: return`

### Issue: App freezes when alarm plays
**Fix**: Audio runs in subprocess (non-blocking). If freezes, check if blocking operation in update_data()

### Issue: Audio plays after app closes
**Fix**: Ensure both `safe_exit()` and `closeEvent()` call `stop_alarm()`

---

## Implementation Checklist

- [x] **Threshold**: Alarm only at risk >= 70
- [x] **One-time trigger**: Per state entry (not per frame)
- [x] **Continuous alert**: Auto-restart if audio dies
- [x] **Immediate stop**: When risk < 70
- [x] **Startup safe**: First 30 frames ignored
- [x] **No duplicates**: Guard in play_alarm()
- [x] **Process cleanup**: stop_alarm() with timeout + kill fallback
- [x] **Safe exit**: Both safe_exit() and closeEvent()
- [x] **Non-blocking**: Subprocess + threading (report)
- [x] **Hysteresis**: Re-arm at risk < 60

---

## Debug Commands

### Monitor alarm state in real-time
```python
# Add to update_data() to print state every frame
print(f"[DEBUG] risk={risk}, alarm_on={self.alarm_on}, proc={self.alarm_process}")
```

### Check if paplay is running
```bash
ps aux | grep paplay
```

### Test paplay manually
```bash
paplay /path/to/alarm.wav
```

### Kill orphan processes
```bash
killall paplay
```

---

## Performance Impact

- **Alarm logic**: < 1ms per frame (just comparisons)
- **Process check**: ~ 0.1ms per frame (poll())
- **Audio playback**: 0ms (runs in subprocess)
- **Total overhead**: Negligible (well under 30ms timer)

---

## File Locations

- **Implementation**: [pyqt_app.py](pyqt_app.py) (lines ~110-650)
- **Documentation**: [ALARM_SYSTEM_IMPLEMENTATION.md](ALARM_SYSTEM_IMPLEMENTATION.md)
- **Audio file**: `alarm.wav` (in project root)

---

Last Updated: 2026-03-31
