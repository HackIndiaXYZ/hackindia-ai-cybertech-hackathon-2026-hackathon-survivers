from pathlib import Path
import cv2
import numpy as np

root = Path("datasets/FixMyCity_Datasets/raw/water_leakage/__extracted/train/train")
out = Path("runs/fixmycity/annotation_audit/water_variants_contact_sheet.jpg")
out.parent.mkdir(parents=True, exist_ok=True)

stems = [
    "H1_135",
    "neg_-10_H1_135",
    "neg_-5_H1_135",
    "pos_5_H1_135",
    "pos_10_H1_135",
]

tiles = []
for stem in stems:
    path = root / f"{stem}.jpg"
    image = cv2.imread(str(path))
    if image is None:
        print("Could not read:", path)
        continue

    h, w = image.shape[:2]
    label_path = Path(
        "datasets/FixMyCity_Datasets/raw/water_leakage/__extracted/"
        "water leakage data/labels/train"
    ) / f"{stem}.txt"

    if label_path.exists():
        for line in label_path.read_text(encoding="utf-8-sig").splitlines():
            p = line.split()
            if len(p) != 5:
                continue
            cls, xc, yc, bw, bh = map(float, p)
            x1, y1 = int((xc-bw/2)*w), int((yc-bh/2)*h)
            x2, y2 = int((xc+bw/2)*w), int((yc+bh/2)*h)
            cv2.rectangle(image, (x1,y1), (x2,y2), (0,0,255), 3)

    image = cv2.resize(image, (480, 360))
    cv2.putText(image, stem, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (0,255,255), 2)
    tiles.append(image)

if tiles:
    sheet = np.vstack([
        np.hstack(tiles[i:i+2] + (
            [np.zeros_like(tiles[0])] if len(tiles[i:i+2]) == 1 else []
        ))
        for i in range(0, len(tiles), 2)
    ])
    cv2.imwrite(str(out), sheet)
    print("Saved contact sheet:", out.resolve())
else:
    print("No images were generated.")
