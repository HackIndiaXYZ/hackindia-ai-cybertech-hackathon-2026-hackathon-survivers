import os
from pathlib import Path
import argparse
import csv

import cv2
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = Path(os.getenv("FIXMYCITY_MODEL_PATH", str(ROOT / "ml" / "deployment_weights" / "fixmycity_yolov8n_best.pt")))
DEFAULT_OUTPUT = ROOT / "runs/fixmycity/demo_predictions"


def main():
    parser = argparse.ArgumentParser(
        description="Detect five types of civic issues with the FixMyCity YOLO model."
    )
    parser.add_argument("--source", required=True, help="Image file or folder of images")
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    weights = Path(args.weights).resolve()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    if not weights.is_file():
        raise FileNotFoundError(f"Model weights not found: {weights}")
    if not source.exists():
        raise FileNotFoundError(f"Input image/source not found: {source}")
    if not 0.0 <= args.conf <= 1.0:
        raise ValueError("--conf must be between 0 and 1")

    model = YOLO(str(weights))
    results = model.predict(
        source=str(source),
        conf=args.conf,
        imgsz=args.imgsz,
        save=False,
        verbose=False,
    )

    image_dir = output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output / "predictions.csv"
    rows = []
    image_count = 0
    images_with_detections = 0
    class_counts = {name: 0 for name in model.names.values()}

    for result in results:
        image_count += 1
        image_path = Path(result.path)
        annotated = result.plot()
        output_image = image_dir / f"{image_path.stem}_prediction.jpg"
        if not cv2.imwrite(str(output_image), annotated):
            raise RuntimeError(f"Could not save annotated image: {output_image}")

        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue

        images_with_detections += 1
        for box in boxes:
            class_id = int(box.cls.item())
            class_name = model.names[class_id]
            confidence = float(box.conf.item())
            x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            rows.append({
                "image": image_path.name,
                "class": class_name,
                "confidence": round(confidence, 4),
                "x1": round(x1, 2),
                "y1": round(y1, 2),
                "x2": round(x2, 2),
                "y2": round(y2, 2),
            })

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        fields = ["image", "class", "confidence", "x1", "y1", "x2", "y2"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("\nFixMyCity prediction summary")
    print(f"Images processed: {image_count}")
    print(f"Images with detections: {images_with_detections}")
    print(f"Total detections: {len(rows)}")
    print(f"Confidence threshold: {args.conf}")
    for name, count in class_counts.items():
        print(f"  {name}: {count}")
    print(f"Annotated images: {image_dir}")
    print(f"CSV report: {csv_path}")
    print("Reminder: predictions and confidence scores are not accuracy measurements.")


if __name__ == "__main__":
    main()
