import requests
import json

BASE_URL = "http://localhost:8000"

def test_hardware_trigger():
    print(f"Testing GET /api/test/trigger_hardware...")
    try:
        res = requests.get(f"{BASE_URL}/api/test/trigger_hardware?alert_level=4")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_manual_trigger():
    print(f"\nTesting POST /api/manual/trigger...")
    try:
        payload = {"action_type": "call_fire", "details": "Manual Fire Alert Test"}
        res = requests.post(f"{BASE_URL}/api/manual/trigger", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_hardware_trigger()
    test_manual_trigger()
