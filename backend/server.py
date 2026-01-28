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

@app.get("/")
async def root():
    """Redirect to dashboard"""
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


@app.post("/api/settings")
async def update_settings(config: dict):
    """Update system configuration"""
    if save_config(config):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


@app.get("/api/video_feed")
async def video_feed(id: str = "esp32_cam_0"):
    """MJPEG Video streaming relay for multiple cameras"""
    vision = get_vision_worker()
    if not vision:
        raise HTTPException(status_code=503, detail="Vision worker not available")

    def generate():
        while True:
            frame = vision.last_frames.get(id)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)  # ~20 FPS

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/cameras/register")
async def register_camera(req: CameraRequest):
    """Register a new WiFi camera"""
    vision = get_vision_worker()
    if vision:
        source = f"http://{req.ip}:81/stream"
        vision.add_camera(req.device_id, source)
        state.update_device(req.device_id, "esp32_cam", True, req.ip)
        return {"status": "success", "device_id": req.device_id}
    raise HTTPException(status_code=503, detail="Vision worker not available")


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

if os.path.exists(FRONTEND_PATH):
    # Serve Public Portal at /public
    if os.path.exists(PUBLIC_PORTAL_PATH):
        app.mount("/public", StaticFiles(directory=PUBLIC_PORTAL_PATH, html=True), name="public")
    
    # Serve Admin Dashboard at /
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="admin")


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
