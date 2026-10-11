import io
import json
import pytest
import numpy as np
import cv2
import math
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import BASE_DIR

client = TestClient(app)

def create_synthetic_probe_bytes(width=300, height=300) -> bytes:
    """Creates a synthetic face portrait for test probe search."""
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

def create_blank_image_bytes(width=200, height=200) -> bytes:
    img = np.full((height, width, 3), 50, dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()

def get_auth_token(username="investigator", password="investigator123") -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


# =========================================================================
# TEST 1: Gallery Index Telemetry & L2 Unit Norm Invariant
# =========================================================================
def test_module_5_gallery_index_telemetry():
    """
    Verifies that the Matching Engine reports gallery size, vector dimension (128),
    calibrated operating points, and L2 unit norm invariant (||v||_2 = 1.0).
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/match/gallery", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "online"
    assert data["embedding_dimensions"] == 128
    assert data["active_enrolled_cases"] >= 2
    assert data["indexed_reference_embeddings"] >= 2
    assert "Cosine Similarity" in data["similarity_metric"]
    assert "Euclidean Distance" in data["distance_metric"]

    # Verify L2 Unit Norm Invariant
    norm_info = data["l2_unit_spherical_normalization"]
    assert norm_info["verified"] is True
    assert norm_info["invariant"] == "||v||₂ = 1.0"
    for sample_norm in norm_info["sample_norms"]:
        assert abs(sample_norm - 1.0) < 0.01

    # Verify calibrated operating points
    ops = data["calibrated_operating_points"]
    assert ops["high_confidence_verified"]["threshold"] >= 0.70
    assert ops["moderate_confidence_lead"]["threshold"] >= 0.50

    # Verify mandatory governance mandate
    assert "ranking signal" in data["governance_mandate"].lower()


# =========================================================================
# TEST 2: Ad-Hoc Gallery Search with Enrolled Ground Truth Matching Face
# =========================================================================
def test_module_5_adhoc_gallery_search_with_matching_identity():
    """
    Searches the enrolled gallery with sample_face.jpg (ground truth for MP-2026-001).
    Verifies Top-1 rank, high similarity score >= 0.70, Euclidean distance,
    probe HUD details, and governance flags.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    sample_img_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    assert sample_img_path.exists(), f"Sample image missing at {sample_img_path}"
    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    res = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 5, "min_threshold": 0.30},
        files={"file": ("probe.jpg", img_bytes, "image/jpeg")}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["gallery_size_searched"] >= 2
    assert data["candidates_returned_count"] >= 1

    # Check probe telemetry
    probe = data["probe"]
    assert len(probe["bbox"]) == 4
    assert len(probe["landmarks"]) == 5
    assert probe["confidence"] > 0.60
    assert probe["aligned_crop_base64"].startswith("data:image/jpeg;base64,")

    # Check Top-1 candidate is ground-truth match
    top1 = data["candidates"][0]
    assert top1["rank"] == 1
    assert top1["reference_no"] == "MP-2026-001"
    assert top1["similarity_score"] >= 0.70
    assert top1["confidence_tier"] == "High Confidence"
    assert top1["requires_human_review"] is True

    # Check mathematical relationship: d = sqrt(2*(1 - cos))
    expected_dist = math.sqrt(max(0.0, 2.0 * (1.0 - top1["similarity_score"])))
    assert abs(top1["euclidean_distance"] - expected_dist) < 0.01

    # Check latency metrics reported
    latency = data["latency_profile_ms"]
    assert latency["total_pipeline_ms"] > 0
    assert latency["vector_search_ms"] >= 0

    # AI Governance
    assert "ranking signal" in data["governance_notice"].lower()


