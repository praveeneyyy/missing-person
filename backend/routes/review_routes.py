import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from backend.database import get_db
from backend.models import ReviewCreate
from backend.auth import require_role

router = APIRouter(prefix="/api/v1/candidates", tags=["Investigator Review Queue"])

@router.get("/pending")
def list_pending_review_candidates(
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns candidate matches awaiting human review across all active sightings.
    Each item contains side-by-side evidence:
    - Sighting media path, time, and location
    - Registered missing person case details and authorized reference photo
    - Similarity score and model version
    - Explicit human review state
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cm.id AS candidate_id, cm.sighting_id, cm.sighting_face_index,
                   cm.similarity_score, cm.rank, cm.model_version, cm.status AS match_status,
                   cm.created_at AS matched_at,
                   s.receipt_no, s.sighting_date, s.sighting_time, s.location_name,
                   s.latitude AS sighting_lat, s.longitude AS sighting_lng,
                   s.description AS sighting_notes,
                   sm.file_path AS sighting_photo_path,
                   c.id AS case_id, c.reference_no, c.full_name AS person_name,
                   c.age, c.gender, c.last_seen_date, c.last_seen_location,
                   c.latitude AS case_lat, c.longitude AS case_lng, c.status AS case_status,
                   ri.file_path AS reference_photo_path
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            JOIN cases c ON cm.case_id = c.id
            JOIN reference_images ri ON cm.reference_image_id = ri.id
            WHERE cm.status = 'requires_human_review'
            ORDER BY cm.similarity_score DESC, cm.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

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

    with get_db() as conn:
        cursor = conn.cursor()

        # Check candidate match exists
        cursor.execute("""
            SELECT cm.*, s.id AS sighting_id, s.receipt_no, c.id AS case_id, c.reference_no, c.full_name
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
        """, (candidate_id, user["id"], payload.disposition, payload.rationale, payload.next_steps))
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

        # 3. Update sighting status
        if payload.disposition == "verified":
            cursor.execute("UPDATE sightings SET status = 'verified_match' WHERE id = ?", (match["sighting_id"],))
            cursor.execute("UPDATE cases SET status = 'under_review', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (match["case_id"],))
        elif payload.disposition == "escalated":
            cursor.execute("UPDATE sightings SET status = 'escalated' WHERE id = ?", (match["sighting_id"],))
        elif payload.disposition == "rejected":
            # If all candidates for this sighting are rejected, mark sighting as reviewed/rejected
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
                "rationale": payload.rationale,
                "reviewer_badge": user.get("badge_number")
            })
        ))

        return {
            "success": True,
            "review_id": review_id,
            "candidate_id": candidate_id,
            "disposition": payload.disposition,
            "new_status": new_match_status,
            "message": f"Review recorded successfully. Lead marked as '{payload.disposition}'."
        }
