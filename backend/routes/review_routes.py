import json
import math
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status, Response
from backend.database import get_db
from backend.models import ReviewCreate, BatchReviewCreate
from backend.auth import require_role

router = APIRouter(prefix="/api/v1/candidates", tags=["Investigator Review Queue"])

def calculate_distance_km(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> Optional[float]:
    """Computes great-circle distance between two geographic coordinates in kilometers."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        r = 6371.0  # Earth radius in km
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(r * c, 2)
    except Exception:
        return None

def calculate_days_delta(date_str_1: Optional[str], date_str_2: Optional[str]) -> Optional[int]:
    """Computes absolute day delta between two dates formatted YYYY-MM-DD."""
    if not date_str_1 or not date_str_2:
        return None
    try:
        d1 = datetime.strptime(str(date_str_1)[:10], "%Y-%m-%d")
        d2 = datetime.strptime(str(date_str_2)[:10], "%Y-%m-%d")
        return abs((d2 - d1).days)
    except Exception:
        return None

def determine_confidence_tier(score: float) -> str:
    """Classifies cosine similarity into forensic confidence tiers."""
    if score >= 0.70:
        return "HIGH (≥ 0.70)"
    elif score >= 0.50:
        return "MODERATE (0.50 - 0.69)"
    return "LOW (< 0.50)"

def get_candidates_data(
    status_filter: Optional[str] = None,
    min_score: Optional[float] = None,
    case_id: Optional[int] = None,
    sighting_id: Optional[int] = None,
    sort_by: Optional[str] = "score_desc"
) -> List[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT cm.id AS candidate_id, cm.sighting_id, cm.sighting_face_index,
                   cm.case_id, cm.reference_image_id,
                   cm.similarity_score, cm.rank, cm.model_version, cm.status AS match_status,
                   cm.created_at AS matched_at,
                   s.receipt_no, s.sighting_date, s.sighting_time, s.location_name,
                   s.latitude AS sighting_lat, s.longitude AS sighting_lng,
                   s.description AS sighting_notes, s.status AS sighting_status,
                   sm.file_path AS sighting_photo_path,
                   sm.faces_metadata_json AS sighting_faces_json,
                   c.reference_no, c.full_name AS person_name,
                   c.age, c.gender, c.last_seen_date, c.last_seen_location,
                   c.latitude AS case_lat, c.longitude AS case_lng, c.status AS case_status,
                   c.assigned_investigator_id,
                   ri.file_path AS reference_photo_path,
                   ri.bbox_json AS ref_bbox_json,
                   ri.landmarks_json AS ref_landmarks_json
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            JOIN cases c ON cm.case_id = c.id
            JOIN reference_images ri ON cm.reference_image_id = ri.id
            WHERE 1=1
        """
        params = []

        if status_filter and str(status_filter).lower() != "all":
            query += " AND cm.status = ?"
            params.append(str(status_filter))

        if min_score is not None:
            query += " AND cm.similarity_score >= ?"
            params.append(float(min_score))

        if case_id is not None:
            query += " AND cm.case_id = ?"
            params.append(int(case_id))

        if sighting_id is not None:
            query += " AND cm.sighting_id = ?"
            params.append(int(sighting_id))

        # Ordering
        if sort_by == "score_asc":
            query += " ORDER BY cm.similarity_score ASC, cm.created_at ASC"
        elif sort_by == "date_desc":
            query += " ORDER BY cm.created_at DESC, cm.similarity_score DESC"
        elif sort_by == "date_asc":
            query += " ORDER BY cm.created_at ASC, cm.similarity_score DESC"
        else:
            query += " ORDER BY cm.similarity_score DESC, cm.created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            item = dict(r)
            dist_km = calculate_distance_km(item.get("case_lat"), item.get("case_lng"),
                                            item.get("sighting_lat"), item.get("sighting_lng"))
            days_delta = calculate_days_delta(item.get("last_seen_date"), item.get("sighting_date"))
            score = float(item["similarity_score"])

            item["spatial_separation_km"] = dist_km
            item["temporal_delta_days"] = days_delta
            item["confidence_tier"] = determine_confidence_tier(score)
            item["requires_human_review"] = (item["match_status"] == "requires_human_review")
            results.append(item)

        # In-memory distance sorting if requested
        if sort_by == "distance_asc":
            results.sort(key=lambda x: (x["spatial_separation_km"] is None, x["spatial_separation_km"] or 0))

        return results

@router.get("")
def list_candidates(
    status_filter: Optional[str] = Query(None, alias="status"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    case_id: Optional[int] = Query(None),
    sighting_id: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("score_desc"),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns candidate matches with forensic correlation metrics:
    - Spatial separation (geodesic distance in km between case origin and sighting site)
    - Temporal delta (elapsed days between last seen date and sighting date)
    - Forensic confidence classification tier
    - Dual image endpoints and detection bounding boxes / 5-point facial landmarks
    """
    return get_candidates_data(
        status_filter=status_filter,
        min_score=min_score,
        case_id=case_id,
        sighting_id=sighting_id,
        sort_by=sort_by
    )

@router.get("/pending")
def list_pending_review_candidates(
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns candidate matches awaiting human review across all active sightings.
    Each item contains side-by-side evidence, facial landmark data, and spatial metrics.
    """
    return get_candidates_data(status_filter="requires_human_review")

@router.get("/stats")
def get_candidate_queue_stats(
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Returns queue workload telemetry and adjudication breakdown."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches;")
        total_candidates = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE status = 'requires_human_review';")
        pending_review = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE status = 'verified';")
        verified_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE status = 'escalated';")
        escalated_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE status = 'info_requested';")
        info_requested_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidate_matches WHERE status = 'rejected';")
        rejected_count = cursor.fetchone()["cnt"]

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM candidate_matches
            WHERE status = 'requires_human_review' AND similarity_score >= 0.70;
        """)
        high_confidence_pending = cursor.fetchone()["cnt"]

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM candidate_matches
            WHERE status = 'requires_human_review' AND similarity_score >= 0.50 AND similarity_score < 0.70;
        """)
        moderate_confidence_pending = cursor.fetchone()["cnt"]

        return {
            "total_candidates": total_candidates,
            "pending_review": pending_review,
            "verified_count": verified_count,
            "escalated_count": escalated_count,
            "info_requested_count": info_requested_count,
            "rejected_count": rejected_count,
            "high_confidence_pending": high_confidence_pending,
            "moderate_confidence_pending": moderate_confidence_pending,
            "governance_rule": "AI similarity is a ranking signal only; human review mandatory."
        }

@router.get("/{candidate_id}")
def get_candidate_detail(
    candidate_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns complete forensic dossier for a single candidate match,
    including sighting media, reference portrait, spatial metrics, and historical reviews.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cm.id AS candidate_id, cm.sighting_id, cm.sighting_face_index,
                   cm.case_id, cm.reference_image_id,
                   cm.similarity_score, cm.rank, cm.model_version, cm.status AS match_status,
                   cm.created_at AS matched_at,
                   s.receipt_no, s.sighting_date, s.sighting_time, s.location_name,
                   s.latitude AS sighting_lat, s.longitude AS sighting_lng,
                   s.description AS sighting_notes, s.status AS sighting_status,
                   sm.file_path AS sighting_photo_path,
                   sm.faces_metadata_json AS sighting_faces_json,
                   c.reference_no, c.full_name AS person_name,
                   c.age, c.gender, c.last_seen_date, c.last_seen_location,
                   c.latitude AS case_lat, c.longitude AS case_lng, c.status AS case_status,
                   c.assigned_investigator_id,
                   ri.file_path AS reference_photo_path,
                   ri.bbox_json AS ref_bbox_json,
                   ri.landmarks_json AS ref_landmarks_json
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            JOIN cases c ON cm.case_id = c.id
            JOIN reference_images ri ON cm.reference_image_id = ri.id
            WHERE cm.id = ?
        """, (candidate_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate match not found")

        item = dict(row)
        dist_km = calculate_distance_km(item.get("case_lat"), item.get("case_lng"),
                                        item.get("sighting_lat"), item.get("sighting_lng"))
        days_delta = calculate_days_delta(item.get("last_seen_date"), item.get("sighting_date"))
        score = float(item["similarity_score"])

        item["spatial_separation_km"] = dist_km
        item["temporal_delta_days"] = days_delta
        item["confidence_tier"] = determine_confidence_tier(score)
        item["requires_human_review"] = (item["match_status"] == "requires_human_review")

        # Fetch reviews for this candidate
        cursor.execute("""
            SELECT r.id, r.disposition, r.rationale, r.next_steps, r.reviewed_at,
                   u.full_name AS reviewer_name, u.badge_number AS reviewer_badge, u.role AS reviewer_role
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.id
            WHERE r.candidate_match_id = ?
            ORDER BY r.reviewed_at DESC
        """, (candidate_id,))
        item["reviews"] = [dict(rev) for rev in cursor.fetchall()]

        return item

@router.get("/{candidate_id}/reviews")
def list_candidate_reviews(
    candidate_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Returns chronological adjudication decisions for a specific candidate match."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM candidate_matches WHERE id = ?", (candidate_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Candidate match not found")

        cursor.execute("""
            SELECT r.id, r.candidate_match_id, r.disposition, r.rationale, r.next_steps, r.reviewed_at,
                   u.id AS reviewer_id, u.full_name AS reviewer_name, u.badge_number AS reviewer_badge
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.id
            WHERE r.candidate_match_id = ?
            ORDER BY r.reviewed_at DESC
        """, (candidate_id,))
        return [dict(rev) for rev in cursor.fetchall()]

@router.post("/{candidate_id}/reviews", status_code=status.HTTP_201_CREATED)
def submit_candidate_review(
    candidate_id: int,
    payload: ReviewCreate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Records an authorized investigator's review decision with mandatory written rationale.
    Updates candidate lead status, sighting status, and case status accordingly.
    All actions are audited to maintain chain of custody and AI governance standards.
    """
    valid_dispositions = ["verified", "escalated", "request_more_info", "rejected"]
    if payload.disposition not in valid_dispositions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid disposition '{payload.disposition}'. Must be one of: {', '.join(valid_dispositions)}"
        )

    if not payload.rationale or len(payload.rationale.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Mandatory written rationale must contain at least 5 non-whitespace characters for legal admissibility."
        )

    with get_db() as conn:
        cursor = conn.cursor()

        # Check candidate match exists
        cursor.execute("""
            SELECT cm.*, s.id AS sighting_id, s.receipt_no, s.location_name,
                   c.id AS case_id, c.reference_no, c.full_name, c.assigned_investigator_id
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            JOIN cases c ON cm.case_id = c.id
            WHERE cm.id = ?
        """, (candidate_id,))
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Candidate match not found")

        # 1. Insert review record
        cursor.execute("""
            INSERT INTO reviews (candidate_match_id, reviewer_id, disposition, rationale, next_steps)
            VALUES (?, ?, ?, ?, ?)
        """, (candidate_id, user["id"], payload.disposition, payload.rationale.strip(), payload.next_steps))
        review_id = cursor.lastrowid

        # 2. Update candidate match status
        match_status_map = {
            "verified": "verified",
            "escalated": "escalated",
            "request_more_info": "info_requested",
            "rejected": "rejected"
        }
        new_match_status = match_status_map[payload.disposition]
        cursor.execute("UPDATE candidate_matches SET status = ? WHERE id = ?", (new_match_status, candidate_id))

        # 3. Update sighting and case statuses based on disposition
        if payload.disposition == "verified":
            cursor.execute("UPDATE sightings SET status = 'verified_match' WHERE id = ?", (match["sighting_id"],))
            cursor.execute("""
                UPDATE cases
                SET status = 'under_review',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'open'
            """, (match["case_id"],))
        elif payload.disposition == "escalated":
            cursor.execute("UPDATE sightings SET status = 'escalated' WHERE id = ?", (match["sighting_id"],))
        elif payload.disposition == "rejected":
            # If all candidates for this sighting are rejected, mark sighting as rejected
            cursor.execute("""
                SELECT COUNT(*) AS pending_count
                FROM candidate_matches
                WHERE sighting_id = ? AND status = 'requires_human_review'
            """, (match["sighting_id"],))
            if cursor.fetchone()["pending_count"] == 0:
                cursor.execute("UPDATE sightings SET status = 'rejected' WHERE id = ?", (match["sighting_id"],))

        # 4. Record audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'REVIEW_SUBMITTED', 'candidate_matches', ?, ?)
        """, (
            user["id"], user["full_name"], str(candidate_id),
            json.dumps({
                "disposition": payload.disposition,
                "case_reference": match["reference_no"],
                "sighting_receipt": match["receipt_no"],
                "rationale": payload.rationale.strip(),
                "reviewer_badge": user.get("badge_number"),
                "similarity_score": match["similarity_score"]
            })
        ))

        # 5. Emit operational notification to assigned investigator or admin
        notif_recipients = set()
        if match["assigned_investigator_id"] and match["assigned_investigator_id"] != user["id"]:
            notif_recipients.add(match["assigned_investigator_id"])
        # Notify admins
        cursor.execute("SELECT id FROM users WHERE role = 'admin' AND id != ?", (user["id"],))
        for adm in cursor.fetchall():
            notif_recipients.add(adm["id"])

        notif_title = f"Adjudication: {match['reference_no']} • {payload.disposition.upper()}"
        notif_msg = (f"Officer {user['full_name']} marked lead #{candidate_id} "
                     f"(Sighting {match['receipt_no']}) as '{payload.disposition}'.")
        for recipient_id in notif_recipients:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, category, link_url)
                VALUES (?, ?, ?, 'review_update', ?)
            """, (recipient_id, notif_title, notif_msg, f"/review?candidate={candidate_id}"))

        return {
            "success": True,
            "review_id": review_id,
            "candidate_id": candidate_id,
            "disposition": payload.disposition,
            "new_status": new_match_status,
            "message": f"Review recorded successfully. Lead marked as '{payload.disposition}'."
        }

@router.post("/batch-review", status_code=status.HTTP_200_OK)
def submit_batch_candidate_review(
    payload: BatchReviewCreate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Submits a batch adjudication across multiple candidate matches simultaneously
    (e.g., bulk rejecting noise leads or escalating multiple field sightings).
    """
    valid_dispositions = ["verified", "escalated", "request_more_info", "rejected"]
    if payload.disposition not in valid_dispositions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid disposition '{payload.disposition}'. Must be one of: {', '.join(valid_dispositions)}"
        )

    if not payload.rationale or len(payload.rationale.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Mandatory written rationale must contain at least 5 non-whitespace characters."
        )

    processed_ids = []
    with get_db() as conn:
        cursor = conn.cursor()
        for cand_id in payload.candidate_ids:
            cursor.execute("SELECT id FROM candidate_matches WHERE id = ?", (cand_id,))
            if cursor.fetchone():
                review_payload = ReviewCreate(
                    disposition=payload.disposition,
                    rationale=payload.rationale,
                    next_steps=payload.next_steps
                )
                submit_candidate_review(cand_id, review_payload, user)
                processed_ids.append(cand_id)

    return {
        "success": True,
        "processed_count": len(processed_ids),
        "candidate_ids": processed_ids,
        "disposition": payload.disposition,
        "message": f"Batch adjudication completed. {len(processed_ids)} leads set to '{payload.disposition}'."
    }

@router.get("/{candidate_id}/export-dossier")
def export_candidate_forensic_dossier(
    candidate_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Generates and downloads a court-admissible Biometric Forensic Examination
    Certificate for the specified candidate match.
    """
    from backend.dossier_generator import generate_forensic_certificate
    try:
        cert_bytes = generate_forensic_certificate(candidate_id)
        return Response(
            content=cert_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=forensic_examination_certificate_cand_{candidate_id}.png"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forensic dossier: {str(e)}")

