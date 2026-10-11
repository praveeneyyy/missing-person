import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db

client = TestClient(app)

def get_staff_token(username="investigator", password="investigator123"):
    """Helper to authenticate and return a valid staff JWT Bearer token."""
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_admin_token():
    """Helper to authenticate and return admin token."""
    return get_staff_token(username="admin", password="admin123")


# ==============================================================================
# 1. CANDIDATE REVIEW QUEUE & ACCESS CONTROL TESTS
# ==============================================================================

def test_candidates_access_control():
    """Verify candidate endpoints enforce authentication and staff RBAC."""
    # 1. Unauthenticated request
    res = client.get("/api/v1/candidates")
    assert res.status_code == 401

    # 2. Authenticated staff user
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/candidates", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_list_candidates_with_forensic_metrics():
    """Verify candidate matches include spatial separation, temporal delta, and confidence tiers."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/candidates", headers=headers)
    assert res.status_code == 200
    candidates = res.json()
    assert len(candidates) > 0

    first = candidates[0]
    assert "candidate_id" in first
    assert "similarity_score" in first
    assert "rank" in first
    assert "confidence_tier" in first
    assert "requires_human_review" in first
    assert "spatial_separation_km" in first
    assert "temporal_delta_days" in first
    assert "receipt_no" in first
    assert "reference_no" in first

    # Verify metric consistency
    assert 0.0 <= first["similarity_score"] <= 1.0
    if first["similarity_score"] >= 0.70:
        assert "HIGH" in first["confidence_tier"]

def test_list_candidates_filters_and_sorting():
    """Verify filtering by status, min_score, and sorting order."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Filter by status
    res = client.get("/api/v1/candidates?status=requires_human_review", headers=headers)
    assert res.status_code == 200
    for c in res.json():
        assert c["match_status"] == "requires_human_review"

    # 2. Filter by minimum score
    res_high = client.get("/api/v1/candidates?min_score=0.70", headers=headers)
    assert res_high.status_code == 200
    for c in res_high.json():
        assert c["similarity_score"] >= 0.70

    # 3. Backward compatible pending endpoint
    res_pending = client.get("/api/v1/candidates/pending", headers=headers)
    assert res_pending.status_code == 200
    assert len(res_pending.json()) > 0

def test_get_single_candidate_detail():
    """Verify single candidate detail returns full dossier and review history."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Get first candidate ID
    list_res = client.get("/api/v1/candidates", headers=headers)
    assert len(list_res.json()) > 0
    candidate_id = list_res.json()[0]["candidate_id"]

    res = client.get(f"/api/v1/candidates/{candidate_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_id"] == candidate_id
    assert "reviews" in data
    assert isinstance(data["reviews"], list)

    # 404 on invalid candidate
    res_404 = client.get("/api/v1/candidates/99999", headers=headers)
    assert res_404.status_code == 404

def test_candidate_queue_telemetry_stats():
    """Verify candidate queue workload stats endpoint."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/candidates/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "total_candidates" in data
    assert "pending_review" in data
    assert "verified_count" in data
    assert "escalated_count" in data
    assert "high_confidence_pending" in data
    assert "governance_rule" in data
    assert data["total_candidates"] >= data["pending_review"]


# ==============================================================================
# 2. ADJUDICATION & REVIEW DECISION WORKFLOW TESTS
# ==============================================================================

def test_submit_candidate_review_verified_workflow():
    """Verify formal review submission with 'verified' disposition propagates across entities."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Find a pending candidate
    res = client.get("/api/v1/candidates?status=requires_human_review", headers=headers)
    assert len(res.json()) > 0
    candidate = res.json()[0]
    candidate_id = candidate["candidate_id"]
    sighting_id = candidate["sighting_id"]
    case_id = candidate["case_id"]

    payload = {
        "disposition": "verified",
        "rationale": "Facial geometry, eye distance, and unique eyebrow scar confirmed by investigating officer.",
        "next_steps": "Dispatch local patrol unit to safehouse, notify family."
    }

    res_review = client.post(f"/api/v1/candidates/{candidate_id}/reviews", json=payload, headers=headers)
    assert res_review.status_code == 201
    rev_data = res_review.json()
    assert rev_data["success"] is True
    assert rev_data["disposition"] == "verified"
    assert rev_data["new_status"] == "verified"

    # Verify candidate status updated
    cand_detail = client.get(f"/api/v1/candidates/{candidate_id}", headers=headers).json()
    assert cand_detail["match_status"] == "verified"
    assert len(cand_detail["reviews"]) >= 1
    assert cand_detail["reviews"][0]["disposition"] == "verified"
    assert cand_detail["reviews"][0]["rationale"] == payload["rationale"]

    # Verify sighting status updated to verified_match
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM sightings WHERE id = ?", (sighting_id,))
        assert cursor.fetchone()["status"] == "verified_match"

        # Verify case status updated to under_review
        cursor.execute("SELECT status FROM cases WHERE id = ?", (case_id,))
        assert cursor.fetchone()["status"] in ["under_review", "resolved"]

        # Verify audit log was recorded
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE action = 'REVIEW_SUBMITTED' AND resource_id = ?
            ORDER BY id DESC LIMIT 1
        """, (str(candidate_id),))
        audit = cursor.fetchone()
        assert audit is not None
        assert "verified" in audit["details_json"]

