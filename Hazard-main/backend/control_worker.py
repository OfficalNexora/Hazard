"""
MOD-EVAC-MS - Control Worker
I designed this worker to be the fail-safe decision engine of the system.
It handles alert logic independently of the API server, ensuring that critical warnings (LEDs/GSM)
can still be triggered even if the frontend or web server crashes.

Features:
- Consumes detection + sensor events
- Generates LED zone commands
- Sends serial commands to ESP32 for LED patterns
- GSM module integration for calling/messaging
- Network fallback: Internet → Serial/Local
"""

import threading
import time
import json
import argparse
from typing import Optional
from enum import IntEnum

from state_manager import state, AlertState
from voice_engine import voice_engine


class GsmStatus(IntEnum):
    IDLE = 0
    CALLING = 1
    MESSAGING = 2
    ERROR = 3


class ControlWorker:
    """
    I implemented this as a dedicated worker thread to decouple high-priority logic from the IO-bound API server.
    This class is responsible for the 'Safety Integrity' level of the application.
    """
    
    def __init__(self, sensor_worker=None, use_internet: bool = True):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sensor_worker = sensor_worker
        
        # Network mode
        # I track internet connectivity explicitly to handle the graceful degradation to SMS/Serial modes.
        self.use_internet = use_internet
        self.internet_available = False
        self.last_connectivity_check = 0
        
        # GSM configuration
        self.gsm_enabled = True
        self.emergency_numbers = ["+639XXXXXXXXX"]  # Configure actual numbers
        self.gsm_status = GsmStatus.IDLE
        
        # Alert thresholds
        # I tuned these thresholds based on the sensor calibration data to minimize false positives from sensor noise.
        self.water_danger_threshold = 70.0    # Water level % for DANGER
        self.water_warning_threshold = 40.0   # Water level % for WARNING
        self.tilt_threshold = 30.0            # Degrees for structural alert
        
        # Hazard classes that trigger immediate DANGER
        self.critical_hazards = ["Fire", "Explosion", "Flood", "Collapsed Structure"]
        self.warning_hazards = ["Smoke", "Falling Debris", "Landslide"]
        
        # Debounce timers
        # I added a 2-second debounce here to prevent alert flapping which causes hardware relay chatter.
        self.last_alert_change = 0
        self.alert_debounce_seconds = 2.0
        self.last_gsm_action = 0
        self.gsm_cooldown_seconds = 30.0  # Reduced cooldown for manual control
        
        # Performance/Retry Config
        self.gsm_max_retries = 5
        self.retry_delay = 5.0
        
        # Load Contacts from DB
        from database import get_gsm_contacts
        self.contacts = get_gsm_contacts()
        
        # Subscribe to state events
        state.subscribe(self._on_state_event)
    
    def _check_internet_connectivity(self) -> bool:
        """Check if internet is available (simple ping test)"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
    
    def _on_state_event(self, event_type: str, data):
        """Handle state change events"""
        if event_type == "detection":
            self._handle_detection(data)
        elif event_type == "sensor_update":
            self._handle_sensor(data)
    
    def _handle_detection(self, data: dict):
        """Process AI detection and trigger alerts"""
        class_name = data.get("class", "")
        confidence = data.get("confidence", 0)
        
        if confidence < 0.5:
            return  # Ignore low-confidence detections
        
        current_alert = state.get_alert()["value"]
        
        if class_name in self.critical_hazards:
            if current_alert < AlertState.DANGER:
                self._trigger_alert(AlertState.DANGER, f"Detected: {class_name}")
        elif class_name in self.warning_hazards:
            if current_alert < AlertState.CALLING:
                self._trigger_alert(AlertState.CALLING, f"Warning: {class_name}")
    
    def _handle_sensor(self, data: dict):
        """Process sensor data and trigger alerts"""
        raining = data.get("raining", 0)
        earthquake = data.get("earthquake", {})
        
        current_alert = state.get_alert()["value"]
        
        # Check water level (now raining)
        if raining >= self.water_danger_threshold:
            if current_alert < AlertState.DANGER:
                self._trigger_alert(AlertState.DANGER, f"Precipitation level critical: {raining:.1f}%")
        elif raining >= self.water_warning_threshold:
            if current_alert < AlertState.CALLING:
                self._trigger_alert(AlertState.CALLING, f"Showers detected: {raining:.1f}%")
        
        # Check tilt (now earthquake monitor)
        tilt_magnitude = abs(earthquake.get("x", 0)) + abs(earthquake.get("y", 0))
        if tilt_magnitude > self.tilt_threshold:
            if current_alert < AlertState.CALLING:
                self._trigger_alert(AlertState.CALLING, f"Ground vibration detected: {tilt_magnitude:.1f}°")
    
    def _trigger_alert(self, alert_state: AlertState, reason: str):
        """Trigger an alert (Vocal/GUI only, doesn't call automatically)"""
        now = time.time()
        if now - self.last_alert_change < self.alert_debounce_seconds:
            return  # Debounce
        
        self.last_alert_change = now
        
        # Update state
        state.set_alert(alert_state, reason)
        print(f"[Control] Alert detected: {alert_state.name} - {reason}")
        
        # Send command to ESP32 for LED visual only
        self._send_led_command(alert_state)
        
        # BROADCAST: 'HAZARD_DETECTED' for UI notification
        state._emit("hazard_detected", {"type": alert_state.name, "reason": reason})
        
        # AUTOMATIC DISPATCH for DANGER/EVACUATE (if Fire, Rain, etc)
        if alert_state >= AlertState.DANGER:
            category = self._get_category_for_hazard(reason)
            # Background thread to not block control loop
            threading.Thread(
                target=self._trigger_gsm_emergency, 
                args=(reason, category, True), 
                daemon=True
            ).start()
    
    def _send_led_command(self, alert_state: AlertState):
        """Send LED command to ESP32 (with fallback)"""
        cmd = {"cmd": "set_alert", "alert": int(alert_state)}
        
        # Try via sensor worker (serial)
        if self.sensor_worker:
            success = self.sensor_worker.send_command(cmd)
            if success:
                print(f"[Control] LED command sent via serial: {alert_state.name}")
                return
        
        # Fallback: If we had internet API, we'd try here
        if self.use_internet and self.internet_available:
            # TODO: HTTP API fallback if needed
            pass
        
        print(f"[Control] Warning: Could not send LED command")

    def _get_category_for_hazard(self, reason: str) -> str:
        """Map a hazard string to its corresponding contact category"""
        r = reason.lower()
        if "fire" in r or "smoke" in r or "explosion" in r:
            return "fire" if "fire" in r or "explosion" in r else "smoke"
        if "flood" in r or "rain" in r or "precipitation" in r:
            return "rain"
        if "debris" in r or "landslide" in r or "structure" in r or "vibration" in r:
            return "debris"
        return "general"
    
    def _trigger_gsm_emergency(self, reason: str, category: str = "general", voice_prompt: bool = True):
        """Trigger emergency GSM call with 5x retry logic and Robot Voice"""
        if not self.gsm_enabled or not self.sensor_worker:
            return
        
        self.gsm_status = GsmStatus.CALLING
        
        # Get latest contacts from DB/State
        from database import get_gsm_contacts
        contacts = get_gsm_contacts().get("call", [])
        
        if not contacts:
            print("[Control] Error: No SOS numbers found in database")
            self.gsm_status = GsmStatus.IDLE
            return

        # Filter contacts by category
        dispatch_list = [c for c in contacts if c.get("category", "general") in ["general", category]]

        if not dispatch_list:
            print(f"[Control] No contacts found for category: {category}")
            self.gsm_status = GsmStatus.IDLE
            return

        for contact in dispatch_list:
            number = contact["number"]
            retries = 0
            answered = False
            
            while retries < self.gsm_max_retries and not answered:
                print(f"[Control] Attempt {retries+1}/5: Calling {number}...")
                
                # Speak locally while calling
                voice_engine.say(f"Alert. Critical hazard detected. {reason}")
                
                # 'robot_talk' flag tells the ESP32 to play the AI prompt once answered
                cmd = {
                    "cmd": "gsm_call", 
                    "number": number, 
                    "robot_talk": voice_prompt,
                    "msg": reason
                }
                
                # Mock high-level logic: If serial cmd fails, it's a hardware signal fail
                if self.sensor_worker.send_command(cmd):
                    # In a real SIM800L loop, we'd wait for 'OK' or 'BUSY'
                    # Here we simulate wait
                    time.sleep(10) 
                    answered = True # For competition demo, we assume first success or simulated answer
                else:
                    retries += 1
                    time.sleep(self.retry_delay)
            
            if not answered:
                 print(f"[Control] CRITICAL: Failed to reach {number} after 5 attempts")
        
        # Also send SOS SMS
        self._send_gsm_message(f"SOS: {reason}", category=category)
        self.gsm_status = GsmStatus.IDLE
    
    def _send_gsm_message(self, message: str, category: str = "general"):
        """Send GSM SMS message to all registered contacts"""
        if not self.gsm_enabled or not self.sensor_worker:
            return
        
        from database import get_gsm_contacts
        contacts = get_gsm_contacts().get("sms", [])
        
        self.gsm_status = GsmStatus.MESSAGING
        
        # Filter contacts by category
        dispatch_list = [c for c in contacts if c.get("category", "general") in ["general", category]]

        for contact in dispatch_list:
            number = contact["number"]
            # Use custom message if contact has one, otherwise the general reason
            msg = contact.get("message") or message
            cmd = {"cmd": "gsm_sms", "number": number, "message": msg}
            self.sensor_worker.send_command(cmd)
            print(f"[Control] GSM SMS sent to {number}: {msg[:30]}...")
        
        self.gsm_status = GsmStatus.IDLE
    
    def set_safe_mode(self):
        """Manually set system to SAFE mode"""
        state.set_alert(AlertState.SAFE, "Manual reset")
        self._send_led_command(AlertState.SAFE)
        print("[Control] SYSTEM SECURED: SAFE MODE")
    
    def set_evacuate_mode(self, exit_zone: int = 3):
        """Trigger evacuation mode"""
        state.set_alert(AlertState.EVACUATE, f"Evacuation to zone {exit_zone}")
        
        if self.sensor_worker:
            cmd = {"cmd": "set_alert", "alert": int(AlertState.EVACUATE)}
            self.sensor_worker.send_command(cmd)
        
        self._trigger_gsm_emergency("EVACUATION INITIATED", category="general")
        print(f"[Control] EVACUATION mode active, exit zone: {exit_zone}")
    
    def _control_loop(self):
        """Main control loop"""
        while self.running:
            # 1. Periodic connectivity check
            now = time.time()
            if now - self.last_connectivity_check > 30:
                self.internet_available = self._check_internet_connectivity()
                self.last_connectivity_check = now
            
            # 2. Process Manual Triggers from Dashboard
            try:
                import queue
                trigger = state._manual_triggers.get_nowait()
                self._handle_manual_trigger(trigger)
            except:
                pass

            # 3. Check for stale alerts (auto-clear after 10 mins)
            current_alert = state.get_alert()
            if current_alert["value"] > 0:
                if now - self.last_alert_change > 600:
                    self.set_safe_mode()
            
            time.sleep(0.5)

    def _handle_manual_trigger(self, trigger):
        """Execute admin-initiated emergency actions"""
        action = trigger.get("type")
        details = trigger.get("details", "Manual trigger")
        
        print(f"[Control] EXECUTIVE OVERRIDE: {action} triggered")
        
        if action == "call_fire":
            self._trigger_gsm_emergency("FIRE EMERGENCY IN PROGRESS", category="fire", voice_prompt=True)
            self._send_led_command(AlertState.DANGER)
            state.set_alert(AlertState.DANGER, "Manual Fire Alert")
            
        elif action == "call_police":
            self._trigger_gsm_emergency("POLICE ASSISTANCE REQUIRED", voice_prompt=True)
            self._send_led_command(AlertState.CALLING)
            state.set_alert(AlertState.CALLING, "Manual Authority Call")
            
        elif action == "earthquake_alert":
            self._trigger_gsm_emergency("MAJOR EARTHQUAKE DETECTED. SEEK COVER.", category="debris", voice_prompt=True)
            self._send_led_command(AlertState.EVACUATE)
            state.set_alert(AlertState.EVACUATE, "Manual Earthquake Response")
            
        elif action == "sms_broadcast":
            self._send_gsm_message(details)
            
        elif action == "set_safe":
            self.set_safe_mode()
    
    def start(self):
        """Start control worker"""
        self.running = True
        self.thread = threading.Thread(target=self._control_loop, daemon=True)
        self.thread.start()
        
        # Initial connectivity check
        self.internet_available = self._check_internet_connectivity()
        print(f"[Control] Started. Internet: {'available' if self.internet_available else 'offline (local mode)'}")
    
    def stop(self):
        """Stop control worker"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        state.unsubscribe(self._on_state_event)
        print("[Control] Stopped")


# Global instance
control_worker: Optional[ControlWorker] = None


def get_control_worker() -> Optional[ControlWorker]:
    return control_worker


def init_control_worker(sensor_worker=None, use_internet: bool = True) -> ControlWorker:
    global control_worker
    control_worker = ControlWorker(sensor_worker=sensor_worker, use_internet=use_internet)
    control_worker.start()
    return control_worker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control Worker")
    parser.add_argument("--no-internet", action="store_true", help="Disable internet mode")
    args = parser.parse_args()
    
    worker = init_control_worker(use_internet=not args.no_internet)
    
    try:
        print("[Control] Running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
