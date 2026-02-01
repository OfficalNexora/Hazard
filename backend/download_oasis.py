import os
import requests

WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")
if not os.path.exists(WSDL_DIR):
    os.makedirs(WSDL_DIR)

BASE_URL = "https://raw.githubusercontent.com/FalkTannhaeuser/python-onvif-zeep/master/wsdl/"

# Only download missing OASIS files
FILES = [
    "b-2.xsd",
    "t-1.xsd",
    "bf-2.xsd",
    "r-2.xsd",
    "ws-addr.xsd",
    "xml.xsd"
]

print(f"Downloading OASIS files to {WSDL_DIR}...")

for filename in FILES:
    url = BASE_URL + filename
    path = os.path.join(WSDL_DIR, filename)
    print(f"Downloading {filename}...")
    try:
        r = requests.get(url, timeout=10) # Add timeout
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            print(f"Saved {filename}")
        else:
            print(f"Failed to download {filename}: {r.status_code}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

print("Done.")
