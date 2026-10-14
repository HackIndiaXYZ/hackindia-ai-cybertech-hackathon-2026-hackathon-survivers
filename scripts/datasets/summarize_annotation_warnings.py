"""Summarize validation warnings from the FixMyCity validation report.

Reads datasets/FixMyCity_Datasets/processed/fixmycity_yolo/validation_report.json
and prints a per-class, per-split breakdown of "full-image box detected" warnings.

The previous implementation derived a "class" key from the warning text by taking
the last whitespace token of the label filename stem, which is not a class name
(e.g. "water_leakage_H1_135"). This version re-reads the actual label files
referenced by the warnings and counts the true class IDs, so the summary is
meaningful and auditable.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from scripts.datasets.config import PROCESSED_ROOT, UNIFIED_CLASSES

REPORT_PATH = PROCESSED_ROOT / "validation_report.json"

# Matches: [train] water_leakage_H1_135.txt:L1: full-image box detected (area=0.995)
WARNING_RE = re.compile(
    r"\[(train|val|test)\]\s+(.+?\.txt):L\d+:\s*full-image box detected\s*\((?:area=)?([0-9.]+)\)"
)


def main() -> int:
    if not REPORT_PATH.exists():
        print(f"ERROR: validation report not found at {REPORT_PATH}", file=sys.stderr)
        return 1

    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    warnings = data.get("warnings", data.get("issues", []))
    if isinstance(warnings, dict):
        warnings = [f"{k}: {v}" for k, v in warnings.items()]

    print("Validation passed:", data.get("validation_passed"))
    print("Errors:", data.get("error_count"))
    print("Warnings:", data.get("warning_count"))

    # Parse warnings into (split, label_filename, area)
    parsed = []
    for item in warnings:
        text = str(item).replace("\n", " ")
        m = WARNING_RE.search(text)
        if m:
            parsed.append((m.group(1), m.group(2), m.group(3)))

    if not parsed:
        print("\nNo full-image box warnings found.")
        return 0

    # Re-read each referenced label file and count the true class IDs of the
    # full-image boxes. This is authoritative: it does not depend on the
    # filename stem or the warning text.
    per_class_per_split: dict[str, Counter] = defaultdict(Counter)
    total_per_split: Counter = Counter()
    missing_files = []

    for split, label_name, area in parsed:
        label_path = PROCESSED_ROOT / "labels" / split / label_name
        if not label_path.exists():
            missing_files.append(str(label_path))
            continue
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 5:
                continue
            try:
                cls_id = int(parts[0])
                w = float(parts[3])
                h = float(parts[4])
            except ValueError:
                continue
            if w * h >= 0.95:
                cname = UNIFIED_CLASSES.get(cls_id, f"unknown_{cls_id}")
                per_class_per_split[split][cname] += 1
                total_per_split[split] += 1

    print("\nFull-image box warnings by split and class:")
    for split in ["train", "val", "test"]:
        counts = per_class_per_split.get(split, Counter())
        total = total_per_split.get(split, 0)
        if total == 0:
            continue
        parts = ", ".join(f"{cname}={n}" for cname, n in sorted(counts.items()))
        print(f"  {split}: {total}  ({parts})")

    grand_total = sum(total_per_split.values())
    grand_by_class = Counter()
    for c in per_class_per_split.values():
        grand_by_class.update(c)
    print("\nGrand total full-image boxes:", grand_total)
    print("  by class:", dict(sorted(grand_by_class.items())))

    if missing_files:
        print("\nWARNING: referenced label files missing:", len(missing_files))
        for f in missing_files[:5]:
            print("  ", f)

    return 0


if __name__ == "__main__":
    sys.exit(main())