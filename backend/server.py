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
import subprocess
import sys
from typing import List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
from database import init_db, get_history, load_config, save_config, add_adb_script, delete_adb_script, get_adb_scripts, add_camera_db, delete_camera_db, get_cameras_db

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

    # Start Cloudflare Tunnel (leakage) if not running via launcher
    try:
        if not os.environ.get("NEXORA_LAUNCHER"):
            tunnel_script = os.path.join(os.path.dirname(__file__), "..", "start_tunnel.py")
            if os.path.exists(tunnel_script):
                print(f"[Server] Auto-launching Cloudflare tunnel: {tunnel_script}")
                subprocess.Popen([sys.executable, tunnel_script], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
    except Exception as e:
        print(f"[Server] Tunnel auto-launch failed: {e}")

    # Load persisted cameras
    try:
        saved_cameras = get_cameras_db()
        vision = get_vision_worker()
        
        # Load Tapo Manager if needed
        tapo_manager = None
        try:
            from tapo_manager import get_tapo_manager
            tapo_manager = get_tapo_manager()
        except ImportError:
            pass

        print(f"[Server] Loading {len(saved_cameras)} cameras from database...")
        
        for cam in saved_cameras:
            try:
                if cam["type"] == "tapo" and tapo_manager:
                     # Re-add Tapo camera using saved credentials
                     print(f"[Server] Restoring Tapo camera: {cam['device_id']}")
                     tapo_manager.add_camera(
                        cam['device_id'], 
                        cam['ip'], 
                        cam['username'], 
                        cam['password'],
                        cam['stream_quality']
                     )
                     state.update_device(cam['device_id'], "camera", True, cam['ip'])
                     
                elif vision:
                    # Re-add generic RTSP/HTTP camera
                    if cam['ip'].startswith("rtsp://"):
                        source = cam['ip']
                    else:
                        source = f"http://{cam['ip']}:81/stream"
                    
                    print(f"[Server] Restoring Generic camera: {cam['device_id']}")
                    vision.add_camera(cam['device_id'], source, vflip=cam['vflip'])
                    state.update_device(cam['device_id'], "camera", True, cam['ip'])
            except Exception as e:
                print(f"[Server] Failed to restore camera {cam['device_id']}: {e}")
                
    except Exception as e:
        print(f"[Server] Error loading cameras on startup: {e}")
    
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

class AdbScriptRequest(BaseModel):
    label: str
    command: str
    category: str = "general"

class AdbExecuteRequest(BaseModel):
    device_id: str
    script_id: int

class ClassificationRequest(BaseModel):
    device_id: str
    classification: str

class CameraRequest(BaseModel):
    device_id: str
    ip: str
    vflip: bool = False  # Flip vertically (for upside-down cameras)
    hflip: bool = False  # Flip horizontally (mirror)
    username: str = ""   # For ONVIF/RTSP authentication
    password: str = ""   # For ONVIF/RTSP authentication
    port: int = 554      # ONVIF port (default 554)

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

class TelemetryRequest(BaseModel):
    device_id: str
    fire_active: Optional[bool] = False
    rain_active: Optional[bool] = False
    seismic_active: Optional[bool] = False
    fire_raw: Optional[int] = 0
    rain_raw: Optional[int] = 0
    ax: Optional[float] = 0
    ay: Optional[float] = 0
    az: Optional[float] = 0
    gx: Optional[float] = 0
    gy: Optional[float] = 0
    gz: Optional[float] = 0

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

@app.get("/api/discovery/tunnel")
async def get_tunnel_leakage():
    """Discover the current public tunnel URL (leakage)"""
    if os.path.exists("tunnel_url.txt"):
        with open("tunnel_url.txt", "r") as f:
            url = f.read().strip()
            return {"status": "found", "url": url}
    return {"status": "not_discovered", "msg": "No tunnel active or start_tunnel.py hasn't been run."}


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
    
    state.set_alert(AlertState(req.alert), req.reason, source="manual")
    
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


# ============================================================================
# ADB & AUTOMATION ENDPOINTS
# ============================================================================

@app.get("/api/adb/devices")
async def get_adb_devices_api():
    """Scan for connected ADB devices"""
    config = load_config()
    adb_path = config.get("adb_path", "adb")
    try:
        result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')[1:]
        devices = []
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({"id": parts[0], "status": parts[1]})
        return {"devices": devices}
    except Exception as e:
        return {"devices": [], "error": str(e)}

@app.get("/api/adb/scripts")
async def get_adb_scripts_api():
    """Get all saved labeled ADB scripts"""
    return get_adb_scripts()

@app.post("/api/adb/scripts")
async def add_adb_script_api(script: AdbScriptRequest):
    """Add a new labeled ADB script"""
    add_adb_script(script.label, script.command, script.category)
    return {"status": "success"}

@app.delete("/api/adb/scripts/{script_id}")
async def delete_adb_script_api(script_id: int):
    """Delete a saved ADB script"""
    delete_adb_script(script_id)
    return {"status": "success"}

@app.post("/api/adb/execute")
async def execute_adb_script(req: AdbExecuteRequest):
    """Execute a saved script on a device"""
    scripts = get_adb_scripts()
    script = next((s for s in scripts if s["id"] == req.script_id), None)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    config = load_config()
    adb_path = config.get("adb_path", "adb")
    
    try:
        # Run the command via adb shell
        # Using shell=True or list depends on security, 
        # but since this is a local tool for devs, list is safer.
        cmd = [adb_path, "-s", req.device_id, "shell"] + script["command"].split()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {
            "status": "executed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="ADB command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def update_settings(config: dict):
    """Update system configuration"""
    if save_config(config):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


@app.get("/api/video_feed")
async def video_feed(id: str = "esp32_cam_0"):
    """MJPEG Video streaming relay for multiple cameras (VisionWorker + TapoCameraManager)"""
    vision = get_vision_worker()
    
    # Also try to get TapoCameraManager
    tapo_manager = None
    try:
        from tapo_manager import get_tapo_manager
        tapo_manager = get_tapo_manager()
    except ImportError:
        pass

    def generate():
        while True:
            frame = None
            
            # First check VisionWorker
            if vision:
                frame = vision.last_frames.get(id)
            
            # If not found, check TapoCameraManager
            if not frame and tapo_manager:
                frame = tapo_manager.get_frame(id)
            
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)  # ~20 FPS

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/cameras/register")
async def register_camera(req: CameraRequest):
    """Register a new WiFi camera or RTSP stream"""
    vision = get_vision_worker()
    if vision:
        # Check if this is an RTSP URL or IP camera
        if req.ip.startswith("rtsp://"):
            source = req.ip  # Already a full RTSP URL
        else:
            source = f"http://{req.ip}:81/stream"  # ESP32-CAM default
        
        vision.add_camera(req.device_id, source, vflip=req.vflip, hflip=req.hflip)
        
        # Save to DB
        add_camera_db(
            device_id=req.device_id,
            name=req.device_id,
            type="generic",
            ip=req.ip,
            vflip=req.vflip
        )
        
        state.update_device(req.device_id, "camera", True, req.ip)
        return {"status": "success", "device_id": req.device_id, "source": source}
    raise HTTPException(status_code=503, detail="Vision worker not available")


@app.post("/api/telemetry")
async def receive_telemetry(req: TelemetryRequest):
    """Receive real-time sensor telemetry from WiFi-based ESP32 controllers (via Tunneling)"""
    state.update_sensor(
        fire=req.fire_active,
        raining=float(req.rain_raw), 
        earthquake={
            "x": req.gx,
            "y": req.gy,
            "z": req.gz
        },
        accel={
            "x": req.ax,
            "y": req.ay,
            "z": req.az
        }
    )
    # Update device status so it shows as connected on the dashboard
    state.update_device(req.device_id, "esp32_main", True, "Remote/Cloud")
    return {"status": "success", "device_id": req.device_id}


@app.get("/api/cameras/debug")
async def debug_cameras():
    """Debug endpoint to view active camera streams"""
    vision = get_vision_worker()
    if vision:
        streams = {}
        for device_id, stream_info in vision.streams.items():
            streams[device_id] = {
                "source": stream_info.get("source"),
                "active": stream_info.get("active"),
                "has_frame": device_id in vision.last_frames
            }
        return {"streams": streams, "total": len(streams)}
    return {"streams": {}, "error": "Vision worker not available"}


class TapoRegisterRequest(BaseModel):
    """Request model for Tapo camera registration"""
    device_id: str
    ip: str
    username: str
    password: str
    stream_quality: str = "stream1"  # stream1 (HD) or stream2 (SD)
    vflip: bool = False


class PTZRequest(BaseModel):
    """Request model for PTZ control"""
    device_id: str
    pan: float = 0.0  # -1.0 to 1.0
    tilt: float = 0.0 # -1.0 to 1.0


@app.post("/api/cameras/ptz/move")
async def move_ptz(req: PTZRequest):
    """Control camera Pan/Tilt via ONVIF (Incremental)"""
    try:
        from tapo_manager import get_tapo_manager
        manager = get_tapo_manager()
        
        # Use incremental step movement
        # Pan/Tilt values in req are now treated as steps (e.g., 0.1, -0.1)
        # Frontend should send small values
        success, msg, status = manager.move_motor_step(req.device_id, req.pan, req.tilt)
        
        if success:
            return {
                "status": "success", 
                "message": msg,
                "new_position": status  # {'pan': x, 'tilt': y, 'zoom': z}
            }
        else:
            raise HTTPException(status_code=400, detail=msg)
            
    except ImportError:
         raise HTTPException(status_code=503, detail="Tapo manager not available")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras/register_tapo")
async def register_tapo_camera(req: TapoRegisterRequest):
    """
    Register a Tapo camera with credential validation.
    Uses official pytapo library to verify connection before streaming.
    Returns detailed error messages for incorrect credentials.
    """
    try:
        from tapo_manager import get_tapo_manager
        
        manager = get_tapo_manager()
        success, message = manager.add_camera(
            camera_id=req.device_id,
            ip=req.ip,
            username=req.username,
            password=req.password,
            stream_quality=req.stream_quality
        )
        
        if success:
            # Save to DB
            add_camera_db(
                device_id=req.device_id,
                name=req.device_id,
                type="tapo",
                ip=req.ip,
                username=req.username,
                password=req.password,
                stream_quality=req.stream_quality,
                vflip=req.vflip
            )
            
            # Also register with state manager for device list
            state.update_device(req.device_id, "camera", True, req.ip)
            return {"status": "success", "message": message, "device_id": req.device_id}
        else:
            # Return validation error with details
            raise HTTPException(status_code=400, detail=message)
            
    except ImportError:
        raise HTTPException(status_code=500, detail="pytapo library not installed. Run: pip install pytapo")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.delete("/api/cameras/{device_id}")
async def delete_camera(device_id: str):
    """Delete a camera from the system and database"""
    
    # 1. Remove from database
    delete_camera_db(device_id)
    
    # 2. Remove from Tapo Manager
    try:
        from tapo_manager import get_tapo_manager
        get_tapo_manager().remove_camera(device_id)
    except:
        pass
        
    # 3. Remove from Vision Worker (Generic/RTSP)
    vision = get_vision_worker()
    if vision and device_id in vision.streams:
        del vision.streams[device_id]
        if device_id in vision.last_frames:
            del vision.last_frames[device_id]
            
    # 4. Remove from State Manager
    state.remove_device(device_id)
    
    return {"status": "success", "message": f"Camera {device_id} deleted"}


@app.get("/api/cameras/discover")
async def discover_cameras():
    """
    Scan local network for ESP32-CAM devices (Port 81).
    This is a quick aggressive scan of the local subnet.
    """
    import socket
    import asyncio
    
    # 1. Get discovered cameras from UDP listener service
    found_cameras = discovery.get_discovered_cameras()
    
    # 2. Add local scan as backup (optional, or remove if confident in UDP)
    # For now, let's keep it simple and just use the UDP results
    # which is much faster and more accurate for our ESP32-CAMs
    
    return {"cameras": found_cameras, "subnet": "auto"}
            
    print(f"[Discovery] Found {len(found_cameras)} cameras")
    return {"cameras": found_cameras, "subnet": f"{subnet_base}.x"}


@app.get("/api/cameras/discover_rtsp")
async def discover_rtsp():
    """
    Scan local network for RTSP/CCTV devices on common ports (554, 8554, 80).
    Returns detected devices with their open ports.
    """
    import socket
    import asyncio
    
    # Get local subnet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    if local_ip == "127.0.0.1":
        return {"cameras": [], "subnet": "unknown"}

    subnet_base = ".".join(local_ip.split(".")[:3])
    print(f"[RTSP Discovery] Scanning subnet: {subnet_base}.x for CCTV/RTSP devices")

    found_cameras = []
    rtsp_ports = [554, 8554, 80, 8080]  # Common RTSP and ONVIF ports

    async def check_ip_port(ip, port):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), 
                timeout=0.3
            )
            writer.close()
            await writer.wait_closed()
            return (ip, port)
        except:
            return None

    # Scan all IPs on all RTSP ports
    tasks = []
    for i in range(2, 255):
        ip = f"{subnet_base}.{i}"
        if ip != local_ip:
            for port in rtsp_ports:
                tasks.append(check_ip_port(ip, port))
    
    results = await asyncio.gather(*tasks)
    
    # Group by IP
    ip_ports = {}
    for result in results:
        if result:
            ip, port = result
            if ip not in ip_ports:
                ip_ports[ip] = []
            ip_ports[ip].append(port)
    
    # Build response
    for ip, ports in ip_ports.items():
        camera_type = "CCTV/IP Camera"
        if 554 in ports:
            camera_type = "RTSP Camera"
        elif 80 in ports or 8080 in ports:
            camera_type = "Network Camera"
        
        found_cameras.append({
            "ip": ip,
            "ports": ports,
            "type": camera_type,
            "suggested_port": 554 if 554 in ports else ports[0]
        })
            
    print(f"[RTSP Discovery] Found {len(found_cameras)} potential CCTV devices")
    return {"cameras": found_cameras, "subnet": f"{subnet_base}.x"}


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


