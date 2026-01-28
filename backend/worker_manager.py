"""
MOD-EVAC-MS - Worker Manager & Discovery Service
I separated this component to handle the dynamic registration of distributed worker nodes.
It uses UDP broadcasting for discovery and TCP for reliable task distribution.
"""

import socket
import threading
import time
import json
import struct
import base64
from typing import Dict, List, Optional
from state_manager import state, DeviceStatus

# =============================================================================
# CONFIGURATION
# =============================================================================
DISCOVERY_PORT = 8002
REGISTRATION_PORT = 8001
BROADCAST_INTERVAL = 2  # seconds
HEARTBEAT_TIMEOUT = 15  # seconds

# =============================================================================
# DISCOVERY SERVICE (UDP BROADCAST)
# =============================================================================
class DiscoveryService:
    """
    I implemented this UDP broadcast service so worker laptops can find the server without manual IP configuration.
    This zero-config approach is crucial for rapid deployment in emergency scenarios.
    """
    def __init__(self, port=DISCOVERY_PORT):
        self.port = port
        self.running = False
        self.thread = None
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        server_ip = self.get_local_ip()
        message = json.dumps({
            "type": "server_announce",
            "ip": server_ip,
            "port": REGISTRATION_PORT,
            "system": "MOD-EVAC-MS"
        }).encode()
        
        print(f"[Discovery] Broadcasting server at {server_ip} on port {self.port}")
        
        while self.running:
            try:
                sock.sendto(message, ('<broadcast>', self.port))
            except Exception as e:
                print(f"[Discovery] Broadcast error: {e}")
            time.sleep(BROADCAST_INTERVAL)
        sock.close()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

