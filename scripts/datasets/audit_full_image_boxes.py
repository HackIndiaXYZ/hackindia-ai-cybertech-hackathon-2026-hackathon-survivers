import re
import json
from pathlib import Path
import cv2

ROOT = Path("datasets/FixMyCity_Datasets/processed/fixmycity_yolo")
REPORT = ROOT / "validation_report.json"
OUT = Path("runs/fixmycity/annotation_audit/suspicious_boxes")
OUT.mkdir(parents=True, exist_ok=True)

report = json.loads(REPORT.read_text(encoding="utf-8"))
warnings = report.get("warnings", report.get("issues", []))

# Support reports where warnings are stored as strings in a list.
if isinstance(warnings, dict):
    warnings = [str(k) + ": " + str(v) for k, v in warnings.items()]

pattern = re.compile(
    r"\[(train|val|test)\]\s*(.+?\.txt):L\d+: full-image box detected \(area=([0-9.]+)\)"
)

class_names = ["pothole", "garbage", "streetlight", "water_leakage", "drainage"]
saved = 0

for warning in warnings:
    match = pattern.search(str(warning).replace("\n", " "))
    if not match:
        continue

    split, label_name, area = match.groups()
    if split != "train" or saved >= 30:
        continue

    label_path = ROOT / "labels" / split / label_name
    image_path = None

    for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        candidate = ROOT / "images" / split / (label_path.stem + ext)
        if candidate.exists():
            image_path = candidate
            break

    if image_path is None or not label_path.exists():
        print("MISSING:", label_name)
        continue

    image = cv2.imread(str(image_path))
    if image is None:
        print("UNREADABLE:", image_path)
        continue

    h, w = image.shape[:2]

    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        cls, xc, yc, bw, bh = map(float, parts)
        x1 = int((xc - bw / 2) * w)
        y1 = int((yc - bh / 2) * h)
        x2 = int((xc + bw / 2) * w)
        y2 = int((yc + bh / 2) * h)

        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
        class_id = int(cls)
        class_name = class_names[class_id] if 0 <= class_id < len(class_names) else str(class_id)
        cv2.putText(image, class_name, (max(0, x1), max(20, y1 + 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.putText(image, f"box area={area}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    destination = OUT / f"{saved + 1:02d}_{label_path.stem}.jpg"
    cv2.imwrite(str(destination), image)
    print(destination)
    saved += 1

print(f"\nSaved {saved} review images to: {OUT.resolve()}")
print("No dataset labels or source images were modified.")
