from pathlib import Path

root = Path("datasets/FixMyCity_Datasets/raw/water_leakage/__extracted")
image_root = root / "train/train"
label_root = root / "water leakage data/labels/train"

files = [
    "H1_135",
    "neg_-10_H1_135",
    "neg_-5_H1_135",
    "pos_5_H1_135",
    "pos_10_H1_135",
]

for stem in files:
    image = next(
        (image_root / f"{stem}{ext}" for ext in [".jpg", ".jpeg", ".png"]
         if (image_root / f"{stem}{ext}").exists()),
        None
    )
    label = label_root / f"{stem}.txt"

    print(f"\n--- {stem} ---")
    print("Image exists:", image is not None)
    print("Label exists:", label.exists())

    if label.exists():
        print("Label contents:")
        print(label.read_text(encoding="utf-8-sig").strip() or "(empty label)")
