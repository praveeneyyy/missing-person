import json
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Query
from backend.database import get_db
from backend.auth import require_role
from backend.config import SIGHTINGS_DIR, SIMILARITY_THRESHOLD_HIGH, DEFAULT_TOP_K
from backend.face_engine import face_engine
from backend.models import SightingLookupResponse, SightingStatusUpdateRequest

router = APIRouter(prefix="/api/v1/sightings", tags=["Sighting Portal"])

STATUS_METADATA = {
    "pending_review": {
        "label": "Screened & Queued for Officer Review",
        "notice": "Your sighting has been biometrically screened and is waiting in the active queue for assigned investigators."
    },
    "in_review": {
        "label": "Under Active Investigation",
        "notice": "An authorized investigator is actively examining this lead and comparing evidence against registered records."
    },
    "verified_match": {
        "label": "Field Follow-up Dispatched",
        "notice": "Law enforcement has verified this lead. Operational response teams have been notified."
    },
    "escalated": {
        "label": "Priority Field Verification in Progress",
        "notice": "This lead has been escalated for immediate priority verification by command staff."
    },
    "rejected": {
        "label": "Reviewed & Classified as Inconclusive",
        "notice": "Officers have examined the lead and concluded it does not match active cases or lacks sufficient evidence."
    }
}

