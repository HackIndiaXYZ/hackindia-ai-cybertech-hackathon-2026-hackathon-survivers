from datetime import datetime, timedelta, timezone

from backend.app.models.complaint import Complaint


def test_overdue_endpoint_returns_old_unresolved_complaint(client):
    response = client.post(
        "/api/complaints",
        json={
            "category": "water_leakage",
            "description": "Water leaking continuously from a street pipe",
            "latitude": 26.8467,
            "longitude": 80.9462,
        },
    )
    assert response.status_code == 201
    ticket_id = response.json()["ticket_id"]

    session_factory = client.app.state.TestingSessionLocal
    with session_factory() as db:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.ticket_id == ticket_id)
            .one()
        )
        complaint.created_at = datetime.now(timezone.utc) - timedelta(hours=24)
        db.commit()

    response = client.get("/api/overdue-complaints")

    assert response.status_code == 200
    data = response.json()
    assert data["total_returned"] == 1
    assert data["complaints"][0]["ticket_id"] == ticket_id
    assert data["complaints"][0]["category"] == "water_leakage"
    assert data["complaints"][0]["hours_overdue"] >= 11.9


def test_overdue_endpoint_excludes_resolved_complaints(client):
    response = client.post(
        "/api/complaints",
        json={
            "category": "water_leakage",
            "description": "Water leaking continuously from a street pipe",
            "latitude": 26.8467,
            "longitude": 80.9462,
        },
    )
    assert response.status_code == 201
    ticket_id = response.json()["ticket_id"]

    session_factory = client.app.state.TestingSessionLocal
    with session_factory() as db:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.ticket_id == ticket_id)
            .one()
        )
        complaint.created_at = datetime.now(timezone.utc) - timedelta(hours=24)
        complaint.status = "resolved"
        db.commit()

    response = client.get("/api/overdue-complaints")

    assert response.status_code == 200
    assert response.json()["total_returned"] == 0
    assert response.json()["complaints"] == []
