import cv2
import os
from dotenv import load_dotenv

def extract_frames():
    """
    Extract frames from a video file and save to raw_data folder.
    """
    load_dotenv()
    
    # --- CONFIGURATION ---
    VIDEO_PATH = "videos/sample.mp4"  # Change to your video path
    OUTPUT_DIR = os.getenv("RAW_DATA_DIR", "raw_data")
    FRAME_INTERVAL = 30  # Save every Nth frame (30 = ~1 frame/sec at 30fps)
    # ---------------------
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Video not found: {VIDEO_PATH}")
        print("Edit VIDEO_PATH in this script to point to your video file.")
        return
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📹 Video: {VIDEO_PATH}")
    print(f"   FPS: {fps}, Total Frames: {total_frames}")
    print(f"   Saving every {FRAME_INTERVAL} frames...")
    
    frame_count = 0
    saved_count = 0
    video_name = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % FRAME_INTERVAL == 0:
            filename = f"{OUTPUT_DIR}/{video_name}_frame_{saved_count:04d}.jpg"
            cv2.imwrite(filename, frame)
            saved_count += 1
        
        frame_count += 1
    
    cap.release()
    print(f"✅ Saved {saved_count} frames to '{OUTPUT_DIR}/'")
    print(f"   Now upload these to Roboflow for annotation!")

if __name__ == "__main__":
    extract_frames()
