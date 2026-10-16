from datetime import datetime, timedelta, timezone

from backend.app.models import Complaint


def test_sla_endpoint_returns_target_and_deadline(client):
    response = client.post(
        "/api/complaints",
        json={
            "category": "garbage",
            "description": "Garbage has accumulated on the roadside.",
            "latitude": 26.45,
            "longitude": 80.33,
        },
    )
    assert response.status_code == 201
    ticket_id = response.json()["ticket_id"]

    response = client.get(f"/api/complaints/{ticket_id}/sla")

    assert response.status_code == 200
    data = response.json()
    assert data["target_hours"] == 24
    assert data["state"] == "on_track"
    assert "deadline" in data
    assert data["remaining_seconds"] is not None


def test_sla_endpoint_returns_404_for_missing_ticket(client):
    response = client.get(
        "/api/complaints/00000000-0000-0000-0000-000000000000/sla"
    )

    assert response.status_code == 404


def test_sla_endpoint_marks_resolved_complaint_closed(client):
    response = client.post(
        "/api/complaints",
        json={
            "category": "pothole",
            "description": "Large pothole causing danger to road users.",
            "latitude": 26.45,
            "longitude": 80.33,
        },
    )
    assert response.status_code == 201
    ticket_id = response.json()["ticket_id"]

    response = client.patch(
        f"/api/complaints/{ticket_id}/status",
        json={"status": "under_review"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/api/complaints/{ticket_id}/status",
        json={"status": "assigned"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/api/complaints/{ticket_id}/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/api/complaints/{ticket_id}/status",
        json={"status": "resolved"},
    )
    assert response.status_code == 200

    response = client.get(f"/api/complaints/{ticket_id}/sla")

    assert response.status_code == 200
    assert response.json()["state"] == "closed"
    assert response.json()["remaining_seconds"] is None
