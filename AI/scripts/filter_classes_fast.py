import os
import yaml
import glob
from concurrent.futures import ProcessPoolExecutor
import time

def process_file(file_path):
    # I'm processing each file individually here. I've designed this to be idempotent 
    # so I can restart it if the lag gets too bad.
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        modified = False
        # I'm stripping out ID 2 (flood) and remapping 3 (smoke) to 2.
        # This keeps my class IDs sequential and clean.
        
        for line in lines:
            parts = line.split()
            if not parts: continue
            
            try:
                class_id = int(parts[0])
            except ValueError:
                continue 

            if class_id == 2:
                modified = True
                continue # I don't need flood data for this model.
            
            if class_id == 3:
                parts[0] = "2" # I've reindexed smoke from 3 to 2.
                modified = True
            
            new_lines.append(" ".join(parts) + "\n")
        
        if modified:
            with open(file_path, 'w') as f:
                f.writelines(new_lines)
                return 1 # I'm returning 1 if I actually changed the file.
    except Exception as e:
        print(f"Caught an error in {file_path}: {e}")
    return 0

def process_dataset_parallel(dataset_path):
    # I'm using parallel processing here because 190k files is too many for a serial loop.
    print(f"I'm scanning for labels in {dataset_path}...")
    label_files = glob.glob(os.path.join(dataset_path, "**", "labels", "*.txt"), recursive=True)
    total = len(label_files)
    print(f"I found {total} files. I'm starting the parallel transformation...")
    
    start = time.time()
    changed_count = 0
    
    # I'm leveraging all my CPU cores to speed this up.
    with ProcessPoolExecutor() as executor:
        # I track progress every 5000 files so I'm not just staring at a blank screen.
        results_in_order = executor.map(process_file, label_files)
        
        for i, res in enumerate(results_in_order):
            changed_count += res
            if (i + 1) % 5000 == 0:
                print(f"My Progress: {i + 1}/{total} files processed... (I've modified {changed_count})")
        
    end = time.time()
    print(f"I've processed all {total} files in {end - start:.2f}s. I modified {changed_count} files in total.")

def update_yaml(yaml_path):
    # I have to update my data.yaml to match the new class mapping.
    print(f"I'm updating my YAML config: {yaml_path}")
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # New Mapping: 0: debris, 1: fire, 2: smoke (Flood is gone).
        data['names'] = {0: 'debris', 1: 'fire', 2: 'smoke'}
        
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)

if __name__ == "__main__":
    # My core dataset directories.
    base_dir = r"c:\Users\busto\OneDrive\Documents\MOD-EVAC-MS\AI\datasets"
    datasets = ["hazard_detection", "final_eval"]
    
    for ds in datasets:
        path = os.path.join(base_dir, ds)
        if os.path.exists(path):
            process_dataset_parallel(path)
            update_yaml(os.path.join(path, "data.yaml"))
