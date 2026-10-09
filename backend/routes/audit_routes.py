import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.database import get_db
from backend.auth import require_role

router = APIRouter(prefix="/api/v1", tags=["Dashboard & Audit"])

@router.get("/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(require_role(["investigator", "admin"]))):
    """Returns real-time operational statistics for the investigator dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total_cases FROM cases WHERE status = 'open';")
        open_cases = cursor.fetchone()["total_cases"]

        cursor.execute("SELECT COUNT(*) AS total_sightings FROM sightings;")
        total_sightings = cursor.fetchone()["total_sightings"]

        cursor.execute("SELECT COUNT(*) AS pending_reviews FROM candidate_matches WHERE status = 'requires_human_review';")
        pending_reviews = cursor.fetchone()["pending_reviews"]

        cursor.execute("SELECT COUNT(*) AS verified_matches FROM candidate_matches WHERE status = 'verified';")
        verified_matches = cursor.fetchone()["verified_matches"]

        cursor.execute("SELECT COUNT(*) AS enrolled_faces FROM reference_images;")
        enrolled_faces = cursor.fetchone()["enrolled_faces"]

        cursor.execute("SELECT COUNT(*) AS total_audits FROM audit_logs;")
        total_audits = cursor.fetchone()["total_audits"]

        return {
            "open_cases": open_cases,
            "total_sightings": total_sightings,
            "pending_reviews": pending_reviews,
            "verified_matches": verified_matches,
            "enrolled_faces": enrolled_faces,
            "total_audit_events": total_audits,
            "system_health": "Operational",
            "detector_model": "YuNet (OpenCV 2023mar)",
            "recognizer_model": "SFace (MobileFaceNet 128-D)"
        }

@router.get("/audit")
def list_audit_logs(
    limit: int = Query(50, le=200),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Returns chronological audit log entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, actor_id, actor_name, action, resource_type, resource_id,
                   details_json, ip_address, created_at
            FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

        results = []
        for r in rows:
            item = dict(r)
            if item.get("details_json"):
                try:
                    item["details"] = json.loads(item["details_json"])
                except Exception:
                    item["details"] = item["details_json"]
            else:
                item["details"] = {}
            results.append(item)
        return results

@router.get("/map/points")
def get_map_points(user: dict = Depends(require_role(["investigator", "admin"]))):
    """
    Returns geographical coordinates for missing person cases and reported sightings
    to render on the interactive investigation map.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Cases with coordinates
        cursor.execute("""
            SELECT id, reference_no, full_name, age, gender, last_seen_date,
                   last_seen_location, latitude, longitude, status,
                   (SELECT file_path FROM reference_images WHERE case_id = cases.id LIMIT 1) AS photo_path
            FROM cases
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        case_points = [dict(c) for c in cursor.fetchall()]

        # Sightings with coordinates
        cursor.execute("""
            SELECT s.id, s.receipt_no, s.sighting_date, s.location_name,
                   s.latitude, s.longitude, s.status,
                   sm.file_path AS photo_path,
                   (SELECT MAX(similarity_score) FROM candidate_matches WHERE sighting_id = s.id) AS max_similarity
            FROM sightings s
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        """)
        sighting_points = [dict(s) for s in cursor.fetchall()]

        return {
            "cases": case_points,
            "sightings": sighting_points
        }

@router.get("/notifications")
def get_notifications(user: dict = Depends(require_role(["investigator", "admin"]))):
    """Returns investigator notification feed."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, message, category, link_url, is_read, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user["id"],))
        return [dict(n) for n in cursor.fetchall()]
