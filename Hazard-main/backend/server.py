"""
MOD-EVAC-MS - FastAPI Server
I built this backend to serve as the high-performance orchestration layer. 
It uses WebSockets for real-time telemetry to ensure the dashboard reflects the state of the world with <50ms latency.

Features:
- /api/status - System status
- /api/devices - Device status
- /api/alerts - Alert history
- /api/control - Manual control endpoints
- /ws/telemetry - WebSocket for real-time updates
"""

import asyncio
import json
import os
import threading
import time
from typing import List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import socket
from database import init_db, get_history, load_config, save_config

from state_manager import state, AlertState
from sensor_worker import init_sensor_worker, get_sensor_worker
from vision_worker import init_vision_worker, get_vision_worker
from control_worker import init_control_worker, get_control_worker
from worker_manager import discovery, worker_manager


# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """
    I implemented this Manager to handle the lifecycle of multiple concurrent WebSocket clients.
    The primary goal here is to ensure atomic broadcasts using thread locks to prevent race conditions during high-throughput events.
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = threading.Lock()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self.active_connections.add(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        with self._lock:
            self.active_connections.discard(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """
        I use this broadcast method to push state changes to all connected clients immediately.
        I added error handling here to silently prune stale connections rather than crashing the loop.
        """
        if not self.active_connections:
            return
        
        json_msg = json.dumps(message)
        disconnected = set()
        
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json_msg)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        with self._lock:
            self.active_connections -= disconnected


manager = ConnectionManager()


# ============================================================================
# STATE EVENT BROADCASTER
# ============================================================================

async def broadcast_state_events():
    """
    I designed this background task to decouple state updates from API responses.
    This runs at roughly 20Hz (50ms sleep) to balance responsiveness with CPU usage.
    """
    while True:
        try:
            # Get event from queue (non-blocking)
            try:
                event = state.event_queue.get_nowait()
                await manager.broadcast(event)
            except:
                pass
            
            await asyncio.sleep(0.05)  # 20Hz check rate
        except Exception as e:
            print(f"[Broadcast] Error: {e}")
            await asyncio.sleep(1)


# ============================================================================
# LIFESPAN HANDLER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup workers on startup/shutdown"""
    print("[Server] Initializing database...")
    init_db()
    
    print("[Server] Starting workers...")
    
    # Initialize workers (they auto-detect ports or run without hardware)
    sensor_worker = None
    vision_worker = None
    control_worker = None
    
    try:
        sensor_worker = init_sensor_worker()
    except Exception as e:
        print(f"[Server] Sensor worker init failed: {e}")
    
    try:
        # Vision worker can run with video source for testing
        vision_worker = init_vision_worker()
    except Exception as e:
        print(f"[Server] Vision worker init failed: {e}")
    
    try:
        control_worker = init_control_worker(
            sensor_worker=sensor_worker,
            use_internet=True
        )
    except Exception as e:
        print(f"[Server] Control worker init failed: {e}")
    
    # Start broadcast task
    broadcast_task = asyncio.create_task(broadcast_state_events())
    
    # Start distributed worker services
    discovery.start()
    worker_manager.start()
    
    # Load persistence
    from database import get_gsm_contacts
    contacts = get_gsm_contacts()
    for mode in ["sms", "call"]:
        for contact in contacts.get(mode, []):
            state.add_gsm_contact(mode, contact["number"], contact["name"], contact["message"], contact.get("category", "general"))
    
    print("[Server] Workers started")
    
    yield
    
    # Cleanup
    print("[Server] Stopping workers...")
    broadcast_task.cancel()
    
    if sensor_worker:
        sensor_worker.stop()
    if vision_worker:
        vision_worker.stop()
    if control_worker:
        control_worker.stop()
    
    discovery.stop()
    worker_manager.stop()
    
    print("[Server] Shutdown complete")


# ============================================================================
# MODELS
# ============================================================================

class GsmContact(BaseModel):
    mode: str  # 'sms' or 'call'
    number: str
    name: str = ""
    message: str = ""
    category: str = "general"

class ClassificationRequest(BaseModel):
    device_id: str
    classification: str

class CameraRequest(BaseModel):
    device_id: str
    ip: str
    vflip: bool = False  # Flip vertically (for upside-down cameras)
    hflip: bool = False  # Flip horizontally (mirror)

class AlertRequest(BaseModel):
    alert: int
    reason: str = "Manual"

class EvacuateRequest(BaseModel):
    exit_zone: int = 3

class VerifyCodeRequest(BaseModel):
    code: str

class ManualTriggerRequest(BaseModel):
    action_type: str
    details: str = ""

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="MOD-EVAC-MS Backend",
    description="Competition-grade hazard detection and evacuation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api")
