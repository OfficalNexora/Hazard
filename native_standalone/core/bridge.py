import threading
import time
import json
import zmq
import sys
import os

# Add parent and backend to path to reuse logic
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

try:
    from backend.state_manager import state
except ImportError:
    state = None

class CoreBridge:
    def __init__(self, zmq_port=5556):
        self.zmq_port = zmq_port
        self.running = False
        self.telemetry_data = {}
        self.detections = []
        self.alerts = []
        
        # ZMQ Context
        self.ctx = zmq.Context()
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.setsockopt(zmq.SUBSCRIBE, b"")
        self.sub.setsockopt(zmq.RCVTIMEO, 1000)

    def start(self):
        self.running = True
        threading.Thread(target=self._telemetry_loop, daemon=True).start()

    def _telemetry_loop(self):
        """Directly listen to ZMQ for real-time detections and state."""
        try:
            self.sub.connect(f"tcp://localhost:{self.zmq_port}")
            print(f"[CoreBridge] Subscribed to ZMQ on {self.zmq_port}")
        except Exception as e:
            print(f"[CoreBridge] Failed to connect to ZMQ: {e}")

        while self.running:
            try:
                # In native mode, we can also poll the state manager directly if in-process
                # But ZMQ is more robust for multi-worker setups
                topic, msg = self.sub.recv_multipart()
                data = json.loads(msg)
                
                if "class" in data: # Detection
                    self.detections.append(data)
                    if len(self.detections) > 50: self.detections.pop(0)
                
            except zmq.error.Again:
                continue
            except Exception as e:
                print(f"[CoreBridge] Loop error: {e}")
                time.sleep(1)

    def get_system_state(self):
        """Fetch current state from the backend logic."""
        if state:
            return state.get_full_state()
        return {}

    def stop(self):
        self.running = False
        self.sub.close()
        self.ctx.term()
