from ultralytics import YOLO
import cv2
import math
import os
from dotenv import load_dotenv

def run_inference(source=0):
    """
    Run inference on a video source (webcam ID or file path).
    source: 0 for webcam, or "path/to/video.mp4"
    """
    # Load Config from .env
    load_dotenv()
    project_name = os.getenv("PROJECT_NAME", "hazard_project")
    exp_name = os.getenv("EXPERIMENT_NAME", "yolov8n_hazard")
    model_type = os.getenv("MODEL_TYPE", "yolov8n.pt")
    
    # Attempt to load trained model first, fallback to base model
    trained_model_path = os.path.join(project_name, exp_name, "weights", "best.pt")
    
    if os.path.exists(trained_model_path):
        model_path = trained_model_path
        print(f"[Check] Found trained model at: {model_path}")
    else:
        model_path = model_type
        print(f"[Warning] Trained model not found. Using base model: {model_path}")
    
    print(f"🔍 Loading Model from: {model_path}")
    model = YOLO(model_path)

    # Define Hazard Colors (BGR format)
    classNames = [
        "Fire", "Smoke", "Flood", "Falling Debris", 
        "Landslide", "Explosion", "Collapsed Structure", "Industrial Accident"
    ]
    
    # Color map for alerts: Red/Orange for high danger, Blue for water
    colors = {
        "Fire": (0, 0, 255),               # Red
        "Explosion": (0, 0, 255),          # Red
        "Smoke": (128, 128, 128),          # Gray
        "Flood": (255, 0, 0),              # Blue
        "Landslide": (0, 165, 255),        # Orange
        "Falling Debris": (0, 255, 255),   # Yellow
        "Collapsed Structure": (0, 0, 128) # Dark Red
    }

    # Open Video Source
    cap = cv2.VideoCapture(source)
    
    # Set webcam resolution (this improves the performance)
    cap.set(3, 1280)
    cap.set(4, 720)

    if not cap.isOpened():
        print(f" Error: Could not open video source {source}")
        return

    print(" Starting Inference... Press 'q' to exit.")

    while True:
        success, img = cap.read()
        if not success:
            break

        # Run Detection
        results = model(img, stream=True, conf=0.4) # Confidence threshold 0.4

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Bounding Box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Class and Confidence
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                
                # Safety check for class index
                if cls < len(classNames):
                    currentClass = classNames[cls]
                else:
                    currentClass = "Hazard" # Fallback

                # Get color
                color = colors.get(currentClass, (0, 255, 0)) # Default Green

                # Draw Visuals
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
                
                label = f'{currentClass} {conf}'
                t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
                c2 = x1 + t_size[0], y1 - t_size[1] - 3
                
                cv2.rectangle(img, (x1, y1), c2, color, -1, cv2.LINE_AA)  # Filled label background
                cv2.putText(img, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=2, lineType=cv2.LINE_AA)

        # Show Output
        cv2.imshow('Hazard Detection System', img)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    # Default to webcam. Change to video path string for file.
    run_inference(0)
