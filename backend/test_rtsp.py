"""
RTSP Stream Test Script
Tests RTSP connectivity independent of the main application
"""
import cv2
import os
import sys

def test_rtsp(url: str):
    """Test RTSP stream connectivity"""
    print(f"\n{'='*60}")
    print(f"Testing RTSP Stream: {url}")
    print(f"{'='*60}\n")
    
    # Set RTSP options
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
    
    print("[1] Creating VideoCapture with CAP_FFMPEG...")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    print(f"[2] isOpened: {cap.isOpened()}")
    
    if not cap.isOpened():
        print("[X] FAILED: Could not open stream")
        print("\nTroubleshooting:")
        print("  1. Is RTSP enabled in your Tapo app?")
        print("  2. Did you create a Camera Account in Tapo app settings?")
        print("  3. Is the IP address correct?")
        print("  4. Try the URL in VLC Media Player to verify it works")
        return False
    
    print("[3] Attempting to read a frame...")
    ret, frame = cap.read()
    
    if ret and frame is not None:
        print(f"[✓] SUCCESS! Frame received: {frame.shape}")
        
        # Save test frame
        cv2.imwrite("test_frame.jpg", frame)
        print("[✓] Saved test_frame.jpg")
        
        cap.release()
        return True
    else:
        print("[X] FAILED: Stream opened but no frames received")
        cap.release()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rtsp.py <rtsp_url>")
        print("Example: python test_rtsp.py rtsp://admin:password@192.168.1.45:554/stream1")
        sys.exit(1)
    
    url = sys.argv[1]
    success = test_rtsp(url)
    sys.exit(0 if success else 1)
