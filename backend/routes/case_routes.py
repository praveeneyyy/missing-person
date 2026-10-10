import json
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Query
from backend.database import get_db
from backend.models import CaseCreate, CaseUpdate, CaseStatusUpdate
from backend.auth import require_role
from backend.config import REFERENCES_DIR
from backend.face_engine import face_engine

router = APIRouter(prefix="/api/v1/cases", tags=["Case Management"])

def generate_case_ref(cursor) -> str:
    """Generates unique monotonic reference code like MP-2026-001."""
    cursor.execute("SELECT reference_no FROM cases WHERE reference_no LIKE 'MP-2026-%' ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    if row and row["reference_no"]:
        try:
            seq = int(row["reference_no"].split("-")[-1])
            return f"MP-2026-{seq + 1:03d}"
        except Exception:
            pass
    cursor.execute("SELECT COUNT(*) AS cnt FROM cases;")
    count = cursor.fetchone()["cnt"] + 1
    return f"MP-2026-{count:03d}"

@router.get("")
def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Lists registered missing-person cases with search and status filtering."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT c.*, u.full_name AS investigator_name,
               (SELECT COUNT(*) FROM reference_images WHERE case_id = c.id) AS reference_photo_count,
               (SELECT file_path FROM reference_images WHERE case_id = c.id LIMIT 1) AS primary_photo_path
        FROM cases c
        LEFT JOIN users u ON c.assigned_investigator_id = u.id
        WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND c.status = ?"
            params.append(status_filter)
        if search:
            query += " AND (c.full_name LIKE ? OR c.reference_no LIKE ? OR c.last_seen_location LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY c.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("", status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Registers a new missing-person case."""
    with get_db() as conn:
        cursor = conn.cursor()
        ref_no = generate_case_ref(cursor)

        cursor.execute("""
            INSERT INTO cases (
                reference_no, full_name, age, gender, last_seen_date, last_seen_time,
                last_seen_location, latitude, longitude, status, assigned_investigator_id,
                identifying_features, clothing_description, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
        """, (
            ref_no, payload.full_name, payload.age, payload.gender, payload.last_seen_date,
            payload.last_seen_time, payload.last_seen_location, payload.latitude,
            payload.longitude, user["id"], payload.identifying_features,
            payload.clothing_description, payload.notes
        ))
        case_id = cursor.lastrowid

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CASE_CREATED', 'cases', ?, ?)
        """, (
            user["id"], user["full_name"], str(case_id),
            json.dumps({"reference_no": ref_no, "name": payload.full_name})
        ))

        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        created = cursor.fetchone()
        return dict(created)

@router.get("/{case_id}")
def get_case(
    case_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Fetches comprehensive case details, reference photos, and associated sighting leads."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, u.full_name AS investigator_name
            FROM cases c
            LEFT JOIN users u ON c.assigned_investigator_id = u.id
            WHERE c.id = ?
        """, (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Fetch reference photos
        cursor.execute("""
            SELECT id, file_path, original_filename, bbox_json, model_name, model_version, created_at
            FROM reference_images WHERE case_id = ?
        """, (case_id,))
        photos = [dict(p) for p in cursor.fetchall()]

        # Fetch candidate matches linked to this case
        cursor.execute("""
            SELECT cm.id AS match_id, cm.similarity_score, cm.rank, cm.status AS match_status,
                   s.id AS sighting_id, s.receipt_no, s.sighting_date, s.location_name, s.latitude, s.longitude,
                   sm.file_path AS sighting_photo_path
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            WHERE cm.case_id = ?
            ORDER BY cm.similarity_score DESC
        """, (case_id,))
        linked_leads = [dict(lead) for lead in cursor.fetchall()]

        result = dict(case)
        result["reference_photos"] = photos
        result["linked_leads"] = linked_leads
        return result

@router.put("/{case_id}")
def update_case(
    case_id: int,
    payload: CaseUpdate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Updates case details or status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Case not found")

        fields = []
        params = []
        for key, val in payload.model_dump(exclude_unset=True).items():
            if val is not None:
                fields.append(f"{key} = ?")
                params.append(val)

        if not fields:
            return dict(existing)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(case_id)
        query = f"UPDATE cases SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, params)

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CASE_UPDATED', 'cases', ?, ?)
        """, (
            user["id"], user["full_name"], str(case_id),
            json.dumps({"updated_fields": list(payload.model_dump(exclude_unset=True).keys())})
        ))

        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        return dict(cursor.fetchone())

@router.post("/{case_id}/references")
async def add_reference_photo(
    case_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Uploads an authorized reference photograph for a missing-person case.
    Performs AI face validation (must contain exactly 1 unambiguous human face).
    Extracts and stores deep 128-D facial embedding.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, reference_no FROM cases WHERE id = ?", (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10 MB limit.")

    try:
        img = face_engine.decode_image(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Validate that exactly one face exists and compute embedding
        validation = face_engine.validate_reference_photo(img)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Save to storage
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        file_ext = ".jpg"

    stored_name = f"ref_{case_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    saved_path = REFERENCES_DIR / stored_name
    with open(saved_path, "wb") as f:
        f.write(content)

    rel_path = f"storage/references/{stored_name}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reference_images (
                case_id, file_path, original_filename, file_size, mime_type,
                face_detected, bbox_json, landmarks_json, embedding_json,
                model_name, model_version
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (
            case_id, rel_path, file.filename or "reference.jpg", len(content),
            file.content_type or "image/jpeg",
            json.dumps(validation["bbox"]),
            json.dumps(validation["landmarks"]),
            json.dumps(validation["embedding"]),
            validation["model_name"],
            validation["model_version"]
        ))
        ref_id = cursor.lastrowid

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'REFERENCE_PHOTO_ENROLLED', 'reference_images', ?, ?)
        """, (
            user["id"], user["full_name"], str(ref_id),
            json.dumps({"case_id": case_id, "bbox": validation["bbox"], "confidence": validation["confidence"]})
        ))

        return {
            "id": ref_id,
            "case_id": case_id,
            "file_path": rel_path,
            "bbox": validation["bbox"],
            "confidence": validation["confidence"],
            "model_version": validation["model_version"],
            "message": "Authorized reference photo enrolled and 128-D embedding generated successfully."
        }

@router.put("/{case_id}/status")
def update_case_status(
    case_id: int,
    payload: CaseStatusUpdate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Updates case status workflow with mandatory audit trail and status note history."""
    valid_statuses = ["draft", "open", "under_review", "resolved", "archived"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'. Must be one of: {', '.join(valid_statuses)}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        old_status = case["status"]
        status_note = payload.notes.strip() if payload.notes else f"Status transitioned from {old_status} to {payload.status}."

        existing_notes = case["notes"] or ""
        updated_notes = f"{existing_notes}\n[{old_status.upper()} -> {payload.status.upper()} by {user['full_name']}]: {status_note}".strip()

        cursor.execute("""
            UPDATE cases
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (payload.status, updated_notes, case_id))

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CASE_STATUS_CHANGED', 'cases', ?, ?)
        """, (
            user["id"], user["full_name"], str(case_id),
            json.dumps({
                "reference_no": case["reference_no"],
                "old_status": old_status,
                "new_status": payload.status,
                "notes": status_note
            })
        ))

        cursor.execute("""
            SELECT c.*, u.full_name AS investigator_name
            FROM cases c
            LEFT JOIN users u ON c.assigned_investigator_id = u.id
            WHERE c.id = ?
        """, (case_id,))
        return dict(cursor.fetchone())

@router.get("/{case_id}/bulletin")
def get_case_bulletin(
    case_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Generates official Missing Person Bulletin / Poster payload for field distribution."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, u.full_name AS investigator_name, u.badge_number AS investigator_badge
            FROM cases c
            LEFT JOIN users u ON c.assigned_investigator_id = u.id
            WHERE c.id = ?
        """, (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        cursor.execute("""
            SELECT id, file_path, original_filename, bbox_json, created_at
            FROM reference_images WHERE case_id = ?
            ORDER BY id ASC
        """, (case_id,))
        photos = [dict(p) for p in cursor.fetchall()]

        return {
            "bulletin_id": f"BULLETIN-{case['reference_no']}",
            "agency": "Tamil Nadu State Police • Missing Persons Bureau",
            "reference_no": case["reference_no"],
            "subject_name": case["full_name"],
            "age": case["age"],
            "gender": case["gender"],
            "last_seen_date": case["last_seen_date"],
            "last_seen_time": case["last_seen_time"],
            "last_seen_location": case["last_seen_location"],
            "latitude": case["latitude"],
            "longitude": case["longitude"],
            "identifying_features": case["identifying_features"] or "None recorded",
            "clothing_description": case["clothing_description"] or "None recorded",
            "status": case["status"],
            "investigating_officer": case["investigator_name"] or "Investigator on Duty",
            "badge_number": case["investigator_badge"] or "INV-44111131",
            "emergency_contact": "Emergency Control Room: 112 / 100",
            "tip_hotline": "+91 44 2844 7777 / missing-help@tnpolice.gov.in",
            "photos": photos,
            "primary_photo_path": photos[0]["file_path"] if photos else None,
            "issued_at": case["created_at"],
            "legal_notice": "Authorized law enforcement missing person bulletin. If spotted, please notify the nearest police post immediately."
        }

@router.delete("/{case_id}")
def archive_or_delete_case(
    case_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Archives a missing person case dossier with audit tracking."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        cursor.execute("""
            UPDATE cases SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (case_id,))

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CASE_ARCHIVED', 'cases', ?, ?)
        """, (
            user["id"], user["full_name"], str(case_id),
            json.dumps({"reference_no": case["reference_no"], "name": case["full_name"]})
        ))

        return {"message": f"Case {case['reference_no']} archived successfully.", "case_id": case_id, "status": "archived"}

@router.delete("/{case_id}/references/{ref_id}")
def delete_reference_photo(
    case_id: int,
    ref_id: int,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Deletes an enrolled reference photo with audit logging."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reference_images WHERE id = ? AND case_id = ?", (ref_id, case_id))
        ref = cursor.fetchone()
        if not ref:
            raise HTTPException(status_code=404, detail="Reference photo not found for this case")

        cursor.execute("SELECT COUNT(*) AS cnt FROM reference_images WHERE case_id = ?", (case_id,))
        cnt = cursor.fetchone()["cnt"]
        if cnt <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the sole reference photo of an active case. Enroll a replacement photo first."
            )

        cursor.execute("DELETE FROM reference_images WHERE id = ?", (ref_id,))

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'REFERENCE_PHOTO_DELETED', 'reference_images', ?, ?)
        """, (
            user["id"], user["full_name"], str(ref_id),
            json.dumps({"case_id": case_id, "file_path": ref["file_path"]})
        ))

        return {"message": "Reference photo deleted successfully.", "ref_id": ref_id}

