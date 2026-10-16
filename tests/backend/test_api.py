import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_sample(client, **overrides):
    payload = {
        "category": "pothole",
        "description": "Large pothole near the college gate.",
        "latitude": 26.4499,
        "longitude": 80.3319,
    }
    payload.update(overrides)
    response = client.post("/api/complaints", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_and_retrieve_complaint(client):
    created = create_sample(client)

    response = client.get(f"/api/complaints/{created['ticket_id']}")
    assert response.status_code == 200
    assert response.json()["ticket_id"] == created["ticket_id"]
    assert response.json()["category"] == "pothole"


def test_list_complaints_filter_by_category(client):
    create_sample(client, category="pothole")
    create_sample(client, category="garbage")

    response = client.get("/api/complaints", params={"category": "garbage"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "garbage"


def test_invalid_coordinates_rejected(client):
    response = client.post(
        "/api/complaints",
        json={
            "category": "pothole",
            "description": "Pothole outside valid coordinates.",
            "latitude": 120,
            "longitude": 80,
        },
    )
    assert response.status_code == 422


def test_missing_ticket_returns_404(client):
    response = client.get("/api/complaints/nonexistent-ticket")
    assert response.status_code == 404


def test_nearby_complaints_returns_nearest_first(client):
    nearby = create_sample(client)
    create_sample(
        client,
        category="garbage",
        description="Garbage beside the market entrance.",
        latitude=26.46,
        longitude=80.34,
    )

    response = client.get(
        "/api/nearby-complaints",
        params={
            "latitude": 26.4499,
            "longitude": 80.3319,
            "radius_km": 5,
        },
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["ticket_id"] == nearby["ticket_id"]
    assert results[0]["distance_km"] == 0


def test_nearby_complaints_excludes_outside_radius(client):
    create_sample(
        client,
        latitude=26.4499,
        longitude=80.3319,
    )
    response = client.get(
        "/api/nearby-complaints",
        params={
            "latitude": 27.5,
            "longitude": 81.5,
            "radius_km": 1,
        },
    )
    assert response.status_code == 200
    assert response.json() == []


def test_hotspots_counts_category_and_status(client):
    create_sample(client, category="pothole")
    create_sample(
        client,
        category="garbage",
        description="Garbage piled beside the bus stop.",
    )

    response = client.get(
        "/api/hotspots",
        params={
            "latitude": 26.4499,
            "longitude": 80.3319,
            "radius_km": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_complaints"] == 2
    assert data["by_category"] == {"pothole": 1, "garbage": 1}
    assert data["by_status"] == {"submitted": 2}


def test_invalid_radius_rejected(client):
    response = client.get(
        "/api/hotspots",
        params={
            "latitude": 26.4499,
            "longitude": 80.3319,
            "radius_km": 0,
        },
    )
    assert response.status_code == 422
