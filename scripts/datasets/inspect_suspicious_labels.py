"""Inspect suspicious full-image boxes in the FixMyCity processed dataset.

Previously this script used a hardcoded list of five label stems, which covered
only 3.5% of the full-image boxes and only the train split. It now discovers
every full-image box (area >= 0.95) directly from the label files, optionally
filtered by split, and prints a per-class summary plus per-file details.

Usage:
    python scripts/datasets/inspect_suspicious_labels.py [--split train|val|test]
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from scripts.datasets.config import PROCESSED_ROOT, UNIFIED_CLASSES

FULL_IMAGE_AREA_RATIO = 0.95


def discover_full_image_boxes(split: str | None = None) -> dict[str, list[str]]:
    """Return {class_name: [label_stem, ...]} for every full-image box."""
    out: dict[str, list[str]] = {}
    for s in (["train", "val", "test"] if split is None else [split]):
        lbl_dir = PROCESSED_ROOT / "labels" / s
        if not lbl_dir.exists():
            continue
        for f in sorted(lbl_dir.iterdir()):
            if f.suffix != ".txt":
                continue
            for line in f.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                try:
                    cls_id = int(parts[0])
                    w = float(parts[3])
                    h = float(parts[4])
                except ValueError:
                    continue
                if w * h >= FULL_IMAGE_AREA_RATIO:
                    cname = UNIFIED_CLASSES.get(cls_id, f"unknown_{cls_id}")
                    out.setdefault(cname, []).append(f"{s}/{f.stem}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "val", "test"], default=None,
                        help="Restrict to one split (default: all)")
    args = parser.parse_args()

    boxes = discover_full_image_boxes(args.split)
    if not boxes:
        print("No full-image boxes found.")
        return 0

    total = sum(len(v) for v in boxes.values())
    print(f"Full-image boxes (area >= {FULL_IMAGE_AREA_RATIO}): {total}")
    for cname in sorted(boxes):
        print(f"  {cname}: {len(boxes[cname])}")
    print("\nPer-file details:")
    for cname in sorted(boxes):
        for stem in boxes[cname]:
            print(f"  {cname}: {stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())