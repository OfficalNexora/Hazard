"""
Tapo Camera Diagnostic Tool
Run this to verify your Tapo camera connection
"""
import sys

def test_tapo_connection(ip: str, username: str, password: str):
    print(f"\n{'='*60}")
    print(f"  TAPO CAMERA DIAGNOSTIC - {ip}")
    print(f"{'='*60}\n")
    
    # Test 1: Network reachability
    print("[1] Testing network connectivity...")
    import subprocess
    result = subprocess.run(["ping", "-n", "2", ip], capture_output=True, text=True)
    if "Reply from" in result.stdout:
        print(f"    [OK] Camera is reachable at {ip}")
    else:
        print(f"    [FAIL] Cannot ping {ip}")
        print(f"       Check: Is the camera on? Is the IP correct?")
        return False
    
    # Test 2: pytapo authentication
    print("\n[2] Testing pytapo authentication...")
    try:
        from pytapo import Tapo
        
        print(f"    Connecting with username: {username}")
        tapo = Tapo(ip, username, password)
        
        info = tapo.getBasicInfo()
        if info:
            device_info = info.get("device_info", {}).get("basic_info", {})
            name = device_info.get("device_alias", "Unknown")
            model = device_info.get("device_model", "Unknown")
            print(f"    [OK] Authentication successful!")
            print(f"    Camera: {name} ({model})")
        else:
            print(f"    [FAIL] Authentication succeeded but no info returned")
            
    except Exception as e:
        error = str(e).lower()
        print(f"    [FAIL] {e}")
        
        if "invalid authentication" in error or "auth" in error:
            print(f"\n    FIX: Wrong username/password")
            print(f"       Open Tapo app -> Camera -> Settings -> Advanced -> Camera Account")
            print(f"       Create/verify the Camera Account credentials")
        elif "connection" in error or "refused" in error:
            print(f"\n    FIX: Camera not accepting connections")
            print(f"       - Make sure camera is powered on")
            print(f"       - Camera and PC must be on same WiFi network")
        elif "timeout" in error:
            print(f"\n    FIX: Connection timeout")
            print(f"       - Check camera IP address in Tapo app")
        return False
    
    # Test 3: RTSP URL
    print("\n[3] Constructing RTSP URL...")
    rtsp_url = f"rtsp://{username}:{password}@{ip}:554/stream1"
    print(f"    URL: rtsp://{username}:****@{ip}:554/stream1")
    
    # Test 4: OpenCV stream test
    print("\n[4] Testing RTSP stream with OpenCV...")
    try:
        import cv2
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
        
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"    [OK] RTSP stream working! Frame size: {frame.shape}")
                cv2.imwrite("tapo_test_frame.jpg", frame)
                print(f"    Saved test frame to tapo_test_frame.jpg")
            else:
                print(f"    [WARN] Stream opened but no frames received")
        else:
            print(f"    [FAIL] Could not open RTSP stream")
            
        cap.release()
    except Exception as e:
        print(f"    [FAIL] OpenCV error: {e}")
    
    print(f"\n{'='*60}")
    print("  DIAGNOSTIC COMPLETE")
    print(f"{'='*60}\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python tapo_diagnostic.py <IP> <username> <password>")
        print("Example: python tapo_diagnostic.py 192.168.1.106 admin mypassword")
        sys.exit(1)
    
    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    test_tapo_connection(ip, username, password)
