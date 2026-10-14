import json
from pathlib import Path

root = Path("datasets/FixMyCity_Datasets/raw/water_leakage/__extracted")
json_files = [
    root / "instances_train2014.json",
    root / "val.json",
]
targets = {"H1_135.jpg", "H1_207.jpg", "H1_174.jpg"}

for path in json_files:
    if not path.exists():
        continue

    print(f"\n{'=' * 20} {path.name} {'=' * 20}")
    data = json.loads(path.read_text(encoding="utf-8"))

    categories = {
        c["id"]: c.get("name", "unknown")
        for c in data.get("categories", [])
    }
    print("Categories:", categories or "(none listed)")

    image_ids = {
        img["id"]: img["file_name"]
        for img in data.get("images", [])
        if img["file_name"] in targets
    }

    print("Target images found:", image_ids)

    for ann in data.get("annotations", []):
        if ann.get("image_id") in image_ids:
            print({
                "image": image_ids[ann["image_id"]],
                "category_id": ann.get("category_id"),
                "category": categories.get(ann.get("category_id"), "unknown"),
                "bbox": ann.get("bbox"),
                "area": ann.get("area"),
                "iscrowd": ann.get("iscrowd"),
            })

