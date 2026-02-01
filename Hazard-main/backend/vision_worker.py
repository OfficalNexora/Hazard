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
# from ultralytics import YOLO  <-- Moved to load_model for lazy loading
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
        
        # self.load_model() <-- Run in background to prevent blocking startup
        threading.Thread(target=self.load_model, daemon=True).start()

    def load_model(self):
        print(f"[VisionWorker] Loading AI Model ({self.model_path})... (This may take 10-20s)")
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print("[VisionWorker] Model Loaded Successfully!")
        except Exception as e:
            print(f"[VisionWorker] FAILED to load model: {e}")

    def add_camera(self, device_id: str, source: str, vflip: bool = False, hflip: bool = False):
        """Add or update a camera source (Serial PORT or HTTP URL)"""
        
        # Check if already exists and active
        if device_id in self.streams and self.streams[device_id].get("active"):
            print(f"[VisionWorker] Camera {device_id} already active, updating config only.")
            self.streams[device_id].update({
                "source": source,
                "vflip": vflip,
                "hflip": hflip
            })
            return

        print(f"[VisionWorker] Starting new stream for {device_id} at {source} (vflip={vflip})")
        self.streams[device_id] = {
            "source": source,
            "active": True,
            "vflip": vflip,
            "hflip": hflip
        }
        thread = threading.Thread(target=self._camera_loop, args=(device_id,), daemon=True)
        self.threads.append(thread)
        thread.start()

    def _camera_loop(self, device_id: str):
        """Dedicated loop for a single camera source"""
        
        cap = None
        last_source = None
        
        while self.running and self.streams[device_id]["active"]:
            stream_config = self.streams[device_id]
            source = stream_config["source"]
            is_serial = source.startswith("COM") or source.startswith("/dev/")
            
            # Re-initialize capture if source has changed
            if source != last_source:
                print(f"[VisionWorker] Switch: {device_id} -> {source}")
                if cap: cap.release()
                if not is_serial:
                    cap = cv2.VideoCapture(source)
                last_source = source

            frame = None
            if is_serial:
                # Serial logic...
                time.sleep(0.1)
                continue
            else:
                if not cap or not cap.isOpened():
                    cap = cv2.VideoCapture(source)
                    state.update_device(device_id, "esp32_cam", True, source, status="Connecting...")
                    time.sleep(1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    print(f"[VisionWorker] Stream {device_id} lost at {source}. Retrying...")
                    
                    # Smart Port Fallback
                    if ":81/" in source:
                        source = source.replace(":81/", ":80/")
                        status = "Retrying (Port 80)..."
                    elif ":80/" in source:
                        source = source.replace(":80/", ":81/")
                        status = "Retrying (Port 81)..."
                    else:
                        status = "Connection Lost"
                    
                    state.update_device(device_id, "esp32_cam", True, source, status=status)
                    self.streams[device_id]["source"] = source
                    cap.open(source)
                    time.sleep(2)
                    continue
                
                # Successful frame read
                state.update_device(device_id, "esp32_cam", True, source, status="Streaming")

                # Apply Transforms
                if stream_config.get("vflip", False):
                    frame = cv2.flip(frame, 0)
                if stream_config.get("hflip", False):
                    frame = cv2.flip(frame, 1)

            # Process and store frame...
            processed = self._process_frame(device_id, frame, int(time.time()))
            _, buffer = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.last_frames[device_id] = buffer.tobytes()
            time.sleep(0.01)

        if cap: cap.release()

    def _process_frame(self, device_id: str, frame: np.ndarray, frame_id: int) -> np.ndarray:
        self.frame_counter += 1
        
        # 1. Aggressive Distributed Delegation (Extreme Offloading)
        from worker_manager import worker_manager
        
        worker_count = len(worker_manager.workers)
        remote_detections = None
        
        # WE ONLY PROCESS LOCALLY IF:
        # A) No workers are connected
        # B) The remote task fails or times out (Safe Fallback)
        if worker_count > 0:
            # Encode frame to base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            import base64
            frame_b64 = base64.b64encode(buffer).decode()
            
            # Try to offload (Wait slightly longer for network latency)
            remote_detections = worker_manager.distribute_task_sync(frame_b64, frame_id, timeout=0.2)
            
            if remote_detections is not None:
                # SUCCESS: We skipped local YOLO! Laptop stays cool.
                detections_to_draw = remote_detections
            else:
                # WORKER TIMEOUT: Fallback to local (prevent freeze)
                print(f"[VisionWorker] Workers busy/slow. Falling back to local AI.")
                detections_to_draw = self._run_local_inference(frame, frame_id)
        else:
            # NO WORKERS: Final resort (Local)
            detections_to_draw = self._run_local_inference(frame, frame_id)
        
        # Draw visualizations (Worker detections use a different color)
        for det in detections_to_draw:
            cls_name = det['class']
            conf = det['confidence']
            bbox = det['bbox']
            x1, y1, x2, y2 = bbox
            
            color = (0, 0, 255) # Red for Local
            if remote_detections is not None:
                color = (0, 255, 0) # Green for Remote Worker (Efficiency Success)
                
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(frame, f"{cls_name} {conf:.2f}", (int(x1), int(y1)-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame

    def _run_local_inference(self, frame, frame_id):
        """Final resort YOLO inference on main host"""
        if self.model is None:
            return []

        results = self.model(frame, verbose=False, conf=0.4)
        self.inference_count += 1
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else "Hazard"
                
                detections.append({
                    "class": cls_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
                
                # Add to state and DB
                state.add_detection(cls_name, conf, [x1, y1, x2, y2], frame_id)
        return detections

    def start(self):
        self.running = True
        # Auto-detect serial cameras is disabled to prevent duplicates with WiFi cameras
        # ports = serial.tools.list_ports.comports()
        # for p in ports:
        #     if any(x in p.description.lower() for x in ['cp210', 'ch340', 'usb serial']):
        #          self.add_camera("esp32_cam_0", p.device)
        #          break
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
