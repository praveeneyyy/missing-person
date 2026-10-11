import csv
import io
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app

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
# 1. ACCESS CONTROL & RBAC ENFORCEMENT
# ==============================================================================

def test_module_7_audit_access_control():
    """Verifies that audit, export, governance, and security health enforce RBAC."""
    # 1. Unauthenticated requests are rejected
    assert client.get("/api/v1/audit").status_code == 401
    assert client.get("/api/v1/audit/export").status_code == 401
    assert client.get("/api/v1/audit/governance").status_code == 401
    assert client.get("/api/v1/system/security-health").status_code == 401

    # 2. Authenticated investigator has access
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/audit", headers=headers).status_code == 200
    assert client.get("/api/v1/audit/export", headers=headers).status_code == 200
    assert client.get("/api/v1/audit/governance", headers=headers).status_code == 200
    assert client.get("/api/v1/system/security-health", headers=headers).status_code == 200

    # 3. Authenticated admin has access
    admin_token = get_admin_token()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert client.get("/api/v1/audit", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/audit/export", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/audit/governance", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/system/security-health", headers=admin_headers).status_code == 200


# ==============================================================================
# 2. AUDIT LOG LISTING, FILTERING & CRYPTOGRAPHIC SEAL
# ==============================================================================

def test_module_7_audit_listing_with_filters():
    """Verifies audit log retrieval, flexible filtering, and cryptographic SHA-256 seal."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Standard fetch
    res = client.get("/api/v1/audit?limit=20", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0

    # Verify cryptographic seal in response headers
    seal = res.headers.get("X-Audit-Checksum-SHA256")
    assert seal is not None
    assert len(seal) == 64  # Valid SHA-256 hex digest
    total_count = res.headers.get("X-Total-Count")
    assert total_count is not None
    assert int(total_count) >= len(logs)

    # Verify log entry fields
    first_log = logs[0]
    assert "id" in first_log
    assert "created_at" in first_log
    assert "actor_name" in first_log
    assert "action" in first_log
    assert "resource_type" in first_log
    assert "resource_id" in first_log

    # 2. Action filter
    action_to_search = first_log["action"]
    res_filtered = client.get(f"/api/v1/audit?action={action_to_search}", headers=headers)
    assert res_filtered.status_code == 200
    filtered_logs = res_filtered.json()
    for log in filtered_logs:
        assert action_to_search in log["action"]

    # 3. Actor filter
    res_actor = client.get(f"/api/v1/audit?actor={first_log['actor_name']}", headers=headers)
    assert res_actor.status_code == 200
    assert len(res_actor.json()) > 0

    # 4. Pagination (limit and offset)
    res_page = client.get("/api/v1/audit?limit=2&offset=1", headers=headers)
    assert res_page.status_code == 200
    assert len(res_page.json()) <= 2


# ==============================================================================
# 3. RFC-4180 CSV FORENSIC CHAIN OF CUSTODY EXPORT
# ==============================================================================

def test_module_7_audit_export_rfc4180_csv():
    """Verifies RFC-4180 compliant CSV export with evidentiary comments and checksums."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/audit/export?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")

    # Content-Disposition header contains download filename
    disposition = res.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "forensic_chain_of_custody_" in disposition
    assert ".csv" in disposition

    # Evidentiary integrity headers
    checksum = res.headers.get("X-Audit-Checksum-SHA256")
    seq_checksum = res.headers.get("X-Record-Sequence-SHA256")
    total_records = res.headers.get("X-Total-Records")
    assert checksum is not None and len(checksum) == 64
    assert seq_checksum is not None and len(seq_checksum) == 64
    assert total_records is not None and int(total_records) > 0

    csv_text = res.text
    # Verify law enforcement provenance comments
    assert "# LAW ENFORCEMENT CHAIN OF CUSTODY AUDIT LOG EXPORT" in csv_text
    assert "# STANDARD_COMPLIANCE: ISO/IEC 27037:2012 Digital Evidence Handling" in csv_text
    assert f"# SHA256_INTEGRITY_SEAL: {seq_checksum}" in csv_text

    # Parse and verify RFC-4180 CSV rows
    lines = [line for line in csv_text.splitlines() if not line.startswith("#")]
    assert len(lines) >= 2  # Header + at least one data row

    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    header = rows[0]
    assert header == [
        "log_id",
        "timestamp_utc",
        "actor_id",
        "actor_name",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
        "details_json"
    ]
    data_rows = rows[1:]
    assert len(data_rows) == int(total_records)


# ==============================================================================
# 4. STRUCTURED FORENSIC JSON AUDIT PACKAGE EXPORT
# ==============================================================================

