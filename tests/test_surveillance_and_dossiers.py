import os
import io
import json
import pytest
import numpy as np
import cv2
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def get_auth_token(username="investigator", password="investigator123") -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_admin_token() -> str:
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]

class TestSurveillanceAndDossiers:
    """
    Test suite for Module 7/8 extensions:
    Live CCTV surveillance management, stream ingestion, watchlist matching,
    real-time alert dispatch, and forensic PDF/image certificate generation.
    """

    def test_01_list_cctv_cameras(self):
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get("/api/v1/surveillance/cameras", headers=headers)
        assert res.status_code == 200
        cameras = res.json()
        assert len(cameras) >= 4
        codes = [c["camera_code"] for c in cameras]
        assert "CAM-METRO-01" in codes
        assert "CAM-TRANSIT-04" in codes

    def test_02_register_and_delete_cctv_camera(self):
        admin_token = get_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Register new camera
        new_cam = {
            "camera_code": "CAM-TEST-99",
            "name": "North Gate CCTV Checkpoint",
            "location_name": "Perambur Railway Flyover",
            "latitude": 13.111,
            "longitude": 80.234,
            "stream_url": "rtsp://surveillance.test/cam-99",
            "fps": 20.0,
            "status": "active"
        }
        res = client.post("/api/v1/surveillance/cameras", json=new_cam, headers=headers)
        assert res.status_code == 201
        created = res.json()
        assert created["camera_code"] == "CAM-TEST-99"
        cam_id = created["id"]

        # Duplicate rejection
        dup_res = client.post("/api/v1/surveillance/cameras", json=new_cam, headers=headers)
        assert dup_res.status_code == 400

        # Delete camera
        del_res = client.delete(f"/api/v1/surveillance/cameras/{cam_id}", headers=headers)
        assert del_res.status_code == 200

    def test_03_scan_camera_frame_with_face_detection(self):
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        ref_path = Path("storage/references/ref_1_primary.jpg")
        assert ref_path.exists(), "Reference photo missing for test"

        with open(ref_path, "rb") as f:
            photo_bytes = f.read()

        # Upload probe frame to CAM-METRO-01 (camera_id=1)
        files = {"frame": ("live_feed_snapshot.jpg", photo_bytes, "image/jpeg")}
        res = client.post("/api/v1/surveillance/cameras/1/scan-frame", files=files, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["camera_code"] == "CAM-METRO-01"
        assert data["faces_detected"] >= 1
        assert len(data["alerts_triggered"]) >= 1

        alert = data["alerts_triggered"][0]
        assert alert["case_id"] == 1
        assert alert["similarity_score"] >= 0.70
        assert alert["confidence_tier"] == "high"

    def test_04_surveillance_alerts_list_and_acknowledgment(self):
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        # List alerts
        res = client.get("/api/v1/surveillance/alerts", headers=headers)
        assert res.status_code == 200
        alerts = res.json()
        assert len(alerts) >= 1

        target_alert = alerts[0]
        alert_id = target_alert["id"]

        # Acknowledge / dispatch alert
        patch_res = client.patch(
            f"/api/v1/surveillance/alerts/{alert_id}/status",
            json={"status": "dispatched", "notes": "Tactical unit dispatched to metro platform"},
            headers=headers
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["new_status"] == "dispatched"

    def test_05_simulate_surveillance_stream(self):
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post("/api/v1/surveillance/simulate-stream", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["alerts_generated"] >= 1

    def test_06_forensic_certificate_export(self):
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Candidate match ID 1 exists from seed data
        res = client.get("/api/v1/candidates/1/export-dossier", headers=headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/png"
        assert len(res.content) > 10000

        # Verify it's a valid PNG
        nparr = np.frombuffer(res.content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None
        assert img.shape[1] == 1000  # width
        assert img.shape[0] == 1300  # height

    def test_07_emergency_poster_export(self):
        # Case ID 1 exists
        res = client.get("/api/v1/cases/1/export-poster")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/png"
        assert len(res.content) > 10000

        nparr = np.frombuffer(res.content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None
        assert img.shape[1] == 1000
        assert img.shape[0] == 1400
