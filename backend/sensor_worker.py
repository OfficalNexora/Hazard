"""
MOD-EVAC-MS - Sensor Worker
Serial port listener for ESP32 sensor telemetry

Reads JSON from COM port, parses sensor data, updates shared state.
"""

import serial
import serial.tools.list_ports
import json
import threading
import time
import argparse
from typing import Optional
from state_manager import state, AlertState


class SensorWorker:
    """
    Worker that reads sensor telemetry from ESP32 main controller via serial.
    Runs in its own thread for true parallelism.
    """
    
    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.device_id = "esp32_main"
        
        # Auto-detect port if not specified
        if not self.port:
            self.port = self._find_esp32_port()
    
    def _find_esp32_port(self) -> Optional[str]:
        """Auto-detect ESP32 serial port"""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # Look for common ESP32 USB-to-serial chips
            if any(x in p.description.lower() for x in ['cp210', 'ch340', 'ftdi', 'usb serial']):
                print(f"[SensorWorker] Auto-detected ESP32 on {p.device}")
                return p.device
        return None
    
    def connect(self) -> bool:
        """Establish serial connection"""
        if not self.port:
            print("[SensorWorker] No port specified and auto-detect failed")
            return False
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Wait for ESP32 to reset after connection
            self.serial.reset_input_buffer()
            print(f"[SensorWorker] Connected to {self.port}")
            state.update_device(self.device_id, "esp32_main", True, self.port)
            return True
        except serial.SerialException as e:
            print(f"[SensorWorker] Connection failed: {e}")
            state.update_device(self.device_id, "esp32_main", False, self.port)
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        state.update_device(self.device_id, "esp32_main", False, "")
        print("[SensorWorker] Disconnected")
    
    def send_command(self, cmd: dict) -> bool:
        """Send JSON command to ESP32"""
        if not self.serial or not self.serial.is_open:
            return False
        try:
            json_str = json.dumps(cmd) + "\n"
            self.serial.write(json_str.encode())
            return True
        except Exception as e:
            print(f"[SensorWorker] Send error: {e}")
            return False
    
    def set_alert(self, alert: AlertState) -> bool:
        """Send alert command to ESP32"""
        return self.send_command({"cmd": "set_alert", "alert": int(alert)})
    
    def _process_line(self, line: str):
        """Process a single line of JSON from ESP32"""
        try:
            data = json.loads(line)
            
            # Handle different message types
            if data.get("type") == "telemetry":
                # Update sensor state
                state.update_sensor(
                    fire=data.get("fire", False),
                    raining=data.get("raining") or data.get("water"),
                    earthquake=data.get("earthquake") or data.get("gyro"),
                    accel=data.get("accel")
                )
                
            elif data.get("event") == "boot":
                print(f"[SensorWorker] ESP32 boot: {data.get('status')}")
                
            elif data.get("event") == "error":
                print(f"[SensorWorker] ESP32 error: {data.get('message')}")
                
            elif data.get("event") == "alert_set":
                print(f"[SensorWorker] Alert set to: {data.get('alert')}")
                
            elif data.get("event") == "pong":
                print(f"[SensorWorker] ESP32 uptime: {data.get('uptime')}ms")
                
        except json.JSONDecodeError:
            # Ignore non-JSON lines
            if line.strip():
                print(f"[SensorWorker] Raw: {line.strip()}")
    
    def _read_loop(self):
        """Main read loop (runs in thread) with auto-reconnection"""
        buffer = ""
        last_ping = time.time()
        
        while self.running:
            try:
                if not self.serial or not self.serial.is_open:
                    print(f"[SensorWorker] Connection lost. Attempting to reconnect...")
                    if self.connect():
                        buffer = "" # Clear buffer on new connection
                    else:
                        time.sleep(5) # Cooldown before next attempt
                        continue

                if self.serial.in_waiting:
                    chunk = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self._process_line(line)
                
                # Periodic ping to check connection
                if time.time() - last_ping > 5:
                    self.send_command({"cmd": "ping"})
                    last_ping = time.time()
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except (serial.SerialException, OSError) as e:
                print(f"[SensorWorker] Serial error: {e}")
                self.disconnect()
                time.sleep(2)
            except Exception as e:
                print(f"[SensorWorker] Unexpected error: {e}")
                time.sleep(1)
    
    def start(self):
        """Start worker thread"""
        if not self.connect():
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print("[SensorWorker] Started")
        return True
    
    def stop(self):
        """Stop worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.disconnect()
        print("[SensorWorker] Stopped")


# Global worker instance
sensor_worker: Optional[SensorWorker] = None


def get_sensor_worker() -> Optional[SensorWorker]:
    """Get the global sensor worker instance"""
    return sensor_worker


def init_sensor_worker(port: str = None) -> SensorWorker:
    """Initialize and start the sensor worker"""
    global sensor_worker
    sensor_worker = SensorWorker(port=port)
    sensor_worker.start()
    return sensor_worker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 Sensor Worker")
    parser.add_argument("--port", type=str, help="Serial port (e.g., COM3)")
    args = parser.parse_args()
    
    worker = init_sensor_worker(port=args.port)
    
    try:
        print("[SensorWorker] Running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
