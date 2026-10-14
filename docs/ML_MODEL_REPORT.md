# FixMyCity AI — ML Model Evaluation Report

## 1. Overview

FixMyCity uses a YOLOv8n object-detection model to identify five categories of civic issues in images:

- Pothole
- Garbage
- Streetlight
- Water leakage
- Drainage

The model produces bounding boxes, class labels, and confidence scores. These predictions can support civic complaint understanding and triage. They do not independently verify a complaint or determine whether a repair is complete.

## 2. Model and Environment

| Item | Value |
|---|---|
| Model | YOLOv8n |
| Framework | Ultralytics |
| Training configuration | 40 epochs, image size 640, batch size 4 |
| Optimizer | AdamW |
| Random seed | 0 |
| Hardware | NVIDIA RTX 3050 Laptop GPU, 4 GB VRAM |
| Best checkpoint | `runs/fixmycity/yolov8n_adamw_v1/weights/best.pt` |
| Dataset configuration | `datasets/FixMyCity_Datasets/processed/fixmycity_yolo/data.yaml` |

The dataset pipeline combines multiple civic-issue datasets into five unified classes. Dataset sources and licensing terms should be reviewed before redistribution.

## 3. Held-Out Test Results

Evaluation was performed on the test split: 866 images and 1,398 labeled instances.

| Metric | Test result |
|---|---:|
| Precision | 0.778 |
| Recall | 0.716 |
| mAP@0.50 | 0.788 |
| mAP@0.50:0.95 | 0.475 |

### Per-class results

| Class | Test instances | Precision | Recall | mAP@0.50 | mAP@0.50:0.95 |
|---|---:|---:|---:|---:|---:|
| Pothole | 263 | 0.786 | 0.742 | 0.789 | 0.475 |
| Garbage | 63 | 0.822 | 0.556 | 0.679 | 0.388 |
| Streetlight | 181 | 0.662 | 0.564 | 0.624 | 0.334 |
| Water leakage | 885 | 0.821 | 0.886 | 0.921 | 0.690 |
| Drainage | 6 | 0.798 | 0.833 | 0.927 | 0.490 |

**Interpretation:** Water-leakage detection has the strongest overall class results in this test. Garbage and streetlight recall need improvement. Drainage has only six test instances, so its reported metrics are highly uncertain and should not be treated as evidence of reliable real-world performance.

## 4. Run Inference

From the repository root, activate the project's virtual environment and run:

```powershell
.\.venv\Scripts\Activate.ps1

python ml/src/predict.py --source "path\to\image.jpg"
```

For a folder of images:

```powershell
python ml/src/predict.py --source "path\to\images"
```

Optional settings include `--conf`, `--imgsz`, `--weights`, and `--output`. Run `python ml/src/predict.py --help` to inspect available arguments.

The prediction script saves annotated images and a `predictions.csv` file in its output directory. The CSV contains image paths, predicted classes, confidence scores, and bounding-box coordinates.

## 5. Re-run Test Evaluation

```powershell
python ml/src/evaluate_test.py
```

This evaluates the saved best checkpoint on the configured test split and writes evaluation artifacts under `runs/fixmycity/test_evaluation`.

## 6. Limitations and Next Steps

- Predictions are model estimates, not confirmed municipal complaints.
- Performance depends on image quality, camera angle, lighting, and similarity between training data and real-world images.
- Garbage and streetlight recall require further investigation.
- Drainage evaluation needs more representative labeled test examples.
- Review false positives and false negatives by class before changing confidence thresholds.
- Test data should remain separate from training and model-selection decisions.
- Severity scoring, duplicate-report detection, department routing, and before/after repair verification are separate capabilities; they are not established by these detection metrics alone.
- Evaluate on diverse real-world images and obtain human review before using predictions to make operational decisions.

## 7. Reproducibility

The trained weights and generated evaluation outputs are local artifacts and may be excluded from Git. Follow the repository's dataset instructions and obtain the required datasets before rerunning the pipeline. Confirm that model weights and datasets are available locally before running the commands above.
