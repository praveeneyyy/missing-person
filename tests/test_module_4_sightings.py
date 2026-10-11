import io
import json
import pytest
import numpy as np
import cv2
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db

client = TestClient(app)

def create_synthetic_face_bytes(width=300, height=300) -> bytes:
    """Creates a synthetic photo with one face for test execution."""
    img = np.full((height, width, 3), 200, dtype=np.uint8)
    center = (width // 2, height // 2)
    axes = (width // 4, height // 3)
    cv2.ellipse(img, center, axes, 0, 0, 360, (140, 170, 215), -1)

    eye_y = center[1] - axes[1] // 4
    eye_offset = axes[0] // 2
    cv2.circle(img, (center[0] - eye_offset, eye_y), 8, (60, 40, 30), -1)
    cv2.circle(img, (center[0] + eye_offset, eye_y), 8, (60, 40, 30), -1)

    nose_y = center[1] + axes[1] // 8
    cv2.circle(img, (center[0], nose_y), 6, (100, 120, 160), -1)

    mouth_y = center[1] + axes[1] // 2
    cv2.ellipse(img, (center[0], mouth_y), (axes[0] // 2, 8), 0, 0, 180, (50, 40, 140), 3)

    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def create_multi_face_bytes(width=600, height=350) -> bytes:
    """Creates a synthetic photo with two distinct faces."""
    img = np.full((height, width, 3), 220, dtype=np.uint8)
    for cx in [160, 440]:
        center = (cx, height // 2)
        axes = (70, 95)
        cv2.ellipse(img, center, axes, 0, 0, 360, (140, 170, 215), -1)
        eye_y = center[1] - axes[1] // 4
        cv2.circle(img, (center[0] - 30, eye_y), 7, (50, 40, 30), -1)
        cv2.circle(img, (center[0] + 30, eye_y), 7, (50, 40, 30), -1)
        cv2.circle(img, (center[0], center[1] + 10), 5, (100, 120, 160), -1)
        cv2.ellipse(img, (center[0], center[1] + 45), (30, 8), 0, 0, 180, (50, 40, 140), 3)

    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def create_blank_image_bytes(width=250, height=250) -> bytes:
    """Creates an image with no faces (e.g. landscape / background)."""
    img = np.full((height, width, 3), 80, dtype=np.uint8)
    cv2.line(img, (0, 0), (width, height), (255, 255, 255), 4)
    cv2.line(img, (0, height), (width, 0), (255, 255, 255), 4)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def get_auth_token(username="investigator", password="investigator123") -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_admin_token() -> str:
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]


# =========================================================================
# TEST 1: Monotonic Sighting Receipt Sequence
# =========================================================================
def test_module_4_monotonic_receipt_generation():
    """Verify monotonic sequence generation STG-2026-XXXX across successive submissions."""
    face_bytes = create_synthetic_face_bytes()

    res1 = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Chennai Central Platform 1",
            "consent_given": "true"
        },
        files={"file": ("photo1.jpg", face_bytes, "image/jpeg")}
    )
    assert res1.status_code == 201
    receipt1 = res1.json()["receipt_no"]
    assert receipt1.startswith("STG-2026-")

    res2 = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Koyambedu CMBT Gate 2",
            "consent_given": "true"
        },
        files={"file": ("photo2.jpg", face_bytes, "image/jpeg")}
    )
    assert res2.status_code == 201
    receipt2 = res2.json()["receipt_no"]
    assert receipt2.startswith("STG-2026-")

    num1 = int(receipt1.split("-")[-1])
    num2 = int(receipt2.split("-")[-1])
    assert num2 > num1, f"Expected monotonic increase: {receipt2} should be greater than {receipt1}"


