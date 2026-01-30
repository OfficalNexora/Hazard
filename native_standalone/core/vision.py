import cv2
import threading
import time
import requests
import numpy as np
from PIL import Image, ImageTk

class VisionStreamer:
    def __init__(self, url, on_frame_callback):
        self.url = url
        self.on_frame = on_frame_callback
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()

    def _stream_loop(self):
        """Consume MJPEG stream manually to avoid OpenCV latency issues."""
        try:
            stream = requests.get(self.url, stream=True, timeout=5)
            if stream.status_code != 200:
                print(f"[Vision] Failed to connect to {self.url}")
                return

            bytes_buf = bytes()
            for chunk in stream.iter_content(chunk_size=1024):
                if not self.running: break
                bytes_buf += chunk
                a = bytes_buf.find(b'\xff\xd8') # JPEG start
                b = bytes_buf.find(b'\xff\xd9') # JPEG end
                if a != -1 and b != -1:
                    jpg = bytes_buf[a:b+2]
                    bytes_buf = bytes_buf[b+2:]
                    
                    # Convert to PIL for Tkinter
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self.on_frame(frame)
        except Exception as e:
            print(f"[Vision] Stream error: {e}")
            time.sleep(2)
            if self.running: self._stream_loop()

    def stop(self):
        self.running = False
