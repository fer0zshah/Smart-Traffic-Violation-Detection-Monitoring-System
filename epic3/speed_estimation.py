"""
speed_estimation_final.py
TVS-7 Complete: Speed estimation with calibration, bidirectional support,
violation flagging, and production-ready output.

Subtasks covered:
1. Define virtual speed-measurement lines in config
2. Calculate pixel-to-meter ratio via calibration
3. Compute speed from time-between-line crossings
4. Flag vehicle if speed exceeds configurable threshold
"""

import cv2
import supervision as sv
from ultralytics import YOLO
import math
import json
from dataclasses import dataclass
from typing import Optional, List, Dict

# ========== CONFIGURATION ==========
VIDEO_PATH = "videos/tt.mp4"
MODEL_PATH = "yolov8n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]
CONFIDENCE = 0.5
IOU = 0.45
DISPLAY_WIDTH = 1280

# --- SPEED LINES ---
LINE_UPPER_Y = 200
LINE_LOWER_Y = 500

# --- CALIBRATION ---
# Method: Use known reference in video
# Option A: If you know lane width (standard = 3.6m)
#   Measure lane width in pixels from video, then:
#   PIXELS_PER_METER = lane_width_pixels / 3.6
#   REAL_DISTANCE = abs(LINE_LOWER_Y - LINE_UPPER_Y) / PIXELS_PER_METER

# Option B: Use realistic speed assumption (easier for dataset videos)
# City traffic ~40 km/h, takes ~8 frames at 30 FPS = 0.267s
# Distance = (40/3.6) * 0.267 ≈ 3 meters
REAL_DISTANCE_METERS = 3.0

# Alternative: Auto-calculate from pixel ratio if you know lane width
# PIXELS_PER_METER = 100  # example: 100 pixels = 1 meter
# REAL_DISTANCE_METERS = abs(LINE_LOWER_Y - LINE_UPPER_Y) / PIXELS_PER_METER


VIDEO_FPS = 30.0
MIN_FRAMES_VALID = 3
DIRECTION_FRAMES = 3
GHOST_FRAMES = 10
REASSIGN_DIST = 100
# ==================================


@dataclass
class SpeedMeasurement:
    """Single speed measurement result."""
    track_id: int
    direction: str
    speed_kmh: float
    violation: bool
    start_frame: int
    end_frame: int
    frames_between: int
    time_seconds: float


