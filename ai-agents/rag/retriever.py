
import json
import re
from pathlib import Path
from typing import Any

from config import RAG_DATA_DIR


GUIDE_FILE = RAG_DATA_DIR / "civic_guides.json"


def load_guides() -> list[dict[str, Any]]:
    """Load locally maintained civic guidance records."""
    if not GUIDE_FILE.exists():
        return []

    with GUIDE_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Civic guides file must contain a JSON list.")

    return data


def tokenize(text: str) -> set[str]:
    """Normalize text into simple searchable terms."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_guidance(
    complaint: str,
    category: str | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant civic guides using transparent keyword overlap.

    This is a lightweight lexical retriever, not semantic embeddings.
    """
    if top_k < 1:
        return []

    query_terms = tokenize(complaint)
    guides = load_guides()
    ranked: list[tuple[int, dict[str, Any]]] = []

    for guide in guides:
        searchable_text = " ".join([
            guide.get("title", ""),
            guide.get("category", ""),
            " ".join(guide.get("keywords", [])),
            " ".join(guide.get("guidance", [])),
        ])

        guide_terms = tokenize(searchable_text)
        score = len(query_terms & guide_terms)

        # Give extra weight to exact guide keywords and category matches.
        guide_keywords = [
            keyword.lower()
            for keyword in guide.get("keywords", [])
        ]

        for keyword in guide_keywords:
            if keyword in complaint.lower():
                score += 3

        if category and guide.get("category") == category.lower():
            score += 3

        if score >= 3:
         ranked.append((score, guide))

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].get("priority") == "critical",
        ),
        reverse=True,
    )

    return [
        {**guide, "retrieval_score": score}
        for score, guide in ranked[:top_k]
    ]
