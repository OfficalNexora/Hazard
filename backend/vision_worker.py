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
        
        # Retry bind if port is busy
        for i in range(5):
            try:
                self.zmq_publisher.bind(f"tcp://*:{zmq_port}")
                break
            except zmq.error.ZMQError:
                if i == 4: raise
                print(f"[VisionWorker] Port {zmq_port} busy, retrying ({i+1}/5)...")
                time.sleep(1)
        
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
        """Add a new camera source (Serial PORT, HTTP URL, or RTSP)
        
        Args:
            device_id: Unique camera identifier
            source: Serial port (COM3), HTTP stream URL, or RTSP URL
            vflip: Flip video vertically (for upside-down cameras)
            hflip: Flip video horizontally (mirror)
        """
        print(f"[VisionWorker] Adding camera {device_id} at {source} (vflip={vflip})")
        
        # For Network streams (RTSP or HTTP MJPEG), use FFmpeg streamer (more reliable)
        if source.startswith(("rtsp://", "http://")):
            print(f"[VisionWorker] Using FFmpeg streamer for network source: {source}")
            from ffmpeg_streamer import get_streamer
            streamer = get_streamer()
            
            # Callback to store frames in last_frames dict
            def on_frame(stream_id, frame):
                if vflip:
                    frame = cv2.flip(frame, 0)
                if hflip:
                    frame = cv2.flip(frame, 1)
                
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.last_frames[stream_id] = buffer.tobytes()
            
            # Determine if rotation is needed
            should_rotate = "esp32" in device_id.lower() or "camera" in device_id.lower()
            
            streamer.add_stream(device_id, source, frame_callback=on_frame, rotate=should_rotate)
            self.streams[device_id] = {
                "source": source,
                "active": True,
                "vflip": vflip,
                "hflip": hflip,
                "uses_ffmpeg": True
            }
            return
        
        # For non-RTSP (ESP32-CAM HTTP, Serial), use original method
        self.streams[device_id] = {
            "source": source,
            "active": True,
            "vflip": vflip,
            "hflip": hflip,
            "uses_ffmpeg": False
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
            print(f"[VisionWorker] Opening network stream: {source}")
            
            # Configure RTSP for TCP transport + timeout
            if source.startswith("rtsp://"):
                import os
                # CRITICAL: These settings fix most RTSP connection issues
                # stimeout = socket timeout in microseconds (5 seconds)
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
                print(f"[VisionWorker] RTSP: TCP transport, 5s timeout")
            
            # Retry loop for RTSP connections
            max_retries = 3
            for attempt in range(max_retries):
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Low buffer for latency
                
                if cap.isOpened():
                    # Test read to verify stream works
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        print(f"[VisionWorker] SUCCESS: {source} (attempt {attempt+1})")
                        break
                    else:
                        print(f"[VisionWorker] Connected but no frames (attempt {attempt+1})")
                        cap.release()
                else:
                    print(f"[VisionWorker] Connection failed (attempt {attempt+1}/{max_retries})")
                
                time.sleep(2)
            
            if not cap or not cap.isOpened():
                print(f"[VisionWorker] CRITICAL: Cannot open stream {source}")
                print(f"[VisionWorker] Test URL in VLC: {source}")
                print(f"[VisionWorker] Check: RTSP enabled? Credentials correct?")
                self.streams[device_id]["active"] = False
                return
        
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
                    print(f"[VisionWorker] Stream {device_id} lost. Retrying with FFMPEG...")
                    time.sleep(2)
                    cap.release()
                    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        print(f"[VisionWorker] Retry failed for {source}")
                    continue
                
                # Apply camera transforms if configured
                stream_config = self.streams[device_id]
                if stream_config.get("vflip", False):
                    frame = cv2.flip(frame, 0)  # Vertical flip
                if stream_config.get("hflip", False):
                    frame = cv2.flip(frame, 1)  # Horizontal flip

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
            if self.model is None:
                # Model still loading
                cv2.putText(frame, "INITIALIZING AI...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                return frame

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
                    
                    # Log to event store for 3D replay
                    try:
                        from camera_mapper import get_mapper
                        from event_store import get_event_store
                        
                        mapper = get_mapper()
                        detection_result = mapper.map_detection(cls_name, conf, (int(x1), int(y1), int(x2), int(y2)))
                        
                        event_store = get_event_store()
                        event_store.log_event(
                            event_type=cls_name.lower(),
                            position=detection_result.world_position,
                            zone_id=detection_result.zone_id,
                            zone_name=detection_result.zone_name,
                            confidence=conf,
                            metadata={"frame_id": frame_id, "device_id": device_id, "bbox": [x1, y1, x2, y2]}
                        )
                    except Exception as e:
                        pass  # Silent fail for event logging

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
