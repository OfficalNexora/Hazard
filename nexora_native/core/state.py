# Nexora Native - Reactive State (Flet Compatible)
# Thread-safe state with pub/sub for UI updates

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable
from datetime import datetime


@dataclass
class SensorData:
    raining: float = 0.0
    fire: bool = False
    earthquake: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    accel: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    timestamp: float = 0.0


@dataclass  
class Detection:
    class_name: str = ""
    confidence: float = 0.0
    bbox: List[float] = field(default_factory=list)
    frame_id: int = 0
    timestamp: float = 0.0


@dataclass
class AlertState:
    state: int = 0
    value: float = 0.0
    reason: str = ""
    
    @property
    def is_critical(self) -> bool:
        return self.state >= 3


@dataclass
class DeviceStatus:
    device_id: str = ""
    device_type: str = ""
    connected: bool = False
    last_seen: float = 0.0
    port: str = ""
    status: str = "UNKNOWN"


class AppState:
    """Reactive state manager for Flet app"""
    
    def __init__(self):
        self.sensor = SensorData()
        self.alert = AlertState()
        self.devices: List[DeviceStatus] = []
        self.detections: List[Detection] = []
        self.access_code: str = "------"
        self.connected: bool = False
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _notify(self, event: str, data: Any = None):
        for cb in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(data))
                else:
                    cb(data)
            except Exception as e:
                print(f"[State] Callback error: {e}")
    
    def update_sensor(self, data: dict):
        self.sensor = SensorData(
            raining=data.get("raining", 0.0),
            fire=data.get("fire", False),
            earthquake=data.get("earthquake", {"x": 0, "y": 0, "z": 0}),
            accel=data.get("accel", {"x": 0, "y": 0, "z": 0}),
            timestamp=data.get("timestamp", datetime.now().timestamp()),
        )
        self._notify("sensor", self.sensor)
    
    def update_alert(self, data: dict):
        self.alert = AlertState(
            state=data.get("state", 0),
            value=data.get("value", 0.0),
            reason=data.get("reason", ""),
        )
        self._notify("alert", self.alert)
    
    def add_detection(self, data: dict):
        det = Detection(
            class_name=data.get("class", "unknown"),
            confidence=data.get("confidence", 0.0),
            bbox=data.get("bbox", []),
            frame_id=data.get("frame_id", 0),
            timestamp=data.get("timestamp", datetime.now().timestamp()),
        )
        self.detections.insert(0, det)
        self.detections = self.detections[:50]
        self._notify("detections", self.detections)
    
    def update_devices(self, devices: List[dict]):
        self.devices = [
            DeviceStatus(
                device_id=d.get("device_id", ""),
                device_type=d.get("device_type", ""),
                connected=d.get("connected", False),
                last_seen=d.get("last_seen", 0),
                port=d.get("port", ""),
                status=d.get("status", "UNKNOWN"),
            )
            for d in devices
        ]
        self._notify("devices", self.devices)
    
    def set_connected(self, connected: bool):
        self.connected = connected
        self._notify("connection", connected)
    
    def init_from_status(self, data: dict):
        if "sensor" in data:
            self.update_sensor(data["sensor"])
        if "alert" in data:
            self.update_alert(data["alert"])
        if "devices" in data:
            self.update_devices(data["devices"])


# Singleton
state = AppState()
