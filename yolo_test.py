import cv2
from ultralytics import YOLO

# Load pre-trained YOLOv8 nano model (lightweight, runs efficiently on CPU)
model = YOLO("yolov8n.pt")

# COCO Dataset classes: 2 = car, 3 = motorcycle, 5 = bus, 7 = truck
target_classes = [2, 3, 5, 7]

# Source video file configured in Sprint 2
video_source = "traffic.mp4"
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print("Error: Could not open video file.")
    exit()

print("YOLO Inference Pipeline Active. Press 'q' to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Video playback finished.")
        break

    # Run object detection inference on the frame
    results = model(frame, verbose=False)[0]

    # Filter detections to extract only target vehicles
    for box in results.boxes:
        cls_id = int(box.cls[0])
        
        if cls_id in target_classes:
            # Extract boundary coordinates and confidence metrics
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            label = f"{model.names[cls_id]} {confidence:.2f}"

            # Visual overlay: Box bounding the object
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Visual overlay: Class name text
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Frame normalization for rendering consistency
    display_frame = cv2.resize(frame, (640, 480))
    cv2.imshow('Traffic Monitor - Sprint 3 Detection', display_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()