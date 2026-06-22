import cv2
import time
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
target_classes = [2, 3, 5, 7]  # Car, Motorcycle, Bus, Truck

video_source = "tt.mp4"
cap = cv2.VideoCapture(video_source)

# Dictionary to track entry timestamps: { track_id: entry_time }
vehicle_timestamps = {}
# Dedicated tracking set to ensure we print to terminal EXACTLY once per car
printed_vehicles = set()

print("Speed Estimation Pipeline Active. Check terminal below for logs. Press 'q' to stop.\n")
print(f"{'VEHICLE TYPE':<15} | {'TRACK ID':<10} | {'CALCULATED SPEED':<18}")
print("-" * 50)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    HEIGHT, WIDTH, _ = frame.shape
    
    # Adjusting lines slightly for better tracking visibility
    LINE_1_Y = 280  # Top line (Yellow)
    LINE_2_Y = 360  # Bottom line (Red)
    REAL_WORLD_DISTANCE_METERS = 10.0

    # Draw timing markers on screen
    cv2.line(frame, (0, LINE_1_Y), (WIDTH, LINE_1_Y), (0, 255, 255), 2)
    cv2.line(frame, (0, LINE_2_Y), (WIDTH, LINE_2_Y), (0, 0, 255), 2)

    results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]

    if results.boxes is not None and results.boxes.id is not None:
        boxes = results.boxes.xyxy.cpu().numpy().astype(int)
        ids = results.boxes.id.cpu().numpy().astype(int)
        clss = results.boxes.cls.cpu().numpy().astype(int)

        for box, track_id, cls_id in zip(boxes, ids, clss):
            if cls_id in target_classes:
                x1, y1, x2, y2 = box
                cx = int((x1 + x2) / 2)
                cy = y2  # Base reference point
                
                current_time = time.time()
                speed_text = ""

                # --- BIDIRECTIONAL TIMING LOGIC ---
                # Check if the car enters the tracking zone between the two lines
                if min(LINE_1_Y, LINE_2_Y) <= cy <= max(LINE_1_Y, LINE_2_Y):
                    if track_id not in vehicle_timestamps:
                        # Record the entry time into the zone
                        vehicle_timestamps[track_id] = {'start_time': current_time, 'calculated_speed': None}
                
                # Check if the car has exited the zone (either above line 1 or below line 2)
                elif track_id in vehicle_timestamps:
                    data = vehicle_timestamps[track_id]
                    
                    if data['calculated_speed'] is None:
                        elapsed_time = current_time - data['start_time']
                        
                        # Only calculate if the car spent a realistic amount of time between lines
                        if elapsed_time > 0.1:  
                            kmh = (REAL_WORLD_DISTANCE_METERS / elapsed_time) * 3.6
                            # Cap extreme outliers due to tracking gaps
                            if kmh < 180:  
                                data['calculated_speed'] = f"{kmh:.1f} km/h"
                    
                    if data['calculated_speed'] is not None:
                        speed_text = data['calculated_speed']
                        
                        # Log to console exactly once per tracking ID
                        if track_id not in printed_vehicles:
                            class_name = model.names[cls_id].upper()
                            print(f"{class_name:<15} | ID: {track_id:<7} | {speed_text:<18}")
                            printed_vehicles.add(track_id)

                # UI Overlay Rendering
                label = f"{model.names[cls_id]} ID:{track_id} {speed_text}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    display_frame = cv2.resize(frame, (640, 480))
    cv2.imshow('Traffic Monitor - Speed Estimation Logs', display_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()