"""Annotation parsers and converters for FixMyCity.

Supports:
- Pascal VOC XML annotations
- YOLO TXT annotations
- COCO JSON annotations (reference parser)

Validates coordinates, clamps minor floating-point drift, rejects malformed
or nonpositive boxes, filters ignored classes, and remaps classes to the
unified 5-class FixMyCity scheme.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import FULL_IMAGE_AREA_RATIO, MAX_BOX_DIM, MIN_BOX_DIM


@dataclass
class BoundingBox:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def is_valid(self) -> Tuple[bool, Optional[str]]:
        """Validate bounding box dimensions and coordinates."""
        if self.width <= MIN_BOX_DIM:
            return False, f"nonpositive width: {self.width}"
        if self.height <= MIN_BOX_DIM:
            return False, f"nonpositive height: {self.height}"
        if not (0.0 <= self.x_center <= 1.0):
            return False, f"x_center out of range [0, 1]: {self.x_center}"
        if not (0.0 <= self.y_center <= 1.0):
            return False, f"y_center out of range [0, 1]: {self.y_center}"
        if self.width > MAX_BOX_DIM:
            return False, f"width exceeds 1.0: {self.width}"
        if self.height > MAX_BOX_DIM:
            return False, f"height exceeds 1.0: {self.height}"
        return True, None

    def is_full_image(self, threshold: float = FULL_IMAGE_AREA_RATIO) -> bool:
        """Return True if the box covers almost the entire image."""
        return (self.width * self.height) >= threshold

    def to_yolo_line(self) -> str:
        """Format as standard YOLO TXT line."""
        return f"{self.class_id} {self.x_center:.6f} {self.y_center:.6f} {self.width:.6f} {self.height:.6f}"


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp float to [min_val, max_val] with tolerance."""
    if abs(val - min_val) < 1e-5:
        return min_val
    if abs(val - max_val) < 1e-5:
        return max_val
    return max(min_val, min(max_val, val))


def parse_voc_xml(
    xml_path: Path,
    actual_width: int,
    actual_height: int,
    class_map: Dict[str, int],
    ignore_classes: Optional[List[str]] = None,
) -> Tuple[List[BoundingBox], List[str]]:
    """Parse a Pascal-VOC XML file into normalized YOLO BoundingBoxes.

    Rejects nonpositive dimensions, inverted coordinates, and unmapped classes.
    """
    ignore_classes = ignore_classes or []
    boxes: List[BoundingBox] = []
    rejected: List[str] = []

    if actual_width <= 0 or actual_height <= 0:
        return [], [f"invalid image dimensions: {actual_width}x{actual_height}"]

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as exc:
        return [], [f"failed to parse XML {xml_path.name}: {exc}"]

    for obj in root.findall("object"):
        name_elem = obj.find("name")
        if name_elem is None or not name_elem.text:
            rejected.append(f"{xml_path.name}: missing object name")
            continue
        raw_name = name_elem.text.strip()

        if raw_name in ignore_classes:
            continue

        if raw_name not in class_map:
            rejected.append(f"{xml_path.name}: unmapped class '{raw_name}'")
            continue

        unified_id = class_map[raw_name]
        bndbox = obj.find("bndbox")
        if bndbox is None:
            rejected.append(f"{xml_path.name}: object missing bndbox")
            continue

        try:
            xmin = float(bndbox.find("xmin").text)
            ymin = float(bndbox.find("ymin").text)
            xmax = float(bndbox.find("xmax").text)
            ymax = float(bndbox.find("ymax").text)
        except Exception as exc:
            rejected.append(f"{xml_path.name}: error reading box coordinates: {exc}")
            continue

        if xmax <= xmin:
            rejected.append(f"{xml_path.name}: nonpositive width (xmin={xmin}, xmax={xmax})")
            continue
        if ymax <= ymin:
            rejected.append(f"{xml_path.name}: nonpositive height (ymin={ymin}, ymax={ymax})")
            continue

        # Clamp pixel coordinates to image boundary
        xmin_c = max(0.0, min(float(actual_width), xmin))
        ymin_c = max(0.0, min(float(actual_height), ymin))
        xmax_c = max(0.0, min(float(actual_width), xmax))
        ymax_c = max(0.0, min(float(actual_height), ymax))

        box_w = xmax_c - xmin_c
        box_h = ymax_c - ymin_c
        if box_w <= 0 or box_h <= 0:
            rejected.append(f"{xml_path.name}: zero dimension after boundary clamping")
            continue

        x_center = clamp(((xmin_c + xmax_c) / 2.0) / actual_width)
        y_center = clamp(((ymin_c + ymax_c) / 2.0) / actual_height)
        norm_w = clamp(box_w / actual_width)
        norm_h = clamp(box_h / actual_height)

        bbox = BoundingBox(
            class_id=unified_id,
            x_center=x_center,
            y_center=y_center,
            width=norm_w,
            height=norm_h,
        )
        valid, reason = bbox.is_valid()
        if valid:
            boxes.append(bbox)
        else:
            rejected.append(f"{xml_path.name}: invalid box: {reason}")

    return boxes, rejected


