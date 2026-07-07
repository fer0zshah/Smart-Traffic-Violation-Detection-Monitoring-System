"""
speed_estimation_fixed.py
TVS-7: calibration with direction-aware zone timing.

Logic:
- Vehicles must ENTER the zone (cross Line 1 from ABOVE) to START
- Vehicles must EXIT the zone (cross Line 2 from ABOVE) to STOP
- If vehicle exits frame before Line 2: measurement is DISCARDED
- If vehicle is already between lines when detected: IGNORE (wait for next vehicle)
"""

import cv2
import supervision as sv
from ultralytics import YOLO
from collections import defaultdict
import math
import json

# ========== CONFIGURATION ==========
VIDEO_PATH = "videos/MVI_20011.mp4"
MODEL_PATH = "yolov8n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]
CONFIDENCE = 0.5
IOU = 0.45
DISPLAY_WIDTH = 1280

# --- SPEED MEASUREMENT LINES ---
# For this video, vehicles move BOTTOM to TOP (Y decreases)
# So we reverse the logic: cross from below = enter, cross from above = exit
SPEED_LINE_1_Y = 600   # Lower line (closer to bottom) = ENTER zone
SPEED_LINE_2_Y = 400   # Upper line (closer to top) = EXIT zone

# --- CALIBRATION ---
REAL_DISTANCE_METERS = 20.0
SPEED_LIMIT_KMH = 60.0
VIDEO_FPS = 30.0

# Minimum frames between lines for valid measurement (filters out false positives)
MIN_FRAMES_FOR_VALID = 5  # At 30 FPS, ~0.16s minimum
# ==================================


class SpeedEstimatorFixed:
    """
    Direction-aware speed estimation.
    Vehicles must fully traverse the zone (enter at Line 1, exit at Line 2).
    """
    def __init__(self, line1_y, line2_y, real_distance_m, fps, speed_limit):
        self.line1_y = line1_y  # Enter line (lower Y)
        self.line2_y = line2_y  # Exit line (higher Y)
        self.real_distance_m = real_distance_m
        self.fps = fps
        self.speed_limit = speed_limit
        self.min_frames = MIN_FRAMES_FOR_VALID
        
        # Track states
        # States: "unknown" -> "entered" -> "exited" (valid) OR "lost" (invalid)
        self.track_states = defaultdict(lambda: {
            "state": "unknown",
            "enter_frame": None,
            "exit_frame": None,
            "last_y": None,
            "speed_kmh": None,
            "violation": False,
            "discarded": False
        })
        
        self.completed_measurements = []
        self.discarded_count = 0
        
    def update(self, track_id, center_y, frame_num):
        """
        Update track state based on position.
        Returns: (event, data) or (None, None)
        """
        state = self.track_states[track_id]
        
        # Initialize if new track
        if state["state"] == "unknown":
            state["last_y"] = center_y
            
            # If vehicle is already ABOVE both lines (exited zone), ignore
            if center_y < self.line2_y:
                state["state"] = "above_zone"
                return None, None
            
            # If vehicle is BELOW both lines (not yet entered), wait
            if center_y > self.line1_y:
                state["state"] = "below_zone"
                return None, None
            
            # If vehicle is BETWEEN lines, wait for it to enter properly
            # (must come from below to be valid)
            state["state"] = "between_lines"
            return None, None
        
        # Track direction (Y decreasing = moving UP)
        direction = "up" if center_y < state["last_y"] else "down"
        state["last_y"] = center_y
        
        # State machine
        if state["state"] == "below_zone":
            # Waiting to enter: must cross Line 1 from below going up
            if center_y <= self.line1_y and direction == "up":
                state["state"] = "entered"
                state["enter_frame"] = frame_num
                return "ENTERED_ZONE", frame_num
                
        elif state["state"] == "entered":
            # In zone, waiting to exit at Line 2
            if center_y <= self.line2_y and direction == "up":
                state["state"] = "exited"
                state["exit_frame"] = frame_num
                
                # Calculate speed
                frames_between = state["exit_frame"] - state["enter_frame"]
                
                # Validate: must take minimum frames (prevents instant crossing)
                if frames_between >= self.min_frames:
                    time_seconds = frames_between / self.fps
                    speed_ms = self.real_distance_m / time_seconds
                    speed_kmh = speed_ms * 3.6
                    
                    state["speed_kmh"] = round(speed_kmh, 1)
                    state["violation"] = speed_kmh > self.speed_limit
                    
                    self.completed_measurements.append({
                        "track_id": track_id,
                        "enter_frame": state["enter_frame"],
                        "exit_frame": state["exit_frame"],
                        "frames_between": frames_between,
                        "time_seconds": round(time_seconds, 2),
                        "speed_kmh": state["speed_kmh"],
                        "violation": state["violation"]
                    })
                    
                    return "SPEED_MEASURED", state["speed_kmh"]
                else:
                    # Too fast = probably false positive
                    state["discarded"] = True
                    self.discarded_count += 1
                    return "DISCARDED_TOO_FAST", None
        
        elif state["state"] == "between_lines":
            # Vehicle was between lines when first seen
            # If it goes up past Line 2, we can't measure (missed entry)
            if center_y <= self.line2_y and direction == "up":
                state["state"] = "missed_entry"
                state["discarded"] = True
                self.discarded_count += 1
                return "MISSED_ENTRY", None
            
            # If it goes back down past Line 1, now it can enter properly
            if center_y >= self.line1_y and direction == "down":
                state["state"] = "below_zone"
                return None, None
        
        return None, None
    
    def mark_lost(self, track_id):
        """Mark track as lost (exited frame)."""
        state = self.track_states[track_id]
        if state["state"] in ["entered", "between_lines"] and not state["discarded"]:
            # Was in zone but never exited = discard
            state["discarded"] = True
            self.discarded_count += 1
            return "LOST_IN_ZONE", None
        return None, None
    
    def get_summary(self):
        total = len(self.completed_measurements)
        violations = sum(1 for m in self.completed_measurements if m["violation"])
        avg_speed = sum(m["speed_kmh"] for m in self.completed_measurements) / total if total > 0 else 0
        
        return {
            "total_valid": total,
            "discarded": self.discarded_count,
            "violations": violations,
            "average_speed": round(avg_speed, 1),
            "speed_limit": self.speed_limit,
            "measurements": self.completed_measurements
        }


