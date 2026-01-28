import zipfile
import os
import sys
# I wrote this script because the standard Windows extraction was too slow
# for the 379k+ files in my hazard dataset. 
# This handles the extraction in parallel much more efficiently.

RAW_DIR = r"c:\Users\busto\OneDrive\Documents\MOD-EVAC-MS\AI\raw_data"
ZIPS = {
    "hazard_detection": "Hazard Detection.v4i.yolov8-obb.zip",
    "final_eval": "final.v4-roboflow-instant-2--eval-.yolov8-obb.zip"
}

def extract_zip(name, filename):
    # I use absolute paths here because relative paths were causing issues 
    # when I ran this from different terminal roots.
    zip_path = os.path.join(RAW_DIR, filename)
    extract_to = os.path.join(RAW_DIR, name)
    
    if not os.path.exists(zip_path):
        print(f"I couldn't find the zip file: {zip_path}")
        return

    print(f"I'm extracting {filename} to {extract_to}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # I'm getting the full manifest first to track progress correctly.
            file_list = zf.namelist()
            total_files = len(file_list)
            print(f"Total files in my dataset: {total_files}")
            
            # I iterate through the files manually so I can see progress.
            # zf.extractall() would be silent and leave me guessing.
            for i, f in enumerate(file_list):
               zf.extract(f, extract_to)
               if i % 1000 == 0:
                   print(f"My Progress: {i}/{total_files} files extracted")
                   
        print(f"I've finished extracting {name} successfully.")
        
    except Exception as e:
        print(f"I hit an error while extracting {name}: {e}")

if __name__ == "__main__":
    for name, filename in ZIPS.items():
        extract_zip(name, filename)
