# ===== config.py =====

# --- STOP LINE CONFIG ---
STOP_LINE_Y = 550   # Y coordinate of stop line (pixels)

# --- VIDEO / MODEL ---
VIDEO_PATH = "videos/tt.mp4"
MODEL_PATH = "yolov8n.pt"

# --- DETECTION ---
VEHICLE_CLASSES = [2, 3, 5, 7]
CONFIDENCE = 0.5
IOU = 0.45

# --- DISPLAY ---
DISPLAY_WIDTH = 1280


# ===== detector.py =====
class RedLightDetector:
    def __init__(self, stop_line_y, cooldown=60):
        self.stop_line_y = stop_line_y
        self.cooldown = cooldown
        self.tracks = {}

        self.signal = "GREEN"

    def update_signal(self, signal):
        self.signal = signal

    def process(self, detections, frame_num):
        events = []

        for track_id, bottom_y in detections:

            if track_id not in self.tracks:
                self.tracks[track_id] = {
                    "last_y": bottom_y,
                    "last_violation_frame": -999,
                }

            track = self.tracks[track_id]

            # cooldown check
            if frame_num - track["last_violation_frame"] < self.cooldown:
                track["last_y"] = bottom_y
                continue

            if self.signal == "RED":
                if bottom_y >= self.stop_line_y and track["last_y"] < self.stop_line_y:
                    events.append(f"Track {track_id} VIOLATION")
                    track["last_violation_frame"] = frame_num

            track["last_y"] = bottom_y

        return events

# ===== main.py =====

from config import STOP_LINE_Y
from detector import RedLightDetector

detector = RedLightDetector(STOP_LINE_Y)

# simulate input
detector.update_signal("RED")

detections = [(1, 540), (1, 560)]  # crossing
events = detector.process(detections, 10)

print(events)

from config import STOP_LINE_Y

def main():
    print("Stop line configured at Y =", STOP_LINE_Y)

if __name__ == "__main__":
    main()