"""
red_light_detection.py
TVS-8: Red light crossing detection with mock signal.

Subtasks:
1. Define stop line position in config
2. Detect track crossing stop line while signal = RED
3. Debounce detection to avoid duplicate triggers
4. Log violation event with frame number and timestamp
"""

import cv2
import supervision as sv
from ultralytics import YOLO
import math
import json
from datetime import datetime
from enum import Enum

# ========== CONFIGURATION ==========
VIDEO_PATH = "videos/tt.mp4"
MODEL_PATH = "yolov8n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]
CONFIDENCE = 0.5
IOU = 0.45
DISPLAY_WIDTH = 1280

# --- STOP LINE ---
STOP_LINE_Y = 550  # Vehicles must stop before this line

# --- MOCK TRAFFIC LIGHT ---
# Since no hardware, we simulate with a timer or keyboard
# States: GREEN -> YELLOW -> RED -> GREEN
LIGHT_CYCLE_FRAMES = 300  # frames per full cycle
GREEN_FRAMES = 120
YELLOW_FRAMES = 60
RED_FRAMES = 120

# Or use keyboard: R=Red, G=Green, Y=Yellow
# Set USE_KEYBOARD = True to control manually
USE_KEYBOARD = True

# --- VIOLATION SETTINGS ---
# Cooldown: don't re-trigger same vehicle for N frames
VIOLATION_COOLDOWN_FRAMES = 60
# Minimum frames vehicle must be tracked before violation (prevent false positives)
MIN_TRACK_FRAMES = 5
# ==================================


