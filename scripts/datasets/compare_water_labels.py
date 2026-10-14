from pathlib import Path

base = Path("datasets/FixMyCity_Datasets")
source_labels = base / "raw/water_leakage/__extracted/water leakage data/labels/train"
unified_labels = base / "processed/fixmycity_yolo/labels/train"

files = [
    "H1_135.txt",
    "H1_174.txt",
    "H1_207.txt",
    "H1_23.txt",
    "H1_33.txt",
]

def read_boxes(path):
    if not path.exists():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split()
        if len(parts) == 5:
            cls, xc, yc, w, h = map(float, parts)
            rows.append((int(cls), xc, yc, w, h))
    return rows

for filename in files:
    original = read_boxes(source_labels / filename)
    unified = read_boxes(unified_labels / f"water_leakage_{filename}")

    print(f"\n--- {filename} ---")
    print("Original:", original)
    print("Unified :", unified)

    if original is None:
        print("Original label not found")
    elif unified is None:
        print("Unified label not found")
    elif len(original) != len(unified):
        print(f"BOX COUNT MISMATCH: original={len(original)}, unified={len(unified)}")
    else:
        for i, (a, b) in enumerate(zip(original, unified)):
            coords_match = all(abs(a[j] - b[j]) < 0.002 for j in range(1, 5))
            print(f"Box {i+1}: coordinates_match={coords_match}")
