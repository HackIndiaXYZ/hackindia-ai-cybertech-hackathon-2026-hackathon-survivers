
import re

from schemas.issue import IssueAnalysis, IssueCategory, IssueSeverity


CRITICAL_KEYWORDS = [
    "live wire",
    "exposed wire",
    "electric shock",
    "sparking wire",
    "electrical fire",
    "fallen electric pole",
    "fire",
    "gas leak",
    "building collapse",
]

HIGH_KEYWORDS = [
    "large pothole",
    "deep pothole",
    "open manhole",
    "major waterlogging",
    "heavy traffic",
    "overflowing sewer",
]

# Only explicitly supported negation patterns are removed from
# the hazard-matching text. The original complaint is preserved.
NEGATED_ELECTRICAL_PATTERNS = [
    r"\bno\s+(?:live\s+)?exposed\s+wire\b",
    r"\b(?:the\s+)?(?:live\s+)?wire\s+is\s+not\s+exposed\b",
    r"\bno\s+live\s+wire\b",
]


def remove_explicitly_negated_electrical_phrases(
    complaint: str,
) -> tuple[str, bool]:
    """
    Return text for hazard matching and whether a supported
    negated electrical phrase was found.
    """
    risk_text = complaint
    negation_detected = False

    for pattern in NEGATED_ELECTRICAL_PATTERNS:
        risk_text, count = re.subn(
            pattern,
            " ",
            risk_text,
            flags=re.IGNORECASE,
        )
        if count:
            negation_detected = True

    return risk_text, negation_detected


def classify_issue(complaint: str) -> IssueAnalysis:
    original = complaint.strip()
    text = original.lower()

    risk_text, negated_electrical_hazard = (
        remove_explicitly_negated_electrical_phrases(text)
    )

    reasoning = []

    # 1. Category classification uses the original complaint.
    if any(word in text for word in [
        "wire", "electricity", "electric pole", "power line",
        "sparking", "electric shock"
    ]):
        category = IssueCategory.ELECTRICITY

    elif any(word in text for word in [
        "pothole", "road", "street", "footpath", "manhole"
    ]):
        category = IssueCategory.ROADS

    elif any(word in text for word in [
        "garbage", "waste", "rubbish", "dustbin",
        "trash", "unclean"
    ]):
        category = IssueCategory.WASTE

    elif any(word in text for word in [
        "water supply", "water leakage", "water leak",
        "drinking water", "water shortage"
    ]):
        category = IssueCategory.WATER

    elif any(word in text for word in [
        "drain", "drainage", "sewer", "waterlogging"
    ]):
        category = IssueCategory.DRAINAGE

    elif any(word in text for word in [
        "sanitation", "dirty", "filthy"
    ]):
        category = IssueCategory.SANITATION

    elif any(word in text for word in [
        "accident", "unsafe", "crime", "danger"
    ]):
        category = IssueCategory.PUBLIC_SAFETY

    else:
        category = IssueCategory.OTHER

    # 2. Severity classification uses the text after removing
    # only explicitly supported negated electrical phrases.
    electrical_hazard = (
        "wire" in risk_text
        and any(word in risk_text for word in [
            "live", "exposed", "sparking", "electric", "electrical"
        ])
    )

    if (
        electrical_hazard
        or any(word in risk_text for word in CRITICAL_KEYWORDS)
    ):
        severity = IssueSeverity.CRITICAL
        reasoning.append("Critical safety hazard detected.")

    elif any(word in risk_text for word in HIGH_KEYWORDS):
        severity = IssueSeverity.HIGH
        reasoning.append("High-priority civic hazard detected.")

    elif any(word in risk_text for word in [
        "broken", "leaking", "overflowing", "blocked",
        "not collected", "for three days"
    ]):
        severity = IssueSeverity.MEDIUM
        reasoning.append("Moderate civic issue detected.")

    else:
        severity = IssueSeverity.LOW
        reasoning.append("No explicit high-risk keyword detected.")

    # Negation is not proof of safety. Flag for verification.
    if negated_electrical_hazard:
        reasoning.append(
            "A supported negated electrical phrase was detected; "
            "verify the actual site conditions before deciding."
        )

    # 3. Confidence and review decision.
    if category == IssueCategory.OTHER:
        confidence = 0.10
        requires_human_review = True
        reasoning.append(
            "Issue category is unclear; human review required."
        )

    elif severity in [
        IssueSeverity.CRITICAL,
        IssueSeverity.HIGH,
    ]:
        confidence = 0.95
        requires_human_review = True
        reasoning.append(
            "High-priority issues require human verification."
        )

    elif negated_electrical_hazard:
        confidence = 0.60
        requires_human_review = True

    else:
        confidence = 0.85
        requires_human_review = False

    # 4. Structured result.
    return IssueAnalysis(
        summary=original[:200] or "Empty complaint",
        category=category,
        severity=severity,
        confidence=confidence,
        location=None,
        evidence_needed=[
            "Photo or video of the issue",
            "Exact location or nearby landmark",
        ],
        reasoning=reasoning,
        requires_human_review=requires_human_review,
    )
