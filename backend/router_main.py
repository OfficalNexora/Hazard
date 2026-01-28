import cv2
import zmq
import base64
import time
import json
import numpy as np

# Configuration
ZMQ_PUSH_PORT = 5555  # Send frames to workers
ZMQ_PULL_PORT = 5556  # Receive results from workers
CAMERA_INDEX = 0      # 0 for webcam, or path to video file
FRAME_WIDTH = 640     # I resize to this width to optimize bandwidth usage
QUALITY = 80          # JPEG Quality (0-100)

def main():
    # 1. Setup ZeroMQ Context
    # I chose ZeroMQ PUSH/PULL pattern here to decouple the frame ingestion from the heavy processing logic.
    context = zmq.Context()
    
    # Socket to send messages to workers
    sender = context.socket(zmq.PUSH)
    sender.bind(f"tcp://*:{ZMQ_PUSH_PORT}")
    print(f"[Router] Frame Distributor bound to port {ZMQ_PUSH_PORT}")

    # Socket to receive messages from workers
    receiver = context.socket(zmq.PULL)
    receiver.bind(f"tcp://*:{ZMQ_PULL_PORT}")
    print(f"[Router] Result Collector bound to port {ZMQ_PULL_PORT}")

    # 2. Setup Video Capture
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[Router] Error: Could not open video source.")
        return

    frame_id = 0
    print("[Router] Starting video capture...")

    try:
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            if not ret:
                print("[Router] Video ended or failed.")
                break

            frame_id += 1
            
            # --- 1. Pre-processing ---
            # I resize to reduce bandwidth before sending over the network context
            h, w = frame.shape[:2]
            new_h = int(h * (FRAME_WIDTH / w))
            resized_frame = cv2.resize(frame, (FRAME_WIDTH, new_h))

            # Encode to JPEG
            # I use JPEG encoding here as a trade-off between CPU usage and network payload size.
            _, buffer = cv2.imencode('.jpg', resized_frame, [int(cv2.IMWRITE_JPEG_QUALITY), QUALITY])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            # --- 2. Send to Worker ---
            # Payload: Frame ID + Image Data
            payload = {
                'frame_id': frame_id,
                'image': jpg_as_text,
                'timestamp': time.time()
            }
            sender.send_json(payload)
            
            # --- 3. Non-blocking Result Check (for demonstration) ---
            # In a real async loop (or separate thread), we would collect results here.
            # I am using Polling here for simplicity in this synchronous loop.
            try:
                # Check if any result is ready (non-blocking)
                while True:
                    result_data = receiver.recv_json(flags=zmq.NOBLOCK)
                    
                    # Log result
                    fid = result_data.get('frame_id')
                    worker = result_data.get('worker_id', 'unknown')
                    detections = result_data.get('detections', [])
                    print(f" > [Result] Frame {fid} processed by {worker}: {len(detections)} detections.")
                    
            except zmq.Again:
                pass # No results waiting

            # Display Local Feed (Optional - for debug)
            cv2.imshow('Router - Source Feed', resized_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Rate Limiting (Simulate 30 FPS Input)
            time.sleep(1/30)

    except KeyboardInterrupt:
        print("[Router] Stopping...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        sender.close()
        receiver.close()
        context.term()

if __name__ == "__main__":
    main()
