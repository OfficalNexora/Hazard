import os
import shutil
import random
from glob import glob
from dotenv import load_dotenv

def organize_dataset():
    # CONFIGURATION (Loaded from .env) 
    load_dotenv()
    
    # Get paths from env, default to current structure if not found
    raw_data_env = os.getenv("RAW_DATA_DIR", "raw_data")
    dataset_env = os.getenv("DATASET_DIR", "datasets")
    
    # Resolve absolute paths based on where script is run (assumed run from project root)
    # If run from scripts/, we go up one level.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    SOURCE_DIR = os.path.join(project_root, raw_data_env)
    BASE_DIR = os.path.join(project_root, dataset_env)
    
    # Split ratio
    TRAIN_RATIO = 0.8  # 80% train, 20% validation
    
    # Supported image extensions
    EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    # ---------------------

    print(f"🔄 Scanning {SOURCE_DIR} for images...")

    # 1. Gather all images
    images = []
    for ext in EXTENSIONS:
        images.extend(glob(os.path.join(SOURCE_DIR, ext)))
    
    if not images:
        print(f"⚠️ No images found in {SOURCE_DIR}. Create the folder and put your files there first!")
        return

    # 2. Shuffle and Split
    random.shuffle(images)
    split_index = int(len(images) * TRAIN_RATIO)
    train_images = images[:split_index]
    val_images = images[split_index:]

    print(f"Found {len(images)} images. Splitting: {len(train_images)} Train, {len(val_images)} Val.")

    # 3. Move Files
    def move_files(file_list, split_name):
        for img_path in file_list:
            filename = os.path.basename(img_path)
            name_no_ext = os.path.splitext(filename)[0]
            
            # Paths
            src_img = img_path
            src_txt = os.path.join(SOURCE_DIR, name_no_ext + ".txt")
            
            dst_img_dir = os.path.join(BASE_DIR, "images", split_name)
            dst_lbl_dir = os.path.join(BASE_DIR, "labels", split_name)
            
            # Move Image
            shutil.copy2(src_img, os.path.join(dst_img_dir, filename))
            
            # Move Label (if exists)
            if os.path.exists(src_txt):
                shutil.copy2(src_txt, os.path.join(dst_lbl_dir, name_no_ext + ".txt"))
            else:
                # No label file? That's fine! 
                # YOLO treats images with no corresponding label file as "background" (Pure Negative).
                # This is exactly how you safely include "images with no hazards".
                pass

    print("🚚 Copying Train files...")
    move_files(train_images, "train")
    
    print("🚚 Copying Val files...")
    move_files(val_images, "val")

    print(f"\n✅ Done! Your dataset is organized in '{BASE_DIR}'.")
    print(f"You can now run 'python scripts/train.py'")

if __name__ == "__main__":
    # Create source dir if not exists just to be helpful
    src = "C:/Users/busto/OneDrive/Documents/MOD-EVAC-MS/raw_data"
    if not os.path.exists(src):
        os.makedirs(src)
        print(f"📁 Created '{src}'. Please put all your images and .txt files there and run this script again.")
    else:
        organize_dataset()