# =========================================================================
# TEST 2: Public Submission with Single Face & Privacy Shield
# =========================================================================
def test_module_4_public_submission_with_single_face():
    """
    Submits a sighting with one detected face.
    Verifies receipt issuance, candidate generation, and privacy non-disclosure.
    """
    face_bytes = create_synthetic_face_bytes()

    res = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "sighting_time": "14:30",
            "location_name": "Marina Beach Promenade",
            "latitude": "13.0500",
            "longitude": "80.2824",
            "description": "Subject wearing blue windbreaker jacket near food stalls",
            "reporter_name": "Citizen Witness",
            "reporter_phone": "+91 98401 22334",
            "consent_given": "true"
        },
        files={"file": ("evidence.jpg", face_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()

    assert data["success"] is True
    assert data["receipt_no"].startswith("STG-2026-")
    assert data["location_name"] == "Marina Beach Promenade"
    assert data["faces_detected_count"] >= 1
    assert "queued" in data["status"].lower() or "submitted" in data["status"].lower()

    # STRICT PRIVACY SHIELD: Confirm confidential investigative data is not exposed
    assert "candidates" not in data
    assert "matches" not in data
    assert "similarity_score" not in data
    assert "case_id" not in data
    assert "full_name" not in data

    # Verify database records
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sightings WHERE receipt_no = ?", (data["receipt_no"],))
        sighting = cursor.fetchone()
        assert sighting is not None
        assert sighting["status"] == "pending_review"

        cursor.execute("SELECT * FROM sighting_media WHERE sighting_id = ?", (sighting["id"],))
        media = cursor.fetchone()
        assert media is not None
        assert media["faces_detected_count"] >= 1

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE sighting_id = ?", (sighting["id"],))
        cand_cnt = cursor.fetchone()["cnt"]
        assert cand_cnt >= 1, "Candidate matches should be ranked against enrolled cases"


# =========================================================================
# TEST 3: Multi-Face Detection Handling
# =========================================================================
def test_module_4_public_submission_with_multi_face():
    """Verifies that an image with multiple individuals indexes all detected faces."""
    multi_face = create_multi_face_bytes()

    res = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Crowded Concourse at Metro Station",
            "consent_given": "true"
        },
        files={"file": ("group.jpg", multi_face, "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["faces_detected_count"] >= 2

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sightings WHERE receipt_no = ?", (data["receipt_no"],))
        sighting_id = cursor.fetchone()["id"]

        cursor.execute("SELECT faces_metadata_json FROM sighting_media WHERE sighting_id = ?", (sighting_id,))
        meta_json = json.loads(cursor.fetchone()["faces_metadata_json"])
        assert len(meta_json) >= 2


# =========================================================================
# TEST 4: Zero Face Handling as Observational Lead
# =========================================================================
def test_module_4_public_submission_with_zero_faces():
    """
    Submits a photo containing no clear frontal faces (e.g. silhouette, back of head).
    System must safely accept the report as an observational lead without crashing.
    """
    blank_bytes = create_blank_image_bytes()

    res = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Park Walkway at Dusk",
            "description": "Person seen from behind wearing grey hoodie",
            "consent_given": "true"
        },
        files={"file": ("observation.jpg", blank_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()

    assert data["success"] is True
    assert data["faces_detected_count"] == 0
    assert "observation lead" in data["status"].lower()
    assert "observational lead" in data["message"].lower()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sightings WHERE receipt_no = ?", (data["receipt_no"],))
        sighting = cursor.fetchone()
        assert sighting is not None

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE sighting_id = ?", (sighting["id"],))
        cand_cnt = cursor.fetchone()["cnt"]
        assert cand_cnt == 0, "No candidate matches should be generated when zero faces are detected"


# =========================================================================
# TEST 5: Input Validation & Anti-Abuse Controls
# =========================================================================
def test_module_4_anti_abuse_and_validation():
    """Verifies strict validation on corrupted files, missing consent, invalid dates, and bad coordinates."""
    face_bytes = create_synthetic_face_bytes()

    # 1. Missing privacy consent
    res_no_consent = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Central",
            "consent_given": "false"
        },
        files={"file": ("img.jpg", face_bytes, "image/jpeg")}
    )
    assert res_no_consent.status_code == 400
    assert "privacy terms" in res_no_consent.json()["detail"].lower()

    # 2. Corrupted / invalid image bytes
    res_corrupt = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Central",
            "consent_given": "true"
        },
        files={"file": ("corrupt.jpg", b"NOT_A_VALID_JPEG_HEADER_BYTES", "image/jpeg")}
    )
    assert res_corrupt.status_code == 400
    assert "decoding failed" in res_corrupt.json()["detail"].lower()

    # 3. Empty file (0 bytes)
    res_empty = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Central",
            "consent_given": "true"
        },
        files={"file": ("empty.jpg", b"", "image/jpeg")}
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # 4. Future date (e.g. next year)
    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    res_future = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": future_date,
            "location_name": "Central",
            "consent_given": "true"
        },
        files={"file": ("img.jpg", face_bytes, "image/jpeg")}
    )
    assert res_future.status_code == 400
    assert "future" in res_future.json()["detail"].lower()

    # 5. Invalid latitude out of range (-90 to 90)
    res_bad_lat = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Central",
            "latitude": "125.5",
            "consent_given": "true"
        },
        files={"file": ("img.jpg", face_bytes, "image/jpeg")}
    )
    assert res_bad_lat.status_code == 400
    assert "latitude" in res_bad_lat.json()["detail"].lower()

    # 6. Blank / too short location description
    res_bad_loc = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": " ",
            "consent_given": "true"
        },
        files={"file": ("img.jpg", face_bytes, "image/jpeg")}
    )
    assert res_bad_loc.status_code == 400
    assert "location landmark" in res_bad_loc.json()["detail"].lower()


