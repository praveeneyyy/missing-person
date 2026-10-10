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

def test_module_1_admin_user_provisioning_and_rbac():
    # 1. Login as Administrator (Dr. S. Gayathri)
    admin_login = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Login as Investigator (Praveen)
    inv_login = client.post("/api/v1/auth/login", json={
        "username": "investigator",
        "password": "investigator123"
    })
    assert inv_login.status_code == 200
    inv_token = inv_login.json()["access_token"]
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    # 3. Investigator attempts to list officers -> Must be FORBIDDEN (403)
    inv_list_res = client.get("/api/v1/auth/users", headers=inv_headers)
    assert inv_list_res.status_code == 403
    assert "Access denied" in inv_list_res.json()["detail"]

    # 4. Admin lists officers -> Must SUCCEED (200)
    admin_list_res = client.get("/api/v1/auth/users", headers=admin_headers)
    assert admin_list_res.status_code == 200
    officers = admin_list_res.json()
    assert len(officers) >= 2

    # 5. Investigator attempts to provision a new officer -> Must be FORBIDDEN (403)
    new_officer_payload = {
        "username": "officer_kumar",
        "email": "kumar.r@missingpersons.gov.in",
        "password": "officerPassword123",
        "full_name": "R. Kumar",
        "badge_number": "INV-9021",
        "role": "investigator"
    }
    inv_create_res = client.post("/api/v1/auth/users", headers=inv_headers, json=new_officer_payload)
    assert inv_create_res.status_code == 403

    # 6. Admin provisions the new officer -> Must SUCCEED (201 Created)
    admin_create_res = client.post("/api/v1/auth/users", headers=admin_headers, json=new_officer_payload)
    assert admin_create_res.status_code == 201
    created_user = admin_create_res.json()
    assert created_user["username"] == "officer_kumar"
    assert created_user["badge_number"] == "INV-9021"
    user_id = created_user["id"]

    # 7. New officer logs in -> Must SUCCEED (200)
    officer_login = client.post("/api/v1/auth/login", json={
        "username": "officer_kumar",
        "password": "officerPassword123"
    })
    assert officer_login.status_code == 200
    assert officer_login.json()["user"]["badge_number"] == "INV-9021"

    # 8. Admin deactivates the officer account -> Must SUCCEED (200)
    deactivate_res = client.put(f"/api/v1/auth/users/{user_id}/status", headers=admin_headers, json={"is_active": False})
    assert deactivate_res.status_code == 200

    # 9. Deactivated officer attempts login -> Must be FORBIDDEN (403)
    blocked_login = client.post("/api/v1/auth/login", json={
        "username": "officer_kumar",
        "password": "officerPassword123"
    })
    assert blocked_login.status_code == 403
    assert "Account is inactive" in blocked_login.json()["detail"]

    # 10. Admin re-activates account -> Officer can login again
    reactivate_res = client.put(f"/api/v1/auth/users/{user_id}/status", headers=admin_headers, json={"is_active": True})
    assert reactivate_res.status_code == 200
    resumed_login = client.post("/api/v1/auth/login", json={
        "username": "officer_kumar",
        "password": "officerPassword123"
    })
    assert resumed_login.status_code == 200

    # 11. Test logout audit endpoint
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {resumed_login.json()['access_token']}"})
    assert logout_res.status_code == 200
