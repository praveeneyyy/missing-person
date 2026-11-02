import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if available
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Environment mode
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "missing_persons.db"))

# Model configuration
YUNET_MODEL_PATH = os.environ.get("YUNET_MODEL_PATH", str(BASE_DIR / "models" / "face_detection_yunet_2023mar.onnx"))
SFACE_MODEL_PATH = os.environ.get("SFACE_MODEL_PATH", str(BASE_DIR / "models" / "face_recognition_sface_2021dec.onnx"))

# Storage directories
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", str(BASE_DIR / "storage")))
REFERENCES_DIR = STORAGE_DIR / "references"
SIGHTINGS_DIR = STORAGE_DIR / "sightings"

REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Authentication & Security
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "investigation-support-prototype-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))

# CORS Allowed Origins (comma-separated in .env, or * in dev)
ALLOWED_ORIGINS_RAW = os.environ.get("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_RAW.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [orig.strip() for orig in ALLOWED_ORIGINS_RAW.split(",") if orig.strip()]

# Server configuration
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# AI Thresholds (calibrated for SFace cosine similarity)
# SFace produces cosine similarity in range [-1.0, 1.0]
# Typical verified face pairs: > 0.70
# Plausible leads requiring high priority review: >= 0.65
# Moderate leads: >= 0.50
SIMILARITY_THRESHOLD_HIGH = float(os.environ.get("SIMILARITY_THRESHOLD_HIGH", "0.70"))
SIMILARITY_THRESHOLD_MODERATE = float(os.environ.get("SIMILARITY_THRESHOLD_MODERATE", "0.50"))
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "5"))

# Geospatial & National Mapping Configuration (Mappls / MapmyIndia)
MAP_PROVIDER = os.environ.get("MAP_PROVIDER", "osm")  # 'osm' or 'mappls'
MAPPLS_REST_API_KEY = os.environ.get("MAPPLS_REST_API_KEY", "")
MAPPLS_MAP_SDK_KEY = os.environ.get("MAPPLS_MAP_SDK_KEY", "")

# National Police & CCTNS Configuration
DEFAULT_STATE_CODE = os.environ.get("DEFAULT_STATE_CODE", "TN")
DEFAULT_DISTRICT_CODE = os.environ.get("DEFAULT_DISTRICT_CODE", "CHN")
AGENCY_NAME = os.environ.get("AGENCY_NAME", "National Crime Records Bureau (NCRB) - Ministry of Home Affairs")


