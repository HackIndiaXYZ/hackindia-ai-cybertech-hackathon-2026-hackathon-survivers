from functools import lru_cache
from pathlib import Path

import cv2
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = (
    ROOT / "runs" / "fixmycity" / "yolov8n_adamw_v1" / "weights" / "best.pt"
)


@lru_cache(maxsize=2)
def _load_model(weights_path: str):
    path = Path(weights_path)

    if not path.is_file():
        raise FileNotFoundError(f"Model weights not found: {path}")

    return YOLO(str(path))


def predict_image(
    image_path: str,
    confidence: float = 0.25,
    image_size: int = 640,
    weights_path: str | None = None,
) -> dict:
    """Detect civic issues in one image and return JSON-compatible results."""

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    if image_size <= 0:
        raise ValueError("image_size must be positive")

    image = Path(image_path).expanduser()

    if not image.is_file():
        return {
            "ok": False,
            "error": "image_not_found",
            "message": f"Image file not found: {image}",
            "predictions": [],
        }

    if cv2.imread(str(image)) is None:
        return {
            "ok": False,
            "error": "invalid_image",
            "message": "The file could not be read as an image.",
            "predictions": [],
        }

    weights = Path(weights_path) if weights_path else DEFAULT_WEIGHTS
    weights = weights.expanduser().resolve()

    try:
        model = _load_model(str(weights))
        result = model.predict(
            source=str(image),
            conf=confidence,
            imgsz=image_size,
            verbose=False,
        )[0]
    except FileNotFoundError:
        raise
    except Exception as exc:
        return {
            "ok": False,
            "error": "inference_failed",
            "message": str(exc),
            "predictions": [],
        }

    predictions = []

    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            predictions.append({
                "class": str(result.names[class_id]),
                "class_id": class_id,
                "confidence": round(float(box.conf.item()), 4),
                "bbox": [
                    round(float(x1), 2),
                    round(float(y1), 2),
                    round(float(x2), 2),
                    round(float(y2), 2),
                ],
            })

    return {
        "ok": True,
        "model": weights.stem,
        "image": image.name,
        "count": len(predictions),
        "predictions": predictions,
    }
