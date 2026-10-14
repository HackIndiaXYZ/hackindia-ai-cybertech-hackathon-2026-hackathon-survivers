"""Explainable preliminary severity estimation for FixMyCity."""

from typing import Any


VALID_ISSUES = {
    "pothole",
    "garbage",
    "streetlight",
    "water_leakage",
    "drainage",
}

BASE_SEVERITY = {
    "pothole": "medium",
    "garbage": "low",
    "streetlight": "medium",
    "water_leakage": "medium",
    "drainage": "medium",
}

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def estimate_severity(
    issue_type: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Estimate preliminary triage severity from issue type and explicit evidence.

    Evidence flags must be provided by a trusted upstream assessment.
    Missing evidence is treated as unknown, not as proof of safety.
    """
    issue = issue_type.strip().lower() if isinstance(issue_type, str) else ""

    if issue not in VALID_ISSUES:
        raise ValueError(
            f"Unsupported issue_type: {issue_type!r}. "
            f"Expected one of: {', '.join(sorted(VALID_ISSUES))}"
        )

    if evidence is None:
        evidence = {}

    if not isinstance(evidence, dict):
        raise TypeError("evidence must be a dictionary or None")

    severity = BASE_SEVERITY[issue]
    reasons = [f"Default preliminary severity for {issue.replace('_', ' ')}"]

    # Escalation requires explicit evidence; issue type alone does not prove danger.
    escalation_rules = [
        ("blocks_traffic", "high", "Issue reported as blocking traffic"),
        ("blocks_emergency_access", "critical", "Issue reported as blocking emergency access"),
        ("immediate_danger", "critical", "Immediate danger explicitly reported"),
        ("affects_multiple_households", "high", "Issue reported to affect multiple households"),
    ]

    for flag, target, reason in escalation_rules:
        value = evidence.get(flag, False)

        if not isinstance(value, bool):
            raise TypeError(f"evidence[{flag!r}] must be a boolean")

        if value and SEVERITY_ORDER[target] > SEVERITY_ORDER[severity]:
            severity = target
            reasons.append(reason)

    return {
        "issue_type": issue,
        "severity": severity,
        "level": SEVERITY_ORDER[severity],
        "method": "rule_based_preliminary_triage",
        "reasons": reasons,
        "requires_human_review": True,
    }
