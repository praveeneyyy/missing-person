import uvicorn
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.seed_data import seed_database
from backend.config import DATABASE_PATH

def main():
    print("=" * 75)
    print("  AI-BASED MISSING PERSON IDENTIFICATION AND TRACKING SYSTEM")
    print("  Computer Vision & Biometric Surveillance Intelligence Platform")
    print("=" * 75)

    # Automatically initialize and seed sample data if database not present
    if not os.path.exists(DATABASE_PATH):
        print("\n[Startup] Database not detected. Initializing schema and seed cases...")
        seed_database()
    else:
        print(f"\n[Startup] Using existing database: {DATABASE_PATH}")

    print("\n[Startup] Starting FastAPI server on http://127.0.0.1:8000 ...")
    print("  - Web Application:       http://127.0.0.1:8000")
    print("  - Interactive API Docs:  http://127.0.0.1:8000/docs")
    print("\n[Staff Credentials]")
    print("  - Lead Investigator:     investigator / investigator123 (INV-1001)")
    print("  - Administrator:         admin / admin123 (ADM-001)")
    print("  - Detective:             detective_chen / investigator123 (INV-7809)")
    print("=" * 75 + "\n")

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
