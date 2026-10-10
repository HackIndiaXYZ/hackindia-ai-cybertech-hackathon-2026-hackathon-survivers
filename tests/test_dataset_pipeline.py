"""Unit tests for FixMyCity dataset preparation, conversion, and validation pipeline.

Runs safe verification without downloading or model training.
"""

from __future__ import annotations

import unittest
from pathlib import Path

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
)


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


if __name__ == "__main__":
    unittest.main()
