"""
FFmpeg RTSP Streamer - Reliable RTSP streaming via FFmpeg subprocess
"""
import subprocess
import threading
import time
import numpy as np
import cv2
from typing import Optional, Dict, Callable
import queue
import shutil


class FFmpegRTSPStreamer:
    """
    Reliable RTSP streaming using FFmpeg subprocess.
    Much more stable than OpenCV's RTSP handling on Windows.
    """
    
    def __init__(self):
        self.streams: Dict[str, dict] = {}
        self.running = True
        
        # Verify FFmpeg is available
        self.ffmpeg_path = shutil.which("ffmpeg")
        
        # If not in PATH, check WinGet installation location (Windows)
        if not self.ffmpeg_path:
            import os
            import glob
            winget_pattern = os.path.expanduser(
                "~/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"
            )
            matches = glob.glob(winget_pattern)
            if matches:
                self.ffmpeg_path = matches[0]
                print(f"[FFmpegStreamer] Found FFmpeg at: {self.ffmpeg_path}")
        
        if not self.ffmpeg_path:
            print("[FFmpegStreamer] WARNING: FFmpeg not found!")
            print("[FFmpegStreamer] Install with: winget install Gyan.FFmpeg")
            print("[FFmpegStreamer] Using OpenCV fallback (less reliable)")
    
    def add_stream(self, stream_id: str, rtsp_url: str, 
                   frame_callback: Optional[Callable] = None,
                   width: int = 640, height: int = 480):
        """
        Add a new RTSP stream.
        
        Args:
            stream_id: Unique identifier for this stream
            rtsp_url: RTSP URL (e.g., rtsp://user:pass@ip:554/stream1)
            frame_callback: Optional callback for each frame
            width: Output frame width
            height: Output frame height
        """
        if stream_id in self.streams:
            self.remove_stream(stream_id)
        
        self.streams[stream_id] = {
            "url": rtsp_url,
            "active": True,
            "process": None,
            "thread": None,
            "frame_queue": queue.Queue(maxsize=2),
            "last_frame": None,
            "callback": frame_callback,
            "width": width,
            "height": height,
            "use_ffmpeg": self.ffmpeg_path is not None
        }
        
        # Start stream thread
        thread = threading.Thread(
            target=self._stream_loop, 
            args=(stream_id,), 
            daemon=True
        )
        self.streams[stream_id]["thread"] = thread
        thread.start()
        
        print(f"[FFmpegStreamer] Started stream: {stream_id}")
    
    def _stream_loop(self, stream_id: str):
        """Main stream processing loop"""
        stream = self.streams.get(stream_id)
        if not stream:
            return
        
        url = stream["url"]
        width = stream["width"]
        height = stream["height"]
        
        if stream["use_ffmpeg"]:
            self._ffmpeg_stream(stream_id, url, width, height)
        else:
            self._opencv_stream(stream_id, url)
    
    def _ffmpeg_stream(self, stream_id: str, url: str, width: int, height: int):
        """Stream using FFmpeg subprocess - most reliable method"""
        stream = self.streams.get(stream_id)
        if not stream:
            return
        
        # FFmpeg command to read RTSP and output raw RGB frames
        cmd = [
            self.ffmpeg_path,
            "-rtsp_transport", "tcp",           # Use TCP for more reliability
            "-i", url,                          # Input RTSP URL
            "-f", "rawvideo",                   # Output raw video
            "-pix_fmt", "bgr24",                # BGR format (OpenCV compatible)
            "-s", f"{width}x{height}",          # Scale to desired size
            "-r", "15",                         # 15 FPS
            "-loglevel", "error",               # Only show errors
            "-"                                 # Output to stdout
        ]
        
        print(f"[FFmpegStreamer] Launching: {' '.join(cmd[:6])}...")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            stream["process"] = process
            
            frame_size = width * height * 3  # BGR = 3 bytes per pixel
            
            while self.running and stream["active"]:
                raw_frame = process.stdout.read(frame_size)
                
                if len(raw_frame) != frame_size:
                    print(f"[FFmpegStreamer] Stream {stream_id} - incomplete frame, reconnecting...")
                    break
                
                # Convert raw bytes to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((height, width, 3))
                
                # Store frame
                stream["last_frame"] = frame
                
                # Convert to JPEG for web streaming
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                try:
                    stream["frame_queue"].put_nowait(jpeg.tobytes())
                except queue.Full:
                    pass
                
                # Callback if provided
                if stream["callback"]:
                    stream["callback"](stream_id, frame)
            
        except Exception as e:
            print(f"[FFmpegStreamer] Error in stream {stream_id}: {e}")
        finally:
            if stream.get("process"):
                stream["process"].terminate()
                stream["process"] = None
    
    def _opencv_stream(self, stream_id: str, url: str):
        """Fallback to OpenCV if FFmpeg not available"""
        stream = self.streams.get(stream_id)
        if not stream:
            return
        
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
        
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            print(f"[FFmpegStreamer] OpenCV failed to open {url}")
            return
        
        while self.running and stream["active"]:
            ret, frame = cap.read()
            if not ret:
                print(f"[FFmpegStreamer] OpenCV stream lost: {stream_id}")
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                continue
            
            stream["last_frame"] = frame
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            
            try:
                stream["frame_queue"].put_nowait(jpeg.tobytes())
            except queue.Full:
                pass
        
        cap.release()
    
    def get_frame(self, stream_id: str) -> Optional[bytes]:
        """Get the latest JPEG frame for a stream"""
        stream = self.streams.get(stream_id)
        if not stream:
            return None
        
        try:
            return stream["frame_queue"].get_nowait()
        except queue.Empty:
            # Return last frame if queue empty
            if stream["last_frame"] is not None:
                _, jpeg = cv2.imencode('.jpg', stream["last_frame"])
                return jpeg.tobytes()
            return None
    
    def remove_stream(self, stream_id: str):
        """Stop and remove a stream"""
        if stream_id in self.streams:
            self.streams[stream_id]["active"] = False
            if self.streams[stream_id].get("process"):
                self.streams[stream_id]["process"].terminate()
            del self.streams[stream_id]
            print(f"[FFmpegStreamer] Removed stream: {stream_id}")
    
    def stop(self):
        """Stop all streams"""
        self.running = False
        for stream_id in list(self.streams.keys()):
            self.remove_stream(stream_id)


# Singleton instance
_streamer: Optional[FFmpegRTSPStreamer] = None

def get_streamer() -> FFmpegRTSPStreamer:
    global _streamer
    if _streamer is None:
        _streamer = FFmpegRTSPStreamer()
    return _streamer
