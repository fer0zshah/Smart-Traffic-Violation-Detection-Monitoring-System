
violation_rule_engine.py
TVS-9: Violation Rule Engine — Epic 3 final module.

Combines speed estimation (TVS-7) and red light crossing detection (TVS-8)
into a single unified pipeline.

Subta"""sks:
1. Combine speed and red light checks in a single pipeline
2. Support configurable cooldown per track ID
3. Emit a structured ViolationEvent object with full metadata
4. Unit tests for edge cases

Design:
  - ViolationRuleEngine is a thin coordinator layer. It does NOT
    re-implement detection logic. It subscribes to events emitted
    by SpeedEstimator (TVS-7) and RedLightDetector (TVS-8) and
    merges them into canonical ViolationEvents.
  - One ViolationEvent per (track_id, violation_type) incident.
  - Cooldown is enforced per (track_id, type) pair so a speeding
    vehicle that also runs a red light gets TWO separate events.
  - Evidence clip: the engine records the frame window around each
    violation for downstream plate-crop and OCR modules.
"""

from __future__ import annotations

import cv2
import supervision as sv
from ultralytics import YOLO
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict
import json
import math
import unittest
from datetime import datetime



#  CONFIGURATION


VIDEO_PATH           = "videos/tt.mp4"
MODEL_PATH           = "yolov8n.pt"
VEHICLE_CLASSES      = [2, 3, 5, 7]
CONFIDENCE           = 0.5
IOU                  = 0.45
DISPLAY_WIDTH        = 1280

# --- Speed zone (TVS-7) ---
LINE_UPPER_Y         = 300
LINE_LOWER_Y         = 600
REAL_DISTANCE_METERS = 3.0
VIDEO_FPS            = 30.0
SPEED_LIMIT_KMH      = 60.0
MIN_FRAMES_VALID     = 3

# --- Stop line / Red light (TVS-8) ---
STOP_LINE_Y          = 400

# --- Direction detection ---
DIRECTION_FRAMES     = 3       # Frames to observe before classifying direction
DIRECTION_MIN_MOVE   = 10      # Minimum Y pixel movement for classification

# --- Signal control ---
USE_KEYBOARD         = True
LIGHT_CYCLE_FRAMES   = 300
GREEN_FRAMES         = 120
YELLOW_FRAMES        = 60
RED_FRAMES           = 120

# --- Rule engine ---
COOLDOWN_FRAMES      = 90      # Min frames between two events for same (track, type)
EVIDENCE_PRE_FRAMES  = 15      # Frames before violation to include in clip window
EVIDENCE_POST_FRAMES = 30      # Frames after violation to include in clip window
MIN_TRACK_FRAMES     = 5       # Min frames tracked before red-light check
STALE_TRACK_FRAMES   = 100     # Frames after loss before track cleanup

# --- Ghost / occlusion ---
GHOST_FRAMES         = 10
REASSIGN_DIST        = 100



#  DATA MODEL


class Direction(Enum):
    UNKNOWN = "UNKNOWN"
    UP      = "UP"       # Y decreasing — enters from bottom
    DOWN    = "DOWN"     # Y increasing — enters from top


