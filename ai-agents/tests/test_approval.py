
import pytest

from review.approval import ReviewError, ReviewManager


@pytest.fixture
def manager():
    return ReviewManager()


@pytest.fixture
def analysis():
    return {
        "category": "electricity",
        "severity": "critical",
        "confidence": 0.95,
        "requires_human_review": True,
    }


def test_submission_enters_pending_queue(manager, analysis):
    record = manager.submit_for_review(
        "Exposed electrical wire near a road",
        analysis,
    )

    assert record["status"] == "pending"
    assert record["review_id"]
    assert len(manager.list_pending()) == 1


def test_authorized_style_decision_is_recorded(manager, analysis):
    record = manager.submit_for_review("Gas leak", analysis)

    result = manager.decide(
        record["review_id"],
        "reviewer-01",
        "approved",
        "Site details checked by reviewer",
    )

    assert result["status"] == "approved"
    assert result["decision"]["reviewer_id"] == "reviewer-01"
    assert result["decision"]["reason"]


def test_rejection_is_recorded(manager, analysis):
    record = manager.submit_for_review("Gas leak", analysis)

    result = manager.decide(
        record["review_id"],
        "reviewer-02",
        "rejected",
        "Insufficient supporting evidence",
    )

    assert result["status"] == "rejected"


def test_second_decision_is_blocked(manager, analysis):
    record = manager.submit_for_review("Gas leak", analysis)

    manager.decide(
        record["review_id"],
        "reviewer-01",
        "approved",
        "Verified",
    )

    with pytest.raises(ReviewError):
        manager.decide(
            record["review_id"],
            "reviewer-02",
            "rejected",
            "Changed decision",
        )


def test_blank_reviewer_is_rejected(manager, analysis):
    record = manager.submit_for_review("Gas leak", analysis)

    with pytest.raises(ReviewError):
        manager.decide(
            record["review_id"],
            " ",
            "approved",
            "Verified",
        )


def test_audit_log_tracks_submission_and_decision(manager, analysis):
    record = manager.submit_for_review("Gas leak", analysis)

    manager.decide(
        record["review_id"],
        "reviewer-01",
        "approved",
        "Verified",
    )

    events = manager.get_audit_log()

    assert [event["event"] for event in events] == [
        "submitted",
        "approved",
    ]
    assert all(event["review_id"] == record["review_id"] for event in events)


def test_invalid_severity_is_rejected(manager):
    with pytest.raises(ReviewError):
        manager.submit_for_review(
            "Unknown issue",
            {"severity": "urgent", "requires_human_review": True},
        )


def test_blank_complaint_is_rejected(manager, analysis):
    with pytest.raises(ReviewError):
        manager.submit_for_review("  ", analysis)