@app.get("/api/test/trigger_hardware")
async def test_hardware_trigger(alert_level: int = 4):
    """
    Simulate a hardware trigger event.
    Iterates through all configured GSM recipients and broadcasts an alert.
    """
    print(f"[TEST] Triggering Alert Level {alert_level} from Frontend")
    
    # 1. Provide visual feedback via LEDs (if control worker is active)
    control = get_control_worker()
    if control:
        try:
            control._send_led_command(AlertState(alert_level))
        except: pass

    # 2. Get all recipients
    contacts = state.get_gsm_contacts()
    sms_recipients = contacts.get("sms", [])
    
    # 3. Broadcast SMS
    from adb_worker import adb_worker
    count = 0
    for contact in sms_recipients:
        msg = contact.get("message", "WARNING: Simulated Hazard Alert! Please evacuate immediately.")
        print(f"[TEST] Broadcasting to {contact['number']}")
        # Use asyncio.to_thread for synchronous adb_worker calls to prevent blocking the event loop
        asyncio.create_task(asyncio.to_thread(adb_worker.send_sms, contact["number"], msg))
        count += 1
        
    return {"status": "triggered", "recipients_notified": count}


@app.get("/api/weather")
async def get_weather(lat: float = 14.5995, lon: float = 120.9842):
    """
    Get weather forecast and generate hazard warnings.
    Defaults to Manila coordinates (since user seems to be in PH/UTC+8).
    """
    import httpx
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "is_day", "rain", "showers", "wind_speed_10m"],
        "hourly": ["temperature_2m", "rain", "wind_speed_10m"],
        "forecast_days": 1
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5.0)
            data = response.json()
            
        if "error" in data:
            raise Exception(data["reason"])
            
        # Analysis for Warnings
        warnings = []
        
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        
        # 1. Heat Warning (>35C)
        max_temp = max(hourly.get("temperature_2m", [0]))
        if max_temp > 35:
            warnings.append({
                "type": "heat",
                "level": "warning" if max_temp < 40 else "danger",
                "message": f"Extreme heat expected! Peak: {max_temp}°C",
                "icon": "thermometer"
            })
            
        # 2. Rain Warning (>5mm/hr is heavy)
        max_rain = max(hourly.get("rain", [0]))
        if max_rain > 5:
            warnings.append({
                "type": "rain",
                "level": "warning" if max_rain < 15 else "danger",
                "message": f"Heavy rain detected! Peak: {max_rain} mm/h",
                "icon": "cloud-rain"
            })
            
        # 3. Wind Warning (>40km/h)
        max_wind = max(hourly.get("wind_speed_10m", [0]))
        if max_wind > 40:
            warnings.append({
                "type": "wind",
                "level": "warning" if max_wind < 80 else "danger",
                "message": f"Strong winds expected! Peak: {max_wind} km/h",
                "icon": "wind"
            })
            
        return {
            "current": current,
            "warnings": warnings,
            "location": {"lat": lat, "lon": lon}
        }
        
    except Exception as e:
        print(f"[Weather] Error: {e}")
        raise HTTPException(status_code=503, detail="Weather service unavailable")


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
# PTZ CAMERA CONTROL ENDPOINTS
# ============================================================================

