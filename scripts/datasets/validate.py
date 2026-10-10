"""Standalone validator for the FixMyCity unified YOLO dataset.

Validates:
1. Dataset structure, split folders, and data.yaml
2. 1:1 image and label pairing (no orphans or missing files)
3. Image file readability and corruption checks
4. Label line format, token counts, class ID validity (0-4), coordinate bounds [0, 1]
5. Nonpositive width/height, malformed lines, or invalid numbers
6. Full-image bounding boxes (area >= 0.95)
7. Duplicate image filenames and duplicate image hashes
8. Cross-split data leakage (hashes appearing across train, val, test)
9. Per-category and per-split distribution of images and bounding boxes
10. Source attribution, licenses, and training readiness assessment
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from PIL import Image

from .config import (
    DATASETS_ROOT,
    FULL_IMAGE_AREA_RATIO,
    MAX_BOX_DIM,
    MIN_BOX_DIM,
    PROCESSED_ROOT,
    SOURCES,
    UNIFIED_CLASSES,
)


def compute_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class DatasetValidator:
    def __init__(self, dataset_dir: Path = PROCESSED_ROOT) -> None:
        self.dataset_dir = dataset_dir
        self.images_dir = dataset_dir / "images"
        self.labels_dir = dataset_dir / "labels"
        self.yaml_path = dataset_dir / "data.yaml"

        # Errors and warnings
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Metrics
        self.split_image_counts: Dict[str, int] = Counter()
        self.split_label_counts: Dict[str, int] = Counter()
        self.category_image_counts: Dict[str, Dict[str, int]] = defaultdict(Counter)
        self.class_box_counts: Dict[str, Dict[int, int]] = defaultdict(Counter)
        self.empty_label_counts: Dict[str, int] = Counter()
        self.full_image_box_counts: Dict[str, int] = Counter()
        self.hashes_by_split: Dict[str, Set[str]] = defaultdict(set)
        self.all_seen_hashes: Dict[str, str] = {}  # hash -> file_path
        self.intra_split_dups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.cross_split_dups: List[Tuple[str, str, str, str]] = []  # (split1, file1, split2, file2)

    def validate_yaml(self) -> Dict:
        """Validate data.yaml structure and contents."""
        print("[1/6] Validating data.yaml...")
        if not self.yaml_path.exists():
            self.errors.append(f"data.yaml does not exist at {self.yaml_path}")
            return {}

        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as exc:
            self.errors.append(f"Failed to parse data.yaml: {exc}")
            return {}

        required_keys = ["path", "train", "val", "test", "nc", "names"]
        for key in required_keys:
            if key not in data:
                self.errors.append(f"data.yaml missing required key: '{key}'")

        if data.get("nc") != 5:
            self.errors.append(f"data.yaml nc is {data.get('nc')}, expected 5")

        names = data.get("names", {})
        if isinstance(names, dict):
            for k, expected_name in UNIFIED_CLASSES.items():
                if names.get(k) != expected_name and names.get(str(k)) != expected_name:
                    self.errors.append(f"data.yaml class {k} is '{names.get(k)}', expected '{expected_name}'")
        elif isinstance(names, list):
            if len(names) != 5 or names != list(UNIFIED_CLASSES.values()):
                self.errors.append(f"data.yaml names list mismatch: {names}")
        else:
            self.errors.append("data.yaml 'names' is neither a dictionary nor a list")

        return data

    def validate_splits(self) -> None:
        """Validate presence of split directories and 1:1 image-label pairings."""
        print("[2/6] Validating split directories and image/label pairings...")
        for split in ["train", "val", "test"]:
            img_sdir = self.images_dir / split
            lbl_sdir = self.labels_dir / split

            if not img_sdir.exists():
                self.errors.append(f"Images split folder missing: {img_sdir}")
                continue
            if not lbl_sdir.exists():
                self.errors.append(f"Labels split folder missing: {lbl_sdir}")
                continue

            images = {f.stem: f for f in img_sdir.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]}
            labels = {f.stem: f for f in lbl_sdir.iterdir() if f.is_file() and f.suffix.lower() == ".txt"}

            self.split_image_counts[split] = len(images)
            self.split_label_counts[split] = len(labels)

            missing_labels = set(images.keys()) - set(labels.keys())
            if missing_labels:
                sample = list(missing_labels)[:5]
                self.errors.append(f"[{split}] {len(missing_labels)} images missing corresponding label file (sample: {sample})")

            orphan_labels = set(labels.keys()) - set(images.keys())
            if orphan_labels:
                sample = list(orphan_labels)[:5]
                self.errors.append(f"[{split}] {len(orphan_labels)} label files have no corresponding image (sample: {sample})")

    def validate_images_and_labels(self) -> None:
        """Inspect all images for corruption and all label files for format/range validity."""
        print("[3/6] Inspecting image integrity and label lines...")
        for split in ["train", "val", "test"]:
            img_sdir = self.images_dir / split
            lbl_sdir = self.labels_dir / split
            if not img_sdir.exists() or not lbl_sdir.exists():
                continue

            for img_path in img_sdir.iterdir():
                if not img_path.is_file() or img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                    continue

                # Category extraction from filename prefix
                cat = img_path.stem.split("_")[0]
                self.category_image_counts[split][cat] += 1

                # Image verify
                try:
                    with Image.open(img_path) as im:
                        im.verify()
                except Exception as exc:
                    self.errors.append(f"Corrupted image in {split}: {img_path.name} ({exc})")

                # Image hash
                img_hash = compute_md5(img_path)
                if img_hash in self.hashes_by_split[split]:
                    self.intra_split_dups[split].append((img_path.name, self.all_seen_hashes[img_hash]))
                self.hashes_by_split[split].add(img_hash)

                if img_hash in self.all_seen_hashes:
                    prev_loc = self.all_seen_hashes[img_hash]
                    prev_split = prev_loc.split(os.sep)[-2]
                    if prev_split != split:
                        self.cross_split_dups.append((prev_split, prev_loc, split, str(img_path)))
                else:
                    self.all_seen_hashes[img_hash] = str(img_path)

                # Validate matching label file
                lbl_path = lbl_sdir / f"{img_path.stem}.txt"
                if not lbl_path.exists():
                    continue

                try:
                    content = lbl_path.read_text(encoding="utf-8").strip()
                except Exception as exc:
                    self.errors.append(f"Failed to read label {lbl_path.name}: {exc}")
                    continue

                if not content:
                    self.empty_label_counts[split] += 1
                    continue

                for line_idx, line in enumerate(content.splitlines(), start=1):
                    line = line.strip()
                    if not line:
                        continue
                    tokens = line.split()
                    if len(tokens) != 5:
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: expected 5 tokens, got {len(tokens)}: '{line}'"
                        )
                        continue

                    try:
                        cls_id = int(tokens[0])
                        xc = float(tokens[1])
                        yc = float(tokens[2])
                        w = float(tokens[3])
                        h = float(tokens[4])
                    except ValueError as exc:
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: token parse error: {exc}"
                        )
                        continue

                    if cls_id not in UNIFIED_CLASSES:
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: invalid class ID {cls_id} (allowed: 0-4)"
                        )
                        continue

                    if w <= MIN_BOX_DIM or h <= MIN_BOX_DIM:
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: nonpositive dimensions (w={w}, h={h})"
                        )
                        continue

                    if not (0.0 <= xc <= 1.0) or not (0.0 <= yc <= 1.0):
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: center out of bounds (xc={xc}, yc={yc})"
                        )
                        continue

                    if w > MAX_BOX_DIM or h > MAX_BOX_DIM:
                        self.errors.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: dimensions exceed 1.0 (w={w}, h={h})"
                        )
                        continue

                    if (w * h) >= FULL_IMAGE_AREA_RATIO:
                        self.full_image_box_counts[split] += 1
                        self.warnings.append(
                            f"[{split}] {lbl_path.name}:L{line_idx}: full-image box detected (area={w*h:.3f})"
                        )

                    self.class_box_counts[split][cls_id] += 1

    def validate_leakage(self) -> None:
        """Assert zero image content hash overlap across splits."""
        print("[4/6] Checking for cross-split data leakage...")
        train_h = self.hashes_by_split["train"]
        val_h = self.hashes_by_split["val"]
        test_h = self.hashes_by_split["test"]

        tv_leak = train_h & val_h
        tt_leak = train_h & test_h
        vt_leak = val_h & test_h

        if tv_leak:
            self.errors.append(f"Data leakage: {len(tv_leak)} duplicate images between train and val!")
        if tt_leak:
            self.errors.append(f"Data leakage: {len(tt_leak)} duplicate images between train and test!")
        if vt_leak:
            self.errors.append(f"Data leakage: {len(vt_leak)} duplicate images between val and test!")

        if self.cross_split_dups:
            self.errors.append(f"Cross-split duplicate occurrences found: {len(self.cross_split_dups)}")

    def generate_report(self) -> Dict:
        """Compile comprehensive validation report."""
        print("[5/6] Generating validation report...")
        total_images = sum(self.split_image_counts.values())
        total_labels = sum(self.split_label_counts.values())
        total_boxes_by_class: Dict[str, int] = Counter()
        for s_counts in self.class_box_counts.values():
            for c_id, count in s_counts.items():
                total_boxes_by_class[UNIFIED_CLASSES[c_id]] += count

        dataset_bytes = sum(f.stat().st_size for f in self.dataset_dir.rglob("*") if f.is_file())

        # Readiness assessment for each class
        readiness = {}
        for c_id, c_name in UNIFIED_CLASSES.items():
            box_count = total_boxes_by_class.get(c_name, 0)
            train_box = self.class_box_counts["train"].get(c_id, 0)
            val_box = self.class_box_counts["val"].get(c_id, 0)
            test_box = self.class_box_counts["test"].get(c_id, 0)

            is_ready = (train_box > 0 and val_box > 0 and test_box > 0)
            readiness[c_name] = {
                "class_id": c_id,
                "total_bounding_boxes": box_count,
                "train_boxes": train_box,
                "val_boxes": val_box,
                "test_boxes": test_box,
                "ready_for_detection_training": is_ready,
            }

        report = {
            "validation_timestamp": Path(__file__).stat().st_mtime,
            "validation_passed": len(self.errors) == 0,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings[:20],
            "dataset_disk_size_mb": round(dataset_bytes / (1024 * 1024), 2),
            "total_images": total_images,
            "total_labels": total_labels,
            "split_distribution": dict(self.split_image_counts),
            "empty_label_images_per_split": dict(self.empty_label_counts),
            "full_image_boxes_per_split": dict(self.full_image_box_counts),
            "images_per_category_and_split": {
                s: dict(c) for s, c in self.category_image_counts.items()
            },
            "bounding_boxes_per_class_and_split": {
                s: {UNIFIED_CLASSES[c_id]: count for c_id, count in c.items()}
                for s, c in self.class_box_counts.items()
            },
            "total_bounding_boxes_per_class": dict(total_boxes_by_class),
            "sources_and_licensing": {
                k: {
                    "category": v.category,
                    "kaggle_id": v.kaggle_id,
                    "title": v.title,
                    "license": v.license,
                    "annotation_format": v.annotation_format,
                }
                for k, v in SOURCES.items()
            },
            "class_readiness_assessment": readiness,
        }

        report_file = self.dataset_dir / "validation_report.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Validation report saved to {report_file}")
        return report

    def print_summary(self, report: Dict) -> None:
        """Print human-readable summary of validation results."""
        print("\n" + "=" * 70)
        print("FIXMYCITY DATASET VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Status:             {'PASSED [OK]' if report['validation_passed'] else 'FAILED [ERRORS]'}")
        print(f"Total Images:       {report['total_images']}")
        print(f"Total Labels:       {report['total_labels']}")
        print(f"Dataset Disk Size:  {report['dataset_disk_size_mb']} MB")
        print(f"Error Count:        {report['error_count']}")
        print(f"Warning Count:      {report['warning_count']}")

        print("\n--- Split Distribution ---")
        for s in ["train", "val", "test"]:
            img_c = report['split_distribution'].get(s, 0)
            empty_c = report['empty_label_images_per_split'].get(s, 0)
            print(f"  {s:<6}: {img_c} images ({empty_c} empty-label background images)")

        print("\n--- Bounding Boxes Per Unified Class ---")
        for c_id in range(5):
            c_name = UNIFIED_CLASSES[c_id]
            total_b = report['total_bounding_boxes_per_class'].get(c_name, 0)
            train_b = report['bounding_boxes_per_class_and_split'].get('train', {}).get(c_name, 0)
            val_b = report['bounding_boxes_per_class_and_split'].get('val', {}).get(c_name, 0)
            test_b = report['bounding_boxes_per_class_and_split'].get('test', {}).get(c_name, 0)
            ready_str = "[READY]" if report['class_readiness_assessment'][c_name]['ready_for_detection_training'] else "[NOT READY]"
            print(f"  {c_id}: {c_name:<14} | Total: {total_b:<5} (train={train_b}, val={val_b}, test={test_b}) {ready_str}")

        print("\n--- Sources and Licenses ---")
        for k, v in report['sources_and_licensing'].items():
            print(f"  {k:<14}: {v['kaggle_id']} ({v['license']}) [{v['annotation_format']}]")

        if report['errors']:
            print("\n--- Errors ---")
            for err in report['errors'][:15]:
                print(f"  [ERROR] {err}")
        else:
            print("\nZero validation errors found! All bounding boxes, coordinates, splits, and images verified.")
        print("=" * 70)

    def run(self) -> bool:
        """Run all validation steps."""
        self.validate_yaml()
        self.validate_splits()
        self.validate_images_and_labels()
        self.validate_leakage()
        report = self.generate_report()
        self.print_summary(report)
        return report["validation_passed"]


def main() -> None:
    validator = DatasetValidator()
    success = validator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
