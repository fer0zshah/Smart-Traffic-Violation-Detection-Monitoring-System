"""
overlay_system.py
TVS-6: Complete detection overlay system with virtual lines and production toggle.

Usage:
    python overlay_system.py              # with overlay (development)
    python overlay_system.py --no-overlay # without overlay (production)
"""

import cv2
import supervision as sv
from ultralytics import YOLO
from collections import defaultdict
import math
import argparse

# ========== CONFIG ==========
VIDEO_PATH = "videos/ttt.mp4"
MODEL_PATH = "yolov8n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]
CONFIDENCE = 0.5
IOU = 0.45
DISPLAY_WIDTH = 1280

# Virtual lines for speed estimation (Epic 3 prep)
# These are Y-coordinates (horizontal lines) - adjust for your video
SPEED_LINE_1_Y = 400   # First speed measurement line
SPEED_LINE_2_Y = 600   # Second speed measurement line

# Stop line for red light detection (Epic 3 prep)
STOP_LINE_Y = 700

# Line colors
SPEED_LINE_COLOR = (0, 255, 255)    # Cyan
STOP_LINE_COLOR = (0, 0, 255)       # Red
LINE_THICKNESS = 2
# ============================

class OcclusionTracker:
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
        self.consistent_history = defaultdict(list)
        
    def update(self, detections, frame_num):
        tracked = self.tracker.update_with_detections(detections)
        
        if tracked.tracker_id is None:
            return tracked
        
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
            self.consistent_history[consistent_id].append((float(cx), float(cy), int(frame_num)))
        
        self._clean_ghosts(frame_num)
        
        for i, tid in enumerate(new_tracker_ids):
            cid = self.id_map[tid]
            x1, y1, x2, y2 = tracked.xyxy[i]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            class_id = int(tracked.class_id[i])
            self.ghost_tracks[cid] = {
                "last_pos": (float(cx), float(cy)),
                "lost_frame": int(frame_num),
                "class": class_id
            }
        
        tracked.tracker_id = new_consistent_ids
        return tracked
