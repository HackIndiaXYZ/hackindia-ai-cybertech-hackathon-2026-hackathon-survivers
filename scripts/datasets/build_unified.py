"""Deterministic pipeline to build the unified FixMyCity YOLO dataset.

Gathers all verified raw source datasets, filters invalid boxes, converts labels,
deduplicates image content via MD5 hashes to prevent cross-split leakage, splits
deterministically using seed 42 (while preserving reliable pre-existing splits),
and exports the standard YOLO directory structure with data.yaml and dataset_report.json.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image

from .config import (
    DATASETS_ROOT,
    PROJECT_ROOT,
    PROCESSED_ROOT,
    RANDOM_SEED,
    RAW_ROOT,
    SOURCES,
    TEST_RATIO,
    TRAIN_RATIO,
    UNIFIED_CLASSES,
    VAL_RATIO,
    RawSource,
)
from .convert import BoundingBox, parse_voc_xml, parse_yolo_txt, write_yolo_labels


def compute_md5(path: Path) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ImageCandidate:
    category: str
    image_path: Path
    boxes: List[BoundingBox]
    image_hash: str
    width: int
    height: int
    preassigned_split: Optional[str] = None  # "train", "val", "test" if preserving original split
    source_notes: str = ""


class DatasetBuilder:
    def __init__(self, output_root: Path = PROCESSED_ROOT, seed: int = RANDOM_SEED) -> None:
        self.output_root = output_root
        self.seed = seed
        self.images_root = output_root / "images"
        self.labels_root = output_root / "labels"

        # Tracking metrics
        self.candidates: List[ImageCandidate] = []
        self.duplicates_skipped: List[Dict[str, str]] = []
        self.unannotated_skipped: List[Dict[str, str]] = []
        self.rejected_boxes: List[str] = []
        self.empty_label_images: List[str] = []
        self.seen_hashes: Dict[str, str] = {}  # hash -> first image path

    def collect_pothole(self) -> None:
        """Collect and convert andrewmvd/pothole-detection (VOC XML)."""
        cat = "pothole"
        src_meta = SOURCES[cat]
        cat_root = RAW_ROOT / src_meta.local_subdir
        img_dir = cat_root / "images"
        anno_dir = cat_root / "annotations"

        print(f"[{cat}] Scanning raw images and Pascal-VOC XML annotations...")
        for img_path in sorted(img_dir.glob("*.png")):
            xml_path = anno_dir / f"{img_path.stem}.xml"
            if not xml_path.exists():
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": "Missing XML annotation file",
                })
                continue

            # Verify image & get dimensions
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as exc:
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": f"Corrupted image: {exc}",
                })
                continue

            boxes, rejected = parse_voc_xml(
                xml_path,
                actual_width=w,
                actual_height=h,
                class_map=src_meta.class_map,
                ignore_classes=src_meta.ignore_classes,
            )
            self.rejected_boxes.extend(rejected)

            img_hash = compute_md5(img_path)
            if img_hash in self.seen_hashes:
                self.duplicates_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "duplicate_of": self.seen_hashes[img_hash],
                    "hash": img_hash,
                })
                continue
            self.seen_hashes[img_hash] = str(img_path)

            self.candidates.append(ImageCandidate(
                category=cat,
                image_path=img_path,
                boxes=boxes,
                image_hash=img_hash,
                width=w,
                height=h,
                source_notes=src_meta.notes,
            ))

    def collect_garbage(self) -> None:
        """Collect and convert hammadarshad18/garbage-detection (YOLO TXT)."""
        cat = "garbage"
        src_meta = SOURCES[cat]
        obj_dir = RAW_ROOT / src_meta.local_subdir / "__extracted" / "Piles-Of-Garbage" / "obj"

        print(f"[{cat}] Scanning raw images and YOLO TXT annotations...")
        img_extensions = {".jpg", ".jpeg", ".png", ".jpg".upper()}
        for img_path in sorted(obj_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue

            txt_path = obj_dir / f"{img_path.stem}.txt"
            if not txt_path.exists():
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": "Missing label TXT file in source",
                })
                continue

            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as exc:
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": f"Corrupted image: {exc}",
                })
                continue

            boxes, rejected = parse_yolo_txt(
                txt_path,
                class_map=src_meta.class_map,
                ignore_classes=src_meta.ignore_classes,
            )
            self.rejected_boxes.extend(rejected)

            img_hash = compute_md5(img_path)
            if img_hash in self.seen_hashes:
                self.duplicates_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "duplicate_of": self.seen_hashes[img_hash],
                    "hash": img_hash,
                })
                continue
            self.seen_hashes[img_hash] = str(img_path)

            self.candidates.append(ImageCandidate(
                category=cat,
                image_path=img_path,
                boxes=boxes,
                image_hash=img_hash,
                width=w,
                height=h,
                source_notes=src_meta.notes,
            ))

    def collect_streetlight(self) -> None:
        """Collect and convert samuelayman/light-poles (YOLO TXT)."""
        cat = "streetlight"
        src_meta = SOURCES[cat]
        img_dir = RAW_ROOT / src_meta.local_subdir / "__extracted" / "final light poles"
        lbl_dir = img_dir / "labels"

        print(f"[{cat}] Scanning raw images and YOLO TXT annotations...")
        seen_stems: Dict[str, Path] = {}
        for img_path in sorted(img_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue

            if img_path.stem in seen_stems:
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": f"Ambiguous label collision: shared stem '{img_path.stem}' with {seen_stems[img_path.stem].name}",
                })
                continue
            seen_stems[img_path.stem] = img_path

            txt_path = lbl_dir / f"{img_path.stem}.txt"
            if not txt_path.exists():
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": "Missing label TXT file in labels directory",
                })
                continue

            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as exc:
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": f"Corrupted image: {exc}",
                })
                continue

            boxes, rejected = parse_yolo_txt(
                txt_path,
                class_map=src_meta.class_map,
                ignore_classes=src_meta.ignore_classes,
            )
            self.rejected_boxes.extend(rejected)

            img_hash = compute_md5(img_path)
            if img_hash in self.seen_hashes:
                self.duplicates_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "duplicate_of": self.seen_hashes[img_hash],
                    "hash": img_hash,
                })
                continue
            self.seen_hashes[img_hash] = str(img_path)

            self.candidates.append(ImageCandidate(
                category=cat,
                image_path=img_path,
                boxes=boxes,
                image_hash=img_hash,
                width=w,
                height=h,
                source_notes=src_meta.notes,
            ))

    def collect_water_leakage(self) -> None:
        """Collect and convert lywang777/water-leakage (YOLO TXT).

        Merges train and val splits while deduplicating by image MD5 hash.
        """
        cat = "water_leakage"
        src_meta = SOURCES[cat]
        ext_dir = RAW_ROOT / src_meta.local_subdir / "__extracted"
        train_img_dir = ext_dir / "train" / "train"
        train_lbl_dir = ext_dir / "water leakage data" / "labels" / "train"

        val_img_dir = ext_dir / "water leakage data" / "val"
        val_lbl_dir = ext_dir / "water leakage data" / "labels" / "val"

        print(f"[{cat}] Scanning raw images and deduplicating cross-split overlaps...")
        # Gather all pairs from train and val
        pairs: List[Tuple[Path, Path]] = []
        for img_p in train_img_dir.glob("*.jpg"):
            lbl_p = train_lbl_dir / f"{img_p.stem}.txt"
            pairs.append((img_p, lbl_p))

        for img_p in val_img_dir.glob("*.jpg"):
            lbl_p = val_lbl_dir / f"{img_p.stem}.txt"
            pairs.append((img_p, lbl_p))

        for img_path, txt_path in sorted(pairs, key=lambda x: str(x[0])):
            if not txt_path.exists():
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": "Missing label TXT file",
                })
                continue

            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as exc:
                self.unannotated_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "reason": f"Corrupted image: {exc}",
                })
                continue

            boxes, rejected = parse_yolo_txt(
                txt_path,
                class_map=src_meta.class_map,
                ignore_classes=src_meta.ignore_classes,
            )
            self.rejected_boxes.extend(rejected)

            img_hash = compute_md5(img_path)
            if img_hash in self.seen_hashes:
                self.duplicates_skipped.append({
                    "category": cat,
                    "image": str(img_path),
                    "duplicate_of": self.seen_hashes[img_hash],
                    "hash": img_hash,
                })
                continue
            self.seen_hashes[img_hash] = str(img_path)

            self.candidates.append(ImageCandidate(
                category=cat,
                image_path=img_path,
                boxes=boxes,
                image_hash=img_hash,
                width=w,
                height=h,
                source_notes=src_meta.notes,
            ))

    def collect_drainage(self) -> None:
        """Collect and convert cubeai/manhole-for-yolov8 (YOLO TXT).

        Preserves original train/valid/test splits (mapping 'valid' to 'val').
        Closed manholes (class 0) are ignored; open manholes (class 1) become class 4.
        """
        cat = "drainage"
        src_meta = SOURCES[cat]
        dr_dir = RAW_ROOT / src_meta.local_subdir / "__extracted"

        print(f"[{cat}] Scanning raw images and preserving reliable original split...")
        split_map = {"train": "train", "valid": "val", "test": "test"}

        for orig_split, target_split in split_map.items():
            img_dir = dr_dir / orig_split / "images"
            lbl_dir = dr_dir / orig_split / "labels"

            for img_path in sorted(img_dir.glob("*.jpg")):
                txt_path = lbl_dir / f"{img_path.stem}.txt"
                if not txt_path.exists():
                    self.unannotated_skipped.append({
                        "category": cat,
                        "image": str(img_path),
                        "reason": "Missing label TXT file",
                    })
                    continue

                try:
                    with Image.open(img_path) as im:
                        w, h = im.size
                except Exception as exc:
                    self.unannotated_skipped.append({
                        "category": cat,
                        "image": str(img_path),
                        "reason": f"Corrupted image: {exc}",
                    })
                    continue

                boxes, rejected = parse_yolo_txt(
                    txt_path,
                    class_map=src_meta.class_map,
                    ignore_classes=src_meta.ignore_classes,
                )
                self.rejected_boxes.extend(rejected)

                img_hash = compute_md5(img_path)
                if img_hash in self.seen_hashes:
                    self.duplicates_skipped.append({
                        "category": cat,
                        "image": str(img_path),
                        "duplicate_of": self.seen_hashes[img_hash],
                        "hash": img_hash,
                    })
                    continue
                self.seen_hashes[img_hash] = str(img_path)

                self.candidates.append(ImageCandidate(
                    category=cat,
                    image_path=img_path,
                    boxes=boxes,
                    image_hash=img_hash,
                    width=w,
                    height=h,
                    preassigned_split=target_split,
                    source_notes=src_meta.notes,
                ))

    def split_and_assign(self) -> Dict[str, List[ImageCandidate]]:
        """Assign candidates to train, val, and test splits deterministically."""
        splits: Dict[str, List[ImageCandidate]] = {
            "train": [],
            "val": [],
            "test": [],
        }

        # Group candidates by category
        by_category = defaultdict(list)
        for cand in self.candidates:
            by_category[cand.category].append(cand)

        rng = random.Random(self.seed)

        for cat, cand_list in sorted(by_category.items()):
            # If candidates have preassigned splits (e.g. drainage), preserve them
            preassigned = [c for c in cand_list if c.preassigned_split is not None]
            if len(preassigned) == len(cand_list):
                for c in cand_list:
                    splits[c.preassigned_split].append(c)
                print(f"[{cat}] Preserved reliable splits: "
                      f"train={sum(1 for c in cand_list if c.preassigned_split=='train')}, "
                      f"val={sum(1 for c in cand_list if c.preassigned_split=='val')}, "
                      f"test={sum(1 for c in cand_list if c.preassigned_split=='test')}")
                continue

            # Deterministic shuffle
            shuffled = list(cand_list)
            # Sort first by hash for total determinism before random shuffle
            shuffled.sort(key=lambda c: c.image_hash)
            rng.shuffle(shuffled)

            n_total = len(shuffled)
            n_train = int(round(n_total * TRAIN_RATIO))
            n_val = int(round(n_total * VAL_RATIO))
            # Test gets whatever remains to ensure exact sum == n_total
            n_test = n_total - n_train - n_val

            train_slice = shuffled[:n_train]
            val_slice = shuffled[n_train:n_train + n_val]
            test_slice = shuffled[n_train + n_val:]

            splits["train"].extend(train_slice)
            splits["val"].extend(val_slice)
            splits["test"].extend(test_slice)

            print(f"[{cat}] Deterministic split ({TRAIN_RATIO*100:.0f}/{VAL_RATIO*100:.0f}/{TEST_RATIO*100:.0f}): "
                  f"train={len(train_slice)}, val={len(val_slice)}, test={len(test_slice)} (total={n_total})")

        return splits

    def write_dataset(self, splits: Dict[str, List[ImageCandidate]]) -> Dict:
        """Write processed images, labels, data.yaml, and dataset_report.json."""
        print(f"\nWriting processed dataset to {self.output_root}...")

        # Setup directory structure cleanly (prevent mixing stale files on rerun)
        for split_name in ["train", "val", "test"]:
            img_sdir = self.images_root / split_name
            lbl_sdir = self.labels_root / split_name
            if img_sdir.exists():
                shutil.rmtree(img_sdir)
            if lbl_sdir.exists():
                shutil.rmtree(lbl_sdir)
            img_sdir.mkdir(parents=True, exist_ok=True)
            lbl_sdir.mkdir(parents=True, exist_ok=True)

        counts_per_split: Dict[str, int] = Counter()
        images_per_cat_per_split: Dict[str, Dict[str, int]] = defaultdict(Counter)
        boxes_per_class_per_split: Dict[str, Dict[int, int]] = defaultdict(Counter)
        empty_label_counts: Dict[str, int] = Counter()

        used_filenames: Set[str] = set()

        for split_name, cand_list in splits.items():
            for cand in cand_list:
                ext = cand.image_path.suffix.lower()
                # Collision-safe filename: <category>_<original_stem><ext>
                safe_name = f"{cand.category}_{cand.image_path.stem}{ext}"
                if safe_name in used_filenames:
                    # Append short hash if duplicate stem within category
                    safe_name = f"{cand.category}_{cand.image_hash[:8]}_{cand.image_path.stem}{ext}"
                used_filenames.add(safe_name)

                dst_img = self.images_root / split_name / safe_name
                dst_lbl = self.labels_root / split_name / f"{dst_img.stem}.txt"

                # Copy image file
                shutil.copy2(cand.image_path, dst_img)

                # Write YOLO label file
                write_yolo_labels(cand.boxes, dst_lbl)

                counts_per_split[split_name] += 1
                images_per_cat_per_split[split_name][cand.category] += 1

                if not cand.boxes:
                    empty_label_counts[split_name] += 1
                    self.empty_label_images.append(str(dst_lbl))

                for box in cand.boxes:
                    boxes_per_class_per_split[split_name][box.class_id] += 1

        # Write data.yaml with absolute and relative paths
        data_yaml_content = f"""# FixMyCity Unified YOLOv8 Dataset Configuration