class PTZRequest(BaseModel):
    camera_id: str
    direction: str  # 'up', 'down', 'left', 'right', 'zoom_in', 'zoom_out', 'stop'
    speed: float = 0.5


class PTZConnectRequest(BaseModel):
    camera_id: str
    ip: str
    port: int = 80
    username: str
    password: str


@app.post("/api/cameras/ptz/connect")
async def ptz_connect(req: PTZConnectRequest):
    """Connect to ONVIF camera for PTZ control"""
    from ptz_manager import get_ptz_manager
    ptz = get_ptz_manager()
    
    if ptz.connect(req.camera_id, req.ip, req.port, req.username, req.password):
        return {"status": "connected", "camera_id": req.camera_id}
    raise HTTPException(status_code=503, detail="Failed to connect to ONVIF camera")


@app.post("/api/cameras/ptz/move")
async def ptz_move(req: PTZRequest):
    """Control PTZ camera movement"""
    from ptz_manager import get_ptz_manager
    ptz = get_ptz_manager()
    
    if req.direction == "stop":
        if ptz.stop(req.camera_id):
            return {"status": "stopped"}
    else:
        if ptz.move(req.camera_id, req.direction, req.speed):
            return {"status": "moving", "direction": req.direction}
    
    raise HTTPException(status_code=400, detail="PTZ command failed")


# ============================================================================
# COMMUNICATIONS & GSM ENDPOINTS
# ============================================================================

class SmsRequest(BaseModel):
    number: str
    message: str

class CallRequest(BaseModel):
    number: str

@app.post("/api/communication/sms")
async def send_sms_api(req: SmsRequest):
    """Send SMS via ADB or GSM hardware"""
    try:
        from adb_worker import adb_worker
        # Run in thread since adb_worker.send_sms is sync and blocks for several seconds per message
        success = await asyncio.to_thread(adb_worker.send_sms, req.number, req.message)
        
        if success:
            return {"status": "success", "method": "adb"}
            
        return {"status": "error", "message": "Failed to send SMS via ADB"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/communication/call")
async def initiate_call_api(req: CallRequest):
    """Initiate Call via ADB"""
    try:
        from adb_worker import adb_worker
        if adb_worker.make_call(req.number):
            return {"status": "success"}
        return {"status": "error", "message": "Failed to initiate call"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        reload=True,
        log_level="info"
    )
