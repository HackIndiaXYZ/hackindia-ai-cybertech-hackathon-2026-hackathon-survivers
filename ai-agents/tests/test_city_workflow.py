import pytest

from agents.issue_classifier import classify_issue
from schemas.issue import IssueAnalysis, IssueCategory, IssueSeverity
from workflow.city_workflow import (
    gemini_analysis_node,
    safety_review_node,
)


def make_analysis(
    category=IssueCategory.ROADS,
    severity=IssueSeverity.LOW,
    confidence=0.90,
    requires_human_review=False,
):
    return IssueAnalysis(
        summary="Test civic complaint",
        category=category,
        severity=severity,
        confidence=confidence,
        reasoning=["Test analysis"],
        requires_human_review=requires_human_review,
    )


def test_exposed_electrical_wire_is_critical():
    result = classify_issue(
        "There is a live exposed electrical wire across a busy road"
    )

    assert result.category == IssueCategory.ELECTRICITY
    assert result.severity == IssueSeverity.CRITICAL
    assert result.requires_human_review is True


def test_vague_complaint_requires_review():
    result = classify_issue("Please help with this issue")

    assert result.category == IssueCategory.OTHER
    assert result.requires_human_review is True


def test_safety_review_preserves_higher_rule_severity():
    rule_result = classify_issue("There is a live exposed electrical wire")
    ai_result = make_analysis()

    result = safety_review_node({
        "complaint": "There is a live exposed electrical wire",
        "rule_analysis": rule_result,
        "ai_analysis": ai_result,
    })

    final_analysis = result["final_analysis"]

    assert final_analysis.severity == IssueSeverity.CRITICAL
    assert final_analysis.requires_human_review is True


def test_gemini_failure_uses_rule_fallback(monkeypatch):
    rule_result = classify_issue(
        "There is a live exposed electrical wire"
    )

    def fake_gemini(_complaint):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(
        "workflow.city_workflow.analyze_with_gemini",
        fake_gemini,
    )

    result = gemini_analysis_node({
        "complaint": "There is a live exposed electrical wire",
        "rule_analysis": rule_result,
    })

    assert result["ai_analysis"].severity == IssueSeverity.CRITICAL
    assert result["ai_analysis"].requires_human_review is True
    assert "quota exceeded" in result["error"].lower()


def test_low_risk_analysis_does_not_force_review():
    rule_result = make_analysis()
    ai_result = make_analysis()

    result = safety_review_node({
        "complaint": "A small road issue",
        "rule_analysis": rule_result,
        "ai_analysis": ai_result,
    })

    assert result["final_analysis"].severity == IssueSeverity.LOW
    assert result["final_analysis"].requires_human_review is False

@pytest.mark.parametrize(
    "complaint",
    [
        "There is no exposed wire here",
        "The live wire is not exposed",
    ],
)
def test_explicitly_negated_wire_hazard_is_not_automatically_critical(
    complaint,
):
    result = classify_issue(complaint)

    assert result.category == IssueCategory.ELECTRICITY
    assert result.severity != IssueSeverity.CRITICAL

def test_negated_wire_does_not_hide_a_separate_gas_leak():
    result = classify_issue(
        "There is no exposed wire here, but there is a gas leak"
    )

    assert result.severity == IssueSeverity.CRITICAL
    assert result.requires_human_review is True

def test_ai_critical_severity_is_preserved():
    rule_result = make_analysis(severity=IssueSeverity.LOW)
    ai_result = make_analysis(
        severity=IssueSeverity.CRITICAL,
        requires_human_review=False,
    )

    result = safety_review_node({
        "complaint": "Potential serious hazard",
        "rule_analysis": rule_result,
        "ai_analysis": ai_result,
    })

    final_analysis = result["final_analysis"]

    assert final_analysis.severity == IssueSeverity.CRITICAL
    assert final_analysis.requires_human_review is True


def test_higher_rule_severity_is_explained():
    rule_result = make_analysis(
        severity=IssueSeverity.CRITICAL,
        requires_human_review=True,
    )
    ai_result = make_analysis(severity=IssueSeverity.LOW)

    result = safety_review_node({
        "complaint": "Potential electrical hazard",
        "rule_analysis": rule_result,
        "ai_analysis": ai_result,
    })

    final_analysis = result["final_analysis"]

    assert final_analysis.severity == IssueSeverity.CRITICAL
    assert final_analysis.requires_human_review is True
    assert any(
        "higher rule-based severity" in message.lower()
        for message in final_analysis.reasoning
    )
