import cv2
import time
from ultralytics import YOLO

# 1. Load Models
print("Loading Human Detection Model (yolov12s.pt)...")
human_model = YOLO('yolov12s.pt')

print("Loading Fire/Smoke Detection Model (best_nano_111.pt)...")
fire_model = YOLO('best_nano_111.pt')

# 2. Connect to the default webcam
cap = cv2.VideoCapture(0)

# Set target FPS and timing
TARGET_FPS = 24
prev_frame_time = 0

print("Starting Combined Detection System (Press 'q' to quit)...")

while cap.isOpened():
    # FPS Control
    time_elapsed = time.time() - prev_frame_time
    if time_elapsed < 1./TARGET_FPS:
        continue
    
    success, frame = cap.read()
    if not success:
        break

    # 3. AI Inference (Dual Model)
    
    # Human Detection (Class 0 = Person)
    human_results = human_model.predict(
        source=frame, 
        imgsz=640, 
        classes=[0], 
        conf=0.45, 
        verbose=False
    )
    
    # Fire/Smoke Detection (Only Class 0 = Fire)
    fire_results = fire_model.predict(
        source=frame,
        imgsz=640,
        conf=0.40,
        classes=[0],  # Filter out Smoke (Class 1) to reduce hallucinations
        verbose=False
    )

    # 4. Process and Visualize (Merge Results)
    annotated_frame = frame.copy()

    # Draw Humans (Green boxes usually default)
    for r in human_results:
        annotated_frame = r.plot(img=annotated_frame)
    
    # Draw Fire/Smoke (Overlay on top)
    for r in fire_results:
        # We manually draw to ensure visibility if plot() overwrites too much, 
        # but r.plot(img=...) is designed to composite.
        annotated_frame = r.plot(img=annotated_frame)

    # Display FPS
    actual_fps = 1 / time_elapsed
    cv2.putText(annotated_frame, f"FPS: {int(actual_fps)} | Combined Vision", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    cv2.imshow("NEXORA - Combined Vision (Human + Fire + Smoke)", annotated_frame)
    
    prev_frame_time = time.time()

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()