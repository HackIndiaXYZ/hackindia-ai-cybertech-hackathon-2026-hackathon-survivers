from datetime import datetime, timedelta, timezone

# Prototype SLA targets measured from complaint creation.
# These are project defaults, not official municipal service guarantees.
SLA_HOURS_BY_CATEGORY = {
    "pothole": 72,
    "garbage": 24,
    "streetlight": 48,
    "water_leakage": 12,
    "drainage": 24,
}

RESOLVED_STATUSES = {"resolved", "rejected"}


def get_sla_details(
    category: str,
    created_at: datetime,
    status: str,
    now: datetime | None = None,
) -> dict:
    """Return the SLA target, deadline, state, and remaining seconds."""
    target_hours = SLA_HOURS_BY_CATEGORY.get(category)

    if target_hours is None:
        raise ValueError(f"No SLA configured for category: {category}")

    current_time = now or datetime.now(timezone.utc)

    # SQLite may return naive datetimes despite timezone=True.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    deadline = created_at + timedelta(hours=target_hours)
    is_closed = status in RESOLVED_STATUSES
    remaining_seconds = int((deadline - current_time).total_seconds())

    if is_closed:
        state = "closed"
        remaining = None
    elif remaining_seconds < 0:
        state = "overdue"
        remaining = remaining_seconds
    else:
        state = "on_track"
        remaining = remaining_seconds

    return {
        "target_hours": target_hours,
        "deadline": deadline,
        "state": state,
        "remaining_seconds": remaining,
    }
