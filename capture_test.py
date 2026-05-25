import cv2
import os

# 1. Place a sample traffic video in your E:\ISDIOT folder and name it 'traffic.mp4'
video_source = "t.mp4" 

# Check if the file exists before trying to open it
if not os.path.exists(video_source):
    print(f"Error: '{video_source}' not found in the directory!")
    print("Please download a sample video, rename it to 'traffic.mp4', and place it in this folder.")
    exit()

cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print("Error: Could not open video file.")
    exit()

print("Video file loaded successfully.")

while True:
    ret, frame = cap.read()
    
    # If ret is False, the video has reached the end
    if not ret:
        print("Video playback finished.")
        break

    # Resize frame for consistent YOLOv8 input sizes later (Sprint 3)
    processed_frame = cv2.resize(frame, (640, 480))

    # Display the frame
    cv2.imshow('Traffic Monitor - Sprint 2 Video Test', processed_frame)

    # cv2.waitKey(25) adds a 25ms delay between frames so the video plays at normal speed.
    # Press 'q' to exit early.
    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()