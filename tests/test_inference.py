import tempfile
import unittest
from pathlib import Path

from ml.src.inference import predict_image


class TestInference(unittest.TestCase):
    def test_missing_image_returns_error(self):
        result = predict_image("this_image_does_not_exist.jpg")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "image_not_found")
        self.assertEqual(result["predictions"], [])

    def test_invalid_image_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_file = Path(tmp) / "invalid.jpg"
            bad_file.write_text("not an image", encoding="utf-8")
            result = predict_image(str(bad_file))
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "invalid_image")

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_image("anything.jpg", confidence=1.5)

    def test_invalid_image_size_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_image("anything.jpg", image_size=0)


if __name__ == "__main__":
    unittest.main()
