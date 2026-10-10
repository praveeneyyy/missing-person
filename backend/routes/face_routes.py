import os
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from backend.face_engine import face_engine
from backend.auth import require_role
from backend.config import YUNET_MODEL_PATH, SFACE_MODEL_PATH

router = APIRouter(prefix="/api/v1/faces", tags=["Face Processing Engine"])

@router.get("/models")
def get_face_models_telemetry():
    """Returns technical metadata for OpenCV YuNet detection and SFace feature extraction."""
    return {
        "status": "online",
        "detection_stage": {
            "model_name": "OpenCV YuNet DNN",
            "model_version": "2023mar",
            "weights_file": os.path.basename(YUNET_MODEL_PATH),
            "file_size_bytes": os.path.getsize(YUNET_MODEL_PATH) if os.path.exists(YUNET_MODEL_PATH) else None,
            "architecture": "Single-stage lightweight convolutional face detector",
            "detection_threshold": face_engine.detector_score_thresh,
            "nms_threshold": face_engine.detector_nms_thresh,
            "landmarks_count": 5,
            "landmarks_mapping": ["Right Eye", "Left Eye", "Nose Tip", "Right Mouth Corner", "Left Mouth Corner"],
            "dynamic_resolution": True
        },
        "recognition_stage": {
            "model_name": "OpenCV SFace DNN",
            "model_version": "2021dec",
            "weights_file": os.path.basename(SFACE_MODEL_PATH),
            "file_size_bytes": os.path.getsize(SFACE_MODEL_PATH) if os.path.exists(SFACE_MODEL_PATH) else None,
            "canonical_crop_size": "112x112",
            "output_dimensions": 128,
            "normalization": "L2 Unit Spherical Normalization",
            "metric": "Cosine Similarity",
            "calibrated_thresholds": {
                "high_confidence_verified": 0.70,
                "moderate_plausible_lead": 0.50,
                "low_non_match": 0.40
            }
        }
    }

@router.post("/analyze")
async def analyze_face(
    file: UploadFile = File(...)
):
    """
    Diagnostic endpoint inspecting the 3-stage face processing pipeline:
    Detection -> Landmark Alignment -> 128-D Feature Extraction.
    """
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file exceeds 15 MB limit.")

    try:
        img = face_engine.decode_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis = face_engine.analyze_face_image(img)
    return analysis

@router.post("/compare")
async def compare_faces(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):
    """
    Direct pairwise 1-to-1 biometric comparison between two face images.
    Returns cosine similarity, euclidean distance, aligned 112x112 crops, and confidence disposition.
    """
    content1 = await file1.read()
    content2 = await file2.read()

    try:
        img1 = face_engine.decode_image(content1)
        img2 = face_engine.decode_image(content2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = face_engine.compare_two_faces(img1, img2)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
