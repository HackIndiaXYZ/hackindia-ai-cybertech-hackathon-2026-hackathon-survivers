from sqlalchemy.orm import Session

from backend.app.models import Complaint, TicketHistory

DEPARTMENT_BY_CATEGORY = {
    "pothole": "Roads Department",
    "garbage": "Sanitation Department",
    "streetlight": "Electrical Department",
    "water_leakage": "Water Supply Department",
    "drainage": "Drainage Department",
}

ALLOWED_TRANSITIONS = {
    "submitted": {"under_review", "rejected"},
    "under_review": {"assigned", "rejected"},
    "assigned": {"in_progress", "under_review"},
    "in_progress": {"resolved", "assigned"},
    "resolved": {"in_progress"},
    "rejected": set(),
}


def assign_department(
    db: Session,
    complaint: Complaint,
    department: str | None = None,
) -> None:
    selected = department or DEPARTMENT_BY_CATEGORY.get(complaint.category)

    if not selected:
        raise ValueError("No department configured for this category")

    old_status = complaint.status
    complaint.department = selected

    if complaint.status in {"submitted", "under_review"}:
        complaint.status = "assigned"

    if old_status != complaint.status:
        db.add(
            TicketHistory(
                complaint_id=complaint.id,
                old_status=old_status,
                new_status=complaint.status,
                note=f"Assigned to {selected}",
            )
        )

    db.add(complaint)


def update_status(
    db: Session,
    complaint: Complaint,
    new_status: str,
    note: str | None = None,
) -> None:
    allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())

    if new_status not in allowed:
        raise ValueError(
            f"Cannot change status from '{complaint.status}' to '{new_status}'"
        )

    old_status = complaint.status
    complaint.status = new_status

    db.add(
        TicketHistory(
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )
    )
    db.add(complaint)
