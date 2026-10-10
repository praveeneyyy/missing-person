import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.seed_data import seed_database
from backend.config import BASE_DIR

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "YuNet" in data["models"]["face_detector"]

def test_auth_login_success():
    res = client.post("/api/v1/auth/login", json={
        "username": "investigator",
        "password": "investigator123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "investigator"
    assert data["user"]["badge_number"] == "INV-44111131"

def test_auth_login_invalid_password():
    res = client.post("/api/v1/auth/login", json={
        "username": "investigator",
        "password": "wrong_password"
    })
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]

def test_public_lookup_sighting():
    res = client.get("/api/v1/sightings/lookup/STG-2026-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["receipt_no"] == "STG-2026-0001"
    assert "Tambaram" in data["location_name"]
    # PRD FR-05 requirement: No confidential case data or match scores exposed
    assert "similarity_score" not in data
    assert "case_name" not in data
    assert "notice" in data

def test_investigator_cases_and_review_workflow():
    # 1. Login as investigator
    login_res = client.post("/api/v1/auth/login", json={
        "username": "investigator",
        "password": "investigator123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List cases
    cases_res = client.get("/api/v1/cases", headers=headers)
    assert cases_res.status_code == 200
    cases = cases_res.json()
    assert len(cases) >= 2

    # 3. View review queue
    pending_res = client.get("/api/v1/candidates/pending", headers=headers)
    assert pending_res.status_code == 200
    pending = pending_res.json()
    assert len(pending) >= 1

    # Check top candidate
    top_cand = pending[0]
    cand_id = top_cand["candidate_id"]

    # 4. Record review decision with rationale
    review_res = client.post(
        f"/api/v1/candidates/{cand_id}/reviews",
        headers=headers,
        json={
            "disposition": "verified",
            "rationale": "Facial geometry matches reference photo MP-2026-001. Contacted railway post; verified by family.",
            "next_steps": "Dispatch local patrol unit to Tambaram junction."
        }
    )
    assert review_res.status_code == 201
    rev_data = review_res.json()
    assert rev_data["success"] is True
    assert rev_data["disposition"] == "verified"

def test_benchmark_endpoint():
    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/benchmark", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["embedding_dimensions"] == 128
    assert "metrics" in data
    assert data["metrics"]["recall_at_1_percent"] >= 90.0
