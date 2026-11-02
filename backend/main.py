import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.config import BASE_DIR, STORAGE_DIR
from backend.routes.auth_routes import router as auth_router
from backend.routes.case_routes import router as case_router
from backend.routes.sighting_routes import router as sighting_router
from backend.routes.review_routes import router as review_router
from backend.routes.audit_routes import router as audit_router
from backend.routes.benchmark_routes import router as benchmark_router
from backend.routes.face_routes import router as face_router
from backend.routes.match_routes import router as match_router
from backend.routes.surveillance_routes import router as surveillance_router

from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.config import (
    BASE_DIR, STORAGE_DIR, ALLOWED_ORIGINS, ENVIRONMENT, IS_PRODUCTION,
    MAP_PROVIDER, MAPPLS_REST_API_KEY, MAPPLS_MAP_SDK_KEY,
    DEFAULT_STATE_CODE, DEFAULT_DISTRICT_CODE, AGENCY_NAME
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="AI-Based Missing Person Identification & Tracking System",
    description="Investigation-support platform utilizing facial recognition, computer vision, and human-in-the-loop candidate review.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not IS_PRODUCTION else "/docs",  # Kept accessible or configurable
    redoc_url="/redoc" if not IS_PRODUCTION else None
)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(auth_router)
app.include_router(case_router)
app.include_router(sighting_router)
app.include_router(review_router)
app.include_router(audit_router)
app.include_router(benchmark_router)
app.include_router(face_router)
app.include_router(match_router)
app.include_router(surveillance_router)


@app.get("/healthz", tags=["System"])
def container_liveness_probe():
    """Liveness probe for container orchestration."""
    return {"status": "ok"}


@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "missing-person-ai-platform",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "models": {
            "face_detector": "YuNet (ONNX)",
            "face_recognizer": "SFace 128-D (ONNX)"
        }
    }

@app.get("/api/v1/system/config", tags=["System"])
def get_system_config():
    return {
        "agency": AGENCY_NAME,
        "cctns_compliance": "NCRB-CCTNS-v4.2",
        "jurisdiction": {
            "country": "India",
            "state_code": DEFAULT_STATE_CODE,
            "district_code": DEFAULT_DISTRICT_CODE
        },
        "gis": {
            "provider": MAP_PROVIDER,
            "mappls_configured": bool(MAPPLS_MAP_SDK_KEY or MAPPLS_REST_API_KEY),
            "mappls_sdk_key": MAPPLS_MAP_SDK_KEY if MAPPLS_MAP_SDK_KEY else None
        },
        "offline_ready": True
    }


# Mount uploaded media storage
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Mount frontend static assets
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="frontend_static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/{catchall:path}")
    def serve_frontend_paths(catchall: str):
        target = frontend_dir / catchall
        if target.exists() and target.is_file():
            return FileResponse(str(target))
        # Fallback to SPA index
        return FileResponse(str(frontend_dir / "index.html"))