def generate_receipt_no(cursor) -> str:
    """Generates unique monotonic receipt identifier like STG-2026-0001."""
    cursor.execute("""
        SELECT receipt_no FROM sightings
        WHERE receipt_no LIKE 'STG-2026-%'
        ORDER BY id DESC LIMIT 1
    """)
    last_row = cursor.fetchone()
    if last_row and last_row["receipt_no"]:
        try:
            last_num = int(last_row["receipt_no"].split("-")[-1])
            next_num = last_num + 1
        except Exception:
            next_num = 1
    else:
        cursor.execute("SELECT COUNT(*) AS cnt FROM sightings")
        next_num = cursor.fetchone()["cnt"] + 1
    return f"STG-2026-{next_num:04d}"

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
    # 1. Privacy consent validation
    if not consent_given:
        raise HTTPException(
            status_code=400,
            detail="Notice and privacy terms acknowledgement is required to submit a sighting."
        )

    # 2. Date validation
    cleaned_date = sighting_date.strip()
    try:
        parsed_date = datetime.strptime(cleaned_date, "%Y-%m-%d").date()
        today = datetime.now().date()
        if parsed_date > today + timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail=f"Sighting date '{cleaned_date}' cannot be in the future."
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format '{cleaned_date}'. Please use YYYY-MM-DD."
        )

    # 3. Location landmark validation
    cleaned_location = location_name.strip() if location_name else ""
    if len(cleaned_location) < 2:
        raise HTTPException(
            status_code=400,
            detail="Location landmark or description must be at least 2 characters long."
        )

    # 4. GPS Coordinates validation (if provided)
    if latitude is not None and not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=400, detail="Latitude must be between -90.0 and 90.0 degrees.")
    if longitude is not None and not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=400, detail="Longitude must be between -180.0 and 180.0 degrees.")

    # 5. Photographic and video evidence file validation
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="A photographic or surveillance video evidence file is required.")

    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    image_exts = [".jpg", ".jpeg", ".png", ".webp"]
    video_exts = [".mp4", ".avi", ".mov", ".mkv", ".webm"]

    is_video = (file_ext in video_exts) or (bool(file.content_type) and file.content_type.startswith("video/"))
    is_image = (file_ext in image_exts) or (bool(file.content_type) and file.content_type.startswith("image/"))

    if not is_video and not is_image:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: Images (JPEG, PNG, WebP) or Video (MP4, AVI, MOV, MKV, WebM)."
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    max_limit = 50 * 1024 * 1024 if is_video else 15 * 1024 * 1024
    if len(content) > max_limit:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum {'50 MB surveillance video' if is_video else '15 MB image'} limit."
        )

    with get_db() as conn:
        cursor = conn.cursor()
        receipt_no = generate_receipt_no(cursor)

        # 6. Save sighting record
        cursor.execute("""
            INSERT INTO sightings (
                receipt_no, sighting_date, sighting_time, location_name,
                latitude, longitude, description, reporter_name, reporter_phone,
                reporter_email, consent_given, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
        """, (
            receipt_no, cleaned_date, sighting_time, cleaned_location,
            latitude, longitude, description, reporter_name, reporter_phone,
            reporter_email, 1 if consent_given else 0
        ))
        sighting_id = cursor.lastrowid

        # 7. Save media file securely to storage/sightings
        prefix = "sight_video" if is_video else "sight"
        stored_name = f"{prefix}_{sighting_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        saved_path = SIGHTINGS_DIR / stored_name
        with open(saved_path, "wb") as f:
            f.write(content)

        rel_path = f"storage/sightings/{stored_name}"

        # 8. Biometric Multi-Stage Face & Video Processing
        query_faces = []

        if is_video:
            try:
                video_res = face_engine.process_sighting_video(str(saved_path))
                tracklets = video_res["tracklets"]
                faces_count = len(tracklets)
                faces_metadata_payload = {
                    "media_type": "video",
                    "metadata": video_res["video_metadata"],
                    "tracklets": tracklets
                }
                faces_metadata_json = json.dumps(faces_metadata_payload)
                for t in tracklets:
                    query_faces.append({
                        "face_index": t["tracklet_id"],
                        "embedding": t["embedding"],
                        "exemplar_timestamp": t["exemplar_timestamp_str"]
                    })
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video decoding and frame processing failed: {str(e)}"
                )
        else:
            try:
                img = face_engine.decode_image(content)
                if img is None:
                    raise ValueError("Decoded image buffer is None")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image decoding failed: file is corrupted or not a valid image format ({str(e)})."
                )

            detected_faces = face_engine.process_sighting_image(img)
            faces_count = len(detected_faces)
            faces_metadata_json = json.dumps([{
                "face_index": f["face_index"],
                "bbox": f["bbox"],
                "confidence": f["confidence"]
            } for f in detected_faces])

            for f in detected_faces:
                query_faces.append({
                    "face_index": f["face_index"],
                    "embedding": f["embedding"]
                })

        # Save media asset record
        cursor.execute("""
            INSERT INTO sighting_media (
                sighting_id, file_path, original_filename,
                faces_detected_count, faces_metadata_json
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            sighting_id, rel_path, file.filename or ("sighting.mp4" if is_video else "sighting.jpg"),
            faces_count,
            faces_metadata_json
        ))

        matches_generated = 0
        high_similarity_alerts = []

        # 9. Perform vector candidate retrieval if faces are present
        if len(query_faces) > 0:
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

            for qf in query_faces:
                query_emb = qf["embedding"]
                top_matches = face_engine.rank_candidates(query_emb, enrolled_cases, top_k=DEFAULT_TOP_K)

                for match in top_matches:
                    cursor.execute("""
                        INSERT INTO candidate_matches (
                            sighting_id, sighting_face_index, case_id, reference_image_id,
                            similarity_score, rank, model_version, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'requires_human_review')
                    """, (
                        sighting_id, qf["face_index"], match["case_id"],
                        match["reference_image_id"], match["similarity_score"],
                        match["rank"], match["model_version"]
                    ))
                    matches_generated += 1

                    if match["similarity_score"] >= SIMILARITY_THRESHOLD_HIGH:
                        high_similarity_alerts.append(match)

            # 10. Create notifications for investigators if high similarity lead detected
            if high_similarity_alerts:
                cursor.execute("SELECT id FROM users WHERE role IN ('investigator', 'admin')")
                investigator_ids = [u["id"] for u in cursor.fetchall()]
                for inv_id in investigator_ids:
                    cursor.execute("""
                        INSERT INTO notifications (user_id, title, message, category, link_url)
                        VALUES (?, ?, ?, 'match_alert', ?)
                    """, (
                        inv_id,
                        f"High Similarity Lead: Sighting {receipt_no}",
                        f"Sighting at {cleaned_location} matched registered case with score {high_similarity_alerts[0]['similarity_score']:.2f}. Review required.",
                        f"/review/{sighting_id}"
                    ))

        # 11. Audit log entry
        cursor.execute("""
            INSERT INTO audit_logs (actor_name, action, resource_type, resource_id, details_json)
            VALUES ('Public Reporter', 'SIGHTING_SUBMITTED', 'sightings', ?, ?)
        """, (
            str(sighting_id),
            json.dumps({
                "receipt_no": receipt_no,
                "media_type": "video" if is_video else "image",
                "faces_detected": faces_count,
                "candidates_ranked": matches_generated
            })
        ))

        # 12. Contextual citizen feedback message
        if is_video:
            if faces_count > 0:
                user_message = (
                    f"Thank you for submitting this surveillance video sighting. System extracted and deduplicated "
                    f"{faces_count} person tracklet(s) across the video timeline, and queued biometric leads for investigator review."
                )
                submission_status = "Submitted and queued for authorized investigator review"
            else:
                user_message = (
                    "Thank you for submitting this video sighting. No automated facial biometrics could be extracted from sampled video frames; "
                    "this report has been securely queued as an observational lead for manual officer review."
                )
                submission_status = "Observation lead queued for manual investigator assessment"
        else:
            if faces_count > 0:
                user_message = (
                    f"Thank you for submitting this sighting. System detected {faces_count} face(s) and queued "
                    f"biometric leads for authorized investigator verification. Keep this receipt number for your records."
                )
                submission_status = "Submitted and queued for authorized investigator review"
            else:
                user_message = (
                    "Thank you for submitting this sighting. No automated facial biometric could be detected in this photo; "
                    "this report has been securely queued as an observational lead for manual officer review."
                )
                submission_status = "Observation lead queued for manual investigator assessment"

        return {
            "success": True,
            "sighting_id": sighting_id,
            "receipt_no": receipt_no,
            "sighting_date": cleaned_date,
            "location_name": cleaned_location,
            "faces_detected_count": faces_count,
            "media_type": "video" if is_video else "image",
            "matches_generated": matches_generated,
            "status": submission_status,
            "message": user_message
        }

@router.get("")
def list_sightings(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
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

        if search:
            query += " AND (s.receipt_no LIKE ? OR s.location_name LIKE ? OR s.description LIKE ?)"
            s_term = f"%{search.strip()}%"
            params.extend([s_term, s_term, s_term])

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

@router.patch("/{sighting_id}/status")
def update_sighting_status(
    sighting_id: int,
    payload: SightingStatusUpdateRequest,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Updates the operational lifecycle status of a sighting.
    Requires mandatory written rationale for auditability and AI governance.
    """
    valid_statuses = ["pending_review", "in_review", "verified_match", "escalated", "rejected"]
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Must be one of: {', '.join(valid_statuses)}"
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sightings WHERE id = ?", (sighting_id,))
        sighting = cursor.fetchone()
        if not sighting:
            raise HTTPException(status_code=404, detail="Sighting not found")

        old_status = sighting["status"]
        cursor.execute("UPDATE sightings SET status = ? WHERE id = ?", (payload.status, sighting_id))

        # Log audit trail
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'SIGHTING_STATUS_UPDATED', 'sightings', ?, ?)
        """, (
            user["id"], user["full_name"], str(sighting_id),
            json.dumps({
                "receipt_no": sighting["receipt_no"],
                "old_status": old_status,
                "new_status": payload.status,
                "rationale": payload.rationale
            })
        ))

        return {
            "success": True,
            "sighting_id": sighting_id,
            "receipt_no": sighting["receipt_no"],
            "previous_status": old_status,
            "current_status": payload.status,
            "updated_by": user["full_name"],
            "message": f"Sighting status successfully updated to '{payload.status}'"
        }

@router.delete("/{sighting_id}", status_code=status.HTTP_200_OK)
def delete_sighting(
    sighting_id: int,
    user: dict = Depends(require_role(["admin"]))
):
    """
    Administratively purges a sighting and its associated media/matches.
    Restricted to Administrator role.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sightings WHERE id = ?", (sighting_id,))
        sighting = cursor.fetchone()
        if not sighting:
            raise HTTPException(status_code=404, detail="Sighting not found")

        # Find media files to remove from filesystem
        cursor.execute("SELECT file_path FROM sighting_media WHERE sighting_id = ?", (sighting_id,))
        media_rows = cursor.fetchall()
        for m in media_rows:
            try:
                p = Path(m["file_path"])
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        # Delete database records (cascaded by SQLite schema)
        cursor.execute("DELETE FROM sightings WHERE id = ?", (sighting_id,))

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'SIGHTING_DELETED', 'sightings', ?, ?)
        """, (
            user["id"], user["full_name"], str(sighting_id),
            json.dumps({"receipt_no": sighting["receipt_no"], "location": sighting["location_name"]})
        ))

        return {
            "success": True,
            "message": f"Sighting {sighting['receipt_no']} and all associated media have been deleted."
        }

@router.get("/lookup/{receipt_no}", response_model=SightingLookupResponse)
def public_lookup_receipt(receipt_no: str):
    """
    Public lookup by receipt number.
    Returns general verification status without leaking case names, suspect details,
    or match scores (fulfills privacy standard in PRD FR-05 & Design Spec).
    """
    cleaned_receipt = receipt_no.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.receipt_no, s.sighting_date, s.sighting_time, s.location_name, s.status, s.created_at,
                   sm.faces_detected_count
            FROM sightings s
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            WHERE UPPER(s.receipt_no) = UPPER(?)
        """, (cleaned_receipt,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Sighting receipt not found. Please verify your receipt reference number."
            )

        status_info = STATUS_METADATA.get(row["status"], {
            "label": row["status"].replace("_", " ").title(),
            "notice": "Investigation record is being tracked."
        })

        return {
            "receipt_no": row["receipt_no"],
            "sighting_date": row["sighting_date"],
            "sighting_time": row["sighting_time"],
            "location_name": row["location_name"],
            "status": row["status"],
            "status_label": status_info["label"],
            "faces_detected_count": row["faces_detected_count"] or 0,
            "submitted_at": str(row["created_at"]),
            "notice": status_info["notice"],
            "privacy_statement": "This public lookup provides verification status only. Suspect dossiers and facial biometrics are shielded by law enforcement privacy standards."
        }

