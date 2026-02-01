import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from onvif import ONVIFCamera

# Configuration (from previous logs)
IP = "192.168.1.106"
PORT = 2020
USER = "Administration"
PASS = "Administration"

# Path to WSDL
WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")

print(f"Testing ONVIF connection to {IP}:{PORT}...")
print(f"User: {USER}")
print(f"WSDL Dir: {WSDL_DIR}")

if not os.path.exists(WSDL_DIR):
    print("ERROR: WSDL directory does not exist!")
    sys.exit(1)

try:
    # 1. Connect
    mycam = ONVIFCamera(IP, PORT, USER, PASS, wsdl_dir=WSDL_DIR)
    print("Connected to Camera!")

    # 2. Get Device Info
    resp = mycam.devicemgmt.GetDeviceInformation()
    print(f"Device: {resp.Manufacturer} {resp.Model}")

    # 3. Create Media Service
    print("Creating Media Service...")
    media = mycam.create_media_service()
    profiles = media.GetProfiles()
    token = profiles[0].token
    print(f"Profile Token: {token}")

    # 4. Create PTZ Service
    print("Creating PTZ Service...")
    ptz = mycam.create_ptz_service()
    print("PTZ Service Created!")
    
    # 5. Check Status
    status = ptz.GetStatus({'ProfileToken': token})
    print(f"PTZ Status: {status}")

    print("SUCCESS: ONVIF PTZ is working!")

except Exception as e:
    print("\nFAILED!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
