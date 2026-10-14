from pathlib import Path
from ultralytics import YOLO


def main():
    root = Path(__file__).resolve().parents[2]
    weights = root / "runs/fixmycity/yolov8n_adamw_v1/weights/best.pt"
    data = root / "datasets/FixMyCity_Datasets/processed/fixmycity_yolo/data.yaml"

    if not weights.is_file():
        raise FileNotFoundError(f"Model weights not found: {weights}")
    if not data.is_file():
        raise FileNotFoundError(f"Dataset config not found: {data}")

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data),
        split="test",
        imgsz=640,
        batch=4,
        workers=0,
        conf=0.001,
        plots=True,
        project=str(root / "runs/fixmycity"),
        name="test_evaluation",
        exist_ok=True,
    )

    print("\n--- HELD-OUT TEST METRICS ---")
    print(f"Precision:  {metrics.box.mp:.4f}")
    print(f"Recall:     {metrics.box.mr:.4f}")
    print(f"mAP50:      {metrics.box.map50:.4f}")
    print(f"mAP50-95:   {metrics.box.map:.4f}")
    print(f"\nArtifacts: {root / 'runs/fixmycity/test_evaluation'}")


if __name__ == "__main__":
    main()

