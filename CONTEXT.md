# System Context: NEXORA MOD-EVAC

## Overview
The NEXORA MOD-EVAC (Hazard) system is an integrated hardware-software solution for real-time hazard detection and automated evacuation guidance. It is designed for competitive environments where low latency and reliable coordination are critical.

## Architecture
The system follows a hub-and-spoke architecture:
- **Hub**: The primary computer running `nexus_launcher.py` and the FastAPI backend.
- **Spokes**: 
    - ESP32-CAM nodes for visual monitoring.
    - ESP32 Main Controller for environmental sensing and physical alert outputs.
    - Distributed laptop workers for scaling AI inference.

## Key Technologies
- **Python (FastAPI)**: High-performance backend.
- **Next.js**: Modern, responsive web dashboards.
- **YOLO (Ultralytics)**: Real-time visual hazard detection.
- **ZeroMQ & WebSockets**: Low-latency communication between components.
- **SQLite**: Local persistence for logs and configuration.

## Core Logic (Alert Levels)
The system operates on five alert levels:
- `Level 0 (SAFE)`: Green. System monitoring normally.
- `Level 1 (CAUTION)`: Orange/Yellow. Minor anomaly detected.
- `Level 2 (WARNING)`: Red. Confirmed hazard in locality.
- `Level 3 (EVACUATE)`: Flashing Red + Alarm. Urgent evacuation required.
- `Level 4 (CRITICAL)`: Manual Override/System Failure.

## Interaction Patterns
1. **Sensors -> Backend**: Serial data (JSON) or HTTP/WebSocket from ESP32s.
2. **Backend -> UI**: Push updates via `/ws/telemetry`.
3. **UI -> Backend**: Control commands via REST API.
4. **Backend -> Workers**: Task distribution via ZeroMQ/HTTP.

## Purpose of this Repository
This repository contains the full stack: from low-level C++ firmware to modern React-based frontends, providing a complete "Smart Building" safety system.
