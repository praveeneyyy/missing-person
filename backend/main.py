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

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="AI-Based Missing Person Identification & Tracking System",
    description="Investigation-support platform utilizing facial recognition, computer vision, and human-in-the-loop candidate review.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "missing-person-ai-platform",
        "version": "1.0.0",
        "models": {
            "face_detector": "YuNet (ONNX)",
            "face_recognizer": "SFace 128-D (ONNX)"
        }
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
