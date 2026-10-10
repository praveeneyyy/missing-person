import sqlite3
import json
from contextlib import contextmanager
from typing import Generator
import backend.config

def get_db_connection() -> sqlite3.Connection:
    """Creates a SQLite connection with foreign keys enabled and row factory set to Row."""
    conn = sqlite3.connect(backend.config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes database schema matching the PRD and Architecture data models."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table (Admin, Investigator, Public)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            badge_number TEXT,
            role TEXT NOT NULL CHECK(role IN ('admin', 'investigator', 'public')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Cases table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_no TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            last_seen_date TEXT NOT NULL,
            last_seen_time TEXT,
            last_seen_location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('draft', 'open', 'under_review', 'resolved', 'archived')),
            assigned_investigator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            identifying_features TEXT,
            clothing_description TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Reference images for registered cases
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            face_detected INTEGER NOT NULL DEFAULT 1,
            bbox_json TEXT,
            landmarks_json TEXT,
            embedding_json TEXT NOT NULL,
            model_name TEXT NOT NULL DEFAULT 'YuNet + SFace',
            model_version TEXT NOT NULL DEFAULT 'v1.0-onnx',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Sightings submitted by public reporters
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE NOT NULL,
            sighting_date TEXT NOT NULL,
            sighting_time TEXT,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            description TEXT,
            reporter_name TEXT,
            reporter_phone TEXT,
            reporter_email TEXT,
            consent_given INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending_review' CHECK(status IN ('pending_review', 'in_review', 'verified_match', 'escalated', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Media assets associated with a sighting
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sighting_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sighting_id INTEGER NOT NULL REFERENCES sightings(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            faces_detected_count INTEGER NOT NULL DEFAULT 0,
            faces_metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Candidate matches between a sighting and registered cases
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidate_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sighting_id INTEGER NOT NULL REFERENCES sightings(id) ON DELETE CASCADE,
            sighting_face_index INTEGER NOT NULL DEFAULT 0,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            reference_image_id INTEGER NOT NULL REFERENCES reference_images(id) ON DELETE CASCADE,
            similarity_score REAL NOT NULL,
            rank INTEGER NOT NULL,
            model_version TEXT NOT NULL DEFAULT 'v1.0-onnx',
            status TEXT NOT NULL DEFAULT 'requires_human_review' CHECK(status IN ('requires_human_review', 'verified', 'escalated', 'rejected', 'info_requested')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Investigator reviews on candidates
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_match_id INTEGER NOT NULL REFERENCES candidate_matches(id) ON DELETE CASCADE,
            reviewer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            disposition TEXT NOT NULL CHECK(disposition IN ('verified', 'escalated', 'request_more_info', 'rejected')),
            rationale TEXT NOT NULL,
            next_steps TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Audit logs for traceability and AI governance
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            actor_name TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            details_json TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Notifications for investigators
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'match_alert',
            link_url TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_ref ON cases(reference_no);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sightings_receipt ON sightings(receipt_no);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sightings_status ON sightings(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_sighting ON candidate_matches(sighting_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_case ON candidate_matches(case_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);")
