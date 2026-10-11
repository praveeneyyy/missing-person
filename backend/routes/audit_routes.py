import json
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from backend.database import get_db
from backend.auth import require_role
from backend.models import NotificationCreate

router = APIRouter(prefix="/api/v1", tags=["Dashboard & Audit"])

def calculate_distance_km(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> Optional[float]:
    """Computes geodesic distance between two points in km."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(r * c, 2)
    except Exception:
        return None

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
def get_map_points(
    min_similarity: Optional[float] = Query(None, ge=0.0, le=1.0),
    status_filter: Optional[str] = Query(None),
    case_id: Optional[int] = Query(None),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns geographical coordinates for missing person cases, reported sightings,
    and spatial correlation vectors between matched cases and sightings.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Cases with coordinates
        case_query = """
            SELECT c.id, c.reference_no, c.full_name, c.age, c.gender, c.last_seen_date,
                   c.last_seen_location, c.latitude, c.longitude, c.status,
                   (SELECT file_path FROM reference_images WHERE case_id = c.id LIMIT 1) AS photo_path,
                   (SELECT COUNT(*) FROM candidate_matches WHERE case_id = c.id) AS correlated_leads_count
            FROM cases c
            WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
        """
        case_params = []
        if case_id is not None:
            case_query += " AND c.id = ?"
            case_params.append(case_id)

        cursor.execute(case_query, case_params)
        case_points = [dict(c) for c in cursor.fetchall()]

        # Sightings with coordinates
        sighting_query = """
            SELECT s.id, s.receipt_no, s.sighting_date, s.sighting_time, s.location_name,
                   s.latitude, s.longitude, s.status,
                   sm.file_path AS photo_path,
                   (SELECT MAX(similarity_score) FROM candidate_matches WHERE sighting_id = s.id) AS max_similarity,
                   (SELECT c.reference_no FROM candidate_matches cm JOIN cases c ON cm.case_id = c.id WHERE cm.sighting_id = s.id ORDER BY cm.similarity_score DESC LIMIT 1) AS top_matched_case_ref
            FROM sightings s
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        """
        s_params = []

        if status_filter and status_filter.lower() != "all":
            sighting_query += " AND s.status = ?"
            s_params.append(status_filter)

        cursor.execute(sighting_query, s_params)
        sighting_rows = [dict(s) for s in cursor.fetchall()]

        if min_similarity is not None:
            sighting_rows = [s for s in sighting_rows if s.get("max_similarity") is not None and s["max_similarity"] >= min_similarity]

        # Spatial correlation vectors connecting sightings to their matched cases
        cursor.execute("""
            SELECT cm.id AS candidate_id, cm.similarity_score, cm.status AS match_status,
                   s.id AS sighting_id, s.receipt_no, s.location_name AS sighting_location,
                   s.latitude AS sighting_lat, s.longitude AS sighting_lng,
                   c.id AS case_id, c.reference_no AS case_ref, c.full_name AS person_name,
                   c.latitude AS case_lat, c.longitude AS case_lng
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            JOIN cases c ON cm.case_id = c.id
            WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
              AND c.latitude IS NOT NULL AND c.longitude IS NOT NULL
            ORDER BY cm.similarity_score DESC
        """)
        vectors = []
        for v in cursor.fetchall():
            item = dict(v)
            if min_similarity is not None and item["similarity_score"] < min_similarity:
                continue
            if case_id is not None and item["case_id"] != case_id:
                continue
            dist = calculate_distance_km(item["case_lat"], item["case_lng"], item["sighting_lat"], item["sighting_lng"])
            item["distance_km"] = dist
            vectors.append(item)

        return {
            "cases": case_points,
            "sightings": sighting_rows,
            "correlation_vectors": vectors,
            "total_case_pins": len(case_points),
            "total_sighting_pins": len(sighting_rows),
            "total_vectors": len(vectors)
        }

@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Returns investigator notification feed with unread counter."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT id, user_id, title, message, category, link_url, is_read, created_at
            FROM notifications
            WHERE user_id = ?
        """
        params = [user["id"]]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        notifications = [dict(n) for n in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) AS unread_cnt FROM notifications WHERE user_id = ? AND is_read = 0", (user["id"],))
        unread_count = cursor.fetchone()["unread_cnt"]

        return {
            "unread_count": unread_count,
            "total_returned": len(notifications),
            "notifications": notifications
        }

@router.get("/notifications/unread-count")
def get_unread_notification_count(user: dict = Depends(require_role(["investigator", "admin"]))):
    """Returns unread notification counter for badge rendering."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS unread_cnt FROM notifications WHERE user_id = ? AND is_read = 0", (user["id"],))
        return {"unread_count": cursor.fetchone()["unread_cnt"]}

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: dict = Depends(require_role(["investigator", "admin"]))):
    """Marks a single notification as read."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notifications WHERE id = ? AND user_id = ?", (notification_id, user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Notification not found")

        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        return {"success": True, "notification_id": notification_id, "is_read": 1}

@router.put("/notifications/read-all")
def mark_all_notifications_read(user: dict = Depends(require_role(["investigator", "admin"]))):
    """Marks all notifications for current user as read."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
        return {"success": True, "message": "All notifications marked as read."}

@router.post("/notifications", status_code=status.HTTP_201_CREATED)
def create_operational_notification(
    payload: NotificationCreate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Dispatches a manual or automated operational alert to staff."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipient user not found")

        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, category, link_url)
            VALUES (?, ?, ?, ?, ?)
        """, (payload.user_id, payload.title.strip(), payload.message.strip(), payload.category, payload.link_url))
        notif_id = cursor.lastrowid
        return {
            "success": True,
            "notification_id": notif_id,
            "recipient_id": payload.user_id,
            "title": payload.title
        }