# Generated automatically by FixMyCity preparation pipeline

path: {self.output_root.as_posix()}
train: images/train
val: images/val
test: images/test

nc: 5
names:
  0: pothole
  1: garbage
  2: streetlight
  3: water_leakage
  4: drainage
"""
        yaml_path = self.output_root / "data.yaml"
        yaml_path.write_text(data_yaml_content, encoding="utf-8")
        print(f"Wrote data.yaml to {yaml_path}")

        # Compute total processed size
        total_bytes = sum(f.stat().st_size for f in self.output_root.rglob("*") if f.is_file())

        # Compile detailed report
        total_boxes_per_class: Dict[int, int] = Counter()
        for s_boxes in boxes_per_class_per_split.values():
            for c_id, count in s_boxes.items():
                total_boxes_per_class[c_id] += count

        report = {
            "dataset_name": "FixMyCity_Unified_YOLO",
            "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "random_seed": self.seed,
            "unified_classes": UNIFIED_CLASSES,
            "sources": {k: asdict(v) for k, v in SOURCES.items()},
            "split_distribution": dict(counts_per_split),
            "empty_label_images_per_split": dict(empty_label_counts),
            "total_images": sum(counts_per_split.values()),
            "total_bounding_boxes": sum(total_boxes_per_class.values()),
            "images_per_category_and_split": {
                s: dict(c) for s, c in images_per_cat_per_split.items()
            },
            "bounding_boxes_per_class_and_split": {
                s: {UNIFIED_CLASSES[c_id]: count for c_id, count in c.items()}
                for s, c in boxes_per_class_per_split.items()
            },
            "total_boxes_per_class": {
                UNIFIED_CLASSES[c_id]: count for c_id, count in total_boxes_per_class.items()
            },
            "duplicates_deduplicated_count": len(self.duplicates_skipped),
            "duplicates_deduplicated_list": self.duplicates_skipped,
            "unannotated_skipped_count": len(self.unannotated_skipped),
            "unannotated_skipped_list": self.unannotated_skipped,
            "rejected_invalid_boxes_count": len(self.rejected_boxes),
            "rejected_invalid_boxes_sample": self.rejected_boxes[:50],
            "dataset_disk_size_mb": round(total_bytes / (1024 * 1024), 2),
            "status": "COMPLETED",
        }

        report_path = self.output_root / "dataset_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote dataset_report.json to {report_path}")

        return report

    def run(self) -> Dict:
        """Execute full build pipeline."""
        start_time = time.time()
        print("=" * 70)
        print("FixMyCity — Unified Dataset Preparation Pipeline")
        print("=" * 70)

        # 1. Collect all categories
        self.collect_pothole()
        self.collect_garbage()
        self.collect_streetlight()
        self.collect_water_leakage()
        self.collect_drainage()

        total_collected = len(self.candidates)
        print(f"\nTotal candidate images gathered across 5 classes: {total_collected}")
        print(f"Duplicates deduplicated: {len(self.duplicates_skipped)}")
        print(f"Unannotated/corrupted skipped: {len(self.unannotated_skipped)}")
        print(f"Invalid boxes rejected: {len(self.rejected_boxes)}")

        # 2. Split deterministically
        splits = self.split_and_assign()

        # 3. Export to processed YOLO folder
        report = self.write_dataset(splits)

        elapsed = time.time() - start_time
        print(f"\nPipeline completed in {elapsed:.2f} seconds.")
        print(f"Processed dataset location: {self.output_root}")
        print("=" * 70)
        return report


def main() -> None:
    builder = DatasetBuilder()
    builder.run()


if __name__ == "__main__":
    main()
