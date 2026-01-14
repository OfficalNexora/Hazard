from ultralytics import YOLO
import os
from dotenv import load_dotenv

def validate_model():
    print("📊 Starting Model Evaluation...")

    # Load Config
    load_dotenv()
    project_name = os.getenv("PROJECT_NAME", "hazard_project")
    exp_name = os.getenv("EXPERIMENT_NAME", "yolov8n_hazard")
    data_yaml = os.getenv("DATA_YAML_PATH", "data.yaml")

    # Construct path to best.pt
    # Assumes script is run from project root, or handles relative paths
    best_weights_path = os.path.join(project_name, exp_name, "weights", "best.pt")
    
    # If absolute path needed, use basic logic (optional, but robust)
    if not os.path.exists(best_weights_path):
        # unexpected, maybe try absolute?
        pass

    print(f"🔍 Looking for model at: {best_weights_path}")
    
    try:
        model = YOLO(best_weights_path)
    except Exception as e:
        print(f"Could not load trained model at {best_weights_path}.")
        print("Using standard 'yolov8n.pt' for demonstration.")
        model = YOLO("yolov8n.pt")

    # Run Validation
    # This runs on the 'val' dataset defined in data.yaml
    metrics = model.val(data=data_yaml)

    # Print Key Metrics
    print("\n📈 Evaluation Results:")
    print(f"mAP@50: {metrics.box.map50:.3f}")
    print(f"mAP@50-95: {metrics.box.map:.3f}")
    print(f"Precision: {metrics.box.mp:.3f}")
    print(f"Recall: {metrics.box.mr:.3f}")
    
    print("\nValidation Complete. Check runs/detect/val for confusion matrices and plots.")

if __name__ == '__main__':
    validate_model()