# =============================================================================
# WORKER MANAGER (TCP)
# =============================================================================
class WorkerManager:
    """
    I designed this TCP server to manage persistent connections with worker nodes.
    I chose TCP over UDP here because reliable delivery of inference results and heartbeats is strictly required.
    """
    def __init__(self, port=REGISTRATION_PORT):
        self.port = port
        self.workers: Dict[str, dict] = {}  # worker_id -> info
        self.pending_tasks: Dict[int, dict] = {} # frame_id -> {"event": Event, "result": None}
        self.current_worker_index = 0
        self.running = False
        self.thread = None
        
    def _handle_worker(self, conn, addr):
        worker_id = None
        print(f"[WorkerManager] New connection from {addr}")
        
        try:
            while self.running:
                # Receive message
                len_data = conn.recv(4)
                if not len_data: break
                length = struct.unpack('>I', len_data)[0]
                
                data = b''
                while len(data) < length:
                    chunk = conn.recv(length - len(data))
                    if not chunk: break
                    data += chunk
                
                if not data: break
                msg = json.loads(data.decode("utf-8", errors="replace"))
                
                # Handle message types
                msg_type = msg.get('type')
                
                if msg_type == 'register':
                    worker_id = msg.get('worker_id')
                    specialty = msg.get('specialty', 'Generalist')
                    role = msg.get('role', 'sub-worker')
                    
                    print(f"[WorkerManager] Registering {role}: {worker_id} (Specialty: {specialty})")
                    self.workers[worker_id] = {
                        "conn": conn,
                        "addr": addr,
                        "name": msg.get('name'),
                        "model": msg.get('model'),
                        "specialty": specialty,
                        "role": role,
                        "last_seen": time.time(),
                        "stats": {}
                    }
                    # Update global state
                    state.update_device(worker_id, f"worker_{specialty.lower().replace(' ', '_')}", True, f"{addr[0]}:{addr[1]}")
                    
                    # Send ack
                    ack = json.dumps({"type": "registered", "worker_id": worker_id}).encode()
                    conn.sendall(struct.pack('>I', len(ack)) + ack)
                    
                elif msg_type == 'heartbeat':
                    if worker_id in self.workers:
                        self.workers[worker_id]["last_seen"] = time.time()
                        self.workers[worker_id]["stats"] = msg.get('stats', {})
                        
                elif msg_type == 'inference_result':
                    frame_id = msg.get('frame_id', 0)
                    
                    # 1. Check if this was a synchronous task waiting for result
                    if frame_id in self.pending_tasks:
                        task = self.pending_tasks[frame_id]
                        task["result"] = msg.get('detections', [])
                        task["event"].set() # Wake up the waiting thread
                    
                    # 2. Process detections (Global State Update)
                    detections = msg.get('detections', [])
                    for det in detections:
                        state.add_detection(
                            det['class'], 
                            det['confidence'], 
                            det['bbox'], 
                            frame_id
                        )
                    print(f"[WorkerManager] Received {len(detections)} detections from {worker_id}")
                    
        except Exception as e:
            print(f"[WorkerManager] Error handling worker {worker_id}: {e}")
        finally:
            if worker_id in self.workers:
                print(f"[WorkerManager] Worker disconnected: {worker_id}")
                state.update_device(worker_id, "worker_laptop", False)
                del self.workers[worker_id]
            conn.close()

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.port))
        sock.listen(5)
        
        print(f"[WorkerManager] Listening for workers on port {self.port}")
        
        while self.running:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_worker, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[WorkerManager] Accept error: {e}")
        sock.close()

    def _cleanup_loop(self):
        """Periodically check for timed-out workers."""
        while self.running:
            now = time.time()
            to_remove = []
            for wid, info in self.workers.items():
                if now - info["last_seen"] > HEARTBEAT_TIMEOUT:
                    to_remove.append(wid)
            
            for wid in to_remove:
                print(f"[WorkerManager] Worker heartbeat timeout: {wid}")
                state.update_device(wid, "worker_laptop", False)
                try: self.workers[wid]["conn"].close()
                except: pass
                del self.workers[wid]
                
            time.sleep(5)

    def distribute_task_sync(self, frame_data_base64, frame_id, required_specialty: Optional[str] = None, timeout=0.2):
        """
        Sends task to a worker and WAITS for the result.
        If required_specialty is provided, it only routes to workers with that specialty.
        Returns detections list if successful, None if timeout/failure.
        """
        if not self.workers:
            return None

        # 1. Filter Workers by Capability
        eligible_workers = []
        for wid, info in self.workers.items():
            if required_specialty is None or info.get("specialty") == required_specialty or info.get("specialty") == "Generalist":
                eligible_workers.append(wid)

        if not eligible_workers:
            return None
        
        # 2. Load Balance (Round-Robin among eligible)
        self.current_worker_index = (self.current_worker_index + 1) % len(eligible_workers)
        target_wid = eligible_workers[self.current_worker_index]
        target_info = self.workers[target_wid]

        # 3. Setup Wait Event
        event = threading.Event()
        self.pending_tasks[frame_id] = {"event": event, "result": None}

        # 4. Send Task
        task = {
            "type": "inference_task",
            "frame_id": frame_id,
            "frame_data": frame_data_base64
        }
        
        try:
            data = json.dumps(task).encode()
            target_info["conn"].sendall(struct.pack('>I', len(data)) + data)
        except Exception as e:
            print(f"[WorkerManager] Send failed to {target_wid}: {e}")
            del self.pending_tasks[frame_id]
            return None

        # 5. Wait for Result (High-Performance Blocking)
        flag = event.wait(timeout)
        
        # 6. Retrieve Result
        result = None
        if flag:
            result = self.pending_tasks[frame_id]["result"]
        
        # Cleanup
        if frame_id in self.pending_tasks:
            del self.pending_tasks[frame_id]
            
        return result

    def distribute_task(self, frame_data_base64, frame_id):
        # Legacy fire-and-forget method (kept for compatibility)
        return self.distribute_task_sync(frame_data_base64, frame_id, timeout=0) is not None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def stop(self):
        self.running = False


# Global instances
discovery = DiscoveryService()
worker_manager = WorkerManager()
