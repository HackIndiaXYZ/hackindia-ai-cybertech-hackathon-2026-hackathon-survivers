import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from ml.src.repair_verification import (
    _load_image,
    compare_repair_evidence,
)


class TestRepairVerification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        before = np.zeros((100, 120, 3), dtype=np.uint8)
        after = before.copy()
        cv2.rectangle(after, (20, 20), (80, 70), (255, 255, 255), -1)

        self.before_path = self.folder / "before.jpg"
        self.after_path = self.folder / "after.jpg"

        cv2.imwrite(str(self.before_path), before)
        cv2.imwrite(str(self.after_path), after)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_image_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            _load_image(self.folder / "missing.jpg")

    def test_invalid_image_raises_error(self):
        invalid = self.folder / "invalid.jpg"
        invalid.write_text("not an image", encoding="utf-8")

        with self.assertRaises(ValueError):
            _load_image(invalid)

    @patch("ml.src.repair_verification.predict_image")
    def test_comparison_returns_evidence_not_repair_certification(
        self, mock_predict
    ):
        mock_predict.side_effect = [
            {
                "ok": True,
                "predictions": [
                    {"class": "pothole", "confidence": 0.9}
                ],
            },
            {"ok": True, "predictions": []},
        ]

        result = compare_repair_evidence(
            self.before_path,
            self.after_path,
            issue_type="pothole",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["detection_evidence"]["before_count"], 1
        )
        self.assertEqual(
            result["detection_evidence"]["after_count"], 0
        )
        self.assertFalse(result["repair_confirmed"])
        self.assertTrue(result["requires_human_review"])
        self.assertGreater(
            result["visual_change"]["changed_pixel_fraction"], 0
        )

    @patch("ml.src.repair_verification.predict_image")
    def test_inference_failure_does_not_confirm_repair(self, mock_predict):
        mock_predict.side_effect = [
            {"ok": True, "predictions": []},
            {
                "ok": False,
                "error": "inference_failed",
                "predictions": [],
            },
        ]

        result = compare_repair_evidence(
            self.before_path, self.after_path
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["repair_confirmed"])
        self.assertTrue(result["requires_human_review"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