def test_module_7_audit_export_forensic_json():
    """Verifies ISO/IEC 27037 structured forensic JSON export package."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/audit/export?format=json", headers=headers)
    assert res.status_code == 200
    assert "application/json" in res.headers.get("content-type", "")

    data = res.json()
    assert "export_metadata" in data
    assert "audit_trail" in data

    meta = data["export_metadata"]
    assert meta["standard"] == "ISO/IEC 27037:2012 Digital Evidence Handling"
    assert "export_timestamp_utc" in meta
    assert "exporting_officer" in meta
    assert meta["exporting_officer"]["role"] == "investigator"
    assert "sha256_checksum" in meta
    assert len(meta["sha256_checksum"]) == 64
    assert meta["total_records"] == len(data["audit_trail"])

    # Verify audit event payload
    events = data["audit_trail"]
    assert len(events) > 0
    first_event = events[0]
    assert "id" in first_event
    assert "action" in first_event
    assert "actor_name" in first_event
    assert "resource_type" in first_event


# ==============================================================================
# 5. AUDIT IMMUTABILITY & TAMPER RESISTANCE
# ==============================================================================

def test_module_7_audit_immutability():
    """Verifies that audit logs cannot be modified or deleted via API."""
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to DELETE audit logs -> 405 Method Not Allowed
    res_del = client.delete("/api/v1/audit", headers=headers)
    assert res_del.status_code == 405

    # Attempt to PUT/modify audit logs -> 405 Method Not Allowed
    res_put = client.put("/api/v1/audit", headers=headers)
    assert res_put.status_code == 405

    # Attempt to DELETE specific log -> 405
    res_del_item = client.delete("/api/v1/audit/1", headers=headers)
    assert res_del_item.status_code in [404, 405]


# ==============================================================================
# 6. AI GOVERNANCE, ETHICS & DEMOGRAPHIC PARITY
# ==============================================================================

def test_module_7_ai_governance_report():
    """Verifies AI governance metrics, 100% human-in-the-loop compliance, and model disclosures."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/audit/governance", headers=headers)
    assert res.status_code == 200
    gov = res.json()

    assert gov["governance_status"] == "COMPLIANT"

    # 1. Non-Autonomous Human-in-the-Loop Guarantee
    hitl = gov["human_in_the_loop"]
    assert hitl["autonomous_decisions_count"] == 0
    assert hitl["human_in_the_loop_compliance_rate_percent"] == 100.0
    assert hitl["total_cases_enrolled"] >= 0
    assert hitl["total_candidate_leads"] >= 0

    # 2. Operating Point Calibration & Score Stability
    calib = gov["operating_point_calibration"]
    assert calib["operating_point_tau"] == 0.70
    assert calib["review_floor_tau"] == 0.50
    assert calib["threshold_calibration_status"] == "Calibrated & Stable"

    # 3. Demographic Fairness & Balance Monitoring
    fairness = gov["demographic_fairness"]
    assert "case_gender_distribution" in fairness
    assert "case_age_distribution" in fairness
    assert "match_retrieval_gender_distribution" in fairness
    assert "parity_monitoring_status" in fairness

    # 4. Model Lineage & Open Source Licensing (BSD 3-Clause)
    lineage = gov["model_lineage"]
    assert lineage["face_detector"]["license"] == "BSD 3-Clause"
    assert lineage["face_detector"]["model_name"].startswith("YuNet")
    assert lineage["face_recognizer"]["license"] == "BSD 3-Clause"
    assert lineage["face_recognizer"]["embedding_dimensions"] == 128
    assert "ethical_disclaimer" in lineage

    # Verify alias route /api/v1/governance/metrics returns identical payload
    res_alias = client.get("/api/v1/governance/metrics", headers=headers)
    assert res_alias.status_code == 200
    assert res_alias.json()["governance_status"] == "COMPLIANT"


# ==============================================================================
# 7. SYSTEM SECURITY HEALTH & HARDENING TELEMETRY
# ==============================================================================

def test_module_7_system_security_health_check():
    """Verifies SQLite B-Tree integrity, media isolation, model checksums, and auth hardening."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/system/security-health", headers=headers)
    assert res.status_code == 200
    sec = res.json()

    assert sec["status"] == "HARDENED_OPERATIONAL"

    # 1. SQLite B-Tree Integrity
    db = sec["database_integrity"]
    assert db["is_healthy"] is True
    assert db["sqlite_pragma_check"].lower() == "ok"
    assert db["database_size_bytes"] > 0
    assert db["foreign_keys_enabled"] is True

    # 2. Private Media Storage Isolation
    storage = sec["storage_isolation"]
    assert storage["references_isolated"] is True
    assert storage["sightings_isolated"] is True
    assert storage["path_traversal_mitigation"] == "Enforced"

    # 3. Biometric Model Weights Integrity
    models = sec["model_weights_integrity"]
    assert models["models_tamper_free"] is True
    assert models["yunet_verified"] is True
    assert models["sface_verified"] is True
    assert len(models["yunet_sha256"]) == 64
    assert len(models["sface_sha256"]) == 64

    # 4. Security Hardening Telemetry
    hardening = sec["security_hardening"]
    assert hardening["jwt_algorithm"] == "HS256"
    assert "PBKDF2-SHA256" in hardening["password_hashing"]
    assert "10 req / 60 sec" in hardening["sighting_intake_rate_limiting"]
    assert hardening["active_authorized_accounts"] > 0


# ==============================================================================
# 8. DASHBOARD STATS TELEMETRY INTEGRATION
# ==============================================================================

def test_module_7_dashboard_stats_telemetry():
    """Verifies operational dashboard stats include audit counters and model telemetry."""
    token = get_staff_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()

    assert "open_cases" in stats
    assert "total_sightings" in stats
    assert "pending_reviews" in stats
    assert "verified_matches" in stats
    assert "enrolled_faces" in stats
    assert "total_audit_events" in stats
    assert stats["total_audit_events"] > 0
    assert stats["system_health"] == "Operational"
    assert "YuNet" in stats["detector_model"]
    assert "SFace" in stats["recognizer_model"]
