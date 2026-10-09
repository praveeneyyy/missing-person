import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "missing_persons.db"))

# Model configuration
YUNET_MODEL_PATH = str(BASE_DIR / "models" / "face_detection_yunet_2023mar.onnx")
SFACE_MODEL_PATH = str(BASE_DIR / "models" / "face_recognition_sface_2021dec.onnx")

# Storage directories
STORAGE_DIR = BASE_DIR / "storage"
REFERENCES_DIR = STORAGE_DIR / "references"
SIGHTINGS_DIR = STORAGE_DIR / "sightings"

REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Authentication & Security
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "investigation-support-prototype-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

# AI Thresholds (calibrated for SFace cosine similarity)
# SFace produces cosine similarity in range [-1.0, 1.0]
# Typical verified face pairs: > 0.70
# Plausible leads requiring high priority review: >= 0.65
# Moderate leads: >= 0.50
SIMILARITY_THRESHOLD_HIGH = 0.70
SIMILARITY_THRESHOLD_MODERATE = 0.50
DEFAULT_TOP_K = 5