class OcclusionTracker:
    """Reused from Epic 2."""
    def __init__(self, frame_rate=30):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=frame_rate
        )
        self.ghost_tracks = {}
        self.id_map = {}
        self.next_consistent_id = 1
        self.active_ids = set()
        
    def update(self, detections, frame_num):
        tracked = self.tracker.update_with_detections(detections)
        
        prev_active = self.active_ids.copy()
        self.active_ids = set()
        
        if tracked.tracker_id is None:
            return tracked, prev_active - self.active_ids  # all lost
        
        new_tracker_ids = tracked.tracker_id.tolist()
        new_consistent_ids = []
        
        for i, tid in enumerate(new_tracker_ids):
            x1, y1, x2, y2 = tracked.xyxy[i]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            
            if tid in self.id_map:
                consistent_id = self.id_map[tid]
            else:
                consistent_id = self._try_reassign(cx, cy, frame_num)
                if consistent_id is None:
                    consistent_id = self.next_consistent_id
                    self.next_consistent_id += 1
                self.id_map[tid] = consistent_id
            
            new_consistent_ids.append(consistent_id)
            self.active_ids.add(consistent_id)
        
        self._clean_ghosts(frame_num)
        
        for i, tid in enumerate(new_tracker_ids):
            cid = self.id_map[tid]
            x1, y1, x2, y2 = tracked.xyxy[i]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            self.ghost_tracks[cid] = {
                "last_pos": (float(cx), float(cy)),
                "lost_frame": int(frame_num)
            }
        
        tracked.tracker_id = new_consistent_ids
        lost_ids = prev_active - self.active_ids
        return tracked, lost_ids
    
    def _try_reassign(self, cx, cy, frame_num):
        best_match = None
        best_dist = float('inf')
        for gid, ghost in self.ghost_tracks.items():
            if frame_num - ghost["lost_frame"] > 15:
                continue
            gx, gy = ghost["last_pos"]
            dist = math.sqrt((float(cx) - gx)**2 + (float(cy) - gy)**2)
            if dist < 80 and dist < best_dist:
                best_dist = dist
                best_match = gid
        if best_match is not None:
            del self.ghost_tracks[best_match]
            return best_match
        return None
    
    def _clean_ghosts(self, frame_num):
        to_remove = [gid for gid, ghost in self.ghost_tracks.items() 
                    if frame_num - ghost["lost_frame"] > 15]
        for gid in to_remove:
            del self.ghost_tracks[gid]


def resize_for_display(frame, target_width=1280):
    h, w = frame.shape[:2]
    scale = target_width / w
    return cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_AREA)


