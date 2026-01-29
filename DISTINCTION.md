# Project Distinction and Annotations

This document outlines the roles and responsibilities of each component in the Hazard (NEXORA MOD-EVAC) system.

## Core Components

### 1. Nexus Launcher (`nexus_launcher.py`)
- **Role**: Central orchestrator and GUI for starting the system.
- **Responsibilities**:
    - Launches the FastAPI backend.
    - Provides a visual interface for system logs and status.
    - Generates and displays pairing codes for the Public Portal.
    - Monitors local IP and provides quick links to Admin/Public interfaces.

### 2. Backend (`backend/`)
- **Role**: Orchestration layer and API provider.
- **Key Files**:
    - `server.py`: FastAPI entry point, manages WebSockets and API endpoints.
    - `state_manager.py`: Centralized state for the entire system (sensors, devices, alerts).
    - `sensor_worker.py`: Communicates with hardware sensors (via Serial/ESP32).
    - `vision_worker.py`: Handles AI detection using YOLO/ultralytics.
    - `control_worker.py`: Decision-making logic for alerts and evacuation triggers.
    - `worker_manager.py`: Manages distributed worker nodes.

### 3. Worker (`worker/`)
- **Role**: Distributed node for offloading computation.
- **Responsibilities**:
    - Can run vision or logic tasks on separate hardware.
    - Communicates back to the main backend server.

### 4. Frontends (`frontend/` & `frontend_public/`)
- **Role**: User Interface.
- **Frontend (Admin)**: Detailed dashboard for monitoring sensors, viewing camera feeds, and managing alerts.
- **Frontend Public**: Minimalist portal for public awareness, requires a pairing code.
- **Tech Stack**: Next.js, Tailwind CSS, Lucide icons.

### 5. Firmware (`firmware/`)
- **Role**: Hardware-level logic.
- **ESP32-CAM**: Firmware for the cameras used in visual detection.
- **Main Controller**: Firmware for the central hardware hub (buzzer, LEDs, sensor reading).

### 6. AI (`AI/`)
- **Role**: Intelligence layer.
- **Responsibilities**: Contains training scripts, datasets, and models for hazard detection (fire, smoke, etc.).

## Operation Flow
1. **Bootstrap**: `nexus_launcher.py` starts.
2. **Backend**: `server.py` initializes database and starts workers.
3. **Detection**: `sensor_worker` and `vision_worker` feed data to `state_manager`.
4. **Logic**: `control_worker` evaluates state and updates `AlertState`.
5. **UI**: Dashboards reflect state changes via WebSockets.
