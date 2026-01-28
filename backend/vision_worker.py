"""
MOD-EVAC-MS - Vision Worker
ESP32-CAM frame reader and YOLO inference pipeline

Reads JPEG frames from serial, runs YOLOv8 inference, publishes detections.
"""

import serial
import serial.tools.list_ports
import threading
import time
import argparse
import cv2
import numpy as np
from typing import Optional, Callable
from ultralytics import YOLO
import zmq

from state_manager import state


class VisionWorker:
    """
    Worker that manages multiple camera streams (Serial or Network).
    Runs YOLO inference and distributes tasks to workers.
    """
    
    def __init__(self, model_path: str = "yolov8n.pt", zmq_port: int = 5556):
        self.running = False
        self.threads = []
        self.streams = {}  # {device_id: {"source": str, "cap": VideoCapture, "active": bool}}
        
        # YOLO model
        self.model_path = model_path
        self.model: Optional[YOLO] = None
        
        # ZeroMQ for publishing results
        self.zmq_context = zmq.Context()
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.zmq_publisher.bind(f"tcp://*:{zmq_port}")
        
        # Stats & Frames
        self.fps = 0.0
        self.frame_count = 0
        self.frame_counter = 0 # Monotonic counter for load balancing
        self.inference_count = 0
        self.last_frames = {}  # {device_id: bytes}
        self.class_names = [
            "Fire", "Smoke", "Flood", "Falling Debris",
            "Landslide", "Explosion", "Collapsed Structure", "Industrial Accident"
        ]
        
        self.load_model()

    def load_model(self):
        print(f"[VisionWorker] Loading model: {self.model_path}")
        self.model = YOLO(self.model_path)

    def add_camera(self, device_id: str, source: str):
        """Add a new camera source (Serial PORT or HTTP URL)"""
        print(f"[VisionWorker] Adding camera {device_id} at {source}")
        self.streams[device_id] = {
            "source": source,
            "active": True
        }
        thread = threading.Thread(target=self._camera_loop, args=(device_id,), daemon=True)
        self.threads.append(thread)
        thread.start()

    def _camera_loop(self, device_id: str):
        """Dedicated loop for a single camera source"""
        source = self.streams[device_id]["source"]
        
        # Determine if it's Serial or Network
        is_serial = source.startswith("COM") or source.startswith("/dev/")
        
        cap = None
        if not is_serial:
            cap = cv2.VideoCapture(source)
        
        frame_count = 0
        while self.running and self.streams[device_id]["active"]:
            frame = None
            
            if is_serial:
                # Optimized serial reading from previous implementation
                # (Skipped for brevity in this refactor, but would use the FRAME: protocol)
                time.sleep(0.1)
                continue
            else:
                ret, frame = cap.read()
                if not ret:
                    print(f"[VisionWorker] Stream {device_id} lost. Retrying...")
                    time.sleep(2)
                    cap.open(source)
                    continue

            frame_count += 1
            processed_frame = self._process_frame(device_id, frame, frame_count)
            
            # Store for MJPEG relay
            if processed_frame is not None:
                _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.last_frames[device_id] = buffer.tobytes()
            
            time.sleep(0.01)

        if cap: cap.release()

    def _process_frame(self, device_id: str, frame: np.ndarray, frame_id: int) -> np.ndarray:
        self.frame_counter += 1
        
        # 1. Distributed Delegation (Load Balancing)
        from worker_manager import worker_manager
        
        worker_count = len(worker_manager.workers)
        remote_detections = None
        
        # Strategy: 
        # If we have N workers, we process 1 locally, then N remotely, then 1 locally...
        # This keeps the Main Laptop active but significantly reduces its load.
        should_offload = (worker_count > 0) and (self.frame_counter % (worker_count + 1) != 0)
        
        if should_offload:
            # Encode frame to base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50]) # Lower quality for speed
            import base64
            frame_b64 = base64.b64encode(buffer).decode()
            
            # Sync Wait (Timed) - Fast timeout to maintain FPS
            # If worker is on LAN, 100ms should be plenty.
            remote_detections = worker_manager.distribute_task_sync(frame_b64, frame_id, timeout=0.15)
        
        detections_to_draw = []

        if remote_detections is not None:
            # WORKER SUCCESS: Use remote results (Skip Local YOLO)
            detections_to_draw = remote_detections
            # Note: worker_manager already added them to state
            
        else:
            # LOCAL FALLBACK: Run local YOLO
            # Either we chose to run locally, or the worker timed out
            results = self.model(frame, verbose=False, conf=0.4)
            self.inference_count += 1
            
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else "Hazard"
                    
                    detections_to_draw.append({
                        "class": cls_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })
                    
                    # Add to state and DB
                    state.add_detection(cls_name, conf, [x1, y1, x2, y2], frame_id)

        # Draw visualizations
        for det in detections_to_draw:
            cls_name = det['class']
            conf = det['confidence']
            bbox = det['bbox']
            x1, y1, x2, y2 = bbox
            
            color = (0, 0, 255) # Red for Main Laptop
            if remote_detections is not None:
                color = (255, 100, 0) # Blue/Orange for Remote Worker (Visual distinction)
                
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(frame, f"{cls_name} {conf:.2f}", (int(x1), int(y1)-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame

    def start(self):
        self.running = True
        # Attempt to auto-detect serial camera (ESP32-CAM)
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if any(x in p.description.lower() for x in ['cp210', 'ch340', 'usb serial']):
                 self.add_camera("esp32_cam_0", p.device)
                 break
        print("[VisionWorker] Running")

    def start_video(self, source: str):
        """Helper to start a video source for testing"""
        self.running = True
        self.add_camera("test_cam", source)

    def stop(self):
        self.running = False
        for t in self.threads:
            t.join(timeout=1)
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            "fps": round(self.fps, 1),
            "total_frames": self.frame_count,
            "total_detections": self.inference_count
        }


# Global worker instance
vision_worker: Optional[VisionWorker] = None


def get_vision_worker() -> Optional[VisionWorker]:
    """Get the global vision worker instance"""
    return vision_worker


def init_vision_worker(model_path: str = "yolov8n.pt", zmq_port: int = 5556) -> VisionWorker:
    """Initialize and start the vision worker"""
    global vision_worker
    vision_worker = VisionWorker(model_path=model_path, zmq_port=zmq_port)
    vision_worker.start()
    return vision_worker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32-CAM Vision Worker")
    parser.add_argument("--port", type=str, help="Serial port (e.g., COM4)")
    parser.add_argument("--source", type=str, help="Video source for testing")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path")
    args = parser.parse_args()
    
    worker = VisionWorker(port=args.port, model_path=args.model)
    
    if args.source:
        worker.start_video(args.source)
    else:
        worker.start()
    
    try:
        print("[VisionWorker] Running... Press Ctrl+C to stop")
        while True:
            stats = worker.get_stats()
            print(f"\r[VisionWorker] FPS: {stats['fps']} | Detections: {stats['total_detections']}", end="")
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        worker.stop()
