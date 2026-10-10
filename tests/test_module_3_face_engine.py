import os
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.face_engine import face_engine
from backend.config import BASE_DIR

client = TestClient(app)

def test_module_3_model_architecture_telemetry():
    res = client.get("/api/v1/faces/models")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"

    # Detection stage
    det = data["detection_stage"]
    assert det["model_name"] == "OpenCV YuNet DNN"
    assert det["landmarks_count"] == 5
    assert len(det["landmarks_mapping"]) == 5
    assert det["dynamic_resolution"] is True

    # Recognition stage
    rec = data["recognition_stage"]
    assert rec["model_name"] == "OpenCV SFace DNN"
    assert rec["output_dimensions"] == 128
    assert "L2" in rec["normalization"]
    assert rec["canonical_crop_size"] == "112x112"
    assert rec["calibrated_thresholds"]["high_confidence_verified"] == 0.70

def test_module_3_face_detection_and_alignment_pipeline():
    sample_face_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    with open(sample_face_path, "rb") as f:
        img_bytes = f.read()

    res = client.post("/api/v1/faces/analyze", files={"file": ("sample.jpg", img_bytes, "image/jpeg")})
    assert res.status_code == 200
    data = res.json()

    assert data["faces_detected_count"] == 1
    assert data["image_dimensions"]["width"] > 0
    assert data["image_dimensions"]["height"] > 0

    # Latency telemetry
    latency = data["latency_profile_ms"]
    assert latency["detection_ms"] > 0
    assert latency["alignment_ms"] > 0
    assert latency["feature_extraction_ms"] > 0
    assert latency["total_pipeline_ms"] < 500  # Well within CPU real-time budget

    # Detection details
    face = data["detections"][0]
    assert len(face["bbox"]) == 4
    assert len(face["landmarks"]) == 5
    assert face["confidence"] >= 0.60
    assert face["sharpness_score"] > 0
    assert face["aligned_crop_base64"].startswith("data:image/jpeg;base64,")

    # 128-D vector summary
    summary = face["embedding_summary"]
    assert summary["dimensions"] == 128
    assert abs(summary["l2_norm"] - 1.0) < 1e-4  # L2 spherical unit norm
    assert len(summary["preview"]) == 8

def test_module_3_multi_face_detection():
    # Construct synthetic 2-face image
    single_face_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    img = cv2.imread(str(single_face_path))
    two_faces = np.hstack([img, img])
    _, encoded = cv2.imencode(".jpg", two_faces)

    res = client.post("/api/v1/faces/analyze", files={"file": ("two_faces.jpg", encoded.tobytes(), "image/jpeg")})
    assert res.status_code == 200
    data = res.json()
    assert data["faces_detected_count"] == 2
    assert len(data["detections"]) == 2

    # Verify both faces received separate bounding boxes and embeddings
    bbox1 = data["detections"][0]["bbox"]
    bbox2 = data["detections"][1]["bbox"]
    assert bbox1 != bbox2
    assert len(data["detections"][0]["embedding"]) == 128
    assert len(data["detections"][1]["embedding"]) == 128

def test_module_3_zero_face_detection():
    zero_face_path = BASE_DIR / "sample_data" / "sample_chicky.jpg"
    with open(zero_face_path, "rb") as f:
        img_bytes = f.read()

    res = client.post("/api/v1/faces/analyze", files={"file": ("zero.jpg", img_bytes, "image/jpeg")})
    assert res.status_code == 200
    data = res.json()
    assert data["faces_detected_count"] == 0
    assert len(data["detections"]) == 0

def test_module_3_pairwise_face_comparison_same_identity():
    sample_face_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    with open(sample_face_path, "rb") as f:
        bytes1 = f.read()

    res = client.post(
        "/api/v1/faces/compare",
        files={
            "file1": ("face1.jpg", bytes1, "image/jpeg"),
            "file2": ("face2.jpg", bytes1, "image/jpeg")
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["cosine_similarity"] >= 0.99
    assert data["similarity_percent"] >= 99.0
    assert data["euclidean_distance"] <= 0.15
    assert data["disposition"] == "verified"
    assert "image1" in data and "image2" in data

def test_module_3_pairwise_face_comparison_different_identities():
    img1_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    img2_path = BASE_DIR / "sample_data" / "sample_messi.jpg"
    with open(img1_path, "rb") as f1, open(img2_path, "rb") as f2:
        res = client.post(
            "/api/v1/faces/compare",
            files={
                "file1": ("person1.jpg", f1.read(), "image/jpeg"),
                "file2": ("person2.jpg", f2.read(), "image/jpeg")
            }
        )
    assert res.status_code == 200
    data = res.json()
    assert data["cosine_similarity"] < 0.60
    assert data["disposition"] == "non_match"
    assert data["euclidean_distance"] > 0.80

def test_module_3_mathematical_invariants():
    # Load 2 distinct faces
    img1 = cv2.imread(str(BASE_DIR / "sample_data" / "sample_face.jpg"))
    img2 = cv2.imread(str(BASE_DIR / "sample_data" / "sample_messi.jpg"))

    faces1 = face_engine.detect_faces(img1)
    faces2 = face_engine.detect_faces(img2)
    assert len(faces1) == 1
    assert len(faces2) == 1

    vec1 = face_engine.extract_embedding(img1, faces1[0]["raw_face"])
    vec2 = face_engine.extract_embedding(img2, faces2[0]["raw_face"])

    # 1. Dimension invariant
    assert len(vec1) == 128
    assert len(vec2) == 128

    # 2. L2 unit norm invariant
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    assert abs(norm1 - 1.0) < 1e-4
    assert abs(norm2 - 1.0) < 1e-4

    # 3. Symmetry invariant: sim(a, b) == sim(b, a)
    sim_12 = face_engine.cosine_similarity(vec1, vec2)
    sim_21 = face_engine.cosine_similarity(vec2, vec1)
    assert abs(sim_12 - sim_21) < 1e-6

    # 4. Identity invariant: sim(a, a) == 1.0
    sim_11 = face_engine.cosine_similarity(vec1, vec1)
    assert abs(sim_11 - 1.0) < 1e-4

    # 5. Range invariant: -1.0 <= sim <= 1.0
    assert -1.0 <= sim_12 <= 1.0