def parse_yolo_txt(
    txt_path: Path,
    class_map: Dict[str, int],
    ignore_classes: Optional[List[str]] = None,
) -> Tuple[List[BoundingBox], List[str]]:
    """Parse a YOLO TXT label file into normalized BoundingBoxes.

    Rejects nonpositive dimensions, out-of-range coords, and unmapped classes.
    """
    ignore_classes = ignore_classes or []
    boxes: List[BoundingBox] = []
    rejected: List[str] = []

    if not txt_path.exists():
        return [], [f"file not found: {txt_path.name}"]

    try:
        content = txt_path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        try:
            content = txt_path.read_text(encoding="latin-1").strip()
        except Exception as exc:
            return [], [f"encoding read error in {txt_path.name}: {exc}"]

    if not content:
        # Valid empty label file
        return [], []

    for line_idx, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            rejected.append(f"{txt_path.name}:L{line_idx}: expected >= 5 tokens, got {len(parts)}")
            continue

        cls_token = parts[0]
        if cls_token in ignore_classes:
            continue

        if cls_token not in class_map:
            rejected.append(f"{txt_path.name}:L{line_idx}: unmapped class ID '{cls_token}'")
            continue

        unified_id = class_map[cls_token]

        try:
            xc = float(parts[1])
            yc = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except ValueError as exc:
            rejected.append(f"{txt_path.name}:L{line_idx}: invalid float: {exc}")
            continue

        if w <= MIN_BOX_DIM or h <= MIN_BOX_DIM:
            rejected.append(f"{txt_path.name}:L{line_idx}: nonpositive dimensions (w={w}, h={h})")
            continue

        # Check for slight drift and clamp if safe
        if -1e-5 <= xc <= 1.0 + 1e-5:
            xc = clamp(xc)
        else:
            rejected.append(f"{txt_path.name}:L{line_idx}: x_center out of bounds: {xc}")
            continue

        if -1e-5 <= yc <= 1.0 + 1e-5:
            yc = clamp(yc)
        else:
            rejected.append(f"{txt_path.name}:L{line_idx}: y_center out of bounds: {yc}")
            continue

        if w > 1.0 + 1e-5 or h > 1.0 + 1e-5:
            rejected.append(f"{txt_path.name}:L{line_idx}: box dimensions exceed 1.0 (w={w}, h={h})")
            continue

        w = clamp(w)
        h = clamp(h)

        bbox = BoundingBox(
            class_id=unified_id,
            x_center=xc,
            y_center=yc,
            width=w,
            height=h,
        )
        valid, reason = bbox.is_valid()
        if valid:
            boxes.append(bbox)
        else:
            rejected.append(f"{txt_path.name}:L{line_idx}: invalid box: {reason}")

    return boxes, rejected


def write_yolo_labels(boxes: List[BoundingBox], output_path: Path) -> None:
    """Write BoundingBoxes to a YOLO format TXT file.

    Creates an empty file if boxes is empty (representing a negative background image).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not boxes:
        output_path.write_text("", encoding="utf-8")
        return

    lines = [box.to_yolo_line() for box in boxes]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
