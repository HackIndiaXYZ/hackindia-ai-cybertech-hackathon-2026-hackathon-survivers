# FixMyCity — Machine Learning Pipeline

This directory contains the machine learning components, configurations, and pipeline code for the FixMyCity civic-issue detection system.

## Detection Classes

FixMyCity detects 5 civic hazard and infrastructure issue categories:

| Class ID | Class Name | Description |
|:---:|---|---|
| `0` | `pothole` | Road surface cavities, structural depressions, and asphalt potholes |
| `1` | `garbage` | Street litter, illegal dumping piles, and overflowing waste |
| `2` | `streetlight` | Streetlight poles, fixtures, and urban lighting infrastructure |
| `3` | `water_leakage` | Active water pipe bursts, localized puddle leakages, and surface water escapes |
| `4` | `drainage` | Open / missing manholes, hazardous storm drains, and uncovered grates |

The class configuration is defined in [`ml/configs/classes.yaml`](file:///C:/Project/Fix%20My%20city/ml/configs/classes.yaml).

## Directory Structure

```text
ml/
├── configs/
│   └── classes.yaml           # Ground truth 5-class mapping
├── notebooks/                 # Experimentation notebooks (Colab-ready)
├── src/
│   └── merge_datasets.py      # Entry point to merge raw sources into unified YOLO dataset
└── README.md                  # This file
```

## Dataset Merging and Validation

To build the unified dataset from raw source datasets:

```powershell
.\.venv\Scripts\python ml/src/merge_datasets.py
```

Or via the scripts package:

```powershell
.\.venv\Scripts\python -m scripts.datasets.build_unified
.\.venv\Scripts\python -m scripts.datasets.validate
```

The resulting unified YOLO dataset is generated at:
`datasets/FixMyCity_Datasets/processed/fixmycity_yolo/`

## Training Rules

- Datasets and model weights (`*.pt`) remain outside Git tracking.
- Preprocessing is fully deterministic (`seed=42`).
- Content hash deduplication ensures zero leakage between `train`, `val`, and `test` splits.
