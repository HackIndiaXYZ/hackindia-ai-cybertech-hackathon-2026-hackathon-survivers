from unittest.mock import patch

from ml.src.analyze_complaint import analyze_complaint


def test_successful_analysis_attaches_severity():
    detection = {
        "ok": True,
        "image": "road.jpg",
        "model": "best",
        "count": 1,
        "predictions": [
            {
                "class": "pothole",
                "class_id": 0,
                "confidence": 0.91,
                "bbox": [10.0, 20.0, 100.0, 120.0],
            }
        ],
    }

    with patch("ml.src.analyze_complaint.predict_image", return_value=detection):
        result = analyze_complaint("road.jpg")

    assert result["ok"] is True
    assert result["issue_count"] == 1
    assert result["issues"][0]["class"] == "pothole"
    assert result["issues"][0]["severity_assessment"]["severity"] == "medium"
    assert result["requires_human_review"] is True


def test_no_detections_is_successful_but_not_proof_of_safety():
    detection = {
        "ok": True,
        "image": "empty.jpg",
        "model": "best",
        "count": 0,
        "predictions": [],
    }

    with patch("ml.src.analyze_complaint.predict_image", return_value=detection):
        result = analyze_complaint("empty.jpg")

    assert result["ok"] is True
    assert result["issue_count"] == 0
    assert result["issues"] == []
    assert result["requires_human_review"] is True
    assert any("does not prove" in item for item in result["limitations"])


def test_inference_error_is_propagated():
    failure = {
        "ok": False,
        "error": "invalid_image",
        "message": "The file could not be read as an image.",
        "predictions": [],
    }

    with patch("ml.src.analyze_complaint.predict_image", return_value=failure):
        result = analyze_complaint("broken.jpg")

    assert result["ok"] is False
    assert result["error"] == "invalid_image"
    assert result["issues"] == []
    assert result["requires_human_review"] is True


def test_evidence_must_be_a_dictionary():
    try:
        analyze_complaint("road.jpg", evidence="blocks_traffic")
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError for invalid evidence")