@router.get("/{sighting_id}/video-analysis")
def get_sighting_video_analysis(
    sighting_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Returns granular forensic video telemetry for a sighting (FR-08):
    Duration, FPS, resolution, sampled frames, deduplicated face tracklets,
    frame timestamps, and correlated case leads.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.receipt_no, s.location_name, s.sighting_date, s.sighting_time,
                   sm.file_path, sm.original_filename, sm.faces_metadata_json
            FROM sightings s
            JOIN sighting_media sm ON s.id = sm.sighting_id
            WHERE s.id = ?
        """, (sighting_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sighting media record not found")

        sighting_data = dict(row)
        meta_json = sighting_data.get("faces_metadata_json") or "{}"
        try:
            parsed_meta = json.loads(meta_json)
        except Exception:
            parsed_meta = {}

        if not isinstance(parsed_meta, dict) or parsed_meta.get("media_type") != "video":
            return {
                "sighting_id": sighting_id,
                "receipt_no": sighting_data["receipt_no"],
                "is_video": False,
                "message": "Sighting media is a static photograph, not a video stream."
            }

        # Fetch candidate matches associated with each tracklet
        cursor.execute("""
            SELECT cm.id AS match_id, cm.sighting_face_index AS tracklet_id, cm.case_id,
                   cm.similarity_score, cm.rank, cm.status AS match_status,
                   c.reference_no, c.full_name, c.age, c.gender, c.status AS case_status
            FROM candidate_matches cm
            JOIN cases c ON cm.case_id = c.id
            WHERE cm.sighting_id = ?
            ORDER BY cm.similarity_score DESC
        """, (sighting_id,))
        matches = [dict(m) for m in cursor.fetchall()]

        # Map matches to tracklets
        tracklets = parsed_meta.get("tracklets", [])
        for t in tracklets:
            tid = t.get("tracklet_id")
            t["candidates"] = [m for m in matches if m.get("tracklet_id") == tid]

        return {
            "sighting_id": sighting_id,
            "receipt_no": sighting_data["receipt_no"],
            "location_name": sighting_data["location_name"],
            "sighting_date": sighting_data["sighting_date"],
            "media_url": f"/{sighting_data['file_path']}",
            "filename": sighting_data["original_filename"],
            "is_video": True,
            "video_metadata": parsed_meta.get("metadata", {}),
            "tracklets": tracklets,
            "total_tracklets": len(tracklets)
        }