class SpeedEstimator:
    """
    Production-ready speed estimator with bidirectional support.
    """
    
    def __init__(self, line_upper: int, line_lower: int, 
                 real_distance_m: float, fps: float, speed_limit: float):
        self.line_upper = line_upper
        self.line_lower = line_lower
        self.real_distance_m = real_distance_m
        self.fps = fps
        self.speed_limit = speed_limit
        self.pixel_distance = abs(line_lower - line_upper)
        
        # Calculate pixels per meter for reference
        self.pixels_per_meter = self.pixel_distance / real_distance_m
        
        # State storage
        self._tracks: Dict[int, dict] = {}
        self._ghosts: List[dict] = []
        self.measurements: List[SpeedMeasurement] = []
        self.discarded_count = 0
        
    def _get_track(self, track_id: int) -> dict:
        """Get or create track state."""
        if track_id not in self._tracks:
            self._tracks[track_id] = {
                "state": "observing",
                "direction": None,
                "positions": [],
                "start_frame": None,
                "end_frame": None,
                "start_line": None,
                "last_y": None,
                "last_top_y": None,
                "last_bottom_y": None,
                "frames_in_state": 0,
            }
        return self._tracks[track_id]
    
    def _find_ghost_match(self, cx: float, cy: float) -> Optional[dict]:
        """Find recently lost track near this position."""
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
    
    def process_detections(self, detections: sv.Detections, frame_num: int) -> List[str]:
        """
        Process all detections in a frame.
        Returns list of event strings for logging.
        """
        events = []
        
        if detections.tracker_id is None:
            # All tracks lost, ghost them
            for tid, track in list(self._tracks.items()):
                self._ghost_track(tid, track)
            self._tracks.clear()
            return events
        
        current_ids = set(detections.tracker_id.tolist())
        lost_ids = set(self._tracks.keys()) - current_ids
        
        # Ghost lost tracks
        for tid in lost_ids:
            self._ghost_track(tid, self._tracks[tid])
            del self._tracks[tid]
        
        # Process current detections
        for i, track_id in enumerate(detections.tracker_id.tolist()):
            x1, y1, x2, y2 = detections.xyxy[i]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            top_y, bottom_y = y1, y2
            
            # Check for ghost reassignment
            if track_id not in self._tracks:
                ghost = self._find_ghost_match(cx, cy)
                if ghost:
                    # Continue from ghost state
                    self._tracks[track_id] = ghost["state"].copy()
                    self._tracks[track_id]["_ghost_continued"] = True
                    self._ghosts.remove(ghost)
                else:
                    # Fresh track
                    self._tracks[track_id] = self._get_track(track_id)
            
            track = self._tracks[track_id]
            track["frames_in_state"] += 1
            
            # State machine
            event = self._process_state(track, track_id, top_y, bottom_y, cy, frame_num)
            if event:
                events.append(event)
            
            # Update position for next frame
            track["last_pos"] = (cx, cy)
            track["last_y"] = cy
            track["last_top_y"] = top_y
            track["last_bottom_y"] = bottom_y
        
        # Clean old ghosts
        self._ghosts = [g for g in self._ghosts if g["frames_since_lost"] <= GHOST_FRAMES]
        for g in self._ghosts:
            g["frames_since_lost"] += 1
        
        return events
    
    def _ghost_track(self, track_id: int, track: dict):
        """Save lost track as ghost."""
        if "last_pos" in track:
            self._ghosts.append({
                "last_pos": track["last_pos"],
                "state": track.copy(),
                "frames_since_lost": 0,
            })
    
    def _process_state(self, track: dict, track_id: int, 
                       top_y: float, bottom_y: float, center_y: float, 
                       frame_num: int) -> Optional[str]:
        """Process single track through state machine."""
        
        state = track["state"]
        
        if state in ("done", "discarded"):
            return None
        
        # OBSERVING: detect direction
        if state == "observing":
            track["positions"].append(center_y)
            
            if len(track["positions"]) < DIRECTION_FRAMES:
                return None
            
            # Determine direction
            first_y = track["positions"][0]
            last_y = track["positions"][-1]
            diff = last_y - first_y
            
            if abs(diff) < 5:
                # Not moving enough
                if len(track["positions"]) > 10:
                    track["state"] = "discarded"
                    self.discarded_count += 1
                    return f"Vehicle #{track_id}: NO_DIRECTION_DISCARDED"
                return None
            
            track["direction"] = "up" if diff < 0 else "down"
            track["state"] = "waiting_first"
            track["positions"] = []
            
            return f"Vehicle #{track_id}: direction={track['direction']}"
        
        # WAITING_FIRST: wait for first line crossing
        if state == "waiting_first":
            direction = track["direction"]
            
            if direction == "up":
                # Moving UP: first line is LOWER (500)
                # Cross when top edge goes from above to at/below line
                if top_y <= self.line_lower and track.get("was_above_lower", True):
                    track["start_frame"] = frame_num
                    track["start_line"] = self.line_lower
                    track["state"] = "timing"
                    track["was_above_lower"] = False
                    return f"Vehicle #{track_id}: STARTED timing (up, line={self.line_lower})"
                
                # Already above upper line = missed both
                if top_y < self.line_upper:
                    track["state"] = "discarded"
                    self.discarded_count += 1
                    return f"Vehicle #{track_id}: MISSED_BOTH"
                
                track["was_above_lower"] = top_y > self.line_lower
                
            else:  # direction == "down"
                # Moving DOWN: first line is UPPER (200)
                # Cross when bottom edge goes from below to at/above line
                if bottom_y >= self.line_upper and track.get("was_below_upper", True):
                    track["start_frame"] = frame_num
                    track["start_line"] = self.line_upper
                    track["state"] = "timing"
                    track["was_below_upper"] = False
                    return f"Vehicle #{track_id}: STARTED timing (down, line={self.line_upper})"
                
                # Already below lower line = missed both
                if bottom_y > self.line_lower:
                    track["state"] = "discarded"
                    self.discarded_count += 1
                    return f"Vehicle #{track_id}: MISSED_BOTH"
                
                track["was_below_upper"] = bottom_y < self.line_upper
            
            return None
        
        # TIMING: wait for second line
        if state == "timing":
            direction = track["direction"]
            
            if direction == "up":
                # Second line is UPPER (200)
                if top_y <= self.line_upper and track["last_top_y"] > self.line_upper:
                    return self._finish_measurement(track, track_id, frame_num, self.line_upper)
                track["last_top_y"] = top_y
                
            else:
                # Second line is LOWER (500)
                if bottom_y >= self.line_lower and track["last_bottom_y"] < self.line_lower:
                    return self._finish_measurement(track, track_id, frame_num, self.line_lower)
                track["last_bottom_y"] = bottom_y
            
            return None
        
        return None
    
    def _finish_measurement(self, track: dict, track_id: int, 
                          end_frame: int, end_line: int) -> str:
        """Calculate and store final speed measurement."""
        frames = end_frame - track["start_frame"]
        
        if frames < MIN_FRAMES_VALID:
            track["state"] = "discarded"
            self.discarded_count += 1
            return f"Vehicle #{track_id}: TOO_FAST_DISCARDED ({frames} frames)"
        
        time_s = frames / self.fps
        speed_ms = self.real_distance_m / time_s
        speed_kmh = round(speed_ms * 3.6, 1)
       
        
        measurement = SpeedMeasurement(
            track_id=track_id,
            direction=track["direction"],
            speed_kmh=speed_kmh,
            violation=violation,
            start_frame=track["start_frame"],
            end_frame=end_frame,
            frames_between=frames,
            time_seconds=round(time_s, 3),
        )
        
        self.measurements.append(measurement)
        track["state"] = "done"
        
        tag = "VIOLATION" if violation else "OK"
        return (f"Vehicle #{track_id}: {speed_kmh} km/h "
                f"({track['direction']}, {frames}fr, {time_s:.2f}s) [{tag}]")
    
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
    
    


