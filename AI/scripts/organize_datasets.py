import shutil
import os

# I use this to move my extracted data from the raw folder to the active dataset folder.
SOURCE_DIR = r"c:\Users\busto\OneDrive\Documents\MOD-EVAC-MS\AI\raw_data"
DEST_DIR = r"c:\Users\busto\OneDrive\Documents\MOD-EVAC-MS\AI\datasets"

DATASETS = ["hazard_detection", "final_eval"]

def organize():
    # I'm ensuring the destination exists before I start moving anything.
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"I've created the datasets directory: {DEST_DIR}")

    for ds in DATASETS:
        src = os.path.join(SOURCE_DIR, ds)
        dest = os.path.join(DEST_DIR, ds)

        if os.path.exists(src):
            print(f"I found the extracted dataset: {ds}")
            if os.path.exists(dest):
                print(f"My destination {dest} already exists. I'm replacing it and merging new data...")
                # I'm using a simple rmtree/move strategy here because I trust my latest extractions.
                try:
                    shutil.rmtree(dest)
                    shutil.move(src, dest)
                    print(f"I've moved {src} to {dest}")
                except Exception as e:
                    print(f"I hit an error moving {ds}: {e}")
            else:
                shutil.move(src, dest)
                print(f"I've moved {src} to {dest}")
        else:
            print(f"I haven't found {src} yet. Is extraction still running?")

if __name__ == "__main__":
    organize()
