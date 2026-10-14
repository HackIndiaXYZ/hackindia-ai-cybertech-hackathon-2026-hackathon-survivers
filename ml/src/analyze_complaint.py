"""Combine image detection with preliminary severity estimates.

This module does not establish real-world danger or certify civic reports.
All severity estimates require human review.
"""

from typing import Any

from ml.src.inference import predict_image
from ml.src.severity import estimate_severity


def analyze_complaint(
    image_path: str,
    confidence: float = 0.25,
    image_size: int = 640,
    weights_path: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect civic issues and attach preliminary severity estimates."""

    if evidence is not None and not isinstance(evidence, dict):
        raise TypeError("evidence must be a dictionary or None")

    detection_result = predict_image(
        image_path=image_path,
        confidence=confidence,
        image_size=image_size,
        weights_path=weights_path,
    )

    if not detection_result.get("ok", False):
        return {
            "ok": False,
            "error": detection_result.get("error", "analysis_failed"),
            "message": detection_result.get("message", "Image analysis failed."),
            "image": detection_result.get("image"),
            "issues": [],
            "requires_human_review": True,
        }

    issues = []

    for prediction in detection_result["predictions"]:
        issue_type = prediction["class"]

        issues.append({
            **prediction,
            "severity_assessment": estimate_severity(
                issue_type=issue_type,
                evidence=evidence,
            ),
        })

    return {
        "ok": True,
        "image": detection_result["image"],
        "model": detection_result["model"],
        "issue_count": len(issues),
        "issues": issues,
        "requires_human_review": True,
        "limitations": [
            "Detection does not prove that a real-world issue exists.",
            "Severity is preliminary and depends on the supplied evidence.",
            "No detections does not prove the image or location is safe.",
        ],
    }