# =========================================================================
# TEST 6: Public Receipt Lookup & Privacy Shield Verification
# =========================================================================
def test_module_4_public_receipt_lookup_and_privacy_shield():
    """
    Submits a sighting and verifies that public lookup returns operational progress
    without exposing confidential case identifiers or suspect names.
    """
    face_bytes = create_synthetic_face_bytes()

    submit_res = client.post(
        "/api/v1/sightings",
        data={
            "sighting_date": "2026-10-09",
            "location_name": "Tambaram West Bus Stand",
            "consent_given": "true"
        },
        files={"file": ("sighting.jpg", face_bytes, "image/jpeg")}
    )
    assert submit_res.status_code == 201
    receipt_no = submit_res.json()["receipt_no"]

    # 1. Lookup with exact receipt code
    lookup_res = client.get(f"/api/v1/sightings/lookup/{receipt_no}")
    assert lookup_res.status_code == 200
    receipt_data = lookup_res.json()

    assert receipt_data["receipt_no"] == receipt_no
    assert receipt_data["location_name"] == "Tambaram West Bus Stand"
    assert "status_label" in receipt_data
    assert "notice" in receipt_data
    assert "privacy_statement" in receipt_data

    # STRICT PRIVACY SHIELD: Zero disclosure of case records or scores
    assert "full_name" not in receipt_data
    assert "case_reference" not in receipt_data
    assert "similarity_score" not in receipt_data
    assert "investigator_name" not in receipt_data

    # 2. Case-insensitive lookup (lowercase)
    lower_lookup = client.get(f"/api/v1/sightings/lookup/{receipt_no.lower()}")
    assert lower_lookup.status_code == 200
    assert lower_lookup.json()["receipt_no"] == receipt_no

    # 3. Non-existent receipt code returns 404
    missing_res = client.get("/api/v1/sightings/lookup/STG-2026-99999")
    assert missing_res.status_code == 404
    assert "not found" in missing_res.json()["detail"].lower()


# =========================================================================
# TEST 7: Investigator Sighting Management, Status Transitions & RBAC
# =========================================================================
def test_module_4_investigator_sighting_management_and_rbac():
    """
    Verifies staff endpoints:
    - Public/unauthenticated access blocked (HTTP 401/403)
    - Investigator listing & search
    - Status lifecycle transitions with mandatory rationale
    - Admin deletion with filesystem cleanup
    """
    # 1. Unauthenticated listing rejected
    unauth_res = client.get("/api/v1/sightings")
    assert unauth_res.status_code in [401, 403]

    # 2. Investigator login and list
    inv_token = get_auth_token("investigator", "investigator123")
    headers = {"Authorization": f"Bearer {inv_token}"}

    list_res = client.get("/api/v1/sightings", headers=headers)
    assert list_res.status_code == 200
    sightings = list_res.json()
    assert isinstance(sightings, list)
    assert len(sightings) >= 1

    first_sighting = sightings[0]
    sighting_id = first_sighting["id"]

    # 3. Sighting detailed view
    detail_res = client.get(f"/api/v1/sightings/{sighting_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == sighting_id
    assert "candidates" in detail_data
    assert "media" in detail_data

    # 4. Status update with mandatory rationale
    patch_res = client.patch(
        f"/api/v1/sightings/{sighting_id}/status",
        headers=headers,
        json={
            "status": "in_review",
            "rationale": "Investigator assigned; requesting CCTV cross-check from junction"
        }
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["current_status"] == "in_review"

    # Verify audit log created
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE action = 'SIGHTING_STATUS_UPDATED' AND resource_id = ?
            ORDER BY id DESC LIMIT 1
        """, (str(sighting_id),))
        log = cursor.fetchone()
        assert log is not None
        assert "Investigator assigned" in log["details_json"]

    # 5. Invalid status update rejected
    bad_status_res = client.patch(
        f"/api/v1/sightings/{sighting_id}/status",
        headers=headers,
        json={
            "status": "invalid_status_code",
            "rationale": "Attempting invalid transition"
        }
    )
    assert bad_status_res.status_code == 400

    # 6. Admin deletion
    admin_token = get_admin_token()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    del_res = client.delete(f"/api/v1/sightings/{sighting_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert "deleted" in del_res.json()["message"].lower()

    # Confirm deletion from database
    get_deleted = client.get(f"/api/v1/sightings/{sighting_id}", headers=headers)
    assert get_deleted.status_code == 404
