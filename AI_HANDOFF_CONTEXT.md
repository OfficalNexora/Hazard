# AI Handoff Context: NEXORA MOD-EVAC (Hazard)

This document is for future AI assistants to understand the current state of the Hazard project after the initial analysis session on Jan 29, 2026.

## 📌 Project Overview
- **Name**: Hazard (NEXORA MOD-EVAC)
- **Goal**: Competitive-grade real-time hazard detection and automated evacuation.
- **Tech Stack**: FastAPI (Backend), Next.js (Frontend), YOLOv8 (AI), ESP32 (Firmware).

## 📂 Key Documentation
- `DISTINCTION.md`: Role of every component.
- `CONTEXT.md`: High-level system architecture.
- `DEBUG_REPORT.md`: Detailed list of bugs found.

## 🔥 Critical Issues (Action Required)
1. **Frontend Builds**: `frontend/out` and `frontend_public/out` are missing. Backend will fail to serve UI until `npm run build` is executed.
2. **AI Label Mismatch**: Default `yolov8n.pt` (COCO) is used, but the code expects Hazard classes. This will cause false positives (e.g., Person -> Fire).
3. **Serial Fragility**: `SensorWorker` needs auto-reconnect logic in its read loop.
4. **Next.js Version**: `package.json` specifies non-existent Next.js 16. Fix to 15 or latest.

## 🏗️ Technical Nuances for AI
- **State Management**: `backend/state_manager.py` uses a thread-safe `RLock` pattern with an async `event_queue` for WebSocket broadcasts.
- **Clustering**: The system supports distributed AI nodes. Look at `backend/worker_manager.py` and `worker/worker_app.py`.
- **Hardware Protocol**: ESP32s communicate via JSON over Serial (Main) and MJPEG over HTTP (CAM).

## 🚀 Suggested Path Forward
- Fix the `VisionWorker` and `WorkerApp` label mapping to prevent false alarms.
- Implement the `SensorWorker` serial reconnection logic.
- Assist the user in building and deploying the frontends.
- Ensure the custom YOLO model is correctly integrated.
