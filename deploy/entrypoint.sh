#!/bin/bash
set -e

echo "========================================================================"
echo "  POLICE BIOMETRIC DISPATCH & TRACKING PLATFORM (PRODUCTION)"
echo "========================================================================"

# Ensure media storage directories exist
mkdir -p storage/references storage/sightings

# Initialize database schema if database file does not exist
if [ ! -f "${DATABASE_PATH:-missing_persons.db}" ]; then
    echo "[Startup] Database not detected. Initializing schema and seed cases..."
    python -c "from backend.seed_data import seed_database; seed_database()"
else
    echo "[Startup] Existing database verified at: ${DATABASE_PATH:-missing_persons.db}"
fi

echo "[Startup] Starting production server with Gunicorn (Uvicorn workers)..."
exec gunicorn -c deploy/gunicorn_conf.py backend.main:app