class SignalState(Enum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"


class ViolationType(str, Enum):
    OVERSPEED  = "OVERSPEED"
    RED_LIGHT  = "RED_LIGHT"


@dataclass
class SpeedMeasurement:
    """Single speed measurement result (TVS-7)."""
    track_id: int
    direction: str
    speed_kmh: float
    violation: bool
    start_frame: int
    end_frame: int
    frames_between: float
    time_seconds: float


@dataclass
class ViolationEvent:
    """
    Canonical violation record emitted by the rule engine.
    Consumed downstream by: plate crop → OCR → MySQL writer → Laravel dashboard.
    """
    event_id:             str              # unique: "{track_id}_{type}_{frame}_{counter}"
    track_id:             int
    violation_type:       ViolationType
    frame_number:         int
    timestamp:            str              # ISO 8601
    direction:            str              # "up" / "down" / "UP" / "DOWN" / "unknown"
    signal_state:         str              # "RED" / "GREEN" / "YELLOW" / "N/A"
    speed_kmh:            Optional[float]  # None for red-light-only events
    speed_limit_kmh:      Optional[float]
    bbox:                 list             # [x1, y1, x2, y2] at violation frame
    evidence_start_frame: int              # clip window start
    evidence_end_frame:   int              # clip window end
    plate_number:         str = ""         # filled by TVS-10/11
    image_path:           str = ""         # filled by TVS-10

    def to_dict(self) -> dict:
        d = asdict(self)
        d["violation_type"] = self.violation_type.value
        return d



#  TRAFFIC LIGHT


class TrafficLight:
    def __init__(self):
        self.state = SignalState.GREEN

    def set_state(self, key: int):
        if key == ord('r'):
            self.state = SignalState.RED
            print("  Signal → RED")
        elif key == ord('y'):
            self.state = SignalState.YELLOW
            print("  Signal → YELLOW")
        elif key == ord('g'):
            self.state = SignalState.GREEN
            print("  Signal → GREEN")

    def auto_update(self, frame_num: int):
        pos = frame_num % LIGHT_CYCLE_FRAMES
        if pos < GREEN_FRAMES:
            self.state = SignalState.GREEN
        elif pos < GREEN_FRAMES + YELLOW_FRAMES:
            self.state = SignalState.YELLOW
        else:
            self.state = SignalState.RED

    def get_bgr(self) -> tuple:
        return {
            SignalState.GREEN:  (0, 255, 0),
            SignalState.YELLOW: (0, 255, 255),
            SignalState.RED:    (0, 0, 255),
        }[self.state]



#  TVS-7: SPEED ESTIMATOR
#  History buffer + sub-frame interpolation for high-speed accuracy.


class SpeedEstimator:
    """
    Advanced speed estimator with a Coordinate History Buffer
    and Sub-Frame Interpolation for high-speed accuracy.
    Ported from TVS-7 (speed_estimation_bidirectional.py).
    """

    def __init__(self, line_upper: int, line_lower: int,
                 real_distance_m: float, fps: float, speed_limit: float):
        self.line_upper       = line_upper
        self.line_lower       = line_lower
        self.real_distance_m  = real_distance_m
        self.fps              = fps
        self.speed_limit      = speed_limit
        self.pixel_distance   = abs(line_lower - line_upper)
        self.pixels_per_meter = self.pixel_distance / real_distance_m

        self._tracks: Dict[int, dict] = {}
        self._ghosts: List[dict]      = []
        self.measurements: List[SpeedMeasurement] = []
        self.discarded_count = 0

    def _get_track(self, track_id: int) -> dict:
        """Get or create track state using a history buffer."""
        if track_id not in self._tracks:
            self._tracks[track_id] = {
                "state": "active",
                "direction": None,
                "history": [],  # (frame_num, top_y, bottom_y, center_y)
            }
        return self._tracks[track_id]

    def _find_ghost_match(self, cx: float, cy: float) -> Optional[dict]:
        best_match = None
        best_dist = float('inf')
        for ghost in self._ghosts:
            if ghost["frames_since_lost"] > GHOST_FRAMES:
                continue
            gx, gy = ghost["last_pos"]
            dist = math.sqrt((cx - gx)**2 + (cy - gy)**2)
            if dist < REASSIGN_DIST and dist < best_dist:
                best_dist = dist
                best_match = ghost
        return best_match

    def _ghost_track(self, track_id: int, track: dict):
        if len(track["history"]) > 0:
            last_cx_cy = (0, track["history"][-1][3])
            self._ghosts.append({
                "last_pos": last_cx_cy,
                "state": track.copy(),
                "frames_since_lost": 0,
            })

    def process(self, detections: sv.Detections, frame_num: int) -> List[dict]:
        """
        Process detections for speed estimation.
        Returns list of speed event dicts (with bbox for rule engine).
        """
        events = []

        if detections.tracker_id is None:
            for tid, track in list(self._tracks.items()):
                self._ghost_track(tid, track)
            self._tracks.clear()
            return events

        tracker_ids = detections.tracker_id
        current_ids = set(tracker_ids.tolist() if hasattr(tracker_ids, 'tolist') else tracker_ids)
        lost_ids = set(self._tracks.keys()) - current_ids

        for tid in lost_ids:
            self._ghost_track(tid, self._tracks[tid])
            del self._tracks[tid]

        tracker_ids = detections.tracker_id
        for i, track_id in enumerate(tracker_ids.tolist() if hasattr(tracker_ids, 'tolist') else tracker_ids):
            x1, y1, x2, y2 = detections.xyxy[i]
            top_y, bottom_y = float(y1), float(y2)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            if track_id not in self._tracks:
                ghost = self._find_ghost_match(cx, cy)
                if ghost:
                    self._tracks[track_id] = ghost["state"].copy()
                    self._ghosts.remove(ghost)
                else:
                    self._get_track(track_id)

            track = self._tracks[track_id]

            # 1. ADD TO HISTORY BUFFER
            if track["state"] == "active":
                track["history"].append((frame_num, top_y, bottom_y, cy))

                # 2. EVALUATE THE BUFFER
                event = self._evaluate_history(
                    track, track_id,
                    bbox=[float(x1), float(y1), float(x2), float(y2)]
                )
                if event:
                    events.append(event)

        # Clean old ghosts
        self._ghosts = [g for g in self._ghosts if g["frames_since_lost"] <= GHOST_FRAMES]
        for g in self._ghosts:
            g["frames_since_lost"] += 1

        return events

    def _get_exact_crossing_frame(self, history: list, line_y: float,
                                   is_up: bool, edge_idx: int) -> Optional[float]:
        """Calculates the exact sub-frame a line was crossed using linear interpolation."""
        for i in range(1, len(history)):
            prev_f = history[i-1][0]
            curr_f = history[i][0]

            y_prev = history[i-1][edge_idx]
            y_curr = history[i][edge_idx]

            if is_up:  # Moving up: Y is decreasing
                if y_prev > line_y >= y_curr:
                    ratio = (y_prev - line_y) / (y_prev - y_curr + 1e-6)
                    return prev_f + ratio * (curr_f - prev_f)
            else:      # Moving down: Y is increasing
                if y_prev < line_y <= y_curr:
                    ratio = (line_y - y_prev) / (y_curr - y_prev + 1e-6)
                    return prev_f + ratio * (curr_f - prev_f)
        return None

    def _evaluate_history(self, track: dict, track_id: int,
                          bbox: list = None) -> Optional[dict]:
        history = track["history"]

        # --- Step A: Determine Direction ---
        if track["direction"] is None:
            if len(history) >= DIRECTION_FRAMES:
                first_y = history[0][3]
                last_y = history[-1][3]
                diff = last_y - first_y

                if abs(diff) < 5:
                    if len(history) > 90:
                        track["state"] = "discarded"
                        self.discarded_count += 1
                    return None

                track["direction"] = "up" if diff < 0 else "down"
            return None

        # --- Step B: Check History Buffer for Crossings ---
        direction = track["direction"]

        if direction == "up":
            # Edge index 1 is top_y
            start_frame_exact = self._get_exact_crossing_frame(
                history, self.line_lower, True, 1)
            end_frame_exact = self._get_exact_crossing_frame(
                history, self.line_upper, True, 1)
        else:
            # Edge index 2 is bottom_y
            start_frame_exact = self._get_exact_crossing_frame(
                history, self.line_upper, False, 2)
            end_frame_exact = self._get_exact_crossing_frame(
                history, self.line_lower, False, 2)

        # --- Step C: Calculate Speed ---
        if start_frame_exact is not None and end_frame_exact is not None:
            frames = end_frame_exact - start_frame_exact

            if frames <= 0 or frames < MIN_FRAMES_VALID:
                track["state"] = "discarded"
                self.discarded_count += 1
                return None

            time_s = frames / self.fps
            speed_ms = self.real_distance_m / time_s
            speed_kmh = round(speed_ms * 3.6, 1)
            violation = speed_kmh > self.speed_limit

            measurement = SpeedMeasurement(
                track_id=track_id,
                direction=direction,
                speed_kmh=speed_kmh,
                violation=violation,
                start_frame=int(start_frame_exact),
                end_frame=int(end_frame_exact),
                frames_between=round(frames, 2),
                time_seconds=round(time_s, 3),
            )

            self.measurements.append(measurement)
            track["state"] = "done"
            track["history"] = []  # Clear memory

            return {
                "track_id":   track_id,
                "direction":  direction,
                "speed_kmh":  speed_kmh,
                "violation":  violation,
                "frames":     round(frames, 2),
                "time_s":     round(time_s, 3),
                "frame_num":  int(end_frame_exact),
                "bbox":       bbox or [0, 0, 0, 0],
            }

        return None

 # ── Accessors ─────────────────────────────────────────────────────────────

    def get_speed(self, track_id: int) -> Optional[float]:
        for m in self.measurements:
            if m.track_id == track_id:
                return m.speed_kmh
        return None

    def is_violation(self, track_id: int) -> bool:
        for m in self.measurements:
            if m.track_id == track_id:
                return m.violation
        return False

    def get_track_state(self, track_id: int) -> str:
        if track_id in self._tracks:
            return self._tracks[track_id]["state"]
        return "unknown"

    def get_direction(self, track_id: int) -> Optional[str]:
        if track_id in self._tracks:
            return self._tracks[track_id].get("direction")
        return None

    def get_summary(self) -> dict:
        total = len(self.measurements)
        violations = sum(1 for m in self.measurements if m.violation)
        avg_speed = sum(m.speed_kmh for m in self.measurements) / total if total else 0
        up = sum(1 for m in self.measurements if m.direction == "up")
        down = sum(1 for m in self.measurements if m.direction == "down")

        return {
            "total_valid": total,
            "up_count": up,
            "down_count": down,
            "discarded": self.discarded_count,
            "violations": violations,
            "average_speed": round(avg_speed, 1),
            "speed_limit": self.speed_limit,
            "real_distance_m": self.real_distance_m,
            "pixels_per_meter": round(self.pixels_per_meter, 1),
            "measurements": [
                {
                    "track_id": m.track_id,
                    "direction": m.direction,
                    "speed_kmh": m.speed_kmh,
                    "violation": m.violation,
                    "frames": m.frames_between,
                    "time_s": m.time_seconds,
                }
                for m in self.measurements
            ]
        }



if __name__ == "__main__":
    main()