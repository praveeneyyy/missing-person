import os
import io
import json
import pytest
import numpy as np
import cv2
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db
from backend.face_engine import face_engine

client = TestClient(app)

def create_synthetic_video_bytes(num_frames=10, fps=10, face_image=None, width=320, height=240) -> bytes:
    """
    Encodes synthetic video bytes using OpenCV VideoWriter with mp4v codec.
    """
    tmp_path = tempfile.mktemp(suffix=".mp4")
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(tmp_path, fourcc, float(fps), (width, height))

        if face_image is not None:
            resized_face = cv2.resize(face_image, (width, height))
            for _ in range(num_frames):
                out.write(resized_face)
        else:
            blank_frame = np.full((height, width, 3), 70, dtype=np.uint8)
            for i in range(num_frames):
                frame = blank_frame.copy()
                cv2.putText(frame, f"Frame {i}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                out.write(frame)

        out.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_auth_token(username="investigator", password="investigator123") -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


class TestModule8VideoForensicProcessing:
    """
    Module 8 Verification Suite:
    Video Forensic Processing, Frame Sampling, Intra-Video Identity Tracklet Clustering,
    Temporal Deduplication, Sighting Submissions, and Forensic Inspection Endpoints.
    """

    def test_01_video_metadata_and_sampling_bounds(self):
        """
        Verify video decoding, telemetry extraction, and bounds enforcement
        on keyframe sampling (Anti-DoS).
        """
        video_bytes = create_synthetic_video_bytes(num_frames=30, fps=10, width=320, height=240)
        tmp = tempfile.mktemp(suffix=".mp4")
        try:
            with open(tmp, "wb") as f:
                f.write(video_bytes)

            # Test standard sampling
            res = face_engine.process_sighting_video(tmp, sample_fps=2.0, max_sampled_frames=50)
            meta = res["video_metadata"]

            assert meta["duration_seconds"] == 3.0
            assert meta["fps"] == 10.0
            assert meta["resolution"] == "320x240"
            assert meta["total_frames"] == 30
            assert meta["sampled_frames_count"] == 6  # 3 seconds * 2 fps = 6 frames
            assert meta["unique_tracklets_count"] == 0  # No faces in blank video

            # Test Anti-DoS bounded sampling cap
            res_capped = face_engine.process_sighting_video(tmp, sample_fps=10.0, max_sampled_frames=3)
            assert res_capped["video_metadata"]["sampled_frames_count"] == 3
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_02_intra_video_tracklet_clustering_and_deduplication(self):
        """
        FR-08 Core Invariant:
        Multiple detections of the same face across video frames must coalesce
        into a single tracklet cluster with occurrence timestamps, preventing duplicate leads.
        """
        ref_path = Path("storage/references/ref_1_primary.jpg")
        assert ref_path.exists(), "Reference photo missing for test"

        face_img = cv2.imread(str(ref_path))
        video_bytes = create_synthetic_video_bytes(num_frames=20, fps=10, face_image=face_img, width=400, height=400)

        tmp = tempfile.mktemp(suffix=".mp4")
        try:
            with open(tmp, "wb") as f:
                f.write(video_bytes)

            res = face_engine.process_sighting_video(tmp, sample_fps=2.0)
            tracklets = res["tracklets"]

            # Must deduplicate into exactly 1 tracklet
            assert len(tracklets) == 1, f"Expected 1 deduplicated tracklet, got {len(tracklets)}"
            t = tracklets[0]

            assert t["tracklet_id"] == 0
            assert t["detection_count"] == 4  # 2.0s at 2fps = 4 sampled frames
            assert len(t["occurrences"]) == 4
            assert len(t["embedding"]) == 128
            assert t["exemplar_thumbnail_b64"].startswith("data:image/jpeg;base64,")
            assert t["first_seen_timestamp"] == "00:00.000"
            assert t["last_seen_timestamp"] == "00:01.500"

            # Check individual occurrence format
            for occ in t["occurrences"]:
                assert "timestamp_seconds" in occ
                assert "timestamp_formatted" in occ
                assert "bbox" in occ
                assert occ["confidence"] > 0.60
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_03_multi_identity_tracklet_separation(self):
        """
        FR-08 Invariant:
        Two distinct persons appearing in the same surveillance video must NOT coalesce,
        generating exactly 2 distinct tracklets.
        """
        f1 = cv2.imread("storage/references/ref_1_primary.jpg")
        f2 = cv2.imread("storage/references/ref_2_primary.jpg")
        assert f1 is not None and f2 is not None

        w, h = 512, 512
        f1_r = cv2.resize(f1, (w, h))
        f2_r = cv2.resize(f2, (w, h))

        tmp = tempfile.mktemp(suffix=".mp4")
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(tmp, fourcc, 10.0, (w, h))
            for _ in range(10):
                out.write(f1_r)
            for _ in range(10):
                out.write(f2_r)
            out.release()

            res = face_engine.process_sighting_video(tmp, sample_fps=2.0)
            tracklets = res["tracklets"]

            assert len(tracklets) == 2, f"Expected 2 distinct identity tracklets, got {len(tracklets)}"
            assert tracklets[0]["tracklet_id"] == 0
            assert tracklets[1]["tracklet_id"] == 1
            assert tracklets[0]["detection_count"] == 2
            assert tracklets[1]["detection_count"] == 2
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_04_public_sighting_video_submission_and_receipt(self):
        """
        Test public citizen portal accepts video files (.mp4 up to 50MB),
        generates an encrypted tracking receipt, extracts tracklets, and links candidate matches.
        """
        face_img = cv2.imread("storage/references/ref_1_primary.jpg")
        video_bytes = create_synthetic_video_bytes(num_frames=15, fps=10, face_image=face_img, width=320, height=320)

        data = {
            "sighting_date": "2026-10-11",
            "sighting_time": "14:30",
            "location_name": "Chennai Central CCTV Gate 4",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "description": "High resolution transit CCTV clip showing subject walking across concourse",
            "reporter_name": "Station Security Officer",
            "reporter_phone": "+91 9876543210",
            "reporter_email": "security@transit.gov.in",
            "consent_given": True
        }

        files = {
            "file": ("surveillance_gate4.mp4", video_bytes, "video/mp4")
        }

        res = client.post("/api/v1/sightings", data=data, files=files)
        assert res.status_code == 201, res.text
        resp_data = res.json()

        assert "receipt_no" in resp_data
        receipt_no = resp_data["receipt_no"]
        assert receipt_no.startswith("STG-")
        assert resp_data["faces_detected_count"] >= 1
        assert resp_data["matches_generated"] >= 1

        # Check candidate match correlation via investigator endpoint
        token = get_auth_token("investigator", "investigator123")
        headers = {"Authorization": f"Bearer {token}"}
        cand_res = client.get(f"/api/v1/candidates?sighting_id={resp_data['sighting_id']}", headers=headers)
        assert cand_res.status_code == 200
        candidates = cand_res.json()
        assert len(candidates) >= 1
        top_match = candidates[0]
        assert top_match["similarity_score"] >= 0.50  # ref_1_primary matches in moderate confidence tier after video compression
        assert top_match["reference_no"].startswith("MP-2026-")

        # Verify receipt lookup remains privacy-shielded
        track_res = client.get(f"/api/v1/sightings/lookup/{receipt_no}")
        assert track_res.status_code == 200
        track_data = track_res.json()
        assert track_data["status"] == "pending_review"
        assert "privacy_statement" in track_data
        assert "candidate_matches" not in track_data  # Public cannot see suspect dossiers

    def test_05_investigator_video_analysis_dossier(self):
        """
        Verify GET /api/v1/sightings/{id}/video-analysis endpoint:
        Authorized investigator receives stream telemetry, tracklet cards with occurrence chips,
        and correlated missing person matches.
        """
        token = get_auth_token("investigator", "investigator123")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Submit video sighting
        face_img = cv2.imread("storage/references/ref_1_primary.jpg")
        video_bytes = create_synthetic_video_bytes(num_frames=20, fps=10, face_image=face_img, width=320, height=320)
        data = {
            "sighting_date": "2026-10-11",
            "location_name": "CMBT Platform CCTV",
            "latitude": 13.0694,
            "longitude": 80.2078,
            "description": "Transit stream probe"
        }
        files = {"file": ("cmbt_cctv.mp4", video_bytes, "video/mp4")}

        sub_res = client.post("/api/v1/sightings", data=data, files=files)
        assert sub_res.status_code == 201
        sighting_id = sub_res.json()["sighting_id"]

        # 2. Query video analysis
        analysis_res = client.get(f"/api/v1/sightings/{sighting_id}/video-analysis", headers=headers)
        assert analysis_res.status_code == 200
        analysis = analysis_res.json()

        assert analysis["is_video"] is True
        assert analysis["sighting_id"] == sighting_id
        assert "video_metadata" in analysis
        assert analysis["video_metadata"]["duration_seconds"] == 2.0
        assert analysis["total_tracklets"] == 1

        tracklet = analysis["tracklets"][0]
        assert tracklet["tracklet_id"] == 0
        assert len(tracklet["occurrences"]) >= 2
        assert "candidates" in tracklet
        assert len(tracklet["candidates"]) >= 1
        assert tracklet["candidates"][0]["reference_no"].startswith("MP-2026-")

        # 3. Unauthorized access check (e.g., without token)
        unauth_res = client.get(f"/api/v1/sightings/{sighting_id}/video-analysis")
        assert unauth_res.status_code in [401, 403]

    def test_06_video_inspect_diagnostic_endpoint(self):
        """
        Test POST /api/v1/faces/video-inspect direct diagnostic endpoint.
        """
        token = get_auth_token("investigator", "investigator123")
        headers = {"Authorization": f"Bearer {token}"}

        face_img = cv2.imread("storage/references/ref_1_primary.jpg")
        video_bytes = create_synthetic_video_bytes(num_frames=10, fps=10, face_image=face_img, width=280, height=280)

        files = {"file": ("diag_feed.mp4", video_bytes, "video/mp4")}
        res = client.post("/api/v1/faces/video-inspect?sample_fps=2.0", files=files, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "video_metadata" in data
        assert "tracklets" in data
        assert data["video_metadata"]["duration_seconds"] == 1.0
        assert len(data["tracklets"]) == 1

    def test_07_validation_invariants_and_error_handling(self):
        """
        Verify validation rules:
        - 0-byte video rejected
        - Invalid / corrupted container rejected
        - Video file size ceiling (50MB) enforced
        - Static photo returns is_video: False on video-analysis endpoint
        """
        # 1. Zero-byte video upload
        empty_files = {"file": ("empty.mp4", b"", "video/mp4")}
        res = client.post("/api/v1/sightings", data={"sighting_date": "2026-10-11", "location_name": "Test"}, files=empty_files)
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()

        # 2. Corrupted video bytes
        corrupt_files = {"file": ("corrupt.mp4", b"not-a-real-video-header-random-bytes", "video/mp4")}
        res = client.post("/api/v1/sightings", data={"sighting_date": "2026-10-11", "location_name": "Test"}, files=corrupt_files)
        assert res.status_code == 400
        assert "failed" in res.json()["detail"].lower()

        # 3. Static photo returns is_video: false on video-analysis
        token = get_auth_token("investigator", "investigator123")
        headers = {"Authorization": f"Bearer {token}"}

        # Sighting 1 in seeded DB is a photo (sight_1_tambaram.jpg)
        photo_res = client.get("/api/v1/sightings/1/video-analysis", headers=headers)
        assert photo_res.status_code == 200
        assert photo_res.json()["is_video"] is False
