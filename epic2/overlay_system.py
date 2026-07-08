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
        to_remove = []
        for gid, ghost in self.ghost_tracks.items():
            if frame_num - ghost["lost_frame"] > 15:
                to_remove.append(gid)
        for gid in to_remove:
            del self.ghost_tracks[gid]


class OverlayRenderer:
    """Handles all visual overlays for the detection system."""
    
    def __init__(self, show_overlay=True):
        self.show_overlay = show_overlay
        self.box_annotator = sv.BoxAnnotator(thickness=2)
        self.label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=0.6)
        self.trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=50)
        
    def draw_virtual_lines(self, frame, frame_width):
        """Draw speed measurement and stop lines."""
        if not self.show_overlay:
            return frame
            
        annotated = frame.copy()
        
        # Speed measurement lines
        cv2.line(annotated, (0, SPEED_LINE_1_Y), (frame_width, SPEED_LINE_1_Y), 
                SPEED_LINE_COLOR, LINE_THICKNESS)
        cv2.line(annotated, (0, SPEED_LINE_2_Y), (frame_width, SPEED_LINE_2_Y), 
                SPEED_LINE_COLOR, LINE_THICKNESS)
        
        # Labels for speed lines
        cv2.putText(annotated, "SPEED LINE 1", (10, SPEED_LINE_1_Y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, SPEED_LINE_COLOR, 1)
        cv2.putText(annotated, "SPEED LINE 2", (10, SPEED_LINE_2_Y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, SPEED_LINE_COLOR, 1)
        
        # Stop line
        cv2.line(annotated, (0, STOP_LINE_Y), (frame_width, STOP_LINE_Y), 
                STOP_LINE_COLOR, LINE_THICKNESS + 1)
        cv2.putText(annotated, "STOP LINE", (10, STOP_LINE_Y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, STOP_LINE_COLOR, 1)
        
        # Legend
        legend_y = 30
        cv2.putText(annotated, "VIRTUAL LINES:", (frame_width - 250, legend_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(annotated, "Cyan = Speed measurement", (frame_width - 250, legend_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, SPEED_LINE_COLOR, 1)
        cv2.putText(annotated, "Red = Stop line (red light)", (frame_width - 250, legend_y + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, STOP_LINE_COLOR, 1)
        
        return annotated
    
    def draw_detections(self, frame, tracked, model_names):
        """Draw bounding boxes, labels, and traces."""
        if not self.show_overlay:
            return frame
            
        labels = []
        if tracked.tracker_id is not None:
            for class_id, track_id in zip(tracked.class_id, tracked.tracker_id):
                class_name = model_names[class_id]
                labels.append(f"ID:{track_id} {class_name}")
        
        annotated = self.box_annotator.annotate(scene=frame, detections=tracked)
        annotated = self.label_annotator.annotate(scene=annotated, detections=tracked, labels=labels)
        
        return annotated
