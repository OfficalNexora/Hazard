import os
import requests

WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")
if not os.path.exists(WSDL_DIR):
    os.makedirs(WSDL_DIR)

BASE_URL = "https://raw.githubusercontent.com/FalkTannhaeuser/python-onvif-zeep/master/wsdl/"

FILES = [
    "devicemgmt.wsdl",
    "media.wsdl",
    "ptz.wsdl",
    "events.wsdl",
    "analytics.wsdl",
    "imaging.wsdl",
    "deviceio.wsdl",
    "display.wsdl",
    "receiver.wsdl",
    "recording.wsdl",
    "replay.wsdl",
    "search.wsdl",
    "security.wsdl",
    "onvif.xsd",
    "xmlmime.xsd",
    "xop-include.xsd",
    "b-2.xsd",
    "t-1.xsd",
    "bf-2.xsd"
]

print(f"Downloading WSDL files to {WSDL_DIR}...")

for filename in FILES:
    url = BASE_URL + filename
    path = os.path.join(WSDL_DIR, filename)
    print(f"Downloading {filename}...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            
            # Create copy without extension if it ends in .xsd (fixes strict import errors)
            if filename.endswith(".xsd"):
                no_ext = os.path.splitext(filename)[0]
                no_ext_path = os.path.join(WSDL_DIR, no_ext)
                with open(no_ext_path, 'wb') as f:
                    f.write(r.content)
                    
                # Specific fix for xop-include -> xop
                if filename == "xop-include.xsd":
                     xop_path = os.path.join(WSDL_DIR, "xop")
                     with open(xop_path, 'wb') as f:
                        f.write(r.content)
        else:
            print(f"Failed to download {filename}: {r.status_code}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

print("Done.")
