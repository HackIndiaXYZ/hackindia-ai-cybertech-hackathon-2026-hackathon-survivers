
import pytest

import workflow.city_workflow as workflow_module
from review.approval import ReviewManager
from schemas.issue import IssueAnalysis, IssueCategory, IssueSeverity


@pytest.fixture
def sample_analysis():
    return IssueAnalysis(
        summary="Exposed electrical wire",
        category=IssueCategory.ELECTRICITY,
        severity=IssueSeverity.CRITICAL,
        confidence=0.95,
        reasoning=["Critical safety hazard detected."],
        requires_human_review=True,
    )


def test_critical_workflow_result_enters_review_queue(
    monkeypatch, sample_analysis
):
    class FakeWorkflow:
        def invoke(self, _state):
            return {
                "final_analysis": sample_analysis,
                "civic_guidance": [],
                "error": None,
            }

    manager = ReviewManager()

    monkeypatch.setattr(
        workflow_module, "city_workflow", FakeWorkflow()
    )
    monkeypatch.setattr(
        workflow_module, "review_manager", manager
    )

    result = workflow_module.run_city_workflow(
        "Exposed electrical wire near the road"
    )

    assert result["review"]["status"] == "pending"
    assert result["review"]["review_id"]
    assert len(manager.list_pending()) == 1
    assert result["analysis"].severity == IssueSeverity.CRITICAL


def test_low_risk_result_does_not_create_review(
    monkeypatch,
):
    low_risk = IssueAnalysis(
        summary="Minor road issue",
        category=IssueCategory.ROADS,
        severity=IssueSeverity.LOW,
        confidence=0.90,
        reasoning=["Low-risk issue."],
        requires_human_review=False,
    )

    class FakeWorkflow:
        def invoke(self, _state):
            return {
                "final_analysis": low_risk,
                "civic_guidance": [],
                "error": None,
            }

    manager = ReviewManager()

    monkeypatch.setattr(
        workflow_module, "city_workflow", FakeWorkflow()
    )
    monkeypatch.setattr(
        workflow_module, "review_manager", manager
    )

    result = workflow_module.run_city_workflow(
        "A minor road issue"
    )

    assert result["review"] is None
    assert manager.list_pending() == []


def test_empty_complaint_is_rejected():
    with pytest.raises(ValueError, match="cannot be empty"):
        workflow_module.run_city_workflow("   ")