def main():
    print("=" * 60)
    print("TVS-7: Speed Estimation (Fixed - Direction Aware)")
    print("=" * 60)
    print(f"\nSpeed Line 1 (Y={SPEED_LINE_1_Y}): ENTER zone (bottom)")
    print(f"Speed Line 2 (Y={SPEED_LINE_2_Y}): EXIT zone (top)")
    print(f"Real distance: {REAL_DISTANCE_METERS} meters")
    print(f"Speed limit: {SPEED_LIMIT_KMH} km/h")
    print(f"Min frames for valid: {MIN_FRAMES_FOR_VALID}")
    print("-" * 60)
    print("Logic: Vehicle must ENTER at Line 1, then EXIT at Line 2")
    print("       Vehicles exiting frame early are DISCARDED")
    print("-" * 60)
    
    model = YOLO(MODEL_PATH)
    tracker = OcclusionTracker(frame_rate=VIDEO_FPS)
    speed_est = SpeedEstimatorFixed(
        SPEED_LINE_1_Y, SPEED_LINE_2_Y,
        REAL_DISTANCE_METERS, VIDEO_FPS, SPEED_LIMIT_KMH
    )
    
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=0.6)
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("ERROR: Cannot open video")
        return
    
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\nVideo: {orig_w}x{orig_h}")
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
            tracked, lost_ids = tracker.update(detections, frame_count)
            
            # Mark lost tracks
            for lost_id in lost_ids:
                event, _ = speed_est.mark_lost(lost_id)
                if event:
                    print(f"  Frame {frame_count}: Vehicle #{lost_id} {event}")
            
            # Check line crossings for active tracks
            if tracked.tracker_id is not None:
                for i, track_id in enumerate(tracked.tracker_id):
                    x1, y1, x2, y2 = tracked.xyxy[i]
                    center_y = (y1 + y2) / 2
                    
                    event, data = speed_est.update(track_id, center_y, frame_count)
                    
                    if event == "ENTERED_ZONE":
                        print(f"  Frame {frame_count}: Vehicle #{track_id} ENTERED speed zone")
                    elif event == "SPEED_MEASURED":
                        speed = data
                        violation = "⚠️ VIOLATION!" if speed > SPEED_LIMIT_KMH else "OK"
                        print(f"  Frame {frame_count}: Vehicle #{track_id} speed = {speed:.1f} km/h {violation}")
                    elif event == "DISCARDED_TOO_FAST":
                        print(f"  Frame {frame_count}: Vehicle #{track_id} DISCARDED (too fast, false positive)")
                    elif event == "MISSED_ENTRY":
                        print(f"  Frame {frame_count}: Vehicle #{track_id} MISSED entry (already in zone)")
            
            # Draw overlays
            annotated = frame.copy()
            
            # Draw zone (between lines)
            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, SPEED_LINE_2_Y), (orig_w, SPEED_LINE_1_Y), (0, 255, 255), -1)
            annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)
            
            # Draw lines
            cv2.line(annotated, (0, SPEED_LINE_1_Y), (orig_w, SPEED_LINE_1_Y), (0, 255, 0), 2)
            cv2.line(annotated, (0, SPEED_LINE_2_Y), (orig_w, SPEED_LINE_2_Y), (0, 0, 255), 2)
            cv2.putText(annotated, "ENTER (Line 1)", (10, SPEED_LINE_1_Y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(annotated, "EXIT (Line 2)", (10, SPEED_LINE_2_Y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Labels with speed
            labels = []
            if tracked.tracker_id is not None:
                for class_id, track_id in zip(tracked.class_id, tracked.tracker_id):
                    class_name = model.names[class_id]
                    speed = speed_est.track_states[track_id]["speed_kmh"]
                    state = speed_est.track_states[track_id]["state"]
                    
                    if speed is not None:
                        label = f"#{track_id} {class_name} {speed}km/h"
                        if speed_est.track_states[track_id]["violation"]:
                            label += " ⚠️"
                    elif state == "entered":
                        label = f"#{track_id} {class_name} [timing...]"
                    elif state == "discarded":
                        label = f"#{track_id} {class_name} [discarded]"
                    else:
                        label = f"#{track_id} {class_name}"
                    
                    labels.append(label)
            
            annotated = box_annotator.annotate(scene=annotated, detections=tracked)
            annotated = label_annotator.annotate(scene=annotated, detections=tracked, labels=labels)
            
            # Info
            active = len(tracked.tracker_id) if tracked.tracker_id is not None else 0
            valid = len(speed_est.completed_measurements)
            discarded = speed_est.discarded_count
            info = f"Frame: {frame_count} | Active: {active} | Valid: {valid} | Discarded: {discarded}"
            cv2.putText(annotated, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        