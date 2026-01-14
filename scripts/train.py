from ultralytics import YOLO
import torch
import os
from dotenv import load_dotenv

def train_hazard_model():
    print("[Start] Starting Hazard Detection Training...")
    
    # Load Config
    load_dotenv()
    model_type = os.getenv("MODEL_TYPE", "yolov8n.pt")
    data_yaml = os.getenv("DATA_YAML_PATH", "data.yaml")
    project_name = os.getenv("PROJECT_NAME", "hazard_project")
    exp_name = os.getenv("EXPERIMENT_NAME", "yolov8n_hazard")
    epochs = int(os.getenv("EPOCHS", 50))
    img_sz = int(os.getenv("IMAGE_SIZE", 640))
    batch_sz = int(os.getenv("BATCH_SIZE", 16))

    print(f"[Start] Using Data Config: {data_yaml}")

    # Load the Model 
    model = YOLO(model_type) 

    #Check Device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"[Settings]  Using Device: {device.upper()}")

    #Train
    results = model.train(
        data=data_yaml,             # Path to data.yaml
        epochs=epochs,              # Configurable epochs
        imgsz=img_sz,               # Configurable image size
        batch=batch_sz,             # Configurable batch
        device=device,
        project=project_name,       # Project name
        name=exp_name,              # Experiment name
        exist_ok=True,              # Overwrite existing experiment
        patience=10                 # Stop early if no improvement
    )

    print("Training Complete!")
    print(f"Best Model Saved at: {results.save_dir}/weights/best.pt")

if __name__ == '__main__':
    train_hazard_model()
