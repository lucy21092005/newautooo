"""
🧠 DECISION ENGINE - Core Logic Flow

Sense → Analyze → Decide → Act

Flow:
1. Take raw perception signals
2. Apply time buffering (temporal validation)
3. Fuse all signals into readiness score
4. Classify into states (NORMAL → WARNING → DANGER → CRITICAL)
5. Trigger actions based on state + duration
"""

class DriverState:
    """Driver state enumeration"""
    NORMAL = "NORMAL"        # All good
    WARNING = "WARNING"      # Minor issues (drowsy OR distracted)
    DANGER = "DANGER"        # Major issue (drowsy + distracted OR sustained closure)
    CRITICAL = "CRITICAL"    # No response + danger


class DecisionEngine:
    """
    Fuses perception signals into actionable decisions.
    
    Key Features:
    - Time buffering (prevents false positives)
    - Data fusion (combines all signals)
    - Readiness scoring (0-100)
    - State machine (proper transitions)
    - Duration tracking (when to escalate)
    """
    
    def __init__(self):
        """Initialize decision engine"""
        
        # ── TEMPORAL BUFFERS (Time Validation) ────────────────────────
        self.drowsy_frame_count = 0       # Consecutive frames with EAR < threshold
        self.distracted_frame_count = 0   # Consecutive frames distracted
        self.closure_frame_count = 0      # Consecutive frames eyes closed
        self.no_response_frame_count = 0  # Consecutive frames no response
        
        # ── STATE TRACKING ────────────────────────────────────────────
        self.current_state = DriverState.NORMAL
        self.prev_state = DriverState.NORMAL
        self.state_entry_frame = 0        # When did we enter current state
        self.frame_number = 0             # Global frame counter
        
        # ── THRESHOLDS (Configurable) ────────────────────────────────
        self.DROWSY_FRAME_THRESHOLD = 48   # ~2 sec at 24 fps (or 1 sec at 48fps)
        self.CLOSURE_FRAME_THRESHOLD = 48  # Same as above
        self.DISTRACTED_FRAME_THRESHOLD = 24  # ~1 sec
        self.NO_RESPONSE_FRAME_THRESHOLD = 30  # ~1.25 sec
        
        # ── STATE THRESHOLDS ─────────────────────────────────────────
        self.WARNING_READINESS_SCORE = 70   # Below this = WARNING
        self.DANGER_READINESS_SCORE = 50    # Below this = DANGER
        self.CRITICAL_READINESS_SCORE = 30  # Below this = CRITICAL
        
        # ── DURATION THRESHOLDS (for action triggers) ────────────────
        self.ALARM_TRIGGER_DURATION_FRAMES = 48   # Alarm after 2 sec in DANGER
        self.SOS_TRIGGER_DURATION_FRAMES = 750    # SOS after 30+ sec in CRITICAL
        
        # ── HEART RATE DETECTION ──────────────────────────────────────
        self.heart_rate_anomaly = False
        self.prev_heart_rate = 60
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 1: TIME BUFFERING (Temporal Validation)
    # ────────────────────────────────────────────────────────────────────
    
    def _update_temporal_buffers(self, perception):
        """
        Apply time buffering to all signals.
        Prevents false positives from single-frame glitches.
        """
        
        # Drowsiness buffer (EAR-based)
        if perception.get("drowsiness_status") == "DROWSY":
            self.drowsy_frame_count += 1
        else:
            self.drowsy_frame_count = 0
        
        # Closure buffer (closure_duration-based)
        closure_dur = perception.get("closure_duration", 0.0)
        if closure_dur > 0.5:  # Eyes closed > 500ms
            self.closure_frame_count += 1
        else:
            self.closure_frame_count = 0
        
        # Distraction buffer (phone detection)
        if perception.get("phone_detected"):
            self.distracted_frame_count += 1
        else:
            self.distracted_frame_count = 0
        
        # No response buffer
        if perception.get("non_responsive"):
            self.no_response_frame_count += 1
        else:
            self.no_response_frame_count = 0
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 2: FEATURE EXTRACTION & VALIDATION
    # ────────────────────────────────────────────────────────────────────
    
    def _extract_validated_features(self, perception):
        """
        Extract features with temporal validation.
        Only report signals that pass time threshold.
        """
        
        features = {
            "is_drowsy": self.drowsy_frame_count >= self.DROWSY_FRAME_THRESHOLD,
            "is_eyes_closed": self.closure_frame_count >= self.CLOSURE_FRAME_THRESHOLD,
            "is_distracted": self.distracted_frame_count >= self.DISTRACTED_FRAME_THRESHOLD,
            "is_no_response": self.no_response_frame_count >= self.NO_RESPONSE_FRAME_THRESHOLD,
            
            # Raw values (for scoring)
            "ear": perception.get("ear", 0.0),
            "closure_duration": perception.get("closure_duration", 0.0),
            "phone_detected": perception.get("phone_detected", False),
            "non_responsive": perception.get("non_responsive", False),
            
            # Buffer counts
            "drowsy_frame_count": self.drowsy_frame_count,
            "distracted_frame_count": self.distracted_frame_count,
            "closure_frame_count": self.closure_frame_count,
            "no_response_frame_count": self.no_response_frame_count,
        }
        
        return features
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 3: DATA FUSION (Readiness Score)
    # ────────────────────────────────────────────────────────────────────
    
    def _calculate_readiness_score(self, features):
        """
        Fuse all signals into single readiness score (0-100).
        
        100 = Perfect driver
        0 = Complete failure
        """
        
        readiness = 100
        
        # Drowsiness penalty
        if features["is_drowsy"]:
            readiness -= 30
        elif features["drowsy_frame_count"] > 0:
            # Partial penalty for not-quite-there drowsiness
            readiness -= int(10 * features["drowsy_frame_count"] / self.DROWSY_FRAME_THRESHOLD)
        
        # Eyes closed penalty (more severe)
        if features["is_eyes_closed"]:
            readiness -= 40
        elif features["closure_frame_count"] > 0:
            readiness -= int(20 * features["closure_frame_count"] / self.CLOSURE_FRAME_THRESHOLD)
        
        # Distraction penalty
        if features["is_distracted"]:
            readiness -= 25
        elif features["phone_detected"]:
            readiness -= int(15 * features["distracted_frame_count"] / self.DISTRACTED_FRAME_THRESHOLD)
        
        # Non-responsive penalty (severe)
        if features["is_no_response"]:
            readiness -= 35
        
        # Heart rate anomaly penalty
        if self.heart_rate_anomaly:
            readiness -= 20
        
        # Clamp to 0-100
        readiness = max(0, min(100, readiness))
        
        return readiness
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 4: STATE CLASSIFICATION (State Machine)
    # ────────────────────────────────────────────────────────────────────
    
    def _classify_state(self, readiness, features):
        """
        Classify driver state based on readiness score + features.
        
        State transitions:
        NORMAL (>=70) → WARNING (50-70) → DANGER (30-50) → CRITICAL (<30)
        """
        
        # Determine new state based on readiness score
        if readiness >= self.WARNING_READINESS_SCORE:
            new_state = DriverState.NORMAL
        elif readiness >= self.DANGER_READINESS_SCORE:
            new_state = DriverState.WARNING
        elif readiness >= self.CRITICAL_READINESS_SCORE:
            new_state = DriverState.DANGER
        else:
            new_state = DriverState.CRITICAL
        
        # Override: If no response detected, force CRITICAL
        if features["is_no_response"]:
            new_state = DriverState.CRITICAL
        
        # Override: If both drowsy AND distracted, force DANGER at minimum
        if features["is_drowsy"] and features["is_distracted"]:
            if new_state != DriverState.CRITICAL:
                new_state = DriverState.DANGER
        
        return new_state
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 5: STATE TRANSITION TRACKING
    # ────────────────────────────────────────────────────────────────────
    
    def _update_state_transitions(self, new_state):
        """
        Track state changes and duration.
        """
        
        if new_state != self.current_state:
            # State changed
            self.prev_state = self.current_state
            self.current_state = new_state
            self.state_entry_frame = self.frame_number
            return True  # State changed
        
        return False  # State unchanged
    
    def _get_state_duration_frames(self):
        """How long have we been in current state?"""
        return self.frame_number - self.state_entry_frame
    
    # ────────────────────────────────────────────────────────────────────
    # STAGE 6: ACTION DECISION
    # ────────────────────────────────────────────────────────────────────
    
    def _decide_actions(self, features):
        """
        Decide what actions to take based on state + duration.
        
        Returns:
        {
            "trigger_alarm": bool,
            "trigger_sos": bool,
            "trigger_warning_alert": bool,
            "reason": str
        }
        """
        
        actions = {
            "trigger_alarm": False,
            "trigger_sos": False,
            "trigger_warning_alert": False,
            "reason": ""
        }
        
        state_duration = self._get_state_duration_frames()
        
        # CRITICAL state: Escalate to SOS
        if self.current_state == DriverState.CRITICAL:
            if state_duration >= self.SOS_TRIGGER_DURATION_FRAMES:
                actions["trigger_sos"] = True
                actions["reason"] = f"CRITICAL state for {state_duration} frames - Emergency SOS"
            else:
                actions["trigger_alarm"] = True
                actions["reason"] = f"CRITICAL state detected"
        
        # DANGER state: Trigger alarm
        elif self.current_state == DriverState.DANGER:
            if state_duration >= self.ALARM_TRIGGER_DURATION_FRAMES:
                actions["trigger_alarm"] = True
                actions["reason"] = f"DANGER state for {state_duration} frames - Sustained risk"
        
        # WARNING state: Visual/audio alert
        elif self.current_state == DriverState.WARNING:
            if state_duration >= 30:  # After 30 frames in WARNING
                actions["trigger_warning_alert"] = True
                actions["reason"] = f"WARNING state for {state_duration} frames"
        
        # NORMAL state: No action
        else:
            actions["reason"] = "Driver NORMAL - no action"
        
        return actions
    
    # ────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT: Process Decision
    # ────────────────────────────────────────────────────────────────────
    
    def process(self, perception):
        """
        Main decision pipeline.
        
        Input: Raw perception data
        Output: Structured decision with actions
        """
        
        self.frame_number += 1
        
        # STAGE 1: Temporal buffering
        self._update_temporal_buffers(perception)
        
        # STAGE 2: Feature extraction with validation
        features = self._extract_validated_features(perception)
        
        # STAGE 3: Fuse signals into readiness score
        readiness_score = self._calculate_readiness_score(features)
        
        # STAGE 4: Classify state
        new_state = self._classify_state(readiness_score, features)
        
        # STAGE 5: Track transitions
        state_changed = self._update_state_transitions(new_state)
        
        # STAGE 6: Decide actions
        actions = self._decide_actions(features)
        
        # Build decision output
        decision = {
            # Core outputs
            "readiness_score": readiness_score,
            "driver_state": self.current_state,
            "state_changed": state_changed,
            "state_duration_frames": self._get_state_duration_frames(),
            
            # Validated signals
            "is_drowsy": features["is_drowsy"],
            "is_eyes_closed": features["is_eyes_closed"],
            "is_distracted": features["is_distracted"],
            "is_no_response": features["is_no_response"],
            
            # Buffers (debug)
            "drowsy_frame_count": self.drowsy_frame_count,
            "closure_frame_count": self.closure_frame_count,
            "distracted_frame_count": self.distracted_frame_count,
            "no_response_frame_count": self.no_response_frame_count,
            
            # Actions
            "trigger_alarm": actions["trigger_alarm"],
            "trigger_sos": actions["trigger_sos"],
            "trigger_warning_alert": actions["trigger_warning_alert"],
            "action_reason": actions["reason"],
        }
        
        return decision
    
    # ────────────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ────────────────────────────────────────────────────────────────────
    
    def reset(self):
        """Reset all buffers (e.g., on app restart)"""
        self.drowsy_frame_count = 0
        self.distracted_frame_count = 0
        self.closure_frame_count = 0
        self.no_response_frame_count = 0
        self.current_state = DriverState.NORMAL
        self.state_entry_frame = 0
    
    def set_heart_rate_anomaly(self, is_anomaly):
        """Update heart rate status"""
        self.heart_rate_anomaly = is_anomaly