async def api_root():
    """API Info"""
    return {"message": "MOD-EVAC-MS Backend API", "docs": "/docs"}


@app.get("/api/status")
async def get_status():
    """Get full system status"""
    return state.get_full_state()


@app.get("/api/sensor")
async def get_sensor():
    """Get current sensor readings"""
    return state.get_sensor()


@app.get("/api/devices")
async def get_devices():
    """Get connected device status"""
    return {"devices": state.get_devices()}


@app.get("/api/workers")
async def get_workers():
    """Get active distributed worker laptops"""
    workers = []
    for wid, info in worker_manager.workers.items():
        workers.append({
            "worker_id": wid,
            "name": info["name"],
            "model": info["model"],
            "last_seen": info["last_seen"],
            "stats": info["stats"]
        })
    return {"workers": workers}


@app.get("/api/detections")
async def get_detections(limit: int = 20):
    """Get recent AI detections"""
    return {"detections": state.get_detections(limit)}


@app.get("/api/alert")
async def get_alert():
    """Get current alert status"""
    return state.get_alert()


@app.get("/api/alerts/history")
async def get_alert_history(limit: int = 20):
    """Get alert history"""
    return {"history": state.get_alert_history(limit)}


@app.post("/api/alert")
async def set_alert(req: AlertRequest):
    """Manually set alert state"""
    if req.alert < 0 or req.alert > 4:
        raise HTTPException(status_code=400, detail="Invalid alert value (0-4)")
    
    state.set_alert(AlertState(req.alert), req.reason)
    
    # Forward to control worker
    control = get_control_worker()
    if control:
        control._send_led_command(AlertState(req.alert))
    
    return state.get_alert()


@app.post("/api/evacuate")
async def trigger_evacuation(req: EvacuateRequest):
    """Trigger evacuation mode"""
    control = get_control_worker()
    if control:
        control.set_evacuate_mode(req.exit_zone)
        return {"status": "evacuation_triggered", "exit_zone": req.exit_zone}
    raise HTTPException(status_code=503, detail="Control worker not available")


@app.post("/api/safe")
async def set_safe_mode():
    """Reset to safe mode"""
    control = get_control_worker()
    if control:
        control.set_safe_mode()
        return {"status": "safe_mode_set"}
    raise HTTPException(status_code=503, detail="Control worker not available")


@app.get("/api/access_code")
async def get_access_code():
    """Get pairing code for Public Portal"""
    return {"code": state.get_access_code()}


@app.post("/api/verify_code")
async def verify_code(req: VerifyCodeRequest):
    """Verify pairing code from Public Portal"""
    if state.verify_access_code(req.code):
        return {"status": "success"}
    raise HTTPException(status_code=401, detail="Invalid access code")


@app.get("/api/gsm/contacts")
async def get_gsm_contacts():
    """Get all emergency contacts"""
    from database import get_gsm_contacts
    return get_gsm_contacts()


@app.post("/api/gsm/contacts")
async def add_gsm_contact(contact: GsmContact):
    """Add a new emergecy contact"""
    from database import add_gsm_number
    add_gsm_number(contact.mode, contact.number, contact.name, contact.message, contact.category)
    state.add_gsm_contact(contact.mode, contact.number, contact.name, contact.message, contact.category)
    return {"status": "success"}


@app.delete("/api/gsm/contacts/{number}")
async def delete_gsm_contact(number: str):
    """Remove an emergency contact"""
    from database import delete_gsm_number
    delete_gsm_number(number)
    state.delete_gsm_contact(number)
    return {"status": "success"}


@app.post("/api/manual/trigger")
async def trigger_manual_action(req: ManualTriggerRequest):
    """Queue a manual intervention (Call Fire, SMS Alert, etc)"""
    state.trigger_manual_action(req.action_type, req.details)
    return {"status": "action_queued", "type": req.action_type}


