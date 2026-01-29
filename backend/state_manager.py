"""
MOD-EVAC-MS - State Manager
Thread-safe shared state for concurrent workers

Provides:
- Current sensor readings
- Detection history
- Device status
- Alert queue
- Event broadcasting
"""

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import IntEnum
import json
from database import log_detection, log_alert


class AlertState(IntEnum):
    SAFE = 0
    CALLING = 1
    MESSAGING = 2
    DANGER = 3
    EVACUATE = 4


@dataclass
class SensorData:
    fire: bool = False
    raining: float = 0.0
    earthquake_x: float = 0.0
    earthquake_y: float = 0.0
    earthquake_z: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    timestamp: float = 0.0


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    frame_id: int
    timestamp: float


@dataclass
class DeviceStatus:
    device_id: str
    device_type: str  # 'esp32_main' or 'esp32_cam'
    connected: bool = False
    last_seen: float = 0.0
    port: str = ""


class StateManager:
    """
    Thread-safe state manager for all system data.
    Uses locks for data access and queues for event distribution.
    """
    
    def __init__(self, max_detections: int = 100, max_alerts: int = 50):
        # Locks
        self._sensor_lock = threading.RLock()
        self._detection_lock = threading.RLock()
        self._device_lock = threading.RLock()
        self._alert_lock = threading.RLock()
        
        # State storage
        self._sensor_data = SensorData()
        self._detections: List[Detection] = []
        self._devices: Dict[str, DeviceStatus] = {}
        self._current_alert = AlertState.SAFE
        self._alert_history: List[dict] = []
        
        # Limits
        self._max_detections = max_detections
        self._max_alerts = max_alerts
        
        # Access Code (Random 6-digit for pairing)
        import random
        self._access_code = str(random.randint(100000, 999999))
        
        # GSM and Manual Controls
        self._gsm_contacts = {"sms": [], "call": []}  # [{"number": str, "name": str, "message": str}]
        self._manual_triggers = queue.Queue(maxsize=10)
        
        # Event subscribers
        self._subscribers: List[Callable[[str, Any], None]] = []
        self._subscriber_lock = threading.Lock()
        
        # Event queue for async processing
        self.event_queue: queue.Queue = queue.Queue(maxsize=1000)
    
    # =========================================================================
    # EVENT SYSTEM
    # =========================================================================
    
    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to state change events"""
        with self._subscriber_lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[str, Any], None]) -> None:
        """Unsubscribe from events"""
        with self._subscriber_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def _emit(self, event_type: str, data: Any) -> None:
        """Emit event to all subscribers"""
        event = {"type": event_type, "data": data, "timestamp": time.time()}
        
        # Queue for async processing
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            pass  # Drop event if queue full
        
        # Direct callback for immediate subscribers
        with self._subscriber_lock:
            for callback in self._subscribers:
                try:
                    callback(event_type, data)
                except Exception as e:
                    print(f"[StateManager] Subscriber error: {e}")
    
    # =========================================================================
    # SENSOR DATA
    # =========================================================================
    
    def update_sensor(self, raining: float = None, fire: bool = None, earthquake: dict = None, 
                      accel: dict = None) -> None:
        """Update sensor readings (thread-safe)"""
        with self._sensor_lock:
            if fire is not None:
                self._sensor_data.fire = fire
            if raining is not None:
                self._sensor_data.raining = raining
            if earthquake:
                self._sensor_data.earthquake_x = earthquake.get('x', self._sensor_data.earthquake_x)
                self._sensor_data.earthquake_y = earthquake.get('y', self._sensor_data.earthquake_y)
                self._sensor_data.earthquake_z = earthquake.get('z', self._sensor_data.earthquake_z)
            if accel:
                self._sensor_data.accel_x = accel.get('x', self._sensor_data.accel_x)
                self._sensor_data.accel_y = accel.get('y', self._sensor_data.accel_y)
                self._sensor_data.accel_z = accel.get('z', self._sensor_data.accel_z)
            self._sensor_data.timestamp = time.time()
        
        self._emit("sensor_update", self.get_sensor())
    
    def get_sensor(self) -> dict:
        """Get current sensor data (thread-safe)"""
        with self._sensor_lock:
            return {
                "fire": self._sensor_data.fire,
                "raining": self._sensor_data.raining,
                "earthquake": {
                    "x": self._sensor_data.earthquake_x,
                    "y": self._sensor_data.earthquake_y,
                    "z": self._sensor_data.earthquake_z
                },
                "accel": {
                    "x": self._sensor_data.accel_x,
                    "y": self._sensor_data.accel_y,
                    "z": self._sensor_data.accel_z
                },
                "timestamp": self._sensor_data.timestamp
            }
    
    # =========================================================================
    # DETECTIONS
    # =========================================================================
    
    def add_detection(self, class_name: str, confidence: float, 
                      bbox: List[float], frame_id: int) -> None:
        """Add a new detection (thread-safe)"""
        detection = Detection(
            class_name=class_name,
            confidence=confidence,
            bbox=bbox,
            frame_id=frame_id,
            timestamp=time.time()
        )
        
        with self._detection_lock:
            self._detections.append(detection)
            # Trim old detections
            if len(self._detections) > self._max_detections:
                self._detections = self._detections[-self._max_detections:]
        
        # PERSIST TO SQLITE
        log_detection(class_name, confidence, bbox, frame_id)
        
        self._emit("detection", {
            "class": class_name,
            "confidence": confidence,
            "bbox": bbox,
            "frame_id": frame_id
        })
    
    def get_detections(self, limit: int = 20) -> List[dict]:
        """Get recent detections (thread-safe)"""
        with self._detection_lock:
            return [
                {
                    "class": d.class_name,
                    "confidence": d.confidence,
                    "bbox": d.bbox,
                    "frame_id": d.frame_id,
                    "timestamp": d.timestamp
                }
                for d in self._detections[-limit:]
            ]
    
    # =========================================================================
    # DEVICES
    # =========================================================================
    
    def update_device(self, device_id: str, device_type: str, 
                      connected: bool, port: str = "") -> None:
        """Update device status (thread-safe)"""
        with self._device_lock:
            self._devices[device_id] = DeviceStatus(
                device_id=device_id,
                device_type=device_type,
                connected=connected,
                last_seen=time.time(),
                port=port
            )
        
        self._emit("device_update", {
            "device_id": device_id,
            "device_type": device_type,
            "connected": connected,
            "port": port
        })
    
    def get_devices(self) -> List[dict]:
        """Get all device statuses (thread-safe)"""
        with self._device_lock:
            return [
                {
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "connected": d.connected,
                    "last_seen": d.last_seen,
                    "port": d.port
                }
                for d in self._devices.values()
            ]
    
    # =========================================================================
    # ALERTS
    # =========================================================================
    
    def set_alert(self, state: AlertState, reason: str = "") -> None:
        """Set current alert state (thread-safe)"""
        with self._alert_lock:
            old_state = self._current_alert
            self._current_alert = state
            
            if old_state != state:
                self._alert_history.append({
                    "from": old_state.name,
                    "to": state.name,
                    "reason": reason,
                    "timestamp": time.time()
                })
                # Trim history
                if len(self._alert_history) > self._max_alerts:
                    self._alert_history = self._alert_history[-self._max_alerts:]
        
        # PERSIST TO SQLITE (Outside Lock)
        log_alert(state.name, reason)
        
        self._emit("alert_change", {
            "state": state.name,
            "value": int(state),
            "reason": reason
        })
    
    def get_alert(self) -> dict:
        """Get current alert state (thread-safe)"""
        with self._alert_lock:
            return {
                "state": self._current_alert.name,
                "value": int(self._current_alert)
            }
    
    def get_alert_history(self, limit: int = 20) -> List[dict]:
        """Get alert history (thread-safe)"""
        with self._alert_lock:
            return self._alert_history[-limit:]
    
    def get_access_code(self) -> str:
        """Get current 6-digit access code for pairing"""
        return self._access_code

    def verify_access_code(self, code: str) -> bool:
        """Verify if provided code matches system code"""
        return str(code) == self._access_code

    # =========================================================================
    # GSM & MANUAL ACTIONS
    # =========================================================================

    def add_gsm_contact(self, mode: str, number: str, name: str = "", message: str = "", category: str = "general") -> None:
        """Add a contact for SMS or Call"""
        if mode not in ["sms", "call"]: return
        with self._alert_lock:
            self._gsm_contacts[mode].append({
                "number": number,
                "name": name,
                "message": message,
                "category": category
            })
        self._emit("gsm_update", self._gsm_contacts)

    def delete_gsm_contact(self, number: str) -> None:
        """Remove a contact by number"""
        with self._alert_lock:
            for mode in ["sms", "call"]:
                self._gsm_contacts[mode] = [c for c in self._gsm_contacts[mode] if c["number"] != number]
        self._emit("gsm_update", self._gsm_contacts)

    def get_gsm_contacts(self) -> dict:
        with self._alert_lock:
            return self._gsm_contacts

    def trigger_manual_action(self, action_type: str, details: str = "") -> None:
        """Queue a manual action (Call, SMS, LED)"""
        action = {
            "type": action_type, # 'call_fire', 'call_police', 'sms_alert', 'led_danger'
            "details": details,
            "timestamp": time.time()
        }
        try:
            self._manual_triggers.put_nowait(action)
        except queue.Full:
            pass
        self._emit("manual_trigger", action)

    # =========================================================================
    # FULL STATE
    # =========================================================================
    
    def get_full_state(self) -> dict:
        """Get complete system state (thread-safe)"""
        return {
            "sensor": self.get_sensor(),
            "alert": self.get_alert(),
            "devices": self.get_devices(),
            "detections": self.get_detections(10)
        }


# Global state instance
state = StateManager()
