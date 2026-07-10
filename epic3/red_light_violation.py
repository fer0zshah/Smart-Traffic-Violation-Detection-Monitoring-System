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
# ===== main.py =====
from config import STOP_LINE_Y

def main():
    print("Stop line configured at Y =", STOP_LINE_Y)

if __name__ == "__main__":
    main()