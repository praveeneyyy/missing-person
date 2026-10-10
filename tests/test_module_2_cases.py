import io
import json
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import BASE_DIR

client = TestClient(app)

def get_auth_headers(username="investigator", password="investigator123"):
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_module_2_case_registration_and_validation():
    headers = get_auth_headers()

    # 1. Register a new missing person case
    case_payload = {
        "full_name": "Kavitha Sundaram",
        "age": 24,
        "gender": "Female",
        "last_seen_date": "2026-10-05",
        "last_seen_time": "18:00",
        "last_seen_location": "T. Nagar Shopping District, Chennai",
        "latitude": 13.0418,
        "longitude": 80.2341,
        "identifying_features": "Black birthmark on right wrist, silver glasses",
        "clothing_description": "Yellow salwar kameez and brown leather sandals",
        "notes": "Reported missing after evening college class."
    }
    create_res = client.post("/api/v1/cases", headers=headers, json=case_payload)
    assert create_res.status_code == 201
    created_case = create_res.json()
    case_id = created_case["id"]
    ref_no = created_case["reference_no"]
    assert ref_no.startswith("MP-2026-")
    assert created_case["full_name"] == "Kavitha Sundaram"
    assert created_case["status"] == "open"

    # 2. Upload valid reference photo (Single face)
    sample_img_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    with open(sample_img_path, "rb") as f:
        photo_bytes = f.read()

    upload_res = client.post(
        f"/api/v1/cases/{case_id}/references",
        headers=headers,
        files={"file": ("kavitha_portrait.jpg", photo_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 200
    ref_data = upload_res.json()
    assert ref_data["case_id"] == case_id
    assert len(ref_data["bbox"]) == 4
    assert ref_data["confidence"] > 0.6
    assert "Authorized reference photo enrolled" in ref_data["message"]

    # 3. Fetch comprehensive case dossier
    dossier_res = client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()
    assert dossier["reference_no"] == ref_no
    assert len(dossier["reference_photos"]) == 1
    assert dossier["reference_photos"][0]["model_name"] == "YuNet + SFace"

def test_module_2_reference_photo_single_face_validation_rejection():
    headers = get_auth_headers()

    # Create dummy case
    create_res = client.post("/api/v1/cases", headers=headers, json={
        "full_name": "Test Subject Validation",
        "last_seen_date": "2026-10-01",
        "last_seen_location": "Egmore, Chennai"
    })
    assert create_res.status_code == 201
    case_id = create_res.json()["id"]

    # Test A: Rejection of zero-face image (chicken photo)
    zero_face_path = BASE_DIR / "sample_data" / "sample_chicky.jpg"
    with open(zero_face_path, "rb") as f:
        zero_face_bytes = f.read()

    res_zero = client.post(
        f"/api/v1/cases/{case_id}/references",
        headers=headers,
        files={"file": ("chicky.jpg", zero_face_bytes, "image/jpeg")}
    )
    assert res_zero.status_code == 422
    assert "No human face was detected" in res_zero.json()["detail"]

    # Test B: Rejection of multiple-face image (2 faces concatenated)
    single_face_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    single_mat = cv2.imread(str(single_face_path))
    two_faces_mat = np.hstack([single_mat, single_mat])
    _, encoded_two_faces = cv2.imencode(".jpg", two_faces_mat)
    two_faces_bytes = encoded_two_faces.tobytes()

    res_multi = client.post(
        f"/api/v1/cases/{case_id}/references",
        headers=headers,
        files={"file": ("two_faces.jpg", two_faces_bytes, "image/jpeg")}
    )
    assert res_multi.status_code == 422
    assert "Multiple faces" in res_multi.json()["detail"]

def test_module_2_case_metadata_update_and_audit():
    headers = get_auth_headers()

    # Create case
    case_res = client.post("/api/v1/cases", headers=headers, json={
        "full_name": "Dinesh Rajan",
        "last_seen_date": "2026-10-02",
        "last_seen_location": "Guindy Industrial Estate"
    })
    case_id = case_res.json()["id"]

    # Update case metadata
    update_res = client.put(f"/api/v1/cases/{case_id}", headers=headers, json={
        "identifying_features": "Prominent surgical scar on left forearm",
        "clothing_description": "White collared shirt, khaki trousers",
        "notes": "Witness spotted individual boarding MTC Bus Route 21G."
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert "surgical scar" in updated["identifying_features"]
    assert "21G" in updated["notes"]

    # Verify audit log recorded CASE_UPDATED
    audit_res = client.get("/api/v1/audit", headers=headers)
    assert audit_res.status_code == 200
    actions = [log["action"] for log in audit_res.json()]
    assert "CASE_UPDATED" in actions

def test_module_2_case_lifecycle_status_transition():
    headers = get_auth_headers()

    # Create case
    case_res = client.post("/api/v1/cases", headers=headers, json={
        "full_name": "Pooja V.",
        "last_seen_date": "2026-10-04",
        "last_seen_location": "Velachery MRTS Station"
    })
    case_id = case_res.json()["id"]
    assert case_res.json()["status"] == "open"

    # Transition to 'under_review'
    t1_res = client.put(f"/api/v1/cases/{case_id}/status", headers=headers, json={
        "status": "under_review",
        "notes": "CCTV camera footage shows matching individual at platform."
    })
    assert t1_res.status_code == 200
    assert t1_res.json()["status"] == "under_review"
    assert "UNDER_REVIEW" in t1_res.json()["notes"]

    # Transition to 'resolved'
    t2_res = client.put(f"/api/v1/cases/{case_id}/status", headers=headers, json={
        "status": "resolved",
        "notes": "Individual located safe in Tambaram; reunited with family."
    })
    assert t2_res.status_code == 200
    assert t2_res.json()["status"] == "resolved"

    # Test invalid status string returns 400
    bad_res = client.put(f"/api/v1/cases/{case_id}/status", headers=headers, json={
        "status": "invalid_status",
        "notes": "test"
    })
    assert bad_res.status_code == 400
    assert "Invalid status" in bad_res.json()["detail"]

def test_module_2_multi_reference_photos_and_safe_deletion():
    headers = get_auth_headers()

    # Create case
    case_res = client.post("/api/v1/cases", headers=headers, json={
        "full_name": "Multi Reference Subject",
        "last_seen_date": "2026-10-06",
        "last_seen_location": "Adyar"
    })
    case_id = case_res.json()["id"]

    # Enroll Portrait 1
    p1_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    with open(p1_path, "rb") as f:
        r1 = client.post(f"/api/v1/cases/{case_id}/references", headers=headers, files={"file": ("face1.jpg", f.read(), "image/jpeg")})
    assert r1.status_code == 200
    ref1_id = r1.json()["id"]

    # Enroll Portrait 2
    p2_path = BASE_DIR / "sample_data" / "sample_messi.jpg"
    with open(p2_path, "rb") as f:
        r2 = client.post(f"/api/v1/cases/{case_id}/references", headers=headers, files={"file": ("face2.jpg", f.read(), "image/jpeg")})
    assert r2.status_code == 200
    ref2_id = r2.json()["id"]

    # Check that dossier has 2 reference photos
    dossier = client.get(f"/api/v1/cases/{case_id}", headers=headers).json()
    assert len(dossier["reference_photos"]) == 2

    # Delete 1 of 2 reference photos -> SUCCEEDS (200)
    del1 = client.delete(f"/api/v1/cases/{case_id}/references/{ref1_id}", headers=headers)
    assert del1.status_code == 200
    assert del1.json()["ref_id"] == ref1_id

    # Try deleting the remaining sole reference photo -> BLOCKED (400)
    del2 = client.delete(f"/api/v1/cases/{case_id}/references/{ref2_id}", headers=headers)
    assert del2.status_code == 400
    assert "Cannot delete the sole reference photo" in del2.json()["detail"]

def test_module_2_official_bulletin_generation():
    headers = get_auth_headers()

    # Get case 1 (Arunachalam Murugan)
    bulletin_res = client.get("/api/v1/cases/1/bulletin", headers=headers)
    assert bulletin_res.status_code == 200
    b = bulletin_res.json()
    assert b["reference_no"] == "MP-2026-001"
    assert b["subject_name"] == "Arunachalam Murugan"
    assert b["emergency_contact"] == "Emergency Control Room: 112 / 100"
    assert b["primary_photo_path"] is not None
    assert "Authorized law enforcement missing person bulletin" in b["legal_notice"]

def test_module_2_case_archiving_and_listing_filter():
    headers = get_auth_headers()

    # Archive Case 2
    archive_res = client.delete("/api/v1/cases/2", headers=headers)
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # List cases with status filter 'archived'
    archived_list = client.get("/api/v1/cases?status=archived", headers=headers).json()
    assert len(archived_list) >= 1
    assert any(c["id"] == 2 for c in archived_list)

    # Search by subject name
    search_list = client.get("/api/v1/cases?search=Arunachalam", headers=headers).json()
    assert len(search_list) >= 1
    assert search_list[0]["reference_no"] == "MP-2026-001"
