"""
Tapo Camera Manager - Official pytapo integration for TP-Link Tapo cameras
Handles authentication validation and RTSP stream URL retrieval
"""
from typing import Optional, Tuple, Dict
import cv2
import threading
import time
import queue


class TapoCamera:
    """
    Official pytapo-based Tapo camera manager.
    Validates credentials before streaming and provides proper error messages.
    """
    
    def __init__(self, ip: str, username: str, password: str, stream_quality: str = "stream1"):
        self.ip = ip
        self.username = username
        self.password = password
        self.stream_quality = stream_quality  # "stream1" (HD) or "stream2" (SD)
        
        self.tapo = None
        self.is_authenticated = False
        self.camera_info = None
        self.rtsp_url = None
        self.error_message = None
        
    def validate_connection(self) -> Tuple[bool, str]:
        """
        Validate camera connection and credentials using pytapo.
        Returns (success, message)
        """
        try:
            from pytapo import Tapo
            
            print(f"[TapoCamera] Connecting to {self.ip}...")
            self.tapo = Tapo(self.ip, self.username, self.password)
            
            # Try to get basic info - this validates authentication
            self.camera_info = self.tapo.getBasicInfo()
            
            if self.camera_info:
                device_name = self.camera_info.get("device_info", {}).get("basic_info", {}).get("device_alias", "Unknown")
                device_model = self.camera_info.get("device_info", {}).get("basic_info", {}).get("device_model", "Unknown")
                print(f"[TapoCamera] Connected to {device_name} ({device_model})")
                
                self.is_authenticated = True
                return True, f"Connected to {device_name} ({device_model})"
            else:
                self.error_message = "Could not retrieve camera info"
                return False, self.error_message
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Parse specific error types
            if "invalid authentication" in error_str or "auth" in error_str:
                self.error_message = "Invalid username or password. Check your Camera Account credentials in the Tapo app."
            elif "connection" in error_str or "refused" in error_str:
                self.error_message = f"Cannot connect to {self.ip}. Check the IP address and ensure the camera is online."
            elif "timeout" in error_str:
                self.error_message = f"Connection timeout to {self.ip}. Camera may be offline or IP incorrect."
            else:
                self.error_message = f"Connection failed: {e}"
            
            print(f"[TapoCamera] ERROR: {self.error_message}")
            return False, self.error_message
    
    def get_rtsp_url(self) -> Optional[str]:
        """
        Get the RTSP stream URL for this camera.
        Uses official pytapo getStreamURL if available, otherwise constructs manually.
        """
        if not self.is_authenticated:
            success, msg = self.validate_connection()
            if not success:
                return None
        
        try:
            # Try to use pytapo's getStreamURL method
            if self.tapo and hasattr(self.tapo, 'getStreamURL'):
                stream_data = self.tapo.getStreamURL()
                if stream_data:
                    # pytapo returns stream URLs in various formats
                    print(f"[TapoCamera] Stream data: {stream_data}")
        except Exception as e:
            print(f"[TapoCamera] getStreamURL not available: {e}")
        
        # Construct RTSP URL manually (official Tapo format)
        # Format: rtsp://username:password@ip:554/stream1
        self.rtsp_url = f"rtsp://{self.username}:{self.password}@{self.ip}:554/{self.stream_quality}"
        print(f"[TapoCamera] RTSP URL: rtsp://{self.username}:****@{self.ip}:554/{self.stream_quality}")
        
        return self.rtsp_url


