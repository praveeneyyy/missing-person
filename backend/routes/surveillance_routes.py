import os
import json
import uuid
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Query
from backend.database import get_db
from backend.models import CameraCreate, CameraResponse, AlertStatusUpdate
from backend.auth import require_role
from backend.config import SIGHTINGS_DIR, SIMILARITY_THRESHOLD_HIGH, SIMILARITY_THRESHOLD_MODERATE
from backend.face_engine import face_engine

router = APIRouter(prefix="/api/v1/surveillance", tags=["Live Surveillance & CCTV"])

@router.get("/cameras", response_model=List[CameraResponse])
def list_cameras(user: dict = Depends(require_role(["investigator", "admin"]))):
    """Lists all registered CCTV surveillance nodes with active status and alert metrics."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM surveillance_alerts WHERE camera_id = c.id) AS alert_count
            FROM cctv_cameras c
            ORDER BY c.camera_code ASC;
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("/cameras", status_code=status.HTTP_201_CREATED, response_model=CameraResponse)
def register_camera(
    camera_data: CameraCreate,
    user: dict = Depends(require_role(["admin", "investigator"]))
):
    """Registers a new CCTV surveillance node into the active monitoring network."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify unique code
        cursor.execute("SELECT id FROM cctv_cameras WHERE camera_code = ?", (camera_data.camera_code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Camera with code '{camera_data.camera_code}' already exists.")

        cursor.execute("""
            INSERT INTO cctv_cameras (camera_code, name, location_name, latitude, longitude, stream_url, fps, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            camera_data.camera_code,
            camera_data.name,
            camera_data.location_name,
            camera_data.latitude,
            camera_data.longitude,
            camera_data.stream_url,
            camera_data.fps or 15.0,
            camera_data.status or "active"
        ))
        cam_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CCTV_CAMERA_REGISTERED', 'cctv_cameras', ?, ?)
        """, (
            user["id"],
            user["full_name"],
            str(cam_id),
            json.dumps({"camera_code": camera_data.camera_code, "name": camera_data.name})
        ))

        cursor.execute("SELECT *, 0 AS alert_count FROM cctv_cameras WHERE id = ?", (cam_id,))
        return dict(cursor.fetchone())

@router.delete("/cameras/{camera_id}", status_code=status.HTTP_200_OK)
def delete_camera(camera_id: int, user: dict = Depends(require_role(["admin"]))):
    """Decommissions a CCTV surveillance node."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT camera_code FROM cctv_cameras WHERE id = ?", (camera_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Camera node not found.")

        cursor.execute("DELETE FROM cctv_cameras WHERE id = ?", (camera_id,))
        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'CCTV_CAMERA_DELETED', 'cctv_cameras', ?, ?)
        """, (
            user["id"],
            user["full_name"],
            str(camera_id),
            json.dumps({"camera_code": row["camera_code"]})
        ))
        return {"status": "success", "message": f"Camera '{row['camera_code']}' decommissioned."}

@router.post("/cameras/{camera_id}/scan-frame")
async def scan_camera_frame(
    camera_id: int,
    frame: UploadFile = File(...),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Ingests an incoming video frame from a surveillance camera feed.
    Performs face detection, 128-D embedding extraction, and multi-target
    watchlist matching against all enrolled open cases. Automatically dispatches
    high-priority alerts if cosine similarity exceeds threshold.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cctv_cameras WHERE id = ?", (camera_id,))
        camera = cursor.fetchone()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera node not found.")

    frame_bytes = await frame.read()
    if not frame_bytes:
        raise HTTPException(status_code=400, detail="Empty frame received.")

    try:
        img = face_engine.decode_image(frame_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid video frame: {str(e)}")

    faces = face_engine.detect_faces(img)
    if not faces:
        return {
            "camera_id": camera_id,
            "camera_code": camera["camera_code"],
            "timestamp": time.time(),
            "faces_detected": 0,
            "alerts_triggered": []
        }

    # Fetch active enrolled gallery
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id AS ref_id, r.case_id, r.embedding_json, c.reference_no, c.full_name
            FROM reference_images r
            JOIN cases c ON r.case_id = c.id
            WHERE c.status IN ('open', 'under_review');
        """)
        enrolled_rows = cursor.fetchall()

    gallery = []
    for r in enrolled_rows:
        try:
            gallery.append({
                "ref_id": r["ref_id"],
                "case_id": r["case_id"],
                "reference_no": r["reference_no"],
                "full_name": r["full_name"],
                "embedding": json.loads(r["embedding_json"])
            })
        except Exception:
            pass

    alerts_triggered = []

    for f_idx, face in enumerate(faces):
        emb = face_engine.extract_embedding(img, face["raw_face"])

        best_match = None
        best_sim = -1.0

        for item in gallery:
            sim = face_engine.cosine_similarity(emb, item["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_match = item

        # Evaluate against calibrated thresholds
        if best_match and best_sim >= SIMILARITY_THRESHOLD_MODERATE:
            tier = "high" if best_sim >= SIMILARITY_THRESHOLD_HIGH else "moderate"

            # Save snapshot
            snap_filename = f"cctv_{camera['camera_code']}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            snap_path = SIGHTINGS_DIR / snap_filename
            with open(snap_path, "wb") as f_out:
                f_out.write(frame_bytes)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO surveillance_alerts (camera_id, case_id, similarity_score, confidence_tier, snapshot_path, bbox_json, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'new')
                """, (
                    camera_id,
                    best_match["case_id"],
                    round(best_sim, 4),
                    tier,
                    f"/storage/sightings/{snap_filename}",
                    json.dumps(face["bbox"])
                ))
                alert_id = cursor.lastrowid

                # Notify investigator staff
                cursor.execute("""
                    INSERT INTO notifications (user_id, title, message, category, link_url)
                    VALUES (?, ?, ?, 'surveillance_match', ?)
                """, (
                    user["id"],
                    f"CCTV MATCH ALERT: {camera['camera_code']}",
                    f"Camera '{camera['name']}' matched Case {best_match['reference_no']} ({best_match['full_name']}) with score {best_sim:.3f}.",
                    f"/surveillance/alerts"
                ))

                cursor.execute("""
                    INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
                    VALUES (?, ?, 'SURVEILLANCE_ALERT_TRIGGERED', 'surveillance_alerts', ?, ?)
                """, (
                    user["id"],
                    "Surveillance Engine",
                    str(alert_id),
                    json.dumps({
                        "camera_code": camera["camera_code"],
                        "case_ref": best_match["reference_no"],
                        "similarity_score": round(best_sim, 4),
                        "confidence_tier": tier
                    })
                ))

            alerts_triggered.append({
                "alert_id": alert_id,
                "case_id": best_match["case_id"],
                "case_ref": best_match["reference_no"],
                "case_name": best_match["full_name"],
                "similarity_score": round(best_sim, 4),
                "confidence_tier": tier,
                "bbox": face["bbox"],
                "snapshot_url": f"/storage/sightings/{snap_filename}"
            })

    return {
        "camera_id": camera_id,
        "camera_code": camera["camera_code"],
        "timestamp": time.time(),
        "faces_detected": len(faces),
        "alerts_triggered": alerts_triggered
    }

@router.get("/alerts")
def list_surveillance_alerts(
    status_filter: Optional[str] = Query(None, alias="status"),
    camera_id: Optional[int] = Query(None),
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Retrieves real-time CCTV surveillance watchlist alerts."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT sa.*,
                   cam.camera_code, cam.name AS camera_name, cam.location_name AS camera_location,
                   cam.latitude AS camera_lat, cam.longitude AS camera_lng,
                   c.reference_no AS case_ref, c.full_name AS case_name, c.age AS case_age,
                   c.status AS case_status
            FROM surveillance_alerts sa
            JOIN cctv_cameras cam ON sa.camera_id = cam.id
            JOIN cases c ON sa.case_id = c.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND sa.status = ?"
            params.append(status_filter)
        if camera_id:
            query += " AND sa.camera_id = ?"
            params.append(camera_id)

        query += " ORDER BY sa.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.patch("/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: int,
    status_data: AlertStatusUpdate,
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """Updates surveillance alert disposition (acknowledged, dispatched, dismissed)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM surveillance_alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Surveillance alert not found.")

        cursor.execute("UPDATE surveillance_alerts SET status = ? WHERE id = ?", (status_data.status, alert_id))

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, actor_name, action, resource_type, resource_id, details_json)
            VALUES (?, ?, 'SURVEILLANCE_ALERT_UPDATED', 'surveillance_alerts', ?, ?)
        """, (
            user["id"],
            user["full_name"],
            str(alert_id),
            json.dumps({"old_status": row["status"], "new_status": status_data.status, "notes": status_data.notes})
        ))

        return {
            "status": "success",
            "alert_id": alert_id,
            "new_status": status_data.status,
            "message": f"Alert status updated to '{status_data.status}'."
        }

@router.post("/simulate-stream")
def simulate_surveillance_stream(
    user: dict = Depends(require_role(["investigator", "admin"]))
):
    """
    Automated surveillance stream simulator:
    Feeds reference gallery photos through active CCTV surveillance cameras to
    simulate real-time field detections and trigger live telemetry alerts.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cctv_cameras WHERE status = 'active' LIMIT 4;")
        cams = cursor.fetchall()
        if not cams:
            raise HTTPException(status_code=400, detail="No active CCTV cameras available.")

        cursor.execute("""
            SELECT r.id AS ref_id, r.case_id, r.file_path, c.reference_no, c.full_name
            FROM reference_images r
            JOIN cases c ON r.case_id = c.id
            WHERE c.status IN ('open', 'under_review')
            LIMIT 2;
        """)
        cases = cursor.fetchall()
        if not cases:
            raise HTTPException(status_code=400, detail="No active enrolled cases in gallery.")

    alerts_created = []
    base_dir = Path(__file__).resolve().parent.parent.parent

    for idx, case_item in enumerate(cases):
        cam = cams[idx % len(cams)]
        photo_rel = case_item["file_path"].lstrip("/")
        photo_abs = base_dir / photo_rel

        if not photo_abs.exists():
            continue

        with open(photo_abs, "rb") as f:
            photo_bytes = f.read()

        img = face_engine.decode_image(photo_bytes)
        faces = face_engine.detect_faces(img)
        if not faces:
            continue

        sim_score = 0.942 if idx == 0 else 0.887
        tier = "high"

        snap_filename = f"cctv_{cam['camera_code']}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        snap_path = SIGHTINGS_DIR / snap_filename
        with open(snap_path, "wb") as f_out:
            f_out.write(photo_bytes)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO surveillance_alerts (camera_id, case_id, similarity_score, confidence_tier, snapshot_path, bbox_json, status)
                VALUES (?, ?, ?, ?, ?, ?, 'new')
            """, (
                cam["id"],
                case_item["case_id"],
                sim_score,
                tier,
                f"/storage/sightings/{snap_filename}",
                json.dumps(faces[0]["bbox"])
            ))
            alert_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, category, link_url)
                VALUES (?, ?, ?, 'surveillance_match', ?)
            """, (
                user["id"],
                f"LIVE CCTV HIT: {cam['camera_code']}",
                f"Camera '{cam['name']}' captured high-confidence target for {case_item['reference_no']} ({case_item['full_name']}) - Score: {sim_score:.3f}.",
                f"/surveillance/alerts"
            ))

            alerts_created.append({
                "alert_id": alert_id,
                "camera_code": cam["camera_code"],
                "camera_name": cam["name"],
                "case_ref": case_item["reference_no"],
                "case_name": case_item["full_name"],
                "similarity_score": sim_score
            })

    return {
        "status": "success",
        "simulated_cameras": len(cams),
        "alerts_generated": len(alerts_created),
        "alerts": alerts_created
    }
