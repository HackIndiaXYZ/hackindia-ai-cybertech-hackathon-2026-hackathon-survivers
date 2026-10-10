# FixMyCity — Dataset Registry & Documentation

This document describes the unified civic-issue object detection dataset for the **FixMyCity AI** platform (HackIndia 2026), covering dataset sources, collection procedures, remapping rules, directory layout, reproducibility, split distribution, licensing, and validation results.

---

## 1. Required Detection Classes

The unified FixMyCity detector targets five civic issue and infrastructure classes:

| Class ID | Class Name | Description |
|:---:|:---|:---|
| `0` | `pothole` | Road surface cavities, structural potholes, and asphalt depressions |
| `1` | `garbage` | Street waste piles, litter heaps, and uncollected municipal garbage |
| `2` | `streetlight` | Streetlight poles, illumination masts, and street-mounted light fixtures |
| `3` | `water_leakage` | Water pipe bursts, localized surface leakages, and urban water escapes |
| `4` | `drainage` | Open/missing manholes, hazardous storm drain openings, and uncovered grates |

---

## 2. Raw Source Datasets

All raw datasets were discovered and collected from Kaggle using the official Kaggle CLI.

| Category | Dataset Identifier (Kaggle) | Raw Format | License | Usability / Description |
|---|---|:---:|:---:|---|
| **pothole** | `andrewmvd/pothole-detection` | Pascal-VOC XML | [DbCL-1.0](https://opendatacommons.org/licenses/dbcl/1.0/) | 665 PNG images with localized bounding boxes for potholes. |
| **garbage** | `hammadarshad18/garbage-detection` | YOLO TXT | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | 393 images with localized bounding boxes of street garbage piles. |
| **streetlight** | `samuelayman/light-poles` | YOLO TXT | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | 910 JPEG images with localized bounding boxes of streetlight poles. |
| **water_leakage** | `lywang777/water-leakage` | YOLO TXT | [DbCL-1.0](https://opendatacommons.org/licenses/dbcl/1.0/) | 4,655 images with localized annotations of water leakages. |
| **drainage** | `cubeai/manhole-for-yolov8` | YOLO TXT | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) | 407 images annotating open manholes (class 1) vs closed manholes (class 0). |

---

## 3. Class Remapping & Semantic Audit

1. **pothole** (`andrewmvd/pothole-detection`):
   - Source XML label `<name>pothole</name>` is directly mapped to unified class `0` (`pothole`).
   - One invalid zero-width annotation in `potholes58.xml` (`xmin=273, xmax=273`) was rejected by the coordinate validator. The remaining 1,739 bounding boxes are valid.

2. **garbage** (`hammadarshad18/garbage-detection`):
   - Source labels `0`, `1`, `2` all represent piles of municipal/street garbage. Mapped to unified class `1` (`garbage`).
   - 3 unannotated images lacking `.txt` files (`9f366cd8-67a0-11e5-a3d2-40f2e96c8ad8`, `pile_183`, `plastic2`) were excluded with documented reasons.
   - 4 exact-content duplicate image pairs were deduplicated using MD5 content hashing.

3. **streetlight** (`samuelayman/light-poles`):
   - Source label `0` ('light pole') is mapped to unified class `2` (`streetlight`).
   - All bounding boxes are verified localized vertical pole detections (0 full-image boxes).
   - 2 duplicate image pairs were deduplicated.
   - 1 ambiguous stem collision (`image44.jpeg` vs `image44.jpg`) was safely resolved.

4. **water_leakage** (`lywang777/water-leakage`):
   - Source label `0` is mapped to unified class `3` (`water_leakage`).
   - Raw dataset had 148 duplicate images shared between its raw `train` and `val` directories. These were deduplicated via MD5 hashing to prevent cross-split leakage.
   - 7 invalid zero-width boxes (`w=0`, `x=0`) were rejected.
   - 100 unlabeled images from `water leakage data/test` were excluded since they lacked ground truth.

5. **drainage** (`cubeai/manhole-for-yolov8`):
   - Visual definition: open / missing manholes and hazardous open storm drains.
   - Source class `1` ('井盖打开', open manhole) is mapped to unified class `4` (`drainage`).
   - Source class `0` ('井盖关闭', closed manhole cover) represents intact, safe infrastructure and is ignored/excluded from defect annotations.
   - Images containing only class 0 are preserved as empty-label negative background images (174 train, 22 val, 7 test) to train the detector to suppress false positives on normal, closed manholes.
   - The original leakage-free 3-way split (train/valid/test) is preserved.

---

## 4. Unified YOLO Dataset Structure

The final dataset is located at:
`datasets/FixMyCity_Datasets/processed/fixmycity_yolo/`

```text
datasets/FixMyCity_Datasets/processed/fixmycity_yolo/
├── data.yaml
├── dataset_report.json
├── validation_report.json
├── images/
│   ├── train/     (4,320 images)
│   ├── val/       (901 images)
│   └── test/      (866 images)
└── labels/
    ├── train/     (4,320 txt files)
    ├── val/       (901 txt files)
    └── test/      (866 txt files)
```

---

## 5. Actual Verified Counts & Split Distribution

### Image Counts Per Split
* **Train**: 4,320 images (including 174 negative background images)
* **Val**: 901 images (including 22 negative background images)
* **Test**: 866 images (including 7 negative background images)
* **Total Images**: **6,087**
* **Total Labels**: **6,087** (100% 1:1 image-to-label pairing)
* **Total Dataset Disk Size**: ~1.62 GB

### Bounding Boxes Per Class & Split

| Class ID | Class Name | Train Boxes | Val Boxes | Test Boxes | Total Boxes | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| `0` | `pothole` | 1,204 | 272 | 263 | **1,739** | **READY** |
| `1` | `garbage` | 326 | 86 | 63 | **475** | **READY** |
| `2` | `streetlight` | 880 | 191 | 181 | **1,252** | **READY** |
| `3` | `water_leakage` | 4,206 | 924 | 885 | **6,015** | **READY** |
| `4` | `drainage` | 188 | 27 | 6 | **221** | **READY** |
| **Total** | | **6,804** | **1,500** | **1,398** | **9,702** | **ALL READY** |

---

## 6. Reproducibility Instructions

### Step 1: Raw Dataset Downloads (if starting from scratch)

```powershell
# Pothole
kaggle datasets download -d andrewmvd/pothole-detection -p datasets/FixMyCity_Datasets/raw/pothole --unzip

# Garbage
kaggle datasets download -d hammadarshad18/garbage-detection -p datasets/FixMyCity_Datasets/raw/garbage/__extracted --unzip

# Streetlight
kaggle datasets download -d samuelayman/light-poles -p datasets/FixMyCity_Datasets/raw/streetlight/__extracted --unzip

# Water Leakage
kaggle datasets download -d lywang777/water-leakage -p datasets/FixMyCity_Datasets/raw/water_leakage/__extracted --unzip

# Drainage
kaggle datasets download -d cubeai/manhole-for-yolov8 -p datasets/FixMyCity_Datasets/raw/drainage/__extracted --unzip
```

### Step 2: Build the Unified Dataset

```powershell
.\.venv\Scripts\python -m scripts.datasets.build_unified
# or
.\.venv\Scripts\python ml/src/merge_datasets.py
```

### Step 3: Run Standalone Validation

```powershell
.\.venv\Scripts\python -m scripts.datasets.validate
```

### Step 4: Run Automated Unit Tests

```powershell
.\.venv\Scripts\python -m unittest discover tests
```

---

## 7. Licensing & Attribution

All included datasets are freely available for research and hackathon use under open licenses:
* `andrewmvd/pothole-detection`: Database Contents License (DbCL) v1.0 (Make ML / Unsplash)
* `hammadarshad18/garbage-detection`: Creative Commons CC0 1.0 Universal (Public Domain)
* `samuelayman/light-poles`: Apache License 2.0
* `lywang777/water-leakage`: Database Contents License (DbCL) v1.0
* `cubeai/manhole-for-yolov8`: Creative Commons CC0 1.0 Universal (Public Domain)

---

## 8. Remaining Limitations & Recommendations

1. **Class Imbalance**:
   - `water_leakage` (6,015 boxes) and `pothole` (1,739 boxes) are well-represented.
   - `drainage` (221 boxes) and `garbage` (475 boxes) have smaller sample counts. During training, use class weighting (`cls=...` loss gain) or mosaic/mixup data augmentation.
2. **Environmental Conditions**:
   - Pothole images are primarily daytime dry road images; streetlight images include daylight and dusk conditions. In future iterations, additional night-time or rainy-weather samples should be added.
3. **Hardware Considerations**:
   - Training on the local NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM) is supported with `batch=8` or `batch=16` using `yolov8n.pt` or `yolov8s.pt` with FP16/AMP enabled.
