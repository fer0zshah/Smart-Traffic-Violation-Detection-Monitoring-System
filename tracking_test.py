import cv2
from ultralytics import YOLO

# Load the pre-trained YOLOv8 nano model
model = YOLO("yolov8n.pt")

# COCO Dataset classes for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
target_classes = [2, 3, 5, 7]

# Source video file
video_source = "traffic.mp4"
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print("Error: Could not open video file.")
    exit()

print("Tracking Pipeline Active. Press 'q' to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Video playback finished.")
        break

    # Run ByteTrack tracking instead of a standard raw detection inference
    # persist=True allows the model to remember tracking IDs across consecutive frames
    results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]

    # Process tracking results if boxes exist
    if results.boxes is not None and results.boxes.id is not None:
        boxes = results.boxes.xyxy.cpu().numpy().astype(int)
        ids = results.boxes.id.cpu().numpy().astype(int)
        clss = results.boxes.cls.cpu().numpy().astype(int)

        for box, track_id, cls_id in zip(boxes, ids, clss):
            if cls_id in target_classes:
                x1, y1, x2, y2 = box
                class_name = model.names[cls_id]
                
                # Create a persistent label incorporating both the class type AND its unique tracking ID
                label = f"{class_name} ID:{track_id}"

                # Visual overlay: Draw bounding box (Blue for tracking)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                # Visual overlay: Text banner for identity mapping
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Frame normalization for rendering consistency
    display_frame = cv2.resize(frame, (640, 480))
    cv2.imshow('Traffic Monitor - Sprint 4 Tracking Engine', display_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()