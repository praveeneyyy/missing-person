import uvicorn
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.seed_data import seed_database
from backend.config import DATABASE_PATH, HOST, PORT, ENVIRONMENT

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

    display_host = "127.0.0.1" if HOST == "0.0.0.0" else HOST
    print(f"\n[Startup] Starting FastAPI server on http://{HOST}:{PORT} (Env: {ENVIRONMENT}) ...")
    print(f"  - Local Web App:         http://{display_host}:{PORT}")
    print(f"  - Interactive API Docs:  http://{display_host}:{PORT}/docs")
    print(f"  - Liveness Health Probe: http://{display_host}:{PORT}/healthz")
    print("\n[Official Law Enforcement Staff Credentials]")
    print("  - Lead IO / Station House Officer: io.raman@police.gov.in (Username: investigator) | Pass: Police@Gov2026!")
    print("  - CCTNS Nodal Administrator:       cctns.admin@ncrb.gov.in (Username: admin)        | Pass: Ncrb@Admin2026!")
    print("  - Supervisory Dy. SP:              dsp.sharma@police.gov.in                         | Pass: Police@Gov2026!")
    print("=" * 75 + "\n")

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
