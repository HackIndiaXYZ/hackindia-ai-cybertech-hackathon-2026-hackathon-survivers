"""FixMyCity ML entry point: Merge raw civic issue datasets into unified YOLO format.

This module exposes the unified dataset merging and validation pipeline
used to produce the 5-class FixMyCity YOLOv8 training dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.datasets.build_unified import DatasetBuilder
from scripts.datasets.validate import DatasetValidator


def merge_and_validate() -> bool:
    """Build the unified YOLO dataset and run comprehensive validation."""
    print("Running FixMyCity dataset merging pipeline...")
    builder = DatasetBuilder()
    builder.run()

    print("\nRunning FixMyCity dataset validation...")
    validator = DatasetValidator()
    return validator.run()


if __name__ == "__main__":
    success = merge_and_validate()
    sys.exit(0 if success else 1)