def test_review_validation_rules():
    """Verify review validation catches invalid dispositions and short rationales."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    cand_id = client.get("/api/v1/candidates", headers=headers).json()[0]["candidate_id"]

    # 1. Invalid disposition
    res_bad_disp = client.post(
        f"/api/v1/candidates/{cand_id}/reviews",
        json={"disposition": "auto_closed", "rationale": "Valid rationale explanation for test."},
        headers=headers
    )
    assert res_bad_disp.status_code == 400

    # 2. Rationale too short (< 5 chars)
    res_short = client.post(
        f"/api/v1/candidates/{cand_id}/reviews",
        json={"disposition": "rejected", "rationale": "No"},
        headers=headers
    )
    assert res_short.status_code in [400, 422]

def test_batch_candidate_review():
    """Verify batch adjudication over multiple candidate matches simultaneously."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    candidates = client.get("/api/v1/candidates", headers=headers).json()
    cand_ids = [c["candidate_id"] for c in candidates[:2]]

    payload = {
        "candidate_ids": cand_ids,
        "disposition": "rejected",
        "rationale": "Routine false positive rejection for low-similarity background detections.",
        "next_steps": "Cleared from active investigation queue."
    }

    res_batch = client.post("/api/v1/candidates/batch-review", json=payload, headers=headers)
    assert res_batch.status_code == 200
    data = res_batch.json()
    assert data["success"] is True
    assert data["processed_count"] == len(cand_ids)
    assert data["disposition"] == "rejected"


# ==============================================================================
# 3. CHRONOLOGICAL CASE TIMELINE TESTS
# ==============================================================================

def test_case_chronological_timeline():
    """Verify case timeline endpoint returns chronologically sorted lifecycle milestones."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    cases = client.get("/api/v1/cases", headers=headers).json()
    assert len(cases) > 0
    case_id = cases[0]["id"]

    res = client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers)
    assert res.status_code == 200
    timeline = res.json()

    assert timeline["case_id"] == case_id
    assert "events" in timeline
    assert isinstance(timeline["events"], list)
    assert len(timeline["events"]) >= 2  # Registration + reference portrait

    # Verify event structure
    first_event = timeline["events"][0]
    assert first_event["event_type"] == "CASE_REGISTERED"
    assert "event_id" in first_event
    assert "title" in first_event
    assert "description" in first_event
    assert "actor_name" in first_event
    assert "timestamp" in first_event
    assert "badge_color" in first_event

    # Verify timestamps are sorted chronologically
    timestamps = [ev["timestamp"] for ev in timeline["events"]]
    assert timestamps == sorted(timestamps)

    # 404 on invalid case
    res_404 = client.get("/api/v1/cases/99999/timeline", headers=headers)
    assert res_404.status_code == 404


# ==============================================================================
# 4. ENHANCED GIS INVESTIGATION MAP TESTS
# ==============================================================================

def test_enhanced_map_points_and_correlation_vectors():
    """Verify GIS map points API returns cases, sightings, and spatial correlation vectors."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/map/points", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "cases" in data
    assert "sightings" in data
    assert "correlation_vectors" in data
    assert "total_case_pins" in data
    assert "total_sighting_pins" in data

    # Verify vector fields
    if len(data["correlation_vectors"]) > 0:
        vec = data["correlation_vectors"][0]
        assert "sighting_id" in vec
        assert "case_id" in vec
        assert "similarity_score" in vec
        assert "distance_km" in vec
        assert "case_lat" in vec
        assert "sighting_lat" in vec
        assert vec["distance_km"] >= 0.0

    # Test filtering by min_similarity
    res_filtered = client.get("/api/v1/map/points?min_similarity=0.70", headers=headers)
    assert res_filtered.status_code == 200
    for s in res_filtered.json()["sightings"]:
        assert s["max_similarity"] >= 0.70


# ==============================================================================
# 5. INVESTIGATOR NOTIFICATION CENTER TESTS
# ==============================================================================

def test_notification_center_lifecycle():
    """Verify notification listing, unread counter, single read, and bulk read."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch unread count
    cnt_res = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert cnt_res.status_code == 200
    assert "unread_count" in cnt_res.json()

    # 2. Fetch notification list
    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert "notifications" in data
    assert "unread_count" in data

    # 3. Create a test notification
    user_me = client.get("/api/v1/auth/me", headers=headers).json()
    new_notif_payload = {
        "user_id": user_me["id"],
        "title": "Field Alert: Verified Match Near Central Station",
        "message": "Patrol Unit Alpha-4 confirmed visual contact with subject.",
        "category": "match_alert",
        "link_url": "/review"
    }
    create_res = client.post("/api/v1/notifications", json=new_notif_payload, headers=headers)
    assert create_res.status_code == 201
    notif_id = create_res.json()["notification_id"]

    # 4. Mark single notification as read
    read_res = client.put(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] == 1

    # 5. Mark all as read
    read_all_res = client.put("/api/v1/notifications/read-all", headers=headers)
    assert read_all_res.status_code == 200
    assert read_all_res.json()["success"] is True

    # 6. Unread count should now be 0
    cnt_after = client.get("/api/v1/notifications/unread-count", headers=headers).json()
    assert cnt_after["unread_count"] == 0
