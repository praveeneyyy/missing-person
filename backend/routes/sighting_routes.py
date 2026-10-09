import json
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Query
from backend.database import get_db
from backend.auth import require_role
from backend.config import SIGHTINGS_DIR, SIMILARITY_THRESHOLD_HIGH, DEFAULT_TOP_K
from backend.face_engine import face_engine
from backend.models import SightingLookupResponse

router = APIRouter(prefix="/api/v1/sightings", tags=["Sighting Portal"])

def generate_receipt_no(cursor) -> str:
    """Generates unique receipt identifier like STG-2026-0042."""
    cursor.execute("SELECT COUNT(*) AS cnt FROM sightings;")
    count = cursor.fetchone()["cnt"] + 1
    return f"STG-2026-{count:04d}"

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_sighting(
    sighting_date: str = Form(...),
    sighting_time: Optional[str] = Form(None),
    location_name: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    reporter_phone: Optional[str] = Form(None),
    reporter_email: Optional[str] = Form(None),
    consent_given: bool = Form(True),
    file: UploadFile = File(...)
):
    """
    Public sighting submission portal.
    Ingests photo/media, extracts face embeddings, runs candidate retrieval
    against enrolled cases, and queues results for investigator review.
    Does NOT disclose confidential case matches to the public reporter.
    """
    if not consent_given:
        raise HTTPException(
            status_code=400,
            detail="Notice and privacy terms acknowledgement is required to submit a sighting."
        )

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum 15 MB limit.")

    try:
        img = face_engine.decode_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decoding failed: {e}")

    # Process all faces in the sighting image
    detected_faces = face_engine.process_sighting_image(img)

    with get_db() as conn:
        cursor = conn.cursor()
        receipt_no = generate_receipt_no(cursor)

        # 1. Save sighting record
        cursor.execute("""
            INSERT INTO sightings (
                receipt_no, sighting_date, sighting_time, location_name,
                latitude, longitude, description, reporter_name, reporter_phone,
                reporter_email, consent_given, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
        """, (
            receipt_no, sighting_date, sighting_time, location_name,
            latitude, longitude, description, reporter_name, reporter_phone,
            reporter_email, 1 if consent_given else 0
        ))
        sighting_id = cursor.lastrowid

        # 2. Save media file securely
        file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            file_ext = ".jpg"

        stored_name = f"sight_{sighting_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        saved_path = SIGHTINGS_DIR / stored_name
        with open(saved_path, "wb") as f:
            f.write(content)

        rel_path = f"storage/sightings/{stored_name}"

        # Save media asset record
        cursor.execute("""
            INSERT INTO sighting_media (
                sighting_id, file_path, original_filename,
                faces_detected_count, faces_metadata_json
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            sighting_id, rel_path, file.filename or "sighting.jpg",
            len(detected_faces),
            json.dumps([{
                "face_index": f["face_index"],
                "bbox": f["bbox"],
                "confidence": f["confidence"]
            } for f in detected_faces])
        ))

        # 3. Retrieve all enrolled reference embeddings for active cases
        cursor.execute("""
            SELECT r.id AS reference_image_id, r.case_id, r.embedding_json,
                   c.reference_no, c.full_name, c.age, c.gender, c.last_seen_date, c.last_seen_location,
                   c.assigned_investigator_id
            FROM reference_images r
            JOIN cases c ON r.case_id = c.id
            WHERE c.status IN ('open', 'under_review')
        """)
        enrolled_rows = cursor.fetchall()

        enrolled_cases = []
        for row in enrolled_rows:
            try:
                emb = json.loads(row["embedding_json"])
                enrolled_cases.append({
                    "case_id": row["case_id"],
                    "reference_image_id": row["reference_image_id"],
                    "reference_no": row["reference_no"],
                    "full_name": row["full_name"],
                    "age": row["age"],
                    "gender": row["gender"],
                    "last_seen_date": row["last_seen_date"],
                    "last_seen_location": row["last_seen_location"],
                    "assigned_investigator_id": row["assigned_investigator_id"],
                    "embedding": emb
                })
            except Exception:
                continue

        # 4. Perform vector similarity ranking for each detected face
        matches_generated = 0
        high_similarity_alerts = []

        for face in detected_faces:
            query_emb = face["embedding"]
            top_matches = face_engine.rank_candidates(query_emb, enrolled_cases, top_k=DEFAULT_TOP_K)

            for match in top_matches:
                cursor.execute("""
                    INSERT INTO candidate_matches (
                        sighting_id, sighting_face_index, case_id, reference_image_id,
                        similarity_score, rank, model_version, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'requires_human_review')
                """, (
                    sighting_id, face["face_index"], match["case_id"],
                    match["reference_image_id"], match["similarity_score"],
                    match["rank"], match["model_version"]
                ))
                matches_generated += 1

                if match["similarity_score"] >= SIMILARITY_THRESHOLD_HIGH:
                    high_similarity_alerts.append(match)

        # 5. Create notifications for investigators if high similarity found
        if high_similarity_alerts:
            # Notify investigators
            cursor.execute("SELECT id FROM users WHERE role IN ('investigator', 'admin')")
            investigator_ids = [u["id"] for u in cursor.fetchall()]
            for inv_id in investigator_ids:
                cursor.execute("""
                    INSERT INTO notifications (user_id, title, message, category, link_url)
                    VALUES (?, ?, ?, 'match_alert', ?)
                """, (
                    inv_id,
                    f"High Similarity Lead: Sighting {receipt_no}",
                    f"Sighting at {location_name} matched registered case with score {high_similarity_alerts[0]['similarity_score']:.2f}. Review required.",
                    f"/review/{sighting_id}"
                ))

        # 6. Audit log entry
        cursor.execute("""
            INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
            VALUES ('Public Reporter', 'SIGHTING_SUBMITTED', 'sightings', ?, ?)
        """, (
            str(sighting_id),
            json.dumps({
                "receipt_no": receipt_no,
                "faces_detected": len(detected_faces),
                "candidates_ranked": matches_generated
            })
        ))

        # Return public receipt only (PRD FR-05 requirement: no confidential case data disclosed)
        return {
            "success": True,
            "receipt_no": receipt_no,
            "sighting_date": sighting_date,
            "location_name": location_name,
            "faces_detected_count": len(detected_faces),
            "status": "Submitted and queued for authorized investigator review",
            "message": "Thank you for submitting this sighting. Authorized investigators will review potential matches. Keep this receipt number for your records."
        }

@router.get("")
def list_sightings(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Lists sightings with candidate lead counts and status (investigators only)."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT s.*, sm.file_path, sm.faces_detected_count,
               (SELECT COUNT(*) FROM candidate_matches WHERE sighting_id = s.id) AS candidate_count,
               (SELECT MAX(similarity_score) FROM candidate_matches WHERE sighting_id = s.id) AS top_similarity
        FROM sightings s
        LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
        WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND s.status = ?"
            params.append(status_filter)

        query += " ORDER BY s.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.get("/{sighting_id}")
def get_sighting_details(
    sighting_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Returns sighting details with candidate matches for review."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sightings WHERE id = ?", (sighting_id,))
        sighting = cursor.fetchone()
        if not sighting:
            raise HTTPException(status_code=404, detail="Sighting not found")

        cursor.execute("SELECT * FROM sighting_media WHERE sighting_id = ?", (sighting_id,))
        media = cursor.fetchone()

        cursor.execute("""
            SELECT cm.id AS match_id, cm.sighting_face_index, cm.similarity_score, cm.rank,
                   cm.model_version, cm.status AS match_status,
                   c.id AS case_id, c.reference_no, c.full_name, c.age, c.gender,
                   c.last_seen_date, c.last_seen_location, c.status AS case_status,
                   ri.file_path AS reference_photo_path,
                   (SELECT COUNT(*) FROM reviews WHERE candidate_match_id = cm.id) AS review_count
            FROM candidate_matches cm
            JOIN cases c ON cm.case_id = c.id
            JOIN reference_images ri ON cm.reference_image_id = ri.id
            WHERE cm.sighting_id = ?
            ORDER BY cm.similarity_score DESC
        """, (sighting_id,))
        candidates = [dict(c) for c in cursor.fetchall()]

        result = dict(sighting)
        result["media"] = dict(media) if media else None
        result["candidates"] = candidates
        return result

@router.get("/lookup/{receipt_no}", response_model=SightingLookupResponse)
def public_lookup_receipt(receipt_no: str):
    """
    Public lookup by receipt number.
    Returns general verification status without leaking case names, suspect details,
    or match scores (fulfills privacy standard in PRD FR-05 & Design Spec).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT receipt_no, sighting_date, sighting_time, location_name, status, created_at FROM sightings WHERE receipt_no = ?",
            (receipt_no.strip(),)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sighting receipt not found. Please verify your receipt reference number.")

        return {
            "receipt_no": row["receipt_no"],
            "sighting_date": row["sighting_date"],
            "sighting_time": row["sighting_time"],
            "location_name": row["location_name"],
            "status": row["status"],
            "submitted_at": str(row["created_at"])
        }
