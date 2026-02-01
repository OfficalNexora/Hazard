import os
import yaml
import glob

def process_labels(dataset_path, remove_id=2, remap_map={3: 2}):
    """
    Iterates through labels, removes remove_id, and remaps others.
    remap_map: dict of {old_id: new_id}
    """
    print(f"Processing dataset: {dataset_path}")
    
    # Find all .txt files in labels folders
    label_files = glob.glob(os.path.join(dataset_path, "**", "labels", "*.txt"), recursive=True)
    print(f"Found {len(label_files)} label files.")

    for file_path in label_files:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        modified = False
        for line in lines:
            parts = line.split()
            if not parts: continue
            
            try:
                class_id = int(parts[0])
            except ValueError:
                continue # Skip malformed lines

            if class_id == remove_id:
                modified = True
                continue # Skip this class (flood)
            
            if class_id in remap_map:
                parts[0] = str(remap_map[class_id])
                modified = True
            
            new_lines.append(" ".join(parts) + "\n")
        
        if modified:
            with open(file_path, 'w') as f:
                f.writelines(new_lines)

def update_yaml(yaml_path):
    print(f"Updating YAML: {yaml_path}")
    if not os.path.exists(yaml_path):
        print("YAML not found.")
        return

    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Update names
    # Original: 0: debris, 1: fire, 2: flood, 3: smoke
    # New: 0: debris, 1: fire, 2: smoke
    if 'names' in data:
        # Check if it's a dict or list (yolov8 dict usually)
        if isinstance(data['names'], dict):
            new_names = {0: 'debris', 1: 'fire', 2: 'smoke'}
            data['names'] = new_names
        elif isinstance(data['names'], list):
            # Assuming strictly ordered
            if len(data['names']) > 3:
                # remove index 2
                data['names'].pop(2) 
    
    # Also ensure paths are correct if needed, but primarily updating names here
    
    with open(yaml_path, 'w') as f:
        yaml.dump(data, f, sort_keys=False)

if __name__ == "__main__":
    # Define datasets to process
    base_dir = r"c:\Users\busto\OneDrive\Documents\MOD-EVAC-MS\AI\datasets"
    
    # Folders we expect to process (adjust names as they will be moved)
    datasets = ["hazard_detection", "final_eval"]
    
    for ds in datasets:
        path = os.path.join(base_dir, ds)
        if os.path.exists(path):
            process_labels(path)
            
            # Find yaml - often in root of dataset
            yaml_file = os.path.join(path, "data.yaml")
            update_yaml(yaml_file)
        else:
            print(f"Dataset path not found (yet): {path}")
