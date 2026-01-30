import cv2
import numpy as np

class ObstructionAI:
    def __init__(self, sensitivity: int = 50):
        """
        Initialize the Obstruction AI.
        :param sensitivity: Sensitivity threshold for edge detection (lower = more sensitive).
        """
        self.sensitivity = sensitivity
        self.kernel = np.ones((5, 5), np.uint8)

    def detect_obstructions(self, frame):
        """
        Detects obstructions in the given frame using edge detection and contour analysis.
        Returns a list of detected obstructions: [{'bbox': (x, y, w, h), 'area': float}]
        """
        if frame is None:
            return []

        # 1. Grayscale & Blur
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (7, 7), 0)

        # 2. Edge Detection (Canny)
        edges = cv2.Canny(blur, self.sensitivity, self.sensitivity * 2)

        # 3. Dilate to connect edges
        dilated = cv2.dilate(edges, self.kernel, iterations=2)

        # 4. Find Contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        obstructions = []
        height, width = frame.shape[:2]
        min_area = (width * height) * 0.05  # Obstruction must be at least 5% of screen

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Filter out things that are too wide/flat (like horizons)
                aspect_ratio = w / float(h)
                if aspect_ratio > 4.0: 
                    continue

                obstructions.append({
                    "bbox": (x, y, w, h),
                    "area": area,
                    "confidence": min(1.0, area / (width * height * 0.5)) # Conf based on size
                })

        return obstructions

    def draw_results(self, frame, obstructions):
        """
        Draws bounding boxes around detected obstructions.
        """
        for obs in obstructions:
            x, y, w, h = obs['bbox']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "OBSTRUCTION", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
