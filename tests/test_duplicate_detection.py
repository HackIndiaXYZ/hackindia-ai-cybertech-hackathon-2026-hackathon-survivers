import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from ml.src.duplicate_detection import compare_images


class TestDuplicateDetection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        image = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(image, (30, 40), (180, 170), (255, 255, 255), -1)
        cv2.circle(image, (240, 80), 35, (180, 180, 180), -1)

        self.original = self.folder / "original.jpg"
        self.resized = self.folder / "resized.jpg"
        cv2.imwrite(str(self.original), image)
        cv2.imwrite(
            str(self.resized),
            cv2.resize(image, (640, 480)),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resized_copy_is_flagged_as_similar(self):
        result = compare_images(self.original, self.resized)
        self.assertTrue(result["is_potential_duplicate"])
        self.assertTrue(result["requires_human_review"])
        self.assertGreaterEqual(result["similarity"], 0.90)

    def test_missing_image_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            compare_images(self.folder / "missing.jpg", self.original)

    def test_invalid_image_raises_error(self):
        invalid = self.folder / "invalid.jpg"
        invalid.write_text("not an image", encoding="utf-8")

        with self.assertRaises(ValueError):
            compare_images(invalid, self.original)

    def test_invalid_threshold_raises_error(self):
        with self.assertRaises(ValueError):
            compare_images(
                self.original, self.resized,
                similarity_threshold=1.5,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