@app.post("/api/cluster/classify")
async def classify_worker(req: ClassificationRequest):
    """Assign a role to a cluster worker (GPU, Tracker, Logic)"""
    from database import set_worker_classification
    set_worker_classification(req.device_id, req.classification)
    return {"status": "success"}


@app.get("/api/history")
async def get_system_history(limit: int = 50):
    """Get historical records from SQLite"""
    return {"history": get_history(limit)}


@app.get("/api/settings")
async def get_settings():
    """Get system configuration"""
    return load_config()


@app.get("/api/network/info")
async def get_network_info():
    """Get current local IP for camera provisioning"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"local_ip": ip, "port": 8000}
    except Exception:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return {"local_ip": ip, "port": 8000}


@app.post("/api/settings")
async def update_settings(config: dict):
    """Update system configuration"""
    if save_config(config):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


@app.get("/api/video_feed")
async def video_feed(id: str = "esp32_cam_0"):
    """MJPEG Video streaming relay with placeholder frames"""
    vision = get_vision_worker()
    if not vision:
        raise HTTPException(status_code=503, detail="Vision worker not available")

    # Fuzzy ID matching
    target_id = id
    if target_id not in vision.last_frames:
        for sid in list(vision.last_frames.keys()):
            if target_id.lower() in sid.lower() or sid.lower() in target_id.lower():
                target_id = sid
                break

    def generate():
        import cv2
        import numpy as np
        
        print(f"[Stream] Relay active for {target_id}")
        while True:
            frame = vision.last_frames.get(target_id)
            if not frame:
                # Black placeholder with text
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                msg = f"WAITING FOR {target_id.upper()}..."
                cv2.putText(img, msg, (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                _, buffer = cv2.imencode('.jpg', img)
                frame = buffer.tobytes()
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1.0)
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/cameras/register")
async def register_camera(req: CameraRequest):
    """Register a new WiFi camera and cleanup duplicates"""
    vision = get_vision_worker()
    if not vision:
        raise HTTPException(status_code=503, detail="Vision worker not available")

    # CLEANUP: If this IP is already registered under 'nexora' but now reports a MAC ID,
    # or vice versa, we want to unify them in the UI.
    devices = state.get_devices()
    for d in devices:
        if d.get("port") == req.ip and d.get("device_id") != req.device_id:
            # Completely remove old ghost devices from the same IP
            state.remove_device(d["device_id"])

    if req.ip and req.ip != "unknown":
        source = f"http://{req.ip}:81/stream"
        # We use the provided ID for the vision layer to maintain consistency
        vision.add_camera(req.device_id, source, vflip=req.vflip, hflip=req.hflip)
        state.update_device(req.device_id, "esp32_cam", True, req.ip, status="CONNECTING")
    else:
        state.update_device(req.device_id, "esp32_cam", False, "pending", status="WAITING FOR IP")
        
    return {"status": "success", "device_id": req.device_id}


# ============================================================================
# 3D DIGITAL TWIN API ENDPOINTS
# ============================================================================

@app.get("/api/diorama/model")
async def get_diorama_model():
    """Get the 3D diorama model configuration."""
    try:
        from diorama_model import get_model
        model = get_model()
        return model.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diorama/model")
async def update_diorama_model(config: dict):
    """Update the diorama model configuration."""
    try:
        from diorama_model import load_model_from_json
        import json
        import tempfile
        
        # Write to temp file and reload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_path = f.name
        
        load_model_from_json(temp_path)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events")
async def get_events(
    start: Optional[float] = None,
    end: Optional[float] = None,
    event_type: Optional[str] = None,
    limit: int = 100
):
    """Get hazard events by time range."""
    try:
        from event_store import get_event_store
        store = get_event_store()
        events = store.get_events(start, end, event_type, limit)
        return {"events": [e.to_dict() for e in events]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/active")
async def get_active_hazards(window: float = 30.0):
    """Get currently active hazards (detected within time window)."""
    try:
        from event_store import get_event_store
        store = get_event_store()
        events = store.get_active_hazards(window)
        return {"hazards": [e.to_dict() for e in events]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/timeline")
async def get_events_timeline(
    start: float,
    end: float,
    bucket_seconds: float = 60.0
):
    """Get event summary grouped by time buckets for timeline visualization."""
    try:
        from event_store import get_event_store
        store = get_event_store()
        timeline = store.get_timeline_summary(start, end, bucket_seconds)
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pathfinding/route")
async def get_evacuation_route(
    start_zone: int,
    hazard_type: str = "fire"
):
    """Calculate evacuation route from a zone avoiding hazards."""
    try:
        from pathfinder import get_pathfinder
        from event_store import get_event_store
        
        # Get active hazard zones
        store = get_event_store()
        active = store.get_active_hazards(30.0)
        hazard_zones = list(set(e.zone_id for e in active if e.zone_id is not None))
        
        # Calculate path
        pathfinder = get_pathfinder()
        result = pathfinder.find_path_to_exit(start_zone, hazard_zones, hazard_type)
        
        return {
            "path": result.path,
            "cost": result.cost,
            "destination": result.destination,
            "valid": result.valid,
            "hazard_zones": hazard_zones
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pathfinding/led_commands")
async def get_led_commands(hazard_type: str = "fire"):
    """Get LED commands for current hazard state."""
    try:
        from pathfinder import get_pathfinder
        from event_store import get_event_store
        
        # Get active hazard zones
        store = get_event_store()
        active = store.get_active_hazards(30.0)
        hazard_zones = list(set(e.zone_id for e in active if e.zone_id is not None))
        
        # Generate LED commands
        pathfinder = get_pathfinder()
        commands = pathfinder.get_led_commands(hazard_zones, hazard_type)
        
        return commands
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/calibrate")
async def calibrate_camera(points: List[dict]):
    """
    Set camera calibration points.
    
    Each point: {"pixel_x": int, "pixel_y": int, "world_x": float, "world_y": float, "world_z": float}
    """
    try:
        from camera_mapper import get_mapper
        
        calibration = [
            (p["pixel_x"], p["pixel_y"], p["world_x"], p["world_y"], p["world_z"])
            for p in points
        ]
        
        mapper = get_mapper()
        mapper.calibrate(calibration)
        
        return {"status": "success", "points": len(calibration)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry"""
    await manager.connect(websocket)
    
    # Send initial state
    try:
        await websocket.send_json({
            "type": "init",
            "data": state.get_full_state()
        })
    except Exception:
        manager.disconnect(websocket)
        return
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30
                )
                
                # Handle client commands
                try:
                    cmd = json.loads(data)
                    if cmd.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "ts": time.time()})
                except:
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive", "ts": time.time()})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        manager.disconnect(websocket)


