# FixMyCity — Machine Learning Pipeline

This directory contains the computer-vision dataset pipeline, trained-model inference utilities, preliminary severity rules, visual duplicate-candidate detection, and before/after repair evidence comparison.

## Detection Classes

The YOLO model supports five civic issue categories:

| Class ID | Class name | Description |
|:---:|---|---|
| `0` | `pothole` | Road surface cavities and potholes |
| `1` | `garbage` | Street litter, dumping piles, and overflowing waste |
| `2` | `streetlight` | Streetlight fixtures and infrastructure |
| `3` | `water_leakage` | Visible water leakage and surface water escape |
| `4` | `drainage` | Open or missing manholes and hazardous drains |

The class configuration is defined in [`configs/classes.yaml`](configs/classes.yaml).

## Source Modules

| Module | Responsibility |
|---|---|
| `src/merge_datasets.py` | Build the unified YOLO dataset from configured sources |
| `src/predict.py` | Run predictions and save annotated outputs |
| `src/evaluate_test.py` | Evaluate the trained model on the held-out test split |
| `src/inference.py` | Reusable single-image inference returning structured predictions |
| `src/severity.py` | Assign preliminary severity using explicit, explainable rules |
| `src/duplicate_detection.py` | Compare images using difference perceptual hashing (dHash) |
| `src/repair_verification.py` | Compare before/after visual evidence and detector outputs |

## Dataset Merging and Validation

Build the unified dataset:

```powershell
.\.venv\Scripts\python.exe ml/src/merge_datasets.py
```

Alternatively, use the dataset pipeline commands:

```powershell
.\.venv\Scripts\python.exe -m scripts.datasets.build_unified
.\.venv\Scripts\python.exe -m scripts.datasets.validate
```

The generated dataset is expected at:

`datasets/FixMyCity_Datasets/processed/fixmycity_yolo/`

Dataset files are not committed by default. Review each source dataset's license and redistribution conditions before sharing it.

## Model Inference

The reusable inference function is `predict_image()` in `src/inference.py`.

```python
from ml.src.inference import predict_image

result = predict_image("path/to/civic_issue.jpg")
print(result)
```

The result includes an `ok` status, model name, image name, prediction count, and detected classes, confidence values, and bounding boxes. By default, the function looks for the locally trained checkpoint at:

`runs/fixmycity/yolov8n_adamw_v1/weights/best.pt`

Provide `weights_path` to use a different checkpoint. The checkpoint must exist locally.

## Preliminary Severity Estimation

```python
from ml.src.severity import estimate_severity

result = estimate_severity(
    "water_leakage",
    {"blocks_traffic": True},
)
print(result)
```

The rule-based module returns a preliminary severity level, reasons, and a human-review flag. Evidence flags must come from a reliable upstream assessment.

**Limitations:** These rules are prototype triage logic, not a clinically or operationally validated risk model. Detection confidence alone does not establish real-world severity. Validate and calibrate the rules with domain experts before operational use.

## Duplicate Complaint Candidates

```python
from ml.src.duplicate_detection import compare_images

result = compare_images(
    "complaint_a.jpg",
    "complaint_b.jpg",
    similarity_threshold=0.90,
)
print(result)
```

The module uses perceptual difference hashing to flag visually similar photos.

**Limitations:** Similarity does not prove that two complaints describe the same incident. Different viewpoints can hide duplicates, and similar scenes can be unrelated. Results require human review; this module does not automatically merge complaints.

## Before/After Repair Evidence

```python
from ml.src.repair_verification import compare_repair_evidence

result = compare_repair_evidence(
    "before.jpg",
    "after.jpg",
    issue_type="pothole",
)
print(result)
```

The function reports basic pixel-difference measurements and detector observations for review.

**Limitations:** Differences are sensitive to camera position, lighting, occlusion, and image alignment. Fewer detections after a repair do not prove successful resolution. The module deliberately does not certify a repair; human verification is required.

## Testing

Run the test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover dataset processing and validation, inference input handling, severity rules, duplicate image comparison, and repair-evidence handling.

## Training and Reproducibility

- Keep raw datasets, generated datasets, model weights (`*.pt`), and training outputs outside Git unless explicitly approved.
- Preserve the configured deterministic dataset-processing and split rules.
- Check for duplicate content and train/validation/test leakage before training.
- Evaluate final model performance on a held-out test set. Do not use training or validation metrics as substitutes for test results.
- Record dataset provenance, licenses, model settings, per-class metrics, and known limitations when reporting results.
