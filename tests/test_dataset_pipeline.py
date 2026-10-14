"""Unit tests for FixMyCity dataset preparation, conversion, and validation pipeline.

Runs safe verification without downloading or model training.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.datasets.config import (
    FULL_IMAGE_AREA_RATIO,
    PROJECT_ROOT,
    RAW_ROOT,
    SOURCES,
    UNIFIED_CLASSES,
)
from scripts.datasets.convert import (
    BoundingBox,
    clamp,
    parse_voc_xml,
    parse_yolo_txt,
    write_yolo_labels,
)
from scripts.datasets.build_unified import DatasetBuilder, ImageCandidate


class TestConfigAndClasses(unittest.TestCase):
    def test_unified_classes_mapping(self):
        """Verify the exact required 5-class mapping."""
        expected = {
            0: "pothole",
            1: "garbage",
            2: "streetlight",
            3: "water_leakage",
            4: "drainage",
        }
        self.assertEqual(UNIFIED_CLASSES, expected)

    def test_classes_yaml_matches(self):
        """Verify ml/configs/classes.yaml matches UNIFIED_CLASSES."""
        yaml_path = PROJECT_ROOT / "ml" / "configs" / "classes.yaml"
        self.assertTrue(yaml_path.exists())
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        names = data.get("names", {})
        for cid, cname in UNIFIED_CLASSES.items():
            self.assertEqual(names.get(cid), cname)

    def test_all_sources_configured(self):
        """Verify all 5 target categories are defined in SOURCES."""
        for cname in UNIFIED_CLASSES.values():
            self.assertIn(cname, SOURCES)
            src = SOURCES[cname]
            self.assertEqual(src.category, cname)
            self.assertTrue(src.kaggle_id)
            self.assertTrue(src.license)
            self.assertIn(src.annotation_format, ["yolo", "voc_xml", "coco_json"])


class TestBoundingBox(unittest.TestCase):
    def test_valid_box(self):
        box = BoundingBox(class_id=0, x_center=0.5, y_center=0.5, width=0.2, height=0.3)
        valid, reason = box.is_valid()
        self.assertTrue(valid)
        self.assertIsNone(reason)
        self.assertFalse(box.is_full_image())

    def test_nonpositive_dimension_rejected(self):
        box = BoundingBox(class_id=0, x_center=0.5, y_center=0.5, width=0.0, height=0.3)
        valid, reason = box.is_valid()
        self.assertFalse(valid)
        self.assertIn("nonpositive width", reason)

        box_neg = BoundingBox(class_id=0, x_center=0.5, y_center=0.5, width=0.2, height=-0.01)
        valid, reason = box_neg.is_valid()
        self.assertFalse(valid)
        self.assertIn("nonpositive height", reason)

    def test_out_of_bounds_center_rejected(self):
        box = BoundingBox(class_id=0, x_center=1.2, y_center=0.5, width=0.2, height=0.3)
        valid, reason = box.is_valid()
        self.assertFalse(valid)
        self.assertIn("x_center out of range", reason)

    def test_full_image_box_flag(self):
        box = BoundingBox(class_id=2, x_center=0.5, y_center=0.5, width=0.98, height=0.98)
        self.assertTrue(box.is_full_image(FULL_IMAGE_AREA_RATIO))

    def test_to_yolo_line(self):
        box = BoundingBox(class_id=1, x_center=0.5, y_center=0.25, width=0.1, height=0.2)
        self.assertEqual(box.to_yolo_line(), "1 0.500000 0.250000 0.100000 0.200000")


class TestParsers(unittest.TestCase):
    def test_clamp_function(self):
        self.assertEqual(clamp(1.000005), 1.0)
        self.assertEqual(clamp(-0.000005), 0.0)
        self.assertEqual(clamp(0.45), 0.45)

    def test_potholes58_invalid_box_rejection(self):
        """potholes58.xml has 3 boxes, box 3 has zero width (xmin=273, xmax=273)."""
        xml_path = RAW_ROOT / "pothole" / "annotations" / "potholes58.xml"
        if xml_path.exists():
            boxes, rejected = parse_voc_xml(xml_path, 400, 300, {"pothole": 0})
            self.assertEqual(len(boxes), 2)
            self.assertEqual(len(rejected), 1)
            self.assertIn("nonpositive width", rejected[0])



class TestProcessedDatasetValidation(unittest.TestCase):
    def test_validation_report_status(self):
        """Verify the generated validation report indicates PASSED with 0 errors."""
        import json
        from scripts.datasets.config import PROCESSED_ROOT
        report_path = PROCESSED_ROOT / "validation_report.json"
        self.assertTrue(report_path.exists(), "validation_report.json must exist")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(report.get("validation_passed"))
        self.assertEqual(report.get("error_count"), 0)
        self.assertEqual(report.get("total_images"), 6087)
        self.assertEqual(report.get("total_labels"), 6087)
        for cname in ["pothole", "garbage", "streetlight", "water_leakage", "drainage"]:
            self.assertTrue(
                report["class_readiness_assessment"][cname]["ready_for_detection_training"]
            )


class TestFullImageBoxPolicy(unittest.TestCase):
    """Focused tests for CONVERT_FULL_IMAGE_BOXES_TO_NEGATIVES and
    DatasetBuilder._filter_full_image_boxes().

    These tests do NOT touch the real dataset on disk; they exercise the
    builder's filtering logic in isolation with synthetic boxes.
    """

    def _box(self, cls: int, w: float, h: float) -> BoundingBox:
        return BoundingBox(class_id=cls, x_center=0.5, y_center=0.5, width=w, height=h)

    def _full_box(self, cls: int) -> BoundingBox:
        """A genuine full-image box: width*height >= FULL_IMAGE_AREA_RATIO."""
        # 0.98 x 0.98 = 0.9604 >= 0.95
        return BoundingBox(class_id=cls, x_center=0.5, y_center=0.5, width=0.98, height=0.98)

    def test_policy_enabled_drops_full_image_boxes(self):
        builder = DatasetBuilder()
        boxes = [
            self._box(0, 0.5, 0.5),          # ordinary pothole box
            self._full_box(1),               # full-image garbage box
        ]
        kept = builder._filter_full_image_boxes(boxes, Path("a.jpg"), "garbage")
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].class_id, 0)
        self.assertEqual(len(builder.full_image_boxes_converted), 1)
        rec = builder.full_image_boxes_converted[0]
        self.assertEqual(rec["category"], "garbage")
        self.assertEqual(rec["class_id"], 1)
        self.assertAlmostEqual(rec["area"], 0.98 * 0.98, places=6)

    def test_policy_enabled_keeps_ordinary_boxes(self):
        builder = DatasetBuilder()
        boxes = [self._box(0, 0.1, 0.1), self._box(1, 0.2, 0.3), self._box(2, 0.4, 0.4)]
        kept = builder._filter_full_image_boxes(boxes, Path("b.jpg"), "pothole")
        self.assertEqual(len(kept), 3)
        self.assertEqual([b.class_id for b in kept], [0, 1, 2])
        self.assertEqual(builder.full_image_boxes_converted, [])

    def test_policy_disabled_keeps_full_image_boxes_as_is(self):
        with patch("scripts.datasets.build_unified.CONVERT_FULL_IMAGE_BOXES_TO_NEGATIVES", False):
            builder = DatasetBuilder()
            boxes = [self._full_box(0)]
            self.assertTrue(boxes[0].is_full_image())
            kept = builder._filter_full_image_boxes(boxes, Path("c.jpg"), "drainage")
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0].class_id, 0)
            self.assertEqual(builder.full_image_boxes_converted, [])

    def test_image_retained_when_all_boxes_filtered(self):
        """The image must remain in the dataset as a negative/background example.

        _filter_full_image_boxes returns an empty list, and the caller still
        appends an ImageCandidate with empty boxes. write_yolo_labels then
        emits an empty label file, preserving the image on disk.
        """
        builder = DatasetBuilder()
        boxes = [self._full_box(3)]
        kept = builder._filter_full_image_boxes(boxes, Path("d.jpg"), "water_leakage")
        self.assertEqual(kept, [])

        cand = ImageCandidate(
            category="water_leakage",
            image_path=Path("d.jpg"),
            boxes=kept,
            image_hash="abc",
            width=100,
            height=100,
        )
        self.assertEqual(cand.boxes, [])

        with tempfile.TemporaryDirectory() as tmp:
            lbl = Path(tmp) / "neg.txt"
            write_yolo_labels(cand.boxes, lbl)
            self.assertTrue(lbl.exists())
            self.assertEqual(lbl.read_text(encoding="utf-8"), "")

    def test_mixed_multiple_annotations_partial_filter(self):
        builder = DatasetBuilder()
        boxes = [
            self._box(0, 0.05, 0.05),
            self._full_box(1),
            self._box(2, 0.3, 0.3),
            self._full_box(3),
        ]
        kept = builder._filter_full_image_boxes(boxes, Path("e.jpg"), "garbage")
        self.assertEqual([b.class_id for b in kept], [0, 2])
        self.assertEqual(len(builder.full_image_boxes_converted), 2)
        classes_converted = sorted(r["class_id"] for r in builder.full_image_boxes_converted)
        self.assertEqual(classes_converted, [1, 3])

    def test_invalid_boxes_are_not_consumed_by_filter(self):
        """Invalid boxes (already rejected upstream) must pass through the
        filter untouched; _filter_full_image_boxes only inspects area."""
        builder = DatasetBuilder()
        # A zero-width box is invalid but is_full_image() is False, so it is kept.
        zero = BoundingBox(class_id=0, x_center=0.5, y_center=0.5, width=0.0, height=0.5)
        self.assertFalse(zero.is_full_image())
        kept = builder._filter_full_image_boxes([zero], Path("f.jpg"), "pothole")
        self.assertEqual(len(kept), 1)
        self.assertIs(kept[0], zero)


if __name__ == "__main__":
    unittest.main()
