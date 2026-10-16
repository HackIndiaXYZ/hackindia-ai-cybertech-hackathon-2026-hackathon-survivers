from sqlalchemy import select

from backend.app.models import TicketHistory
from backend.app.services.ticket_service import (
    DEPARTMENT_BY_CATEGORY,
)


def create_complaint(client, category="pothole"):
    response = client.post(
        "/api/complaints",
        json={
            "category": category,
            "description": "Civic issue near the college gate.",
            "latitude": 26.4499,
            "longitude": 80.3319,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_department_assignment_uses_category_mapping(client):
    complaint = create_complaint(client, "pothole")

    response = client.post(
        f"/api/complaints/{complaint['ticket_id']}/assign",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["department"] == DEPARTMENT_BY_CATEGORY["pothole"]
    assert response.json()["status"] == "assigned"


def test_department_assignment_accepts_custom_department(client):
    complaint = create_complaint(client)

    response = client.post(
        f"/api/complaints/{complaint['ticket_id']}/assign",
        json={"department": "City Roads Team"},
    )

    assert response.status_code == 200
    assert response.json()["department"] == "City Roads Team"


def test_assignment_creates_ticket_history(client):
    complaint = create_complaint(client)

    response = client.post(
        f"/api/complaints/{complaint['ticket_id']}/assign",
        json={},
    )
    assert response.status_code == 200

    history_response = client.get(
        f"/api/complaints/{complaint['ticket_id']}/history"
    )

    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["old_status"] == "submitted"
    assert history[0]["new_status"] == "assigned"
    assert "Roads Department" in history[0]["note"]


def test_valid_status_transition_creates_history(client):
    complaint = create_complaint(client)

    response = client.patch(
        f"/api/complaints/{complaint['ticket_id']}/status",
        json={
            "status": "under_review",
            "note": "Evidence is being reviewed.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "under_review"

    history_response = client.get(
        f"/api/complaints/{complaint['ticket_id']}/history"
    )
    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1
    assert history[0]["old_status"] == "submitted"
    assert history[0]["new_status"] == "under_review"
    assert history[0]["note"] == "Evidence is being reviewed."


def test_invalid_status_transition_returns_400(client):
    complaint = create_complaint(client)

    response = client.patch(
        f"/api/complaints/{complaint['ticket_id']}/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 400
    assert "Cannot change status" in response.json()["detail"]


def test_nonexistent_ticket_assignment_returns_404(client):
    response = client.post(
        "/api/complaints/nonexistent-ticket/assign",
        json={},
    )
    assert response.status_code == 404


def test_nonexistent_ticket_status_update_returns_404(client):
    response = client.patch(
        "/api/complaints/nonexistent-ticket/status",
        json={"status": "under_review"},
    )
    assert response.status_code == 404


def test_nonexistent_ticket_history_returns_404(client):
    response = client.get(
        "/api/complaints/nonexistent-ticket/history"
    )
    assert response.status_code == 404


def test_assignment_to_already_assigned_ticket_does_not_add_duplicate_history(
    client,
):
    complaint = create_complaint(client)

    first = client.post(
        f"/api/complaints/{complaint['ticket_id']}/assign",
        json={},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/complaints/{complaint['ticket_id']}/assign",
        json={},
    )
    assert second.status_code == 200

    history_response = client.get(
        f"/api/complaints/{complaint['ticket_id']}/history"
    )
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
