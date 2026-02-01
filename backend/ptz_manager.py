"""
PTZ Camera Control via ONVIF
Manages Pan-Tilt-Zoom operations for ONVIF-compatible cameras
"""

from onvif import ONVIFCamera
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PTZManager:
    """Manages PTZ operations for ONVIF cameras"""
    
    def __init__(self):
        self.cameras = {}  # {camera_id: ONVIFCamera}
    
    def connect(self, camera_id: str, ip: str, port: int, username: str, password: str):
        """Connect to an ONVIF camera"""
        try:
            cam = ONVIFCamera(ip, port, username, password)
            self.cameras[camera_id] = cam
            logger.info(f"[PTZ] Connected to {camera_id} at {ip}:{port}")
            return True
        except Exception as e:
            logger.error(f"[PTZ] Failed to connect to {camera_id}: {e}")
            return False
    
    def move(self, camera_id: str, direction: str, speed: float = 0.5):
        """
        Move camera in specified direction
        
        Args:
            camera_id: Camera identifier
            direction: 'up', 'down', 'left', 'right', 'zoom_in', 'zoom_out'
            speed: Movement speed (0.0 - 1.0)
        """
        if camera_id not in self.cameras:
            logger.error(f"[PTZ] Camera {camera_id} not connected")
            return False
        
        try:
            cam = self.cameras[camera_id]
            ptz_service = cam.create_ptz_service()
            
            # Get PTZ configuration
            request = ptz_service.create_type('GetConfigurationOptions')
            request.ConfigurationToken = ptz_service.GetConfigurations()[0].token
            
            # Define movement vectors
            movements = {
                'up': {'x': 0, 'y': speed, 'z': 0},
                'down': {'x': 0, 'y': -speed, 'z': 0},
                'left': {'x': -speed, 'y': 0, 'z': 0},
                'right': {'x': speed, 'y': 0, 'z': 0},
                'zoom_in': {'x': 0, 'y': 0, 'z': speed},
                'zoom_out': {'x': 0, 'y': 0, 'z': -speed},
            }
            
            if direction not in movements:
                logger.error(f"[PTZ] Invalid direction: {direction}")
                return False
            
            vec = movements[direction]
            
            # Execute movement
            request = ptz_service.create_type('ContinuousMove')
            request.ProfileToken = ptz_service.GetConfigurations()[0].token
            request.Velocity = {'PanTilt': {'x': vec['x'], 'y': vec['y']}, 'Zoom': {'x': vec['z']}}
            
            ptz_service.ContinuousMove(request)
            logger.info(f"[PTZ] {camera_id} moving {direction}")
            return True
            
        except Exception as e:
            logger.error(f"[PTZ] Move failed for {camera_id}: {e}")
            return False
    
    def stop(self, camera_id: str):
        """Stop PTZ movement"""
        if camera_id not in self.cameras:
            return False
        
        try:
            cam = self.cameras[camera_id]
            ptz_service = cam.create_ptz_service()
            request = ptz_service.create_type('Stop')
            request.ProfileToken = ptz_service.GetConfigurations()[0].token
            ptz_service.Stop(request)
            logger.info(f"[PTZ] {camera_id} stopped")
            return True
        except Exception as e:
            logger.error(f"[PTZ] Stop failed for {camera_id}: {e}")
            return False


# Global instance
ptz_manager: Optional[PTZManager] = None


def get_ptz_manager() -> PTZManager:
    """Get or create PTZ manager"""
    global ptz_manager
    if ptz_manager is None:
        ptz_manager = PTZManager()
    return ptz_manager
