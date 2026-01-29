# NEXORA MOD-EVAC System Analysis & Debug Report

I have analyzed the entire project structure, including the backend, worker, firmware, and frontend components. Below is a detailed breakdown of how the system works and the critical issues I identified.

## 1. System Components (Distinction)

| Component | Responsibility | Tech Stack |
|-----------|----------------|------------|
| **Nexus Launcher** | Visual orchestrator for legal/system startup | Python (CustomTkinter) |
| **Backend Server** | Core logic, API, WebSocket broadcasting | Python (FastAPI, ZeroMQ, Serial) |
| **Vision Worker** | AI inference (YOLO), camera stream management | Python (OpenCV, Ultralytics) |
| **Control Worker** | Decision engine, GSM/LED alert triggers | Python (Thread-safe logic) |
| **Distributed Worker** | Remote AI inference node (Laptop clustering) | Python (TCP/UDP, YOLO) |
| **Frontend(s)** | Mission control and Public portal | Next.js, Tailwind, React |
| **Firmware** | Hardware sensor and actuator control | C++/Arduino (ESP32) |

---

## 2. Identified Errors & Issues

### 🚨 [CRITICAL] Frontend Build Missing
The backend server expects static assets in `frontend/out` and `frontend_public/out` to serve the dashboards.
- **Status**: directories DO NOT exist.
- **Fix**: Run `npm run build` in both the `frontend` and `frontend_public` directories.

### ⚠️ [CRITICAL] YOLO Label Mismatch (Logic Error)
Both `VisionWorker` and `WorkerApp` use a custom `class_names` list (Fire, Smoke, Flood, etc.) but default to the COCO pre-trained model (`yolov8n.pt`).
- **Result**: A "person" (COCO index 0) will be detected as "Fire" (Hazard index 0). This will trigger false emergency calls for every person seen by the camera.
- **Fix**: You MUST use a custom-trained model (e.g., `hazard_v1.pt`) and update the `model_path` in `nexus_launcher.py` and `worker_app.py`.

### ⚠️ [BUG] Serial Reconnection Failure
The `SensorWorker` (which talks to the ESP32) does not have automatic reconnection logic in its read loop.
- **Result**: If the cable is bumped/unplugged, the system stops receiving sensor data until the entire backend is restarted.
- **Fix**: I recommend adding a `self.reconnect()` call in the `_read_loop` exception handler.

### 🔧 [VERSION] Next.js 16.1.4 Typo
The `frontend/package.json` specifies `"next": "16.1.4"`. Next.js 15 is current; 16 does not exist yet.
- **Result**: `npm install` may fail or install a non-existent package.
- **Fix**: Change version to `^15.0.0` or `latest`.

### 📉 [PERFORMANCE] Database Blocking
`log_alert` is called inside the `StateManager`'s `_alert_lock`. While alerts are infrequent, if the database grows large, this might briefly freeze the state manager.
- **Fix**: Move `log_alert` outside the lock, similar to how `log_detection` is handled.

---

## 3. How to Start the System Correctly
1. **Ensure Hardware**: Plug in the ESP32 (Main Controller) and ESP32-CAM.
2. **Build Frontends**:
   ```bash
   cd frontend && npm install && npm run build
   cd ../frontend_public && npm install && npm run build
   ```
3. **Setup AI**: Place your trained `yolov8n.pt` (the one for hazards) in the `backend/` directory.
4. **Launch Controller**:
   ```bash
   python nexus_launcher.py
   ```