def resize_for_display(frame, target_width=1280):
    h, w = frame.shape[:2]
    scale = target_width / w
    return cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_AREA)


def draw_scene(frame, orig_w, speed_est):
    """Draw overlays on frame."""
    annotated = frame.copy()
    
    # Zone shading
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, LINE_UPPER_Y), (orig_w, LINE_LOWER_Y), (255, 255, 0), -1)
    annotated = cv2.addWeighted(annotated, 0.85, overlay, 0.15, 0)
    
    # Lines
    cv2.line(annotated, (0, LINE_UPPER_Y), (orig_w, LINE_UPPER_Y), (0, 0, 255), 3)
    cv2.putText(annotated, f"UPPER (Y={LINE_UPPER_Y})", (10, LINE_UPPER_Y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    cv2.line(annotated, (0, LINE_LOWER_Y), (orig_w, LINE_LOWER_Y), (0, 255, 0), 3)
    cv2.putText(annotated, f"LOWER (Y={LINE_LOWER_Y})", (10, LINE_LOWER_Y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Direction indicators
    mid_y = (LINE_UPPER_Y + LINE_LOWER_Y) // 2
    cv2.putText(annotated, "UP ↑", (50, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(annotated, "↓ DOWN", (orig_w - 200, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Calibration info
    info = f"Dist: {speed_est.real_distance_m}m | PPM: {speed_est.pixels_per_meter:.1f}px/m"
    cv2.putText(annotated, info, (10, orig_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return annotated


def build_labels(tracked, speed_est, model):
    labels = []
    if tracked.tracker_id is None:
        return labels
    
    for class_id, track_id in zip(tracked.class_id, tracked.tracker_id):
        class_name = model.names[class_id]
        speed = speed_est.get_speed(track_id)
        direction = speed_est.get_direction(track_id)
        state = speed_est.get_track_state(track_id)
        
        arrow = "↑" if direction == "up" else "↓" if direction == "down" else "?"
        
        if speed is not None:
            label = f"#{track_id} {arrow} {speed}km/h"
            if speed_est.is_violation(track_id):
                label += " [!VIO]"
        elif state == "timing":
            label = f"#{track_id} {arrow} [timing]"
        elif state == "observing":
            label = f"#{track_id} [detecting]"
        elif state == "waiting_first":
            label = f"#{track_id} {arrow} [wait]"
        elif state == "discarded":
            label = f"#{track_id} [disc]"
        else:
            label = f"#{track_id} {class_name}"
        
        labels.append(label)
    
    return labels


def main():
    print("=" * 60)
    print("TVS-7: Speed Estimation - FINAL")
    print("=" * 60)
    print(f"Lines: Y={LINE_UPPER_Y} (upper) to Y={LINE_LOWER_Y} (lower)")
    print(f"Real distance: {REAL_DISTANCE_METERS} m")
    print(f"Speed limit: {SPEED_LIMIT_KMH} km/h")
    print(f"FPS: {VIDEO_FPS}")
    print("-" * 60)
    
    model = YOLO(MODEL_PATH)
    tracker = sv.ByteTrack(
        track_activation_threshold=0.25,
        lost_track_buffer=30,
        minimum_matching_threshold=0.8,
        frame_rate=VIDEO_FPS,
    )
    
    speed_est = SpeedEstimator(
        line_upper=LINE_UPPER_Y,
        line_lower=LINE_LOWER_Y,
        real_distance_m=REAL_DISTANCE_METERS,
        fps=VIDEO_FPS,
        speed_limit=SPEED_LIMIT_KMH,
    )
    
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=0.6)
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("ERROR: Cannot open video")
        return
    
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {orig_w}x{orig_h}")
    print("Press Q=quit, P=pause")
    print("=" * 60)
    
    frame_count = 0
    paused = False
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Detect & track
            results = model(frame, classes=VEHICLE_CLASSES, conf=CONFIDENCE, iou=IOU, verbose=False)
            detections = sv.Detections.from_ultralytics(results[0])
            tracked = tracker.update_with_detections(detections)
            
            # Speed estimation
            events = speed_est.process_detections(tracked, frame_count)
            for event in events:
                print(f"  Frame {frame_count}: {event}")
            
            # Draw
            annotated = draw_scene(frame, orig_w, speed_est)
            labels = build_labels(tracked, speed_est, model)
            annotated = box_annotator.annotate(scene=annotated, detections=tracked)
            annotated = label_annotator.annotate(scene=annotated, detections=tracked, labels=labels)
            
            active = len(tracked.tracker_id) if tracked.tracker_id is not None else 0
            hud = (f"Frame: {frame_count} | Active: {active} "
                   f"| Valid: {len(speed_est.measurements)} "
                   f"| Disc: {speed_est.discarded_count}")
            cv2.putText(annotated, hud, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            display = resize_for_display(annotated, DISPLAY_WIDTH)
            cv2.imshow("TVS-7 Speed Estimation FINAL", display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("p"):
            paused = not paused
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Report
    summary = speed_est.get_summary()
    print("\n" + "=" * 60)
    print("SPEED ESTIMATION REPORT")
    print("=" * 60)
    print(f"Total valid: {summary['total_valid']} (UP: {summary['up_count']}, DOWN: {summary['down_count']})")
    print(f"Discarded: {summary['discarded']}")
    print(f"Violations: {summary['violations']}")
    print(f"Average speed: {summary['average_speed']} km/h")
    print(f"Calibration: {summary['pixels_per_meter']} px/m")
    
    if summary["measurements"]:
        print("\nMeasurements:")
        for m in summary["measurements"]:
            tag = "VIOLATION" if m["violation"] else "OK"
            print(f"  #{m['track_id']:>3} {m['direction']:>4}: {m['speed_kmh']:>6.1f} km/h "
                  f"({m['frames']} frames, {m['time_s']}s) [{tag}]")
    
    with open("speed_measurements_final.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: speed_measurements_final.json")
    print("=" * 60)


if __name__ == "__main__":
    main()