class SignalState(Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class MockTrafficLight:
    """Simulates traffic light signal. Can be automatic or keyboard-controlled."""
    
    def __init__(self, cycle_frames=300, green=120, yellow=60, red=120):
        self.cycle = cycle_frames
        self.green = green
        self.yellow = yellow
        self.red = red
        self.frame = 0
        self.manual_state = SignalState.GREEN
        
    def update(self, frame_num: int, key=None) -> SignalState:
        if USE_KEYBOARD and key:
            if key == ord('g'):
                self.manual_state = SignalState.GREEN
            elif key == ord('y'):
                self.manual_state = SignalState.YELLOW
            elif key == ord('r'):
                self.manual_state = SignalState.RED
        
        if USE_KEYBOARD:
            return self.manual_state
        
        # Automatic cycle
        pos = frame_num % self.cycle
        if pos < self.green:
            return SignalState.GREEN
        elif pos < self.green + self.yellow:
            return SignalState.YELLOW
        else:
            return SignalState.RED
    
    def get_color(self, state: SignalState) -> tuple:
        colors = {
            SignalState.GREEN: (0, 255, 0),
            SignalState.YELLOW: (0, 255, 255),
            SignalState.RED: (0, 0, 255),
        }
        return colors[state]


class RedLightDetector:
    """
    Detects vehicles crossing stop line during RED signal.
    """
    
    def __init__(self, stop_line_y: int, cooldown_frames: int, min_track_frames: int):
        self.stop_line_y = stop_line_y
        self.cooldown = cooldown_frames
        self.min_track_frames = min_track_frames
        
        # Track states: {track_id: {"frames_tracked": 0, "violated": False, "violation_frame": None, "last_pos_y": None}}
        self.tracks = {}
        
        # Violation log
        self.violations = []
        
        # Current signal state
        self.signal = SignalState.GREEN
        
    def update_signal(self, signal: SignalState):
        self.signal = signal
    
    def process_detections(self, detections: sv.Detections, frame_num: int):
        """
        Check for red light violations.
        Returns list of events.
        """
        events = []
        
        if detections.tracker_id is None:
            return events
        
        current_ids = set(detections.tracker_id.tolist())
        
        for i, track_id in enumerate(detections.tracker_id.tolist()):
            x1, y1, x2, y2 = detections.xyxy[i]
            bottom_y = y2
            center_y = (y1 + y2) / 2
            
            # Initialize or update track
            if track_id not in self.tracks:
                self.tracks[track_id] = {
                    "frames_tracked": 0,
                    "violated": False,
                    "violation_frame": None,
                    "last_bottom_y": bottom_y,
                    "first_seen_frame": frame_num,
                }
            
            track = self.tracks[track_id]
            track["frames_tracked"] += 1
            
            # Only check if signal is RED
            if self.signal != SignalState.RED:
                track["last_bottom_y"] = bottom_y
                continue
            
            # Skip if already violated (cooldown)
            if track["violated"]:
                # Check cooldown expired
                if frame_num - track["violation_frame"] > self.cooldown:
                    track["violated"] = False  # reset for potential re-violation
                else:
                    track["last_bottom_y"] = bottom_y
                    continue
            
            # Need minimum tracking frames for confidence
            if track["frames_tracked"] < self.min_track_frames:
                track["last_bottom_y"] = bottom_y
                continue
            
            # Check crossing: bottom edge crosses stop line from above to below
            # (vehicle was above line, now below or at line)
            if bottom_y >= self.stop_line_y and track["last_bottom_y"] < self.stop_line_y:
                # VIOLATION!
                track["violated"] = True
                track["violation_frame"] = frame_num
                
                violation = {
                    "track_id": track_id,
                    "frame": frame_num,
                    "timestamp": datetime.now().isoformat(),
                    "signal_state": self.signal.value,
                    "stop_line_y": self.stop_line_y,
                    "vehicle_bottom_y": round(bottom_y, 1),
                    "frames_tracked": track["frames_tracked"],
                }
                self.violations.append(violation)
                
                events.append(f"Vehicle #{track_id}: RED LIGHT VIOLATION at frame {frame_num}")
            
            track["last_bottom_y"] = bottom_y
        
        # Clean old tracks
        stale = [tid for tid, t in self.tracks.items() if tid not in current_ids and 
                 frame_num - t.get("last_seen", frame_num) > 100]
        for tid in stale:
            del self.tracks[tid]
        
        return events
    
    def get_summary(self) -> dict:
        return {
            "total_violations": len(self.violations),
            "signal_state": self.signal.value,
            "violations": self.violations,
        }


def resize_for_display(frame, target_width=1280):
    h, w = frame.shape[:2]
    scale = target_width / w
    return cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_AREA)


def draw_scene(frame, orig_w, light, signal_state, detector):
    """Draw stop line and traffic light."""
    annotated = frame.copy()
    
    # Stop line (thick red when signal is RED, thin white otherwise)
    color = (0, 0, 255) if signal_state == SignalState.RED else (200, 200, 200)
    thickness = 4 if signal_state == SignalState.RED else 2
    cv2.line(annotated, (0, detector.stop_line_y), (orig_w, detector.stop_line_y), color, thickness)
    cv2.putText(annotated, f"STOP LINE (Y={detector.stop_line_y})", 
                (10, detector.stop_line_y - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Traffic light indicator (top right corner)
    light_x, light_y = orig_w - 120, 80
    box_size = 80
    
    # Light box
    cv2.rectangle(annotated, (light_x - 10, light_y - 60), 
                  (light_x + box_size + 10, light_y + box_size + 10), (50, 50, 50), -1)
    cv2.rectangle(annotated, (light_x - 10, light_y - 60), 
                  (light_x + box_size + 10, light_y + box_size + 10), (200, 200, 200), 2)
    
    # Three lights
    states = [SignalState.RED, SignalState.YELLOW, SignalState.GREEN]
    for i, st in enumerate(states):
        cy = light_y + i * 30
        color = light.get_color(st) if st == signal_state else (50, 50, 50)
        cv2.circle(annotated, (light_x + 40, cy), 12, color, -1)
        if st == signal_state:
            cv2.circle(annotated, (light_x + 40, cy), 12, (255, 255, 255), 2)
    
    # Signal text
    text_color = light.get_color(signal_state)
    cv2.putText(annotated, signal_state.value, (light_x - 5, light_y + 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
    
    # Keyboard hint
    if USE_KEYBOARD:
        cv2.putText(annotated, "Press R/Y/G for signal", (light_x - 30, light_y + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    return annotated


def build_labels(tracked, detector, model):
    labels = []
    if tracked.tracker_id is None:
        return labels
    
    for class_id, track_id in zip(tracked.class_id, tracked.tracker_id):
        class_name = model.names[class_id]
        
        if track_id in detector.tracks and detector.tracks[track_id]["violated"]:
            label = f"#{track_id} {class_name} [!RED LIGHT VIOLATION!]"
        else:
            label = f"#{track_id} {class_name}"
        
        labels.append(label)
    
    return labels


def main():
    print("=" * 60)
    print("TVS-8: Red Light Crossing Detection")
    print("=" * 60)
    print(f"Stop line: Y={STOP_LINE_Y}")
    print(f"Signal mode: {'KEYBOARD' if USE_KEYBOARD else 'AUTO'}")
    if USE_KEYBOARD:
        print("  Press R=Red, Y=Yellow, G=Green")
    print(f"Cooldown: {VIOLATION_COOLDOWN_FRAMES} frames")
    print("-" * 60)
    
    model = YOLO(MODEL_PATH)
    tracker = sv.ByteTrack(
        track_activation_threshold=0.25,
        lost_track_buffer=30,
        minimum_matching_threshold=0.8,
        frame_rate=30,
    )
    
    light = MockTrafficLight(LIGHT_CYCLE_FRAMES, GREEN_FRAMES, YELLOW_FRAMES, RED_FRAMES)
    detector = RedLightDetector(STOP_LINE_Y, VIOLATION_COOLDOWN_FRAMES, MIN_TRACK_FRAMES)
    
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=0.6)
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("ERROR: Cannot open video")
        return
    
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {orig_w}x{orig_h}")
    print("Press Q=quit, P=pause, R=Red, Y=Yellow, G=Green")
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
            
            # Update signal
            key_pressed = None
            signal = light.update(frame_count, key_pressed)
            detector.update_signal(signal)
            
            # Check violations
            events = detector.process_detections(tracked, frame_count)
            for event in events:
                print(f"  Frame {frame_count}: {event}")
            
            # Draw
            annotated = draw_scene(frame, orig_w, light, signal, detector)
            labels = build_labels(tracked, detector, model)
            annotated = box_annotator.annotate(scene=annotated, detections=tracked)
            annotated = label_annotator.annotate(scene=annotated, detections=tracked, labels=labels)
            
            active = len(tracked.tracker_id) if tracked.tracker_id is not None else 0
            hud = (f"Frame: {frame_count} | Active: {active} "
                   f"| Violations: {len(detector.violations)} | Signal: {signal.value}")
            cv2.putText(annotated, hud, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            display = resize_for_display(annotated, DISPLAY_WIDTH)
            cv2.imshow("TVS-8 Red Light Detection", display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("p"):
            paused = not paused
        elif key in (ord('r'), ord('y'), ord('g')):
            light.update(frame_count, key)
            print(f"  Manual signal change: {chr(key).upper()}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Report
    summary = detector.get_summary()
    print("\n" + "=" * 60)
    print("RED LIGHT DETECTION REPORT")
    print("=" * 60)
    print(f"Total violations: {summary['total_violations']}")
    
    if summary["violations"]:
        print("\nViolation log:")
        for v in summary["violations"]:
            print(f"  Frame {v['frame']}: Vehicle #{v['track_id']} "
                  f"(tracked {v['frames_tracked']} frames)")
    
    with open("red_light_violations.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: red_light_violations.json")
    print("=" * 60)


if __name__ == "__main__":
    main()