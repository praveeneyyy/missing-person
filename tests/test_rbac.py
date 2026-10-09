import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_unauthenticated_access_denied():
    # Attempting to fetch cases without token must return 401
    res = client.get("/api/v1/cases")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

def test_unauthenticated_review_queue_denied():
    res = client.get("/api/v1/candidates/pending")
    assert res.status_code == 401

def test_unauthenticated_audit_logs_denied():
    res = client.get("/api/v1/audit")
    assert res.status_code == 401

def test_review_requires_rationale():
    # Login as investigator
    login_res = client.post("/api/v1/auth/login", json={
        "username": "investigator",
        "password": "investigator123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt review with empty or too short rationale
    res = client.post(
        "/api/v1/candidates/1/reviews",
        headers=headers,
        json={
            "disposition": "verified",
            "rationale": "ok"  # Too short, min length is 5
        }
    )
    assert res.status_code == 422
