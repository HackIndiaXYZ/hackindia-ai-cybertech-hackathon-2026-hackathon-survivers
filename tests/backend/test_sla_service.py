from datetime import datetime, timedelta, timezone

import pytest

from backend.app.services.sla_service import get_sla_details


def test_complaint_is_on_track_before_deadline():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = created_at + timedelta(hours=10)

    result = get_sla_details("garbage", created_at, "submitted", now)

    assert result["target_hours"] == 24
    assert result["state"] == "on_track"
    assert result["remaining_seconds"] == 14 * 60 * 60


def test_complaint_is_overdue_after_deadline():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = created_at + timedelta(hours=25)

    result = get_sla_details("garbage", created_at, "in_progress", now)

    assert result["state"] == "overdue"
    assert result["remaining_seconds"] == -3600


def test_resolved_complaint_is_closed_even_after_deadline():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = created_at + timedelta(days=5)

    result = get_sla_details("pothole", created_at, "resolved", now)

    assert result["state"] == "closed"
    assert result["remaining_seconds"] is None


def test_rejected_complaint_is_closed():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = created_at + timedelta(days=5)

    result = get_sla_details("drainage", created_at, "rejected", now)

    assert result["state"] == "closed"


def test_water_leakage_has_12_hour_target():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = get_sla_details(
        "water_leakage",
        created_at,
        "submitted",
        created_at,
    )

    assert result["target_hours"] == 12
    assert result["state"] == "on_track"


def test_unknown_category_raises_error():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="No SLA configured"):
        get_sla_details("unknown", created_at, "submitted", created_at)


def test_naive_datetime_is_supported():
    created_at = datetime(2026, 1, 1)
    now = created_at + timedelta(hours=1)

    result = get_sla_details("garbage", created_at, "submitted", now)

    assert result["state"] == "on_track"
    assert result["deadline"].tzinfo == timezone.utc
