import zmq
import cv2
import base64
import numpy as np
import json
import time
import socket
from ultralytics import YOLO

# Configuration
ROUTER_IP = "localhost" # Request from Router IP (Change if on different machine)
ZMQ_PULL_PORT = 5555    # Recv frames
ZMQ_PUSH_PORT = 5556    # Send results
WORKER_ID = socket.gethostname()

def main():
    print(f"[Worker] Initializing Node: {WORKER_ID}")
    
    # 1. Load Model (Load once!)
    print("[Worker] Loading YOLOv8 model...")
    # Using 'yolov8n.pt' for speed (Nano model)
    model = YOLO("yolov8n.pt") 
    print("[Worker] Model loaded.")

    # 2. Setup ZeroMQ
    context = zmq.Context()

    # Receive Frames (PULL)
    receiver = context.socket(zmq.PULL)
    receiver.connect(f"tcp://{ROUTER_IP}:{ZMQ_PULL_PORT}")
    print(f"[Worker] Connected to Router Frame Output (Port {ZMQ_PULL_PORT})")

    # Send Results (PUSH)
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://{ROUTER_IP}:{ZMQ_PUSH_PORT}")
    print(f"[Worker] Connected to Router Result Collector (Port {ZMQ_PUSH_PORT})")

    print("[Worker] Waiting for tasks...")
    
    try:
        while True:
            # 1. Receive Task
            payload = receiver.recv_json()
            frame_id = payload.get('frame_id')
            jpg_txt = payload.get('image')
            
            # 2. Decode Image
            jpg_bytes = base64.b64decode(jpg_txt)
            np_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # 3. Inference
            # Run YOLO. agnostic=True for better merging later?
            results = model(frame, verbose=False) 
            
            # 4. Extract Detections
            detections = []
            for r in results:
                for box in r.boxes:
                    # Extract coords, conf, class
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "conf": conf,
                        "class": cls_name,
                        "class_id": cls_id
                    })

            # 5. Send Result
            result_payload = {
                "frame_id": frame_id,
                "worker_id": WORKER_ID,
                "detections": detections,
                "processed_at": time.time()
            }
            sender.send_json(result_payload)
            
            print(f"[Worker] Processed Frame {frame_id} | Found: {len(detections)} objects")

    except KeyboardInterrupt:
        print("[Worker] Stopping...")
    finally:
        receiver.close()
        sender.close()
        context.term()

if __name__ == "__main__":
    main()
