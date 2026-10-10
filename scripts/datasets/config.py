"""Configuration for the FixMyCity dataset preparation pipeline.

Centralizes the unified class mapping, raw-source registry, paths and
reproducibility constants so the discover / convert / split / validate
scripts all agree on the same truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Project roots
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_ROOT = PROJECT_ROOT / "datasets" / "FixMyCity_Datasets"
RAW_ROOT = DATASETS_ROOT / "raw"
PROCESSED_ROOT = DATASETS_ROOT / "processed" / "fixmycity_yolo"

# ---------------------------------------------------------------------------
# Unified class mapping (the ONLY labels the final YOLO dataset may contain)
# ---------------------------------------------------------------------------
UNIFIED_CLASSES: Dict[int, str] = {
    0: "pothole",
    1: "garbage",
    2: "streetlight",
    3: "water_leakage",
    4: "drainage",
}
UNIFIED_NAMES: Dict[str, int] = {v: k for k, v in UNIFIED_CLASSES.items()}

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------
MIN_BOX_DIM = 1e-6          # a box with width/height below this is invalid
MAX_BOX_DIM = 1.0 + 1e-6    # boxes must stay inside [0, 1]
FULL_IMAGE_AREA_RATIO = 0.95  # >= this => treated as a full-image box
DUPLICATE_HASH_ALGO = "md5"
NEAR_DUP_PHASH_BITS = 64
NEAR_DUP_HAMMING_MAX = 8      # <= this hamming distance => near-duplicate group

# ---------------------------------------------------------------------------
# Raw source registry
# ---------------------------------------------------------------------------
@dataclass
class RawSource:
    category: str
    kaggle_id: str
    title: str
    license: str
    annotation_format: str  # "yolo" | "voc_xml" | "coco_json"
    local_subdir: str       # relative to RAW_ROOT
    class_map: Dict[str, int]   # source class name/id -> unified id
    ignore_classes: List[str] = field(default_factory=list)
    has_reliable_split: bool = False
    notes: str = ""


SOURCES: Dict[str, RawSource] = {
    "pothole": RawSource(
        category="pothole",
        kaggle_id="andrewmvd/pothole-detection",
        title="Pothole Detection",
        license="DbCL-1.0",
        annotation_format="voc_xml",
        local_subdir="pothole",
        class_map={"pothole": 0},
        notes="665 Pascal-VOC XML annotations + 665 PNG images, already present.",
    ),
    "garbage": RawSource(
        category="garbage",
        kaggle_id="hammadarshad18/garbage-detection",
        title="Garbage-Detection (Piles of Garbage)",
        license="CC0-1.0",
        annotation_format="yolo",
        local_subdir="garbage",
        class_map={"0": 1, "1": 1, "2": 1},
        notes="All three source classes are piles of street garbage -> unified 'garbage'.",
    ),
    "streetlight": RawSource(
        category="streetlight",
        kaggle_id="samuelayman/light-poles",
        title="Light poles",
        license="Apache-2.0",
        annotation_format="yolo",
        local_subdir="streetlight",
        class_map={"0": 2},
        notes="Single class 'light pole' -> unified 'streetlight'.",
    ),
    "water_leakage": RawSource(
        category="water_leakage",
        kaggle_id="lywang777/water-leakage",
        title="water-leakage",
        license="DbCL-1.0",
        annotation_format="yolo",
        local_subdir="water_leakage",
        class_map={"0": 3},
        notes="COCO-format container but labels are YOLO .txt. Single class '0' = leak. "
              "train and val reference the SAME image files (leakage) -> merged and re-split.",
    ),
    "drainage": RawSource(
        category="drainage",
        kaggle_id="cubeai/manhole-for-yolov8",
        title="Manhole for YOLOv8",
        license="CC0-1.0",
        annotation_format="yolo",
        local_subdir="drainage",
        class_map={"1": 4},
        ignore_classes=["0"],
        has_reliable_split=True,
        notes="class 0 = closed manhole (full-image box, not a defect) -> ignored. "
              "class 1 = open manhole -> unified 'drainage'. Existing train/valid/test split is "
              "leakage-free and preserved.",
    ),
}


def category_dirs(category: str) -> Dict[str, Path]:
    """Return the on-disk locations for one raw category."""
    src = SOURCES[category]
    root = RAW_ROOT / src.local_subdir
    return {
        "root": root,
        "extracted": root / "__extracted",
    }