from ultralytics import YOLOWorld
import cv2

# 1. Load the "Small" world model - Best balance for stones/debris
# In 2026, v2 is the standard for better export and accuracy.
model = YOLOWorld('yolov8s-worldv2.pt') 

# 2. Define your vocabulary. 
# You can be as descriptive as you want to improve accuracy!
model.set_classes(["stone", "loose debris", "large rock", "brick fragment"])

# 3. Run detection (imgsz=640 is standard for the 'Small' model)
results = model.predict("debris_site.jpg", conf=0.25)

# 4. Extract Bounding Boxes for SI Conversion
for r in results:
    img = r.orig_img
    for box in r.boxes:
        # Get pixels [x1, y1, x2, y2]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        # Draw on image
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Calculate pixel-width for SI measurements
        width_px = x2 - x1
        print(f"Detected {model.names[int(box.cls[0])]}: {width_px} pixels wide")

cv2.imshow("YOLO-World 2026", img)
cv2.waitKey(0)