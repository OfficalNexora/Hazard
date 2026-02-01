# Nexora Native - Async API Bridge
# WebSocket + REST client (async httpx)

import json
import asyncio
from typing import Optional, Dict, Any
import httpx

from .config import API_CONFIG
from .state import state


class Bridge:
    """Async WebSocket + REST bridge"""
    
    def __init__(self):
        self._ws = None
        self._running = False
        self._http = httpx.AsyncClient(base_url=API_CONFIG["base_url"], timeout=10.0)
    
    async def connect(self):
        """Start WebSocket connection"""
        self._running = True
        asyncio.create_task(self._ws_loop())
        asyncio.create_task(self._poll_access_code())
    
    async def disconnect(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        await self._http.aclose()
    
    async def _ws_loop(self):
        """WebSocket connection loop with auto-reconnect"""
        try:
            import websockets
        except ImportError:
            print("[Bridge] websockets not installed, using polling")
            await self._polling_fallback()
            return
        
        while self._running:
            try:
                async with websockets.connect(API_CONFIG["ws_url"]) as ws:
                    self._ws = ws
                    state.set_connected(True)
                    print(f"[Bridge] Connected to {API_CONFIG['ws_url']}")
                    
                    async for msg in ws:
                        if not self._running:
                            break
                        await self._handle_message(msg)
            except Exception as e:
                print(f"[Bridge] WS error: {e}")
                state.set_connected(False)
            
            if self._running:
                await asyncio.sleep(3)
    
    async def _polling_fallback(self):
        """Fallback REST polling"""
        state.set_connected(True)
        while self._running:
            try:
                resp = await self._http.get("/api/status")
                if resp.status_code == 200:
                    state.init_from_status(resp.json())
            except Exception as e:
                print(f"[Bridge] Poll error: {e}")
            await asyncio.sleep(2)
    
    async def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
            msg_type = data.get("type", "")
            payload = data.get("data", data)
            
            if msg_type == "init":
                state.init_from_status(payload)
            elif msg_type == "sensor_update":
                state.update_sensor(payload)
            elif msg_type == "detection":
                state.add_detection(payload)
            elif msg_type == "alert_change":
                state.update_alert(payload)
            elif msg_type == "device_update":
                state.update_devices(payload.get("devices", []))
        except Exception as e:
            print(f"[Bridge] Message error: {e}")
    
    async def _poll_access_code(self):
        """Poll access code every 5s"""
        while self._running:
            try:
                resp = await self._http.get("/api/access_code")
                if resp.status_code == 200:
                    state.access_code = resp.json().get("code", "------")
            except:
                pass
            await asyncio.sleep(5)
    
    # =========================================================================
    # REST API
    # =========================================================================
    
    async def fetch_status(self) -> Optional[Dict]:
        try:
            resp = await self._http.get("/api/status")
            return resp.json() if resp.status_code == 200 else None
        except:
            return None
    
    async def set_alert(self, level: int, reason: str = "Manual") -> bool:
        try:
            resp = await self._http.post("/api/alert", json={"alert": level, "reason": reason})
            return resp.status_code == 200
        except:
            return False
    
    async def trigger_evacuation(self, exit_zone: int = 3) -> bool:
        try:
            resp = await self._http.post("/api/evacuate", json={"exit_zone": exit_zone})
            return resp.status_code == 200
        except:
            return False
    
    async def set_safe_mode(self) -> bool:
        try:
            resp = await self._http.post("/api/safe")
            return resp.status_code == 200
        except:
            return False
    
    async def trigger_manual(self, trigger_type: str) -> bool:
        try:
            resp = await self._http.post("/api/manual/trigger", json={"type": trigger_type})
            return resp.status_code == 200
        except:
            return False
    
    async def clear_manual(self, trigger_type: str) -> bool:
        try:
            resp = await self._http.post("/api/manual/clear", json={"type": trigger_type})
            return resp.status_code == 200
        except:
            return False
    
    async def fetch_gsm_contacts(self) -> Dict:
        try:
            resp = await self._http.get("/api/gsm/contacts")
            return resp.json() if resp.status_code == 200 else {"sms": [], "call": []}
        except:
            return {"sms": [], "call": []}
    
    async def fetch_diorama_model(self) -> Optional[Dict]:
        try:
            resp = await self._http.get("/api/diorama/model")
            return resp.json() if resp.status_code == 200 else None
        except:
            return None
    
    async def fetch_settings(self) -> Optional[Dict]:
        try:
            resp = await self._http.get("/api/settings")
            return resp.json() if resp.status_code == 200 else None
        except:
            return None
    
    async def update_settings(self, config: Dict) -> bool:
        try:
            resp = await self._http.post("/api/settings", json=config)
            return resp.status_code == 200
        except:
            return False


# Singleton
bridge = Bridge()
