"""Visual similarity checks for potential duplicate civic complaints."""

from pathlib import Path

import cv2
import numpy as np


def _load_hash(image_path: str | Path) -> np.ndarray:
    path = Path(image_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not read image: {path}")

    # Difference hash (dHash): compact representation of visual structure.
    resized = cv2.resize(image, (9, 8), interpolation=cv2.INTER_AREA)
    return resized[:, 1:] > resized[:, :-1]


def compare_images(
    image_a: str | Path,
    image_b: str | Path,
    similarity_threshold: float = 0.90,
) -> dict:
    """Compare two images and flag whether they are visually similar."""

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0.0 and 1.0")

    hash_a = _load_hash(image_a)
    hash_b = _load_hash(image_b)

    differing_bits = int(np.count_nonzero(hash_a != hash_b))
    total_bits = int(hash_a.size)
    similarity = 1.0 - (differing_bits / total_bits)

    return {
        "image_a": Path(image_a).name,
        "image_b": Path(image_b).name,
        "similarity": round(similarity, 4),
        "is_potential_duplicate": similarity >= similarity_threshold,
        "method": "perceptual_dhash",
        "requires_human_review": True,
        "warning": (
            "Visual similarity alone does not establish that complaints "
            "refer to the same incident."
        ),
    }
