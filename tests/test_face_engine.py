import os
import pytest
import cv2
import numpy as np
from pathlib import Path

from backend.face_engine import FaceEngine
from backend.config import BASE_DIR, YUNET_MODEL_PATH, SFACE_MODEL_PATH

@pytest.fixture
def engine():
    return FaceEngine(YUNET_MODEL_PATH, SFACE_MODEL_PATH)

def test_engine_initialization(engine):
    assert engine.recognizer is not None

def test_detect_faces_valid(engine):
    img_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    assert img_path.exists(), "Test image must exist"
    img = cv2.imread(str(img_path))
    faces = engine.detect_faces(img)
    assert len(faces) >= 1
    face = faces[0]
    assert "bbox" in face
    assert len(face["bbox"]) == 4
    assert face["confidence"] > 0.5
    assert len(face["landmarks"]) == 5

def test_validate_reference_photo_success(engine):
    img_path = BASE_DIR / "sample_data" / "sample_face.jpg"
    img = cv2.imread(str(img_path))
    val = engine.validate_reference_photo(img)
    assert val["model_version"] == "v1.0-onnx"
    assert len(val["embedding"]) == 128
    # Embedding must be normalized (L2 norm approx 1.0)
    norm = np.linalg.norm(np.array(val["embedding"]))
    assert np.isclose(norm, 1.0, atol=1e-3)

def test_validate_reference_photo_rejects_zero_faces(engine):
    # Blank image with no faces
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    with pytest.raises(ValueError) as exc:
        engine.validate_reference_photo(blank)
    assert "No human face was detected" in str(exc.value)

def test_cosine_similarity(engine):
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    assert np.isclose(engine.cosine_similarity(v1, v1), 1.0)

    # Orthogonal vectors
    v2 = [0.0, 1.0, 0.0]
    assert np.isclose(engine.cosine_similarity(v1, v2), 0.0)

    # Opposing vectors
    v3 = [-1.0, 0.0, 0.0]
    assert np.isclose(engine.cosine_similarity(v1, v3), -1.0)

def test_rank_candidates_ordering(engine):
    query = [1.0, 0.0, 0.0]
    enrolled = [
        {"case_id": 1, "reference_no": "MP-01", "full_name": "Person A", "embedding": [0.2, 0.8, 0.0]},
        {"case_id": 2, "reference_no": "MP-02", "full_name": "Person B", "embedding": [0.95, 0.05, 0.0]},
        {"case_id": 3, "reference_no": "MP-03", "full_name": "Person C", "embedding": [0.5, 0.5, 0.0]},
    ]
    ranked = engine.rank_candidates(query, enrolled, top_k=3)
    assert len(ranked) == 3
    # Case 2 should rank 1st with highest similarity
    assert ranked[0]["case_id"] == 2
    assert ranked[0]["rank"] == 1
    assert ranked[0]["similarity_score"] > ranked[1]["similarity_score"]
    assert ranked[1]["similarity_score"] > ranked[2]["similarity_score"]
