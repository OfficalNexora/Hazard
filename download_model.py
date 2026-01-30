import requests
import sys

# Hugging Face Model URL (Guessing 'best.pt' or 'yolov8s-forest-fire.pt')
# Often these repos have the .pt file in the root
urls = [
    "https://huggingface.co/touati-kamel/yolov8s-forest-fire-detection/resolve/main/best.pt",
    "https://huggingface.co/touati-kamel/yolov8s-forest-fire-detection/resolve/main/yolov8s-forest-fire-detection.pt",
    "https://huggingface.co/keremberke/yolov8n-fire-smoke-detection/resolve/main/best.pt" # Another option if first fails
]

target_file = "fire_smoke.pt"

for url in urls:
    print(f"Attempting download from: {url}")
    try:
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            print(f"Downloading to {target_file}...")
            with open(target_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Download Complete!")
            sys.exit(0)
        else:
            print(f"Failed: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

sys.exit(1)
