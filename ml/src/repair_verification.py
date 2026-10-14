"""Evidence-based before/after comparison for civic repair review."""

from pathlib import Path

import cv2
import numpy as np

from ml.src.inference import predict_image


def _load_image(image_path: str | Path) -> np.ndarray:
    path = Path(image_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")

    return image


def compare_repair_evidence(
    before_image: str | Path,
    after_image: str | Path,
    issue_type: str | None = None,
    confidence: float = 0.25,
    image_size: int = 640,
    weights_path: str | None = None,
) -> dict:
    """
    Compare before/after images and detector outputs.

    This function reports evidence only. It does not certify that a repair
    succeeded because viewpoint, lighting, and occlusion affect comparisons.
    """

    before = _load_image(before_image)
    after = _load_image(after_image)

    # Resize to a common size for a basic pixel-difference measurement.
    after_aligned_size = cv2.resize(
        after,
        (before.shape[1], before.shape[0]),
        interpolation=cv2.INTER_AREA,
    )

    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after_aligned_size, cv2.COLOR_BGR2GRAY)

    difference = cv2.absdiff(before_gray, after_gray)
    mean_difference = float(np.mean(difference)) / 255.0
    changed_pixel_fraction = float(np.mean(difference > 25))

    before_result = predict_image(
        str(before_image),
        confidence=confidence,
        image_size=image_size,
        weights_path=weights_path,
    )
    after_result = predict_image(
        str(after_image),
        confidence=confidence,
        image_size=image_size,
        weights_path=weights_path,
    )

    if not before_result.get("ok") or not after_result.get("ok"):
        return {
            "ok": False,
            "error": "inference_failed",
            "before_detection": before_result,
            "after_detection": after_result,
            "repair_confirmed": False,
            "requires_human_review": True,
        }

    def count_for_issue(result: dict) -> int:
        predictions = result["predictions"]
        if issue_type is None:
            return len(predictions)

        target = issue_type.strip().lower()
        return sum(
            1 for item in predictions
            if item["class"].strip().lower() == target
        )

    before_count = count_for_issue(before_result)
    after_count = count_for_issue(after_result)

    if before_count > after_count:
        detector_observation = "fewer_matching_detections_after"
    elif before_count < after_count:
        detector_observation = "more_matching_detections_after"
    else:
        detector_observation = "same_number_of_matching_detections"

    return {
        "ok": True,
        "before_image": Path(before_image).name,
        "after_image": Path(after_image).name,
        "issue_type": issue_type,
        "visual_change": {
            "mean_absolute_difference": round(mean_difference, 4),
            "changed_pixel_fraction": round(changed_pixel_fraction, 4),
            "interpretation": (
                "Pixel difference is sensitive to viewpoint and lighting; "
                "it is not a repair-success score."
            ),
        },
        "detection_evidence": {
            "before_count": before_count,
            "after_count": after_count,
            "observation": detector_observation,
        },
        "repair_confirmed": False,
        "requires_human_review": True,
        "limitations": [
            "Different camera angles and lighting can change image differences.",
            "Detector misses do not prove that an issue has been repaired.",
            "A human reviewer must assess the before/after evidence.",
        ],
    }