# Static Frontend Serving (Local-First Hosting)
# Note: Requires 'npm run build' which creates the 'out' directory
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
PUBLIC_PORTAL_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend_public", "out")

print(f"[SERVER] Front Path: {os.path.abspath(FRONTEND_PATH)} | Exists: {os.path.exists(FRONTEND_PATH)}")
print(f"[SERVER] Public Path: {os.path.abspath(PUBLIC_PORTAL_PATH)} | Exists: {os.path.exists(PUBLIC_PORTAL_PATH)}")

# Serve Public Portal at /public (Longer prefix first)
if os.path.exists(PUBLIC_PORTAL_PATH):
    print(f"[SERVER] Mounting Public Portal from: {PUBLIC_PORTAL_PATH}")
    app.mount("/public", StaticFiles(directory=PUBLIC_PORTAL_PATH, html=True), name="public")
else:
    print(f"[SERVER] WARNING: Public Portal directory missing: {PUBLIC_PORTAL_PATH}")

# Serve Custom Website at /website
WEBSITE_PATH = os.path.join(os.path.dirname(__file__), "..", "WEBSITE")
if os.path.exists(WEBSITE_PATH):
    print(f"[SERVER] Mounting Custom Website from: {WEBSITE_PATH}")
    app.mount("/website", StaticFiles(directory=WEBSITE_PATH, html=True), name="website")

# Serve Admin Dashboard at / (Catch-all)
if os.path.exists(FRONTEND_PATH):
    print(f"[SERVER] Mounting Admin Dashboard from: {FRONTEND_PATH}")
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="admin")
else:
    print(f"[SERVER] WARNING: Admin Dashboard directory missing: {FRONTEND_PATH}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