# =========================================================================
# TEST 3: Strict Descending Rank Ordering & Euclidean Symmetry
# =========================================================================
def test_module_5_strict_rank_ordering_and_euclidean_consistency():
    """
    Verifies that all returned candidates are sorted in strictly non-increasing order
    of similarity score, and Euclidean distance monotonically increases as similarity decreases.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    probe_bytes = create_synthetic_probe_bytes()

    res = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 5, "min_threshold": 0.0},
        files={"file": ("probe.jpg", probe_bytes, "image/jpeg")}
    )
    assert res.status_code == 200
    candidates = res.json()["candidates"]

    if len(candidates) > 1:
        for i in range(len(candidates) - 1):
            assert candidates[i]["similarity_score"] >= candidates[i+1]["similarity_score"], (
                f"Candidate rank #{candidates[i]['rank']} score {candidates[i]['similarity_score']} "
                f"should be >= rank #{candidates[i+1]['rank']} score {candidates[i+1]['similarity_score']}"
            )
            # Euclidean distance should be non-decreasing
            assert candidates[i]["euclidean_distance"] <= candidates[i+1]["euclidean_distance"] + 1e-4


# =========================================================================
# TEST 4: Configurable Top-K Retrieval Parameter
# =========================================================================
def test_module_5_configurable_top_k_parameter():
    """Verifies that the Top-K limit is strictly respected and invalid values rejected."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    probe_bytes = create_synthetic_probe_bytes()

    # top_k = 1
    res1 = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 1, "min_threshold": 0.0},
        files={"file": ("probe.jpg", probe_bytes, "image/jpeg")}
    )
    assert res1.status_code == 200
    assert len(res1.json()["candidates"]) == 1

    # Invalid top_k = 0
    res_bad = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 0, "min_threshold": 0.0},
        files={"file": ("probe.jpg", probe_bytes, "image/jpeg")}
    )
    assert res_bad.status_code == 400


# =========================================================================
# TEST 5: Threshold Cutoff Filtering
# =========================================================================
def test_module_5_threshold_cutoff_filtering():
    """Verifies that candidates below min_threshold are cleanly filtered out."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    probe_bytes = create_synthetic_probe_bytes()

    # Extreme threshold of 0.9999 should filter out all non-identical candidates
    res_high = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 5, "min_threshold": 0.9999},
        files={"file": ("probe.jpg", probe_bytes, "image/jpeg")}
    )
    assert res_high.status_code == 200
    assert len(res_high.json()["candidates"]) == 0
    assert res_high.json()["candidates_returned_count"] == 0


# =========================================================================
# TEST 6: Zero Face Rejection in Probe Image
# =========================================================================
def test_module_5_zero_face_probe_rejection():
    """Verifies that searching with an image lacking a face returns HTTP 400 with helpful guidance."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    blank_bytes = create_blank_image_bytes()

    res = client.post(
        "/api/v1/match/search",
        headers=headers,
        data={"top_k": 5, "min_threshold": 0.30},
        files={"file": ("blank.jpg", blank_bytes, "image/jpeg")}
    )
    assert res.status_code == 400
    assert "no face detected" in res.json()["detail"].lower()


# =========================================================================
# TEST 7: Threshold Simulation & RBAC Protection
# =========================================================================
def test_module_5_threshold_simulation_and_rbac():
    """
    Verifies:
    1. Unauthenticated or public role cannot invoke matching endpoints.
    2. Threshold simulation calculates valid metrics.
    3. Mathematical property: Higher threshold yields lower or equal False Match Rate.
    """
    # 1. Unauthenticated access blocked
    res_unauth = client.get("/api/v1/match/gallery")
    assert res_unauth.status_code in [401, 403]

    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Simulate threshold 0.70
    sim_70 = client.post(
        "/api/v1/match/simulate-threshold",
        headers=headers,
        json={"threshold": 0.70}
    )
    assert sim_70.status_code == 200
    data_70 = sim_70.json()
    assert data_70["threshold"] == 0.70
    assert "tier_label" in data_70
    assert data_70["metrics"]["true_match_retention_percent"] >= 90.0

    # 3. Simulate threshold 0.85
    sim_85 = client.post(
        "/api/v1/match/simulate-threshold",
        headers=headers,
        json={"threshold": 0.85}
    )
    assert sim_85.status_code == 200
    data_85 = sim_85.json()

    # Monotonic property: FMR at 0.85 must be <= FMR at 0.70
    assert data_85["metrics"]["false_match_rate_percent"] <= data_70["metrics"]["false_match_rate_percent"]
    # Workload reduction at 0.85 must be >= Workload reduction at 0.70
    assert data_85["metrics"]["workload_reduction_percent"] >= data_70["metrics"]["workload_reduction_percent"]