class TapoCameraManager:
    """
    Manages multiple Tapo camera streams with proper validation and error handling.
    """
    
    def __init__(self):
        self.cameras: Dict[str, TapoCamera] = {}
        self.streams: Dict[str, dict] = {}
        self.running = True
    
    def add_camera(self, camera_id: str, ip: str, username: str, password: str, 
                   stream_quality: str = "stream1") -> Tuple[bool, str]:
        """
        Add a Tapo camera with RTSP validation.
        Tests RTSP stream directly (pytapo API uses different auth protocol).
        Returns (success, message) for user feedback.
        """
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;10000000"
        
        # Construct RTSP URL
        rtsp_url = f"rtsp://{username}:{password}@{ip}:554/{stream_quality}"
        print(f"[TapoCameraManager] Testing RTSP: rtsp://{username}:****@{ip}:554/{stream_quality}")
        
        # Test RTSP connection directly (more reliable than pytapo API)
        try:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                cap.release()
                return False, f"Cannot connect to camera at {ip}. Check IP address and ensure camera is online."
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                return False, "Connected but no video frames received. Check username/password in Tapo app Camera Account."
            
            # Success - got a frame
            height, width = frame.shape[:2]
            print(f"[TapoCameraManager] RTSP validated: {width}x{height}")
            
        except Exception as e:
            return False, f"RTSP connection error: {str(e)}"
        
        # Create camera object (without pytapo validation)
        camera = TapoCamera(ip, username, password, stream_quality)
        camera.rtsp_url = rtsp_url
        camera.is_authenticated = True
        self.cameras[camera_id] = camera
        
        # Start stream thread
        self.streams[camera_id] = {
            "url": rtsp_url,
            "active": True,
            "last_frame": None,
            "frame_queue": queue.Queue(maxsize=2),
            "thread": None
        }
        
        thread = threading.Thread(target=self._stream_loop, args=(camera_id,), daemon=True)
        self.streams[camera_id]["thread"] = thread
        thread.start()
        
        return True, f"Connected to Tapo camera at {ip} ({width}x{height})"

    def get_ptz_status(self, camera_id: str):
        """Get current PTZ status including position"""
        camera = self.cameras.get(camera_id)
        if not camera or not hasattr(camera, 'ptz_service'):
             return None
        
        try:
            status = camera.ptz_service.GetStatus({'ProfileToken': camera.media_profile})
            return {
                'pan': status.Position.PanTilt.x,
                'tilt': status.Position.PanTilt.y,
                'zoom': status.Position.Zoom.x if status.Position.Zoom else 0
            }
        except Exception as e:
            print(f"[Tapo] GetStatus Error: {e}")
            return None

    def move_motor_step(self, camera_id: str, pan_step: float, tilt_step: float):
        """
        Move camera incrementally (RelativeMove).
        pan_step: Amount to move (-1.0 to 1.0)
        tilt_step: Amount to move (-1.0 to 1.0)
        """
        camera = self.cameras.get(camera_id)
        if not camera:
            return False, "Camera not found", None
            
        try:
            # Initialize ONVIF if needed (same as before)
            if not hasattr(camera, 'ptz_service'):
                from onvif import ONVIFCamera
                import os
                wsdl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")
                mycam = ONVIFCamera(camera.ip, 2020, camera.username, camera.password, wsdl_dir=wsdl_dir)
                media = mycam.create_media_service()
                token = media.GetProfiles()[0].token
                ptz = mycam.create_ptz_service()
                
                camera.ptz_service = ptz
                camera.media_profile = token
            
            # Construct RelativeMove payload
            move_request = {
                'ProfileToken': camera.media_profile,
                'Translation': {
                    'PanTilt': {
                        'x': pan_step,
                        'y': tilt_step
                    },
                    'Zoom': {
                        'x': 0.0
                    }
                },
                'Speed': {
                    'PanTilt': {
                        'x': 1.0,
                        'y': 1.0
                    },
                    'Zoom': {
                        'x': 1.0
                    }
                }
            }
            
            camera.ptz_service.RelativeMove(move_request)
            
            # Fetch new status after a brief delay to allow movement to register
            # (Translation returns immediately, but movement takes physical time)
            import time
            time.sleep(0.2) 
            status = self.get_ptz_status(camera_id)
            
            return True, "Moved", status
            
        except Exception as e:
            print(f"[Tapo] PTZ Step Error: {e}")
            return False, str(e), None
    
    
    def _stream_loop(self, camera_id: str):
        """Stream processing loop using OpenCV with optimized settings"""
        from state_manager import state  # Import here to avoid circular dependencies
        
        stream = self.streams.get(camera_id)
        if not stream:
            return
        
        url = stream["url"]
        ip = self.cameras[camera_id].ip if camera_id in self.cameras else "0.0.0.0"
        
        # Use TCP transport for RTSP (official recommendation for Tapo)
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;10000000"
        
        max_retries = 5
        retry_count = 0
        
        while self.running and stream["active"] and retry_count < max_retries:
            print(f"[TapoCameraManager] Opening stream for {camera_id}...")
            
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                print(f"[TapoCameraManager] Failed to open stream (attempt {retry_count + 1})")
                retry_count += 1
                time.sleep(3)
                continue
            
            print(f"[TapoCameraManager] Stream {camera_id} connected!")
            retry_count = 0  # Reset on successful connection
            
            # Update state immediately
            state.update_device(camera_id, "camera", True, ip)
            last_heartbeat = time.time()
            
            while self.running and stream["active"]:
                ret, frame = cap.read()
                
                if not ret:
                    print(f"[TapoCameraManager] Stream {camera_id} lost connection")
                    break
                
                # Update heartbeat every 2 seconds
                if time.time() - last_heartbeat > 2.0:
                     state.update_device(camera_id, "camera", True, ip)
                     last_heartbeat = time.time()
                
                stream["last_frame"] = frame
                
                # Encode to JPEG
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                try:
                    stream["frame_queue"].put_nowait(jpeg.tobytes())
                except queue.Full:
                    pass
            
            cap.release()
            retry_count += 1
            time.sleep(2)
        
        print(f"[TapoCameraManager] Stream {camera_id} stopped after {max_retries} retries")
    
    def get_frame(self, camera_id: str) -> Optional[bytes]:
        """Get latest frame as JPEG bytes"""
        stream = self.streams.get(camera_id)
        if not stream:
            return None
        
        try:
            return stream["frame_queue"].get_nowait()
        except queue.Empty:
            if stream["last_frame"] is not None:
                _, jpeg = cv2.imencode('.jpg', stream["last_frame"])
                return jpeg.tobytes()
            return None
    
    def remove_camera(self, camera_id: str):
        """Remove and stop a camera stream"""
        if camera_id in self.streams:
            self.streams[camera_id]["active"] = False
            del self.streams[camera_id]
        if camera_id in self.cameras:
            del self.cameras[camera_id]
    
    def stop(self):
        """Stop all streams"""
        self.running = False


# Singleton
_tapo_manager: Optional[TapoCameraManager] = None

def get_tapo_manager() -> TapoCameraManager:
    global _tapo_manager
    if _tapo_manager is None:
        _tapo_manager = TapoCameraManager()
    return _tapo_manager